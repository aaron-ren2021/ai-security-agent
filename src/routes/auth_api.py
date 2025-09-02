"""
OAuth認證API路由
處理所有認證相關的API端點
"""

from flask import Blueprint, request, jsonify, redirect, url_for, make_response, current_app
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
        
        # 取得授權URL
        base_url = request.url_root.rstrip('/')
        oauth_service.base_url = base_url
        
        authorization_url = oauth_service.get_authorization_url(provider, state)
        
        if not authorization_url:
            return jsonify({'error': 'Failed to generate authorization URL'}), 500
        
        return jsonify({
            'authorization_url': authorization_url,
            'state': state,
            'provider': provider
        })
        
    except Exception as e:
        return jsonify({'error': f'Login initiation failed: {str(e)}'}), 500


@auth_bp.route('/callback/<provider>', methods=['GET'])
def oauth_callback(provider):
    """OAuth回調處理"""
    try:
        # 驗證提供商
        if not oauth_service.validate_provider(provider):
            return jsonify({'error': f'Unsupported provider: {provider}'}), 400
        
        # 取得授權碼和狀態
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        
        # 檢查是否有錯誤
        if error:
            error_description = request.args.get('error_description', 'Unknown error')
            return jsonify({
                'error': f'OAuth error: {error}',
                'description': error_description
            }), 400
        
        # 檢查必要參數
        if not code or not state:
            return jsonify({'error': 'Missing authorization code or state'}), 400
        
        # 驗證CSRF狀態
        redirect_url = OAuthState.verify_state(state, provider)
        if redirect_url is None:
            return jsonify({'error': 'Invalid or expired state parameter'}), 400
        
        # 交換授權碼為存取令牌
        base_url = request.url_root.rstrip('/')
        oauth_service.base_url = base_url
        
        token_data = oauth_service.exchange_code_for_token(provider, code)
        if not token_data:
            return jsonify({'error': 'Failed to exchange authorization code'}), 500
        
        # 取得用戶資訊
        access_token = token_data.get('access_token')
        user_info = oauth_service.get_user_info(provider, access_token)
        
        if not user_info:
            return jsonify({'error': 'Failed to fetch user information'}), 500
        
        # 建立或更新用戶
        user = auth_service.create_or_update_user(provider, user_info)
        if not user:
            return jsonify({'error': 'Failed to create or update user'}), 500
        
        # 建立會話
        request_info = get_request_info()
        session_id = auth_service.create_user_session(user, request_info)
        
        if not session_id:
            return jsonify({'error': 'Failed to create user session'}), 500
        
        # 準備回應
        response_data = {
            'success': True,
            'user': user.to_dict(),
            'session_id': session_id,
            'redirect_url': redirect_url
        }
        
        # 設定Cookie（可選）
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
        
    except Exception as e:
        return jsonify({'error': f'OAuth callback failed: {str(e)}'}), 500


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
        
        # 清除Cookie
        response = make_response(jsonify({
            'success': True,
            'message': 'Logged out successfully'
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
        
        from src.models.auth import UserSession
        sessions = UserSession.query.filter_by(user_id=user.id).filter(
            UserSession.expires_at > datetime.utcnow()
        ).all()
        
        session_list = []
        current_session_id = request.headers.get('Authorization')
        if current_session_id and current_session_id.startswith('Bearer '):
            current_session_id = current_session_id[7:]
        
        for sess in sessions:
            session_data = sess.to_dict()
            session_data['is_current'] = sess.session_id == current_session_id
            session_list.append(session_data)
        
        return jsonify({
            'sessions': session_list,
            'total': len(session_list)
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


@auth_bp.route('/providers', methods=['GET'])
def get_providers():
    """取得支援的OAuth提供商"""
    try:
        providers = oauth_service.get_supported_providers()
        return jsonify({'providers': providers})
        
    except Exception as e:
        return jsonify({'error': f'Failed to get providers: {str(e)}'}), 500


@auth_bp.route('/stats', methods=['GET'])
@require_auth
def get_auth_stats():
    """取得認證統計（需要管理員權限）"""
    try:
        # 這裡可以加入管理員權限檢查
        user = get_current_user()
        
        # 簡單的管理員檢查（可以根據需要調整）
        if user.provider != 'microsoft':  # 假設只有Microsoft用戶可以查看統計
            return jsonify({'error': 'Access denied'}), 403
        
        stats = auth_service.get_user_stats()
        cleanup_stats = auth_service.cleanup_expired_data()
        
        return jsonify({
            'user_stats': stats,
            'cleanup_stats': cleanup_stats
        })
        
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

