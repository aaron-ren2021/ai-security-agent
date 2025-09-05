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

# 顯示登入頁面
@app.route('/login')
def login_page():
    """顯示自訂的登入頁面"""
    from flask import send_from_directory
    return send_from_directory(app.static_folder, 'login.html')

# catch-all 路由，用於前端 SPA 或靜態檔案
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    """根路由：檢查認證狀態決定顯示登入頁或主頁"""
    static_folder_path = app.static_folder
    
    # 檢查是否為靜態檔案請求
    if path != '' and os.path.exists(os.path.join(static_folder_path, path)):
        return send_from_directory(static_folder_path, path)
    
    # 對於根路徑或應用程式路徑，檢查認證狀態
    if path == '' or path in ['index', 'index.html', 'app', 'dashboard']:
        # 檢查是否已認證
        session_id = request.cookies.get('session_id')
        if session_id:
            # 已認證，顯示主頁
            return send_from_directory(static_folder_path, 'index.html')
        else:
            # 未認證，顯示登入頁
            return send_from_directory(static_folder_path, 'login.html')
    
    # 其他路徑回傳 SPA 頁面
    return send_from_directory(static_folder_path, 'index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)


