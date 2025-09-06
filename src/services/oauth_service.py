"""
OAuth認證服務 - 簡化版
處理多種OAuth提供商的認證邏輯
"""
import os
import requests
from urllib.parse import urlencode
from typing import Dict, Optional

import os
import requests
import secrets
from urllib.parse import urlencode, parse_qs, urlparse
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
import json

from authlib.integrations.requests_client import OAuth2Session
from authlib.common.errors import AuthlibBaseError

class OAuthConfig:
    """OAuth配置管理 - 簡化版"""
    
    PROVIDERS = {
        'github': {
            'client_id': os.getenv('GITHUB_CLIENT_ID'),
            'client_secret': os.getenv('GITHUB_CLIENT_SECRET'),
            'authorize_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'userinfo_url': 'https://api.github.com/user',
            'scopes': ['user:email', 'read:user']
        },
        'microsoft': {
            'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
            'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
            'tenant_id': os.getenv('MICROSOFT_TENANT_ID', 'common'),
            'authorize_url': 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize',
            'token_url': 'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
            'userinfo_url': 'https://graph.microsoft.com/v1.0/me',
            'scopes': ['openid', 'profile', 'email', 'User.Read'],
            'scope_separator': ' '
        },
        'google': {
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
            'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
            'token_url': 'https://oauth2.googleapis.com/token',
            'userinfo_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
            'scopes': ['openid', 'profile', 'email']
        }
    }
    
    @classmethod
    def get_provider_config(cls, provider: str) -> Optional[Dict]:
        """取得提供商配置"""
        config = cls.PROVIDERS.get(provider)
        if not config or not config.get('client_id') or not config.get('client_secret'):
            return None
        return config
    
    @classmethod
    def is_provider_configured(cls, provider: str) -> bool:
        """檢查提供商是否已配置"""
        config = cls.get_provider_config(provider)
        if not config:
            return False
            
        # 檢查是否為demo值
        client_id = config.get('client_id', '')
        client_secret = config.get('client_secret', '')
        
        # 如果包含demo字樣，視為未配置
        if 'demo' in client_id.lower() or 'demo' in client_secret.lower():
            return False
            
        return True
    
    @classmethod
    def get_configured_providers(cls) -> list:
        """取得已配置的提供商列表"""
        return [provider for provider in cls.PROVIDERS.keys() 
                if cls.is_provider_configured(provider)]


class OAuthService:
    """OAuth認證服務 - 簡化版"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or 'http://localhost:5002'
    
    def get_authorization_url(self, provider: str, state: str, redirect_uri: str = None) -> Optional[str]:
        """取得OAuth授權URL - 最簡易方式"""
        config = OAuthConfig.get_provider_config(provider)
        if not config:
            return None
        
        if not redirect_uri:
            # 強制使用正確的 localhost URL
            redirect_uri = f"http://localhost:5002/auth/callback/{provider}"
        
        # 對於 Microsoft，動態構建 URL
        if provider == 'microsoft':
            tenant_id = config.get('tenant_id', 'common')
            authorize_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize"
        else:
            authorize_url = config['authorize_url']
        
        # 直接構建授權URL
        params = {
            'client_id': config['client_id'],
            'redirect_uri': redirect_uri,
            'scope': ' '.join(config['scopes']),
            'state': state,
            'response_type': 'code'
        }
        
        # Microsoft特殊參數
        if provider == 'microsoft':
            params['response_mode'] = 'query'
        
        authorization_url = f"{authorize_url}?{urlencode(params)}"
        
        print(f"Generated authorization URL for {provider}: {authorization_url}")
        print(f"Using redirect URI: {redirect_uri}")
        print(f"Using tenant_id: {config.get('tenant_id', 'common')}")
        
        return authorization_url
    
    def exchange_code_for_token(self, provider: str, code: str, redirect_uri: str = None) -> Optional[Dict]:
        """交換授權碼為存取令牌 - 最簡易方式"""
        config = OAuthConfig.get_provider_config(provider)
        if not config:
            return None
        
        if not redirect_uri:
            # 強制使用正確的 localhost URL
            redirect_uri = f"http://localhost:5002/auth/callback/{provider}"
        
        # 對於 Microsoft，動態構建 token URL
        if provider == 'microsoft':
            tenant_id = config.get('tenant_id', 'common')
            token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        else:
            token_url = config['token_url']
        
        # 直接發送POST請求交換token
        data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        # Microsoft 需要的額外參數
        if provider == 'microsoft':
            data['scope'] = ' '.join(config['scopes'])
        
        headers = {'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded'}
        
        try:
            print(f"Token exchange request for {provider}:")
            print(f"URL: {token_url}")
            print(f"Data: {data}")
            
            response = requests.post(token_url, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            print(f"Token exchange successful for {provider}")
            print(f"Used redirect URI: {redirect_uri}")
            print(f"Token URL: {token_url}")
            
            return token_data
        except Exception as e:
            print(f"Token exchange error for {provider}: {e}")
            print(f"Token URL used: {token_url}")
            print(f"Response status: {getattr(response, 'status_code', 'N/A')}")
            print(f"Response text: {getattr(response, 'text', 'N/A')}")
            return None
    
    def get_user_info(self, provider: str, access_token: str) -> Optional[Dict]:
        """取得用戶資訊 - 最簡易方式"""
        config = OAuthConfig.get_provider_config(provider)
        if not config:
            return None
        
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            print(f"Fetching user info for {provider} from {config['userinfo_url']}")
            response = requests.get(config['userinfo_url'], headers=headers)
            response.raise_for_status()
            user_data = response.json()
            
            print(f"Raw user data for {provider}: {user_data}")
            
            # 統一處理用戶資訊
            if provider == 'github':
                user_info = {
                    'provider_id': str(user_data.get('id')),
                    'email': user_data.get('email') or self._get_github_email(access_token),
                    'name': user_data.get('name') or user_data.get('login'),
                    'avatar_url': user_data.get('avatar_url'),
                    'raw_data': user_data
                }
            elif provider == 'microsoft':
                # Microsoft Graph API 回應處理
                email = user_data.get('mail') or user_data.get('userPrincipalName') or user_data.get('preferredUsername')
                name = user_data.get('displayName') or user_data.get('givenName', '') + ' ' + user_data.get('surname', '')
                name = name.strip() if name else email.split('@')[0] if email else 'Unknown User'
                
                user_info = {
                    'provider_id': user_data.get('id'),
                    'email': email,
                    'name': name,
                    'avatar_url': None,  # Microsoft Graph 可能需要額外的API調用來取得頭像
                    'raw_data': user_data
                }
            elif provider == 'google':
                user_info = {
                    'provider_id': user_data.get('id'),
                    'email': user_data.get('email'),
                    'name': user_data.get('name'),
                    'avatar_url': user_data.get('picture'),
                    'raw_data': user_data
                }
            else:
                return None
            
            print(f"Processed user info for {provider}: {user_info}")
            
            # 驗證必要欄位
            if not user_info.get('provider_id') or not user_info.get('email'):
                print(f"Missing required fields for {provider}: provider_id={user_info.get('provider_id')}, email={user_info.get('email')}")
                return None
            
            return user_info
            
        except Exception as e:
            print(f"Error fetching user info for {provider}: {e}")
            print(f"Response status: {getattr(response, 'status_code', 'N/A')}")
            print(f"Response text: {getattr(response, 'text', 'N/A')}")
            return None
        except Exception as e:
            print(f"Error fetching user info from {provider}: {e}")
            return None
    
    def _get_github_email(self, access_token: str) -> Optional[str]:
        """取得GitHub email"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get('https://api.github.com/user/emails', headers=headers)
            response.raise_for_status()
            
            emails = response.json()
            # 返回第一個primary或verified的email
            for email_data in emails:
                if email_data.get('primary') or email_data.get('verified'):
                    return email_data.get('email')
            
            return emails[0].get('email') if emails else None
        except:
            return None
    
    def validate_provider(self, provider: str) -> bool:
        """驗證提供商"""
        return OAuthConfig.is_provider_configured(provider)
    
    def get_supported_providers(self) -> Dict[str, Dict]:
        """取得支援的提供商資訊"""
        providers = {}
        configured_providers = OAuthConfig.get_configured_providers()
        
        for provider_name in ['github', 'microsoft', 'google']:
            is_configured = provider_name in configured_providers
            providers[provider_name] = {
                'name': provider_name.title(),
                'display_name': self._get_provider_display_name(provider_name),
                'icon': self._get_provider_icon(provider_name),
                'configured': is_configured
            }
        
        return providers
    
    def _get_provider_display_name(self, provider: str) -> str:
        """取得提供商顯示名稱"""
        names = {'microsoft': 'Microsoft', 'google': 'Google', 'github': 'GitHub'}
        return names.get(provider, provider.title())
    
    def _get_provider_icon(self, provider: str) -> str:
        """取得提供商圖示"""
        icons = {'microsoft': '🏢', 'google': '🔍', 'github': '🐙'}
        return icons.get(provider, '🔐')


# OAuth錯誤類 - 簡化版
class OAuthError(Exception):
    """OAuth錯誤基類"""
    pass

