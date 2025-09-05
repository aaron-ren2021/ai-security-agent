"""
OAuth認證API路由
處理所有認證相關的API端點
"""

from flask import Blueprint, request, jsonify, redirect, url_for, make_response, current_app, g
from urllib.parse import urlencode, parse_qs
import secrets
from datetime import datetime

from src.services.auth_service import AuthService, require_auth, optional_auth, get_current_user, get_request_info
from src.services.oauth_service import OAuthService, OAuthConfig
from src.models.auth import OAuthState, db

# 建立Blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# 初始化服務
auth_service = AuthService()
oauth_service = OAuthService()


@auth_bp.route('/status', methods=['GET'])
@optional_auth
def auth_status():
    """檢查認證狀態"""
    try:
        user = get_current_user()
        
        if user:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict(),
                'providers': oauth_service.get_supported_providers()
            })
        else:
            return jsonify({
                'authenticated': False,
                'user': None,
                'providers': oauth_service.get_supported_providers()
            })
            
    except Exception as e:
        return jsonify({'error': f'Status check failed: {str(e)}'}), 500


@auth_bp.route('/login/<provider>', methods=['GET'])
def oauth_login(provider):
    """開始OAuth登入流程"""
    try:
        # 驗證提供商
        if not oauth_service.validate_provider(provider):
            return jsonify({'error': f'Unsupported provider: {provider}'}), 400
        
        # 取得重定向URL（如果有指定）
        redirect_after_login = request.args.get('redirect', '/')
        
        # 建立CSRF狀態
        state = OAuthState.create_state(provider, redirect_after_login)
        
        # 強制使用localhost來確保與GitHub OAuth設置匹配
        base_url = "http://localhost:5002"
        oauth_service.base_url = base_url
        
        # 調試信息
        current_app.logger.info(f"OAuth login for {provider}, base_url: {base_url}")
        current_app.logger.info(f"Expected redirect URI: {base_url}/auth/callback/{provider}")
        
        authorization_url = oauth_service.get_authorization_url(provider, state)
        
        if not authorization_url:
            return jsonify({'error': 'Failed to generate authorization URL'}), 500
        
        return jsonify({
            'authorization_url': authorization_url,
            'state': state,
            'provider': provider,
            'redirect_uri': f"{base_url}/auth/callback/{provider}"  # 提供調試信息
        })
        
    except Exception as e:
        current_app.logger.error(f"Login initiation failed for {provider}: {str(e)}")
        return jsonify({'error': f'Login initiation failed: {str(e)}'}), 500


@auth_bp.route('/callback/<provider>', methods=['GET'])
def oauth_callback(provider):
    """OAuth回調處理"""
    try:
        # 檢查請求是否來自瀏覽器（需要 HTML 回應）
        accept_header = request.headers.get('Accept', '')
        wants_json = 'application/json' in accept_header and 'text/html' not in accept_header
        
        # 驗證提供商
        if not oauth_service.validate_provider(provider):
            if wants_json:
                return jsonify({'error': f'Unsupported provider: {provider}'}), 400
            else:
                return redirect(f'/?error=unsupported_provider')
        
        # 取得授權碼和狀態
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        # 檢查是否有錯誤
        if error:
            error_description = request.args.get('error_description', 'Unknown error')
            error_uri = request.args.get('error_uri', '')
            
            # Microsoft 特殊錯誤處理
            if provider == 'microsoft':
                if 'AADSTS' in error_description:
                    print(f"Microsoft Azure AD error: {error} - {error_description}")
                    if 'AADSTS700016' in error_description:
                        error_description = 'Application not found in tenant directory. Please check Microsoft app configuration.'
                    elif 'AADSTS50011' in error_description:
                        error_description = 'Invalid redirect URI. Please check Microsoft app registration.'
                    elif 'AADSTS16000' in error_description:
                        error_description = 'User account not found in tenant.'
            
            if wants_json:
                return jsonify({
                    'error': f'OAuth error: {error}',
                    'description': error_description,
                    'error_uri': error_uri
                }), 400
            else:
                return redirect(f'/?error={error}&description={error_description}')
        
        # 檢查必要參數
        if not code or not state:
            if wants_json:
                return jsonify({'error': 'Missing authorization code or state'}), 400
            else:
                return redirect('/?error=missing_parameters')
        
        # 驗證CSRF狀態
        redirect_url = OAuthState.verify_state(state, provider)
        if redirect_url is None:
            if wants_json:
                return jsonify({'error': 'Invalid or expired state parameter'}), 400
            else:
                return redirect('/?error=invalid_state')
        
        # 強制使用localhost來確保與GitHub OAuth設置匹配
        base_url = "http://localhost:5002"
        oauth_service.base_url = base_url
        
        token_data = oauth_service.exchange_code_for_token(provider, code)
        if not token_data:
            if wants_json:
                return jsonify({'error': 'Failed to exchange authorization code'}), 500
            else:
                return redirect('/?error=token_exchange_failed')
        
        # 取得用戶資訊
        access_token = token_data.get('access_token')
        user_info = oauth_service.get_user_info(provider, access_token)
        
        if not user_info:
            if wants_json:
                return jsonify({'error': 'Failed to fetch user information'}), 500
            else:
                return redirect('/?error=user_info_failed')
        
        # 建立或更新用戶
        user = auth_service.create_or_update_user(provider, user_info)
        if not user:
            if wants_json:
                return jsonify({'error': 'Failed to create or update user'}), 500
            else:
                return redirect('/?error=user_creation_failed')
        
        # 建立會話
        request_info = get_request_info()
        session_id = auth_service.create_user_session(user, request_info)
        
        if not session_id:
            if wants_json:
                return jsonify({'error': 'Failed to create user session'}), 500
            else:
                return redirect('/?error=session_creation_failed')
        
        # 準備回應
        response_data = {
            'success': True,
            'user': user.to_dict(),
            'session_id': session_id,
            'redirect_url': redirect_url
        }
        
        # 根據請求類型返回不同格式
        if wants_json:
            # API 請求，返回 JSON
            response = make_response(jsonify(response_data))
            response.set_cookie(
                'session_id',
                session_id,
                max_age=86400,  # 24小時
                httponly=True,
                secure=request.is_secure,
                samesite='Lax'
            )
            return response
        else:
            # 瀏覽器請求，返回成功頁面而不是直接重導向
            success_html = f'''
            <!DOCTYPE html>
            <html lang="zh-TW">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>登入成功 - AI資訊安全RAG Chat機器人</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                    }}
                    .success-container {{
                        background: rgba(255, 255, 255, 0.95);
                        backdrop-filter: blur(10px);
                        border-radius: 20px;
                        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                        padding: 40px;
                        text-align: center;
                        max-width: 500px;
                        width: 90%;
                    }}
                    .success-icon {{
                        width: 80px;
                        height: 80px;
                        background: linear-gradient(135deg, #28a745, #20c997);
                        border-radius: 50%;
                        margin: 0 auto 20px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 32px;
                        color: white;
                        animation: bounce 1s ease-out;
                    }}
                    @keyframes bounce {{
                        0%, 20%, 50%, 80%, 100% {{ transform: translateY(0); }}
                        40% {{ transform: translateY(-10px); }}
                        60% {{ transform: translateY(-5px); }}
                    }}
                    h1 {{
                        color: #28a745;
                        margin-bottom: 15px;
                        font-size: 24px;
                    }}
                    .user-info {{
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        text-align: left;
                    }}
                    .redirect-info {{
                        color: #666;
                        margin: 20px 0;
                        font-size: 14px;
                    }}
                    .countdown {{
                        font-weight: bold;
                        color: #667eea;
                    }}
                </style>
            </head>
            <body>
                <div class="success-container">
                    <div class="success-icon">✅</div>
                    <h1>登入成功！</h1>
                    <p>歡迎使用 AI資訊安全RAG Chat機器人</p>
                    
                    <div class="user-info">
                        <strong>登入資訊：</strong><br>
                        用戶名：{user.name}<br>
                        Email：{user.email}<br>
                        提供商：{user.provider.title()}
                    </div>
                    
                    <div class="redirect-info">
                        <p>正在跳轉到主頁面...</p>
                        <p class="countdown">3 秒後自動跳轉</p>
                    </div>
                </div>

                <script>
                    // 設定會話Cookie
                    document.cookie = "session_id={session_id}; path=/; max-age=86400; SameSite=Lax";
                    
                    // 倒數計時跳轉
                    let countdown = 3;
                    const countdownElement = document.querySelector('.countdown');
                    
                    const timer = setInterval(() => {{
                        countdown--;
                        if (countdown > 0) {{
                            countdownElement.textContent = `${{countdown}} 秒後自動跳轉`;
                        }} else {{
                            countdownElement.textContent = '正在跳轉...';
                            clearInterval(timer);
                            window.location.href = '{redirect_url}';
                        }}
                    }}, 1000);
                    
                    // 點擊頁面也可以立即跳轉
                    document.addEventListener('click', () => {{
                        clearInterval(timer);
                        window.location.href = '{redirect_url}';
                    }});
                </script>
            </body>
            </html>
            '''
            
            response = make_response(success_html)
            response.set_cookie(
                'session_id',
                session_id,
                max_age=86400,  # 24小時
                httponly=True,
                secure=request.is_secure,
                samesite='Lax'
            )
            return response
        
    except Exception as e:
        current_app.logger.error(f"OAuth callback error for {provider}: {str(e)}")
        if wants_json:
            return jsonify({'error': f'OAuth callback failed: {str(e)}'}), 500
        else:
            # 返回錯誤頁面而不是簡單重導向
            error_html = f'''
            <!DOCTYPE html>
            <html lang="zh-TW">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>登入失敗 - AI資訊安全RAG Chat機器人</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        min-height: 100vh;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        margin: 0;
                    }}
                    .error-container {{
                        background: rgba(255, 255, 255, 0.95);
                        backdrop-filter: blur(10px);
                        border-radius: 20px;
                        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
                        padding: 40px;
                        text-align: center;
                        max-width: 500px;
                        width: 90%;
                    }}
                    .error-icon {{
                        width: 80px;
                        height: 80px;
                        background: linear-gradient(135deg, #dc3545, #e74c3c);
                        border-radius: 50%;
                        margin: 0 auto 20px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        font-size: 32px;
                        color: white;
                    }}
                    h1 {{
                        color: #dc3545;
                        margin-bottom: 15px;
                        font-size: 24px;
                    }}
                    .error-details {{
                        background: #f8f9fa;
                        padding: 20px;
                        border-radius: 10px;
                        margin: 20px 0;
                        text-align: left;
                        border-left: 4px solid #dc3545;
                    }}
                    .retry-btn {{
                        background: #667eea;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 16px;
                        margin: 10px;
                        text-decoration: none;
                        display: inline-block;
                    }}
                    .retry-btn:hover {{
                        background: #5a67d8;
                    }}
                    .home-btn {{
                        background: #28a745;
                        color: white;
                        border: none;
                        padding: 12px 24px;
                        border-radius: 8px;
                        cursor: pointer;
                        font-size: 16px;
                        margin: 10px;
                        text-decoration: none;
                        display: inline-block;
                    }}
                    .home-btn:hover {{
                        background: #218838;
                    }}
                </style>
            </head>
            <body>
                <div class="error-container">
                    <div class="error-icon">❌</div>
                    <h1>登入失敗</h1>
                    <p>很抱歉，{provider.title()} 登入過程中發生錯誤</p>
                    
                    <div class="error-details">
                        <strong>錯誤詳情：</strong><br>
                        {str(e)}<br><br>
                        <strong>提供商：</strong> {provider.title()}<br>
                        <strong>時間：</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </div>
                    
                    <a href="/login.html" class="retry-btn">🔄 重試登入</a>
                    <a href="/" class="home-btn">🏠 返回首頁</a>
                </div>
            </body>
            </html>
            '''
            return make_response(error_html), 500


@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """登出"""
    try:
        user = get_current_user()
        session_id = request.headers.get('Authorization')
        
        if session_id and session_id.startswith('Bearer '):
            session_id = session_id[7:]
        
        if not session_id:
            session_id = request.cookies.get('session_id')
        
        # 撤銷會話
        if session_id:
            auth_service.revoke_session(session_id)
        
        # 檢查請求是否來自瀏覽器（需要重定向）
        accept_header = request.headers.get('Accept', '')
        wants_html = 'text/html' in accept_header
        
        if wants_html:
            # 瀏覽器請求，重定向到登入頁面
            response = make_response(redirect('/login.html'))
            response.set_cookie('session_id', '', expires=0)
            return response
        else:
            # API 請求，返回 JSON
            response = make_response(jsonify({
                'success': True,
                'message': 'Logged out successfully',
                'redirect_url': '/login.html'
            }))
            response.set_cookie('session_id', '', expires=0)
            return response
        
    except Exception as e:
        return jsonify({'error': f'Logout failed: {str(e)}'}), 500


@auth_bp.route('/user', methods=['GET'])
@require_auth
def get_user_info():
    """取得當前用戶資訊"""
    try:
        user = get_current_user()
        return jsonify({
            'user': user.to_dict(),
            'provider_data': user.get_provider_data()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get user info: {str(e)}'}), 500


@auth_bp.route('/user', methods=['PUT'])
@require_auth
def update_user_info():
    """更新用戶資訊"""
    try:
        user = get_current_user()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # 只允許更新特定欄位
        allowed_fields = ['name']
        updated = False
        
        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])
                updated = True
        
        if updated:
            user.updated_at = datetime.utcnow()
            db.session.commit()
        
        return jsonify({
            'success': True,
            'user': user.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update user info: {str(e)}'}), 500


@auth_bp.route('/sessions', methods=['GET'])
@require_auth
def get_user_sessions():
    """取得用戶的所有會話"""
    try:
        user = get_current_user()
        current_session_id = getattr(g, 'session_id', None)
        
        from src.models.auth import UserSession
        # 取得所有有效會話
        sessions = UserSession.query.filter_by(user_id=user.id).filter(
            UserSession.expires_at > datetime.utcnow()
        ).order_by(UserSession.last_accessed.desc()).all()
        
        session_list = []
        for sess in sessions:
            session_data = sess.to_dict()
            session_data['is_current'] = sess.session_id == current_session_id
            session_list.append(session_data)
        
        return jsonify({
            'sessions': session_list,
            'total': len(session_list),
            'current_session_id': current_session_id
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get sessions: {str(e)}'}), 500


@auth_bp.route('/sessions/<session_id>', methods=['DELETE'])
@require_auth
def revoke_session(session_id):
    """撤銷指定會話"""
    try:
        user = get_current_user()
        
        # 檢查會話是否屬於當前用戶
        from src.models.auth import UserSession
        session_obj = UserSession.query.filter_by(session_id=session_id).first()
        
        if not session_obj or session_obj.user_id != user.id:
            return jsonify({'error': 'Session not found or access denied'}), 404
        
        # 撤銷會話
        success = auth_service.revoke_session(session_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Session revoked'})
        else:
            return jsonify({'error': 'Failed to revoke session'}), 500
            
    except Exception as e:
        return jsonify({'error': f'Failed to revoke session: {str(e)}'}), 500


@auth_bp.route('/sessions', methods=['DELETE'])
@require_auth
def revoke_all_sessions():
    """撤銷用戶的所有會話（除了當前會話）"""
    try:
        user = get_current_user()
        current_session_id = request.headers.get('Authorization')
        
        if current_session_id and current_session_id.startswith('Bearer '):
            current_session_id = current_session_id[7:]
        
        # 撤銷所有會話
        revoked_count = auth_service.revoke_all_user_sessions(user.id)
        
        # 重新建立當前會話（如果需要保持登入）
        keep_current = request.json.get('keep_current', True) if request.json else True
        
        if keep_current and current_session_id:
            request_info = get_request_info()
            new_session_id = auth_service.create_user_session(user, request_info)
            
            return jsonify({
                'success': True,
                'message': f'Revoked {revoked_count} sessions',
                'new_session_id': new_session_id
            })
        else:
            return jsonify({
                'success': True,
                'message': f'Revoked {revoked_count} sessions'
            })
            
    except Exception as e:
        return jsonify({'error': f'Failed to revoke sessions: {str(e)}'}), 500


@auth_bp.route('/debug/config', methods=['GET'])
def debug_oauth_config():
    """調試OAuth配置"""
    try:
        from src.services.oauth_service import OAuthConfig
        
        # 取得當前基礎URL
        base_url = request.url_root.rstrip('/')
        
        config_info = {}
        for provider in ['microsoft', 'google', 'github']:
            provider_config = OAuthConfig.get_provider_config(provider)
            if provider_config:
                config_info[provider] = {
                    'configured': True,
                    'client_id': provider_config.get('client_id', 'Not set')[:10] + '...' if provider_config.get('client_id') else 'Not set',
                    'has_secret': bool(provider_config.get('client_secret')),
                    'expected_redirect_uri': f"{base_url}/auth/callback/{provider}",
                    'scopes': provider_config.get('scopes', [])
                }
            else:
                config_info[provider] = {
                    'configured': False,
                    'reason': 'Missing client_id or client_secret'
                }
        
        return jsonify({
            'base_url': base_url,
            'providers': config_info,
            'note': 'Make sure the redirect_uri matches what is configured in your OAuth provider settings'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get debug config: {str(e)}'}), 500


@auth_bp.route('/providers', methods=['GET'])
def get_providers():
    """取得支援的OAuth提供商"""
    try:
        providers = oauth_service.get_supported_providers()
        return jsonify({'providers': providers})
        
    except Exception as e:
        return jsonify({'error': f'Failed to get providers: {str(e)}'}), 500


@auth_bp.route('/cleanup/auto', methods=['POST'])
def auto_cleanup():
    """自動清理過期會話和狀態（系統端點）"""
    try:
        # 允許從內部或有特定標頭的請求調用
        auth_header = request.headers.get('X-Auto-Cleanup-Token')
        if auth_header != 'internal-cleanup-2024':
            return jsonify({'error': 'Unauthorized'}), 401
        
        # 執行清理
        result = auth_service.auto_cleanup_expired()
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 500
        
        return jsonify({
            'success': True,
            'message': 'Auto cleanup completed',
            'cleaned_sessions': result['sessions_cleaned'],
            'cleaned_states': result['states_cleaned'],
            'total_cleaned': result['sessions_cleaned'] + result['states_cleaned']
        })
        
    except Exception as e:
        return jsonify({'error': f'Auto cleanup failed: {str(e)}'}), 500


@auth_bp.route('/admin/cleanup', methods=['POST'])
@require_auth
def admin_cleanup():
    """管理員清理過期會話和狀態"""
    try:
        user = get_current_user()
        
        # 檢查管理員權限
        admin_users = ['aaron-ren2021']  # 管理員用戶名列表
        admin_providers = ['microsoft', 'github']  # 允許的提供商
        
        if user.name not in admin_users and user.provider not in admin_providers:
            return jsonify({'error': 'Access denied - Admin privileges required'}), 403
        
        # 清理過期會話
        from src.models.auth import UserSession, OAuthState, db
        
        # 清理過期的用戶會話
        expired_sessions = UserSession.query.filter(
            UserSession.expires_at < datetime.utcnow()
        ).all()
        
        session_count = len(expired_sessions)
        for session in expired_sessions:
            db.session.delete(session)
        
        # 清理過期的 OAuth 狀態
        expired_states = OAuthState.query.filter(
            OAuthState.expires_at < datetime.utcnow()
        ).all()
        
        state_count = len(expired_states)
        for state in expired_states:
            db.session.delete(state)
        
        # 提交變更
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Cleanup completed',
            'cleaned_sessions': session_count,
            'cleaned_states': state_count,
            'total_cleaned': session_count + state_count
        })
        
    except Exception as e:
        return jsonify({'error': f'Cleanup failed: {str(e)}'}), 500


@auth_bp.route('/admin/sessions/all', methods=['GET'])
@require_auth
def admin_get_all_sessions():
    """管理員查看所有用戶會話"""
    try:
        user = get_current_user()
        
        # 檢查管理員權限
        admin_users = ['aaron-ren2021']
        admin_providers = ['microsoft', 'github']
        
        if user.name not in admin_users and user.provider not in admin_providers:
            return jsonify({'error': 'Access denied - Admin privileges required'}), 403
        
        from src.models.auth import UserSession, User
        
        # 取得所有有效會話，包含用戶資訊
        sessions = db.session.query(UserSession, User).join(
            User, UserSession.user_id == User.id
        ).filter(
            UserSession.expires_at > datetime.utcnow()
        ).order_by(UserSession.last_accessed.desc()).all()
        
        session_list = []
        for sess, sess_user in sessions:
            session_data = sess.to_dict()
            session_data['user_info'] = {
                'id': sess_user.id,
                'name': sess_user.name,
                'email': sess_user.email,
                'provider': sess_user.provider
            }
            session_list.append(session_data)
        
        return jsonify({
            'sessions': session_list,
            'total': len(session_list)
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get all sessions: {str(e)}'}), 500


@auth_bp.route('/admin/stats', methods=['GET'])
@require_auth
def admin_get_stats():
    """管理員取得系統統計"""
    try:
        user = get_current_user()
        
        # 檢查管理員權限
        admin_users = ['aaron-ren2021']
        admin_providers = ['microsoft', 'github']
        
        if user.name not in admin_users and user.provider not in admin_providers:
            return jsonify({'error': 'Access denied - Admin privileges required'}), 403
        
        from src.models.auth import UserSession, OAuthState, User
        
        # 統計資料
        total_users = User.query.count()
        active_sessions = UserSession.query.filter(
            UserSession.expires_at > datetime.utcnow()
        ).count()
        expired_sessions = UserSession.query.filter(
            UserSession.expires_at <= datetime.utcnow()
        ).count()
        pending_states = OAuthState.query.filter(
            OAuthState.expires_at > datetime.utcnow()
        ).count()
        expired_states = OAuthState.query.filter(
            OAuthState.expires_at <= datetime.utcnow()
        ).count()
        
        # 按提供商統計用戶
        provider_stats = {}
        providers = db.session.query(User.provider, db.func.count(User.id)).group_by(User.provider).all()
        for provider, count in providers:
            provider_stats[provider] = count
        
        return jsonify({
            'total_users': total_users,
            'active_sessions': active_sessions,
            'expired_sessions': expired_sessions,
            'pending_oauth_states': pending_states,
            'expired_oauth_states': expired_states,
            'provider_distribution': provider_stats,
            'cleanup_recommended': expired_sessions > 0 or expired_states > 0
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500


@auth_bp.route('/stats', methods=['GET'])
@require_auth
def get_auth_stats():
    """取得認證統計（需要管理員權限）"""
    try:
        user = get_current_user()
        
        # 允許特定用戶或所有認證用戶存取統計
        admin_users = ['aaron-ren2021']  # 管理員用戶名列表
        admin_providers = ['microsoft', 'github']  # 允許的提供商
        
        if user.name not in admin_users and user.provider not in admin_providers:
            return jsonify({'error': 'Access denied'}), 403
        
        stats = auth_service.get_user_stats()
        return jsonify(stats)
        
    except Exception as e:
        return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500


# 錯誤處理
@auth_bp.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@auth_bp.errorhandler(401)
def unauthorized(error):
    return jsonify({'error': 'Unauthorized'}), 401


@auth_bp.errorhandler(403)
def forbidden(error):
    return jsonify({'error': 'Forbidden'}), 403


@auth_bp.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@auth_bp.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# 健康檢查
@auth_bp.route('/health', methods=['GET'])
def health_check():
    """認證服務健康檢查"""
    try:
        # 檢查資料庫連接
        from src.models.auth import User
        User.query.limit(1).all()
        
        # 檢查OAuth配置
        configured_providers = OAuthConfig.get_configured_providers()
        
        return jsonify({
            'status': 'healthy',
            'configured_providers': configured_providers,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

