"""
OAuth認證相關的資料模型
"""

from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
import secrets
import json

db = SQLAlchemy()

class User(db.Model):
    """用戶模型"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    avatar_url = Column(String(500))
    provider = Column(String(50), nullable=False)  # 'microsoft', 'google', 'github'
    provider_id = Column(String(255), nullable=False)
    provider_data = Column(Text)  # JSON格式的提供商資料
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    # 關聯
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    
    def __init__(self, email, name, provider, provider_id, avatar_url=None, provider_data=None):
        self.email = email
        self.name = name
        self.provider = provider
        self.provider_id = provider_id
        self.avatar_url = avatar_url
        self.provider_data = json.dumps(provider_data) if provider_data else None
    
    def get_provider_data(self):
        """取得提供商資料"""
        if self.provider_data:
            return json.loads(self.provider_data)
        return {}
    
    def set_provider_data(self, data):
        """設定提供商資料"""
        self.provider_data = json.dumps(data) if data else None
    
    def update_last_login(self):
        """更新最後登入時間"""
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        """轉換為字典格式"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'avatar_url': self.avatar_url,
            'provider': self.provider,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    @classmethod
    def find_by_email(cls, email):
        """根據email查找用戶"""
        return cls.query.filter_by(email=email).first()
    
    @classmethod
    def find_by_provider(cls, provider, provider_id):
        """根據提供商和提供商ID查找用戶"""
        return cls.query.filter_by(provider=provider, provider_id=provider_id).first()
    
    def __repr__(self):
        return f'<User {self.email}>'


class OAuthState(db.Model):
    """OAuth狀態模型，用於CSRF保護"""
    __tablename__ = 'oauth_states'
    
    id = Column(Integer, primary_key=True)
    state = Column(String(255), unique=True, nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    redirect_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    def __init__(self, provider, redirect_url=None, expires_in=600):
        self.state = secrets.token_urlsafe(32)
        self.provider = provider
        self.redirect_url = redirect_url
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    @classmethod
    def create_state(cls, provider, redirect_url=None):
        """建立新的OAuth狀態"""
        state = cls(provider=provider, redirect_url=redirect_url)
        db.session.add(state)
        db.session.commit()
        return state.state
    
    @classmethod
    def verify_state(cls, state, provider):
        """驗證OAuth狀態"""
        oauth_state = cls.query.filter_by(state=state, provider=provider).first()
        if not oauth_state:
            return None
        
        # 檢查是否過期
        if datetime.utcnow() > oauth_state.expires_at:
            db.session.delete(oauth_state)
            db.session.commit()
            return None
        
        redirect_url = oauth_state.redirect_url
        db.session.delete(oauth_state)
        db.session.commit()
        return redirect_url
    
    @classmethod
    def cleanup_expired(cls):
        """清理過期的狀態記錄"""
        expired_states = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for state in expired_states:
            db.session.delete(state)
        db.session.commit()
        return len(expired_states)
    
    def __repr__(self):
        return f'<OAuthState {self.provider}:{self.state[:8]}...>'


class UserSession(db.Model):
    """用戶會話模型"""
    __tablename__ = 'user_sessions'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    ip_address = Column(String(45))  # 支援IPv6
    user_agent = Column(String(500))
    
    # 關聯
    user = relationship("User", back_populates="sessions")
    
    def __init__(self, user_id, expires_in=86400, ip_address=None, user_agent=None):
        self.session_id = secrets.token_urlsafe(32)
        self.user_id = user_id
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.ip_address = ip_address
        self.user_agent = user_agent
    
    def is_valid(self):
        """檢查會話是否有效"""
        return datetime.utcnow() < self.expires_at
    
    def extend_session(self, expires_in=86400):
        """延長會話時間"""
        self.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        self.last_accessed = datetime.utcnow()
    
    @classmethod
    def create_session(cls, user_id, expires_in=86400, ip_address=None, user_agent=None):
        """建立新會話"""
        session = cls(
            user_id=user_id,
            expires_in=expires_in,
            ip_address=ip_address,
            user_agent=user_agent
        )
        db.session.add(session)
        db.session.commit()
        return session.session_id
    
    @classmethod
    def get_session(cls, session_id):
        """取得會話"""
        session = cls.query.filter_by(session_id=session_id).first()
        if not session or not session.is_valid():
            if session:
                db.session.delete(session)
                db.session.commit()
            return None
        
        # 更新最後存取時間
        session.last_accessed = datetime.utcnow()
        db.session.commit()
        return session
    
    @classmethod
    def revoke_session(cls, session_id):
        """撤銷會話"""
        session = cls.query.filter_by(session_id=session_id).first()
        if session:
            db.session.delete(session)
            db.session.commit()
            return True
        return False
    
    @classmethod
    def revoke_user_sessions(cls, user_id):
        """撤銷用戶的所有會話"""
        sessions = cls.query.filter_by(user_id=user_id).all()
        for session in sessions:
            db.session.delete(session)
        db.session.commit()
        return len(sessions)
    
    @classmethod
    def cleanup_expired(cls):
        """清理過期的會話"""
        expired_sessions = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for session in expired_sessions:
            db.session.delete(session)
        db.session.commit()
        return len(expired_sessions)
    
    def to_dict(self):
        """轉換為字典格式"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'expires_at': self.expires_at.isoformat(),
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'ip_address': self.ip_address,
            'user_agent': self.user_agent
        }
    
    def __repr__(self):
        return f'<UserSession {self.session_id[:8]}... for user {self.user_id}>'


# 資料庫初始化函數
def init_auth_db(app):
    """初始化認證資料庫"""
    db.init_app(app)
    
    with app.app_context():
        # 建立所有表格
        db.create_all()
        
        # 清理過期記錄
        OAuthState.cleanup_expired()
        UserSession.cleanup_expired()
        
        print("認證資料庫初始化完成")


# 資料庫遷移支援
def create_migration_env():
    """建立資料庫遷移環境"""
    from flask_migrate import Migrate
    
    def setup_migrate(app):
        migrate = Migrate(app, db)
        return migrate
    
    return setup_migrate

