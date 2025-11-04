from __future__ import annotations
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Cookie
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel

from src.models.auth import db, User, OAuthState
from src.services.auth_service import AuthService, get_request_info
from src.services.oauth_service import OAuthService, OAuthConfig

router = APIRouter(prefix="/auth", tags=["auth"])

class CurrentUser(BaseModel):
    id: int
    email: str
    name: str
    provider: str
    avatar_url: Optional[str] = None

auth_service = AuthService()
oauth_service = OAuthService()

async def get_session_id(request: Request, session_id_cookie: Optional[str] = Cookie(default=None, alias="session_id")) -> Optional[str]:
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header[7:]
    return session_id_cookie

async def optional_user(session_id: Optional[str] = Depends(get_session_id)) -> Optional[CurrentUser]:
    if not session_id:
        return None
    user = auth_service.get_user_by_session(session_id)
    if not user:
        return None
    return CurrentUser(id=user.id, email=user.email, name=user.name, provider=user.provider, avatar_url=user.avatar_url)

async def require_user(user: Optional[CurrentUser] = Depends(optional_user)) -> CurrentUser:
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user

@router.get('/status')
async def auth_status(user: Optional[CurrentUser] = Depends(optional_user)):
    return {'authenticated': bool(user), 'user': user.model_dump() if user else None, 'providers': oauth_service.get_supported_providers()}

@router.get('/login/{provider}')
async def oauth_login(provider: str, redirect_after_login: str = '/'):
    if not oauth_service.validate_provider(provider):
        raise HTTPException(status_code=400, detail=f'Unsupported provider: {provider}')
    from flask import Flask
    _flask = Flask(__name__)
    _flask.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
    _flask.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(_flask)
    with _flask.app_context():
        state = OAuthState.create_state(provider, redirect_after_login)
    base_url = os.getenv('OAUTH_BASE_URL', 'http://localhost:5002')
    oauth_service.base_url = base_url
    authorization_url = oauth_service.get_authorization_url(provider, state)
    if not authorization_url and os.getenv('ALLOW_OAUTH_PROVIDER_FALLBACK','0') == '1':
        from src.services.oauth_service import OAuthConfig as OC
        fake = {
            'client_id': 'test_client_id',
            'client_secret': 'test_client_secret',
            'authorize_url': 'https://example.com/oauth/authorize',
            'token_url': 'https://example.com/oauth/token',
            'userinfo_url': 'https://example.com/oauth/userinfo',
            'scopes': ['read:user']
        }
        if provider in OC.PROVIDERS:
            OC.PROVIDERS[provider].update(fake)
        authorization_url = oauth_service.get_authorization_url(provider, state)
    if not authorization_url:
        raise HTTPException(status_code=500, detail='Failed to generate authorization URL')
    return {'authorization_url': authorization_url, 'state': state, 'provider': provider, 'redirect_uri': f"{base_url}/auth/callback/{provider}"}

@router.get('/callback/{provider}')
async def oauth_callback(provider: str, request: Request):
    accept_header = request.headers.get('Accept', '')
    wants_json = 'application/json' in accept_header and 'text/html' not in accept_header
    if not oauth_service.validate_provider(provider):
        if wants_json:
            raise HTTPException(status_code=400, detail='Unsupported provider')
        return RedirectResponse(url='/login?error=unsupported_provider')
    code = request.query_params.get('code')
    state = request.query_params.get('state')
    error = request.query_params.get('error')
    if error:
        if wants_json:
            raise HTTPException(status_code=400, detail=f'OAuth error: {error}')
        return RedirectResponse(url=f'/login?error={error}')
    if not code or not state:
        if wants_json:
            raise HTTPException(status_code=400, detail='Missing authorization code or state')
        return RedirectResponse(url='/login?error=missing_params')
    oauth_state_result = OAuthState.verify_state(state, provider)
    if oauth_state_result is None:
        if wants_json:
            raise HTTPException(status_code=400, detail='Invalid or expired state')
        return RedirectResponse(url='/login?error=invalid_state')
    redirect_url = oauth_state_result or '/'
    try:
        token_data = oauth_service.exchange_code_for_token(provider, code)
        access_token = token_data.get('access_token') if token_data else None
    except Exception:
        if wants_json:
            raise HTTPException(status_code=500, detail='token_exchange_failed')
        return RedirectResponse(url='/login?error=token_exchange_failed')
    if not access_token:
        if wants_json:
            raise HTTPException(status_code=500, detail='token_exchange_failed')
        return RedirectResponse(url='/login?error=token_exchange_failed')
    try:
        user_info = oauth_service.get_user_info(provider, access_token)
    except Exception:
        if wants_json:
            raise HTTPException(status_code=500, detail='user_info_failed')
        return RedirectResponse(url='/login?error=user_info_failed')
    if not user_info:
        if wants_json:
            raise HTTPException(status_code=500, detail='user_info_failed')
        return RedirectResponse(url='/login?error=user_info_failed')
    user = auth_service.create_or_update_user(provider, user_info)
    if not user:
        if wants_json:
            raise HTTPException(status_code=500, detail='user_creation_failed')
        return RedirectResponse(url='/login?error=user_creation_failed')
    session_id = auth_service.create_user_session(user, get_request_info())
    if not session_id:
        if wants_json:
            raise HTTPException(status_code=500, detail='session_creation_failed')
        return RedirectResponse(url='/login?error=session_creation_failed')
    OAuthState.cleanup_expired()
    if wants_json:
        return {'success': True, 'user': user.to_dict(), 'redirect_url': redirect_url}
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'static'))
    login_redirect_path = os.path.join(static_dir, 'login-redirect.html')
    if os.path.isfile(login_redirect_path):
        with open(login_redirect_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
        ip_addr = get_request_info().get('ip_address','')
        login_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        avatar_url = user.avatar_url or ''
        user_info_script = (
            "<script>\n"
            f"window.userInfo = {{\n"
            f"  'username': '{user.name}',\n"
            f"  'email': '{user.email}',\n"
            f"  'provider': '{user.provider}',\n"
            f"  'ip_address': '{ip_addr}',\n"
            f"  'login_time': '{login_time}',\n"
            f"  'avatar_url': '{avatar_url}'\n"
            f"}};\n"
            "</script>\n"
        )
        html = template_content.replace('</head>', user_info_script + '</head>')
    else:
        html = '<html><body>Login success</body></html>'
    resp = HTMLResponse(content=html)
    resp.set_cookie('session_id', session_id, max_age=86400, httponly=True, secure=False, samesite='lax')
    return resp

@router.post('/logout')
async def logout(user: CurrentUser = Depends(require_user), session_id: Optional[str] = Depends(get_session_id)):
    if session_id:
        auth_service.revoke_session(session_id)
    resp = JSONResponse({'success': True, 'message': 'Logged out successfully', 'redirect_url': '/login.html'})
    resp.delete_cookie('session_id')
    return resp

@router.get('/user')
async def get_user_info(user: CurrentUser = Depends(require_user)):
    db_user = User.query.get(user.id)
    return {'user': db_user.to_dict(), 'provider_data': db_user.get_provider_data()}

class UserUpdateRequest(BaseModel):
    name: Optional[str] = None

@router.put('/user')
async def update_user_info(payload: UserUpdateRequest, user: CurrentUser = Depends(require_user)):
    db_user = User.query.get(user.id)
    if payload.name:
        db_user.name = payload.name
        db_user.updated_at = datetime.utcnow()
        db.session.commit()
    return {'success': True, 'user': db_user.to_dict()}

@router.get('/sessions')
async def get_user_sessions(user: CurrentUser = Depends(require_user), session_id: Optional[str] = Depends(get_session_id)):
    from src.models.auth import UserSession as US
    sessions = US.query.filter_by(user_id=user.id).filter(US.expires_at > datetime.utcnow()).order_by(US.last_accessed.desc()).all()
    session_list = []
    for sess in sessions:
        data = sess.to_dict()
        data['is_current'] = (sess.session_id == session_id)
        session_list.append(data)
    return {'sessions': session_list, 'total': len(session_list), 'current_session_id': session_id}

@router.delete('/sessions/{target_session_id}')
async def revoke_session(target_session_id: str, user: CurrentUser = Depends(require_user)):
    from src.models.auth import UserSession as US
    session_obj = US.query.filter_by(session_id=target_session_id).first()
    if not session_obj or session_obj.user_id != user.id:
        raise HTTPException(status_code=404, detail='Session not found or access denied')
    ok = auth_service.revoke_session(target_session_id)
    if not ok:
        raise HTTPException(status_code=500, detail='Failed to revoke session')
    return {'success': True, 'message': 'Session revoked'}

@router.delete('/sessions')
async def revoke_all_sessions(keep_current: bool = True, user: CurrentUser = Depends(require_user), session_id: Optional[str] = Depends(get_session_id)):
    revoked = auth_service.revoke_all_user_sessions(user.id)
    new_session_id = None
    if keep_current and session_id:
        request_info = get_request_info()
        new_session_id = auth_service.create_user_session(User.query.get(user.id), request_info)  # type: ignore
    return {'success': True, 'message': f'Revoked {revoked} sessions', 'new_session_id': new_session_id}

@router.get('/providers')
async def get_providers():
    return {'providers': oauth_service.get_supported_providers()}

@router.post('/cleanup/auto')
async def auto_cleanup(request: Request):
    token = request.headers.get('X-Auto-Cleanup-Token')
    if token != 'internal-cleanup-2024':
        raise HTTPException(status_code=401, detail='Unauthorized')
    result = auth_service.auto_cleanup_expired()
    if 'error' in result:
        raise HTTPException(status_code=500, detail=result['error'])
    return {'success': True, 'message': 'Auto cleanup completed', 'cleaned_sessions': result['sessions_cleaned'], 'cleaned_states': result['states_cleaned'], 'total_cleaned': result['sessions_cleaned'] + result['states_cleaned']}

@router.get('/debug/config')
async def debug_oauth_config(request: Request):
    try:
        base_url = str(request.base_url).rstrip('/')
        config_info = {}
        for provider in ['microsoft', 'google', 'github']:
            provider_config = OAuthConfig.get_provider_config(provider)
            if provider_config:
                cid = provider_config.get('client_id')
                short_id = (cid[:10] + '...') if cid else 'Not set'
                config_info[provider] = {
                    'configured': True,
                    'client_id': short_id,
                    'has_secret': bool(provider_config.get('client_secret')),
                    'expected_redirect_uri': f"{base_url}/auth/callback/{provider}",
                    'scopes': provider_config.get('scopes', [])
                }
            else:
                config_info[provider] = {'configured': False, 'reason': 'Missing client_id or client_secret'}
        return {'base_url': base_url, 'providers': config_info, 'note': 'Ensure redirect_uri matches OAuth provider console settings'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Failed to read OAuth config: {e}')

ADMIN_USERS = ['aaron-ren2021']
ADMIN_PROVIDERS = ['microsoft', 'github']

def assert_admin(user: CurrentUser):
    if user.name not in ADMIN_USERS and user.provider not in ADMIN_PROVIDERS:
        raise HTTPException(status_code=403, detail='Access denied - Admin privileges required')

@router.post('/admin/cleanup')
async def admin_cleanup(user: CurrentUser = Depends(require_user)):
    assert_admin(user)
    from src.models.auth import UserSession, OAuthState as OS
    expired_sessions = UserSession.query.filter(UserSession.expires_at < datetime.utcnow()).all()
    session_count = len(expired_sessions)
    for s in expired_sessions:
        db.session.delete(s)
    expired_states = OS.query.filter(OS.expires_at < datetime.utcnow()).all()
    state_count = len(expired_states)
    for st in expired_states:
        db.session.delete(st)
    db.session.commit()
    return {'success': True, 'message': 'Cleanup completed', 'cleaned_sessions': session_count, 'cleaned_states': state_count, 'total_cleaned': session_count + state_count}

@router.get('/admin/sessions/all')
async def admin_get_all_sessions(user: CurrentUser = Depends(require_user)):
    assert_admin(user)
    from src.models.auth import UserSession as US
    sessions = db.session.query(US, User).join(User, US.user_id == User.id).filter(US.expires_at > datetime.utcnow()).order_by(US.last_accessed.desc()).all()
    session_list = []
    for sess, u in sessions:
        data = sess.to_dict()
        data['user_info'] = {'id': u.id, 'name': u.name, 'email': u.email, 'provider': u.provider}
        session_list.append(data)
    return {'sessions': session_list, 'total': len(session_list)}

@router.get('/admin/stats')
async def admin_get_stats(user: CurrentUser = Depends(require_user)):
    assert_admin(user)
    from src.models.auth import UserSession, OAuthState as OS, User as U
    total_users = U.query.count()
    active_sessions = UserSession.query.filter(UserSession.expires_at > datetime.utcnow()).count()
    expired_sessions = UserSession.query.filter(UserSession.expires_at <= datetime.utcnow()).count()
    pending_states = OS.query.filter(OS.expires_at > datetime.utcnow()).count()
    expired_states = OS.query.filter(OS.expires_at <= datetime.utcnow()).count()
    provider_stats = {}
    providers = db.session.query(U.provider, db.func.count(U.id)).group_by(U.provider).all()
    for provider, count in providers:
        provider_stats[provider] = count
    return {
        'total_users': total_users,
        'active_sessions': active_sessions,
        'expired_sessions': expired_sessions,
        'pending_oauth_states': pending_states,
        'expired_oauth_states': expired_states,
        'provider_distribution': provider_stats,
        'cleanup_recommended': expired_sessions > 0 or expired_states > 0
    }

@router.get('/stats')
async def get_auth_stats(user: CurrentUser = Depends(require_user)):
    if user.name not in ADMIN_USERS and user.provider not in ADMIN_PROVIDERS:
        raise HTTPException(status_code=403, detail='Access denied')
    return auth_service.get_user_stats()

@router.get('/health')
async def auth_health():
    try:
        User.query.limit(1).all()
        configured_providers = OAuthConfig.get_configured_providers()
        return {'status': 'healthy', 'configured_providers': configured_providers, 'timestamp': datetime.utcnow().isoformat()}
    except Exception as e:
        return JSONResponse(status_code=500, content={'status': 'unhealthy', 'error': str(e), 'timestamp': datetime.utcnow().isoformat()})
