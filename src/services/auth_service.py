"""
認證管理服務
處理用戶認證、會話管理和權限控制
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from flask import request, session, g, current_app, jsonify

from src.models.auth import User, UserSession, OAuthState, db
from src.services.oauth_service import OAuthService, OAuthError


class AuthService:
    """認證管理服務"""
    
    def __init__(self):
        self.oauth_service = OAuthService()
    
    def create_or_update_user(self, provider: str, user_info: Dict) -> Optional[User]:
        """
        建立或更新用戶
        
        Args:
            provider: OAuth提供商
            user_info: 用戶資訊
            
        Returns:
            用戶物件或None
        """
        try:
            provider_id = user_info.get('provider_id')
            email = user_info.get('email')
            name = user_info.get('name')
            
            if not provider_id or not email or not name:
                return None
            
            # 先嘗試根據提供商和ID查找用戶
            user = User.find_by_provider(provider, provider_id)
            
            if user:
                # 更新現有用戶資訊
                user.name = name
                user.avatar_url = user_info.get('avatar_url')
                user.set_provider_data(user_info.get('raw_data'))
                user.update_last_login()
                user.is_active = True
            else:
                # 檢查是否有相同email的用戶（可能來自不同提供商）
                existing_user = User.find_by_email(email)
                if existing_user:
                    # 如果email已存在但提供商不同，可以選擇合併或拒絕
                    # 這裡選擇拒絕，避免帳號混淆
                    return None
                
                # 建立新用戶
                user = User(
                    email=email,
                    name=name,
                    provider=provider,
                    provider_id=provider_id,
                    avatar_url=user_info.get('avatar_url'),
                    provider_data=user_info.get('raw_data')
                )
                user.update_last_login()
                db.session.add(user)
            
            db.session.commit()
            return user
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating/updating user: {e}")
            return None
    
    def create_user_session(self, user: User, request_info: Dict = None) -> Optional[str]:
        """
        建立用戶會話
        
        Args:
            user: 用戶物件
            request_info: 請求資訊（IP、User-Agent等）
            
        Returns:
            會話ID或None
        """
        try:
            ip_address = None
            user_agent = None
            
            if request_info:
                ip_address = request_info.get('ip_address')
                user_agent = request_info.get('user_agent')
            
            # 建立會話（預設24小時過期）
            session_id = UserSession.create_session(
                user_id=user.id,
                expires_in=86400,  # 24小時
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            return session_id
            
        except Exception as e:
            print(f"Error creating user session: {e}")
            return None
    
    def get_user_by_session(self, session_id: str) -> Optional[User]:
        """
        根據會話ID取得用戶
        
        Args:
            session_id: 會話ID
            
        Returns:
            用戶物件或None
        """
        try:
            user_session = UserSession.get_session(session_id)
            if not user_session:
                return None
            
            user = User.query.get(user_session.user_id)
            if not user or not user.is_active:
                return None
            
            return user
            
        except Exception as e:
            print(f"Error getting user by session: {e}")
            return None
    
    def revoke_session(self, session_id: str) -> bool:
        """
        撤銷會話
        
        Args:
            session_id: 會話ID
            
        Returns:
            是否成功撤銷
        """
        try:
            return UserSession.revoke_session(session_id)
        except Exception as e:
            print(f"Error revoking session: {e}")
            return False
    
    def revoke_all_user_sessions(self, user_id: int) -> int:
        """
        撤銷用戶的所有會話
        
        Args:
            user_id: 用戶ID
            
        Returns:
            撤銷的會話數量
        """
        try:
            return UserSession.revoke_user_sessions(user_id)
        except Exception as e:
            print(f"Error revoking user sessions: {e}")
            return 0
    
    def extend_session(self, session_id: str, expires_in: int = 86400) -> bool:
        """
        延長會話時間
        
        Args:
            session_id: 會話ID
            expires_in: 延長時間（秒）
            
        Returns:
            是否成功延長
        """
        try:
            user_session = UserSession.get_session(session_id)
            if not user_session:
                return False
            
            user_session.extend_session(expires_in)
            db.session.commit()
            return True
            
        except Exception as e:
            print(f"Error extending session: {e}")
            return False
    
    def cleanup_expired_data(self) -> Dict[str, int]:
        """
        清理過期資料
        
        Returns:
            清理統計
        """
        try:
            expired_states = OAuthState.cleanup_expired()
            expired_sessions = UserSession.cleanup_expired()
            
            return {
                'expired_states': expired_states,
                'expired_sessions': expired_sessions
            }
            
        except Exception as e:
            print(f"Error cleaning up expired data: {e}")
            return {'expired_states': 0, 'expired_sessions': 0}
    
    def get_user_stats(self) -> Dict[str, Any]:
        """
        取得用戶統計資訊
        
        Returns:
            統計資訊
        """
        try:
            total_users = User.query.count()
            active_users = User.query.filter_by(is_active=True).count()
            
            # 各提供商用戶數量
            provider_stats = {}
            for provider in ['microsoft', 'google', 'github']:
                count = User.query.filter_by(provider=provider, is_active=True).count()
                provider_stats[provider] = count
            
            # 最近登入用戶（7天內）
            recent_login_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_logins = User.query.filter(
                User.last_login >= recent_login_cutoff,
                User.is_active == True
            ).count()
            
            # 活躍會話數量
            active_sessions = UserSession.query.filter(
                UserSession.expires_at > datetime.utcnow()
            ).count()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'provider_stats': provider_stats,
                'recent_logins': recent_logins,
                'active_sessions': active_sessions
            }
            
        except Exception as e:
            print(f"Error getting user stats: {e}")
            return {}
    
    def deactivate_user(self, user_id: int) -> bool:
        """
        停用用戶
        
        Args:
            user_id: 用戶ID
            
        Returns:
            是否成功停用
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            user.is_active = False
            user.updated_at = datetime.utcnow()
            
            # 撤銷所有會話
            self.revoke_all_user_sessions(user_id)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error deactivating user: {e}")
            return False
    
    def reactivate_user(self, user_id: int) -> bool:
        """
        重新啟用用戶
        
        Args:
            user_id: 用戶ID
            
        Returns:
            是否成功啟用
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False
            
            user.is_active = True
            user.updated_at = datetime.utcnow()
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error reactivating user: {e}")
            return False


# Flask裝飾器和中間件
def require_auth(f):
    """需要認證的裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 檢查會話
        session_id = request.headers.get('Authorization')
        if session_id and session_id.startswith('Bearer '):
            session_id = session_id[7:]  # 移除 'Bearer ' 前綴
        
        if not session_id:
            # 也檢查cookie中的會話
            session_id = request.cookies.get('session_id')
        
        if not session_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        auth_service = AuthService()
        user = auth_service.get_user_by_session(session_id)
        
        if not user:
            return jsonify({'error': 'Invalid or expired session'}), 401
        
        # 將用戶資訊存儲到g中，供視圖函數使用
        g.current_user = user
        g.session_id = session_id
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """可選認證的裝飾器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 嘗試取得用戶資訊，但不強制要求
        session_id = request.headers.get('Authorization')
        if session_id and session_id.startswith('Bearer '):
            session_id = session_id[7:]
        
        if not session_id:
            session_id = request.cookies.get('session_id')
        
        g.current_user = None
        g.session_id = None
        
        if session_id:
            auth_service = AuthService()
            user = auth_service.get_user_by_session(session_id)
            if user:
                g.current_user = user
                g.session_id = session_id
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_current_user() -> Optional[User]:
    """取得當前用戶"""
    return getattr(g, 'current_user', None)


def get_current_session_id() -> Optional[str]:
    """取得當前會話ID"""
    return getattr(g, 'session_id', None)


def is_authenticated() -> bool:
    """檢查是否已認證"""
    return get_current_user() is not None


# 請求資訊提取器
def get_request_info() -> Dict[str, str]:
    """取得請求資訊"""
    return {
        'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', '')[:500]  # 限制長度
    }

