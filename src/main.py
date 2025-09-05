import os
import sys
# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, send_from_directory, make_response, redirect, request
from flask_cors import CORS
from dotenv import load_dotenv
from datetime import datetime
from src.models.auth import db
from src.routes.rag_api import rag_bp
from src.routes.auth_api import auth_bp

# 載入環境變數
load_dotenv()

app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

# 使用環境變數或預設密鑰
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'asdf#FGSgvasgf$5$WGT')

# 啟用CORS - 允許所有來源以支援部署
CORS(app, origins="*", allow_headers="*", methods="*")

# 註冊Blueprint
app.register_blueprint(rag_bp, url_prefix='/api/rag')
app.register_blueprint(auth_bp, url_prefix='/auth')

# 簡化的資料庫配置 - 使用專案根目錄的 SQLite
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
with app.app_context():
    db.create_all()

# 添加測試登入路由
@app.route('/test-login')
def test_login():
    """測試登入功能 - 創建一個臨時會話"""
    from src.services.auth_service import AuthService, get_request_info
    from src.models.auth import User, db
    
    auth_service = AuthService()
    
    # 創建或取得測試用戶
    test_user = User.query.filter_by(email='test@example.com').first()
    if not test_user:
        test_user = User(
            name='測試用戶',
            email='test@example.com',
            provider='test',
            provider_id='test123'
        )
        db.session.add(test_user)
        db.session.commit()
    
    # 創建會話
    request_info = {
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent', ''),
        'timestamp': datetime.utcnow()
    }
    session_id = auth_service.create_user_session(test_user, request_info)
    
    # 設置 Cookie 並重定向到主頁
    response = make_response(redirect('/'))
    response.set_cookie(
        'session_id',
        session_id,
        max_age=86400,  # 24小時
        httponly=True,
        secure=request.is_secure,
        samesite='Lax'
    )
    return response

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    static_folder_path = app.static_folder
    if static_folder_path is None:
            return "Static folder not configured", 404

    if path != "" and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    else:
        index_path = os.path.join(static_folder_path, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(static_folder_path, 'index.html')
        else:
            return "index.html not found", 404


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)


