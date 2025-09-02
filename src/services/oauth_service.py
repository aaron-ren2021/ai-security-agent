"""
OAuth認證服務
處理多種OAuth提供商的認證邏輯
"""

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
    """OAuth配置管理"""
    
    PROVIDERS = {
        'microsoft': {
            'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
            'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
            'tenant_id': os.getenv('MICROSOFT_TENANT_ID', 'common'),
            'authorize_url': 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize',
            'token_url': 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
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
            'scopes': ['openid', 'profile', 'email'],
            'scope_separator': ' '
        },
        'github': {
            'client_id': os.getenv('GITHUB_CLIENT_ID'),
            'client_secret': os.getenv('GITHUB_CLIENT_SECRET'),
            'authorize_url': 'https://github.com/login/oauth/authorize',
            'token_url': 'https://github.com/login/oauth/access_token',
            'userinfo_url': 'https://api.github.com/user',
            'email_url': 'https://api.github.com/user/emails',
            'scopes': ['user:email', 'read:user'],
            'scope_separator': ' '
        }
    }
    
    @classmethod
    def get_provider_config(cls, provider: str) -> Optional[Dict]:
        """取得提供商配置"""
        config = cls.PROVIDERS.get(provider)
        if not config:
            return None
        
        # 檢查必要的配置
        if not config.get('client_id') or not config.get('client_secret'):
            return None
        
        # 處理Microsoft的tenant_id
        if provider == 'microsoft':
            tenant_id = config['tenant_id']
            config = config.copy()
            config['authorize_url'] = config['authorize_url'].format(tenant=tenant_id)
            config['token_url'] = config['token_url'].format(tenant=tenant_id)
        
        return config
    
    @classmethod
    def is_provider_configured(cls, provider: str) -> bool:
        """檢查提供商是否已配置"""
        return cls.get_provider_config(provider) is not None
    
    @classmethod
    def get_configured_providers(cls) -> list:
        """取得已配置的提供商列表"""
        return [provider for provider in cls.PROVIDERS.keys() 
                if cls.is_provider_configured(provider)]


class OAuthService:
    """OAuth認證服務"""
    
    def __init__(self, base_url: str = None):
        self.base_url = base_url or 'http://localhost:5002'
    
    def get_authorization_url(self, provider: str, state: str, redirect_uri: str = None) -> Optional[str]:
        """
        取得OAuth授權URL
        
        Args:
            provider: OAuth提供商名稱
            state: CSRF保護狀態參數
            redirect_uri: 重定向URI
            
        Returns:
            授權URL或None
        """
        config = OAuthConfig.get_provider_config(provider)
        if not config:
            return None
        
        if not redirect_uri:
            redirect_uri = f"{self.base_url}/auth/callback/{provider}"
        
        try:
            client = OAuth2Session(
                client_id=config['client_id'],
                redirect_uri=redirect_uri,
                scope=config['scopes']
            )
            
            authorization_url, _ = client.create_authorization_url(
                config['authorize_url'],
                state=state
            )
            
            return authorization_url
            
        except AuthlibBaseError as e:
            print(f"OAuth authorization URL error for {provider}: {e}")
            return None
    
    def exchange_code_for_token(self, provider: str, code: str, redirect_uri: str = None) -> Optional[Dict]:
        """
        交換授權碼為存取令牌
        
        Args:
            provider: OAuth提供商名稱
            code: 授權碼
            redirect_uri: 重定向URI
            
        Returns:
            令牌資料或None
        """
        config = OAuthConfig.get_provider_config(provider)
        if not config:
            return None
        
        if not redirect_uri:
            redirect_uri = f"{self.base_url}/auth/callback/{provider}"
        
        try:
            client = OAuth2Session(
                client_id=config['client_id'],
                redirect_uri=redirect_uri
            )
            
            token = client.fetch_token(
                config['token_url'],
                code=code,
                client_secret=config['client_secret']
            )
            
            return token
            
        except AuthlibBaseError as e:
            print(f"OAuth token exchange error for {provider}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error during token exchange for {provider}: {e}")
            return None
    
    def get_user_info(self, provider: str, access_token: str) -> Optional[Dict]:
        """
        取得用戶資訊
        
        Args:
            provider: OAuth提供商名稱
            access_token: 存取令牌
            
        Returns:
            用戶資訊或None
        """
        config = OAuthConfig.get_provider_config(provider)
        if not config:
            return None
        
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            
            # 取得基本用戶資訊
            response = requests.get(config['userinfo_url'], headers=headers)
            response.raise_for_status()
            user_data = response.json()
            
            # 根據提供商處理用戶資訊
            if provider == 'microsoft':
                return self._process_microsoft_user_data(user_data)
            elif provider == 'google':
                return self._process_google_user_data(user_data)
            elif provider == 'github':
                return self._process_github_user_data(user_data, access_token)
            
            return None
            
        except requests.RequestException as e:
            print(f"Error fetching user info from {provider}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error fetching user info from {provider}: {e}")
            return None
    
    def _process_microsoft_user_data(self, user_data: Dict) -> Dict:
        """處理Microsoft用戶資料"""
        return {
            'provider_id': user_data.get('id'),
            'email': user_data.get('mail') or user_data.get('userPrincipalName'),
            'name': user_data.get('displayName'),
            'avatar_url': None,  # Microsoft Graph需要額外API調用取得頭像
            'raw_data': user_data
        }
    
    def _process_google_user_data(self, user_data: Dict) -> Dict:
        """處理Google用戶資料"""
        return {
            'provider_id': user_data.get('id'),
            'email': user_data.get('email'),
            'name': user_data.get('name'),
            'avatar_url': user_data.get('picture'),
            'raw_data': user_data
        }
    
    def _process_github_user_data(self, user_data: Dict, access_token: str) -> Dict:
        """處理GitHub用戶資料"""
        # GitHub可能需要額外API調用取得email
        email = user_data.get('email')
        
        if not email:
            email = self._get_github_primary_email(access_token)
        
        return {
            'provider_id': str(user_data.get('id')),
            'email': email,
            'name': user_data.get('name') or user_data.get('login'),
            'avatar_url': user_data.get('avatar_url'),
            'raw_data': user_data
        }
    
    def _get_github_primary_email(self, access_token: str) -> Optional[str]:
        """取得GitHub主要email地址"""
        try:
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get('https://api.github.com/user/emails', headers=headers)
            response.raise_for_status()
            
            emails = response.json()
            # 尋找主要且已驗證的email
            for email_data in emails:
                if email_data.get('primary') and email_data.get('verified'):
                    return email_data.get('email')
            
            # 如果沒有主要email，返回第一個已驗證的
            for email_data in emails:
                if email_data.get('verified'):
                    return email_data.get('email')
            
            return None
            
        except Exception as e:
            print(f"Error fetching GitHub emails: {e}")
            return None
    
    def revoke_token(self, provider: str, access_token: str) -> bool:
        """
        撤銷存取令牌
        
        Args:
            provider: OAuth提供商名稱
            access_token: 存取令牌
            
        Returns:
            是否成功撤銷
        """
        config = OAuthConfig.get_provider_config(provider)
        if not config:
            return False
        
        try:
            if provider == 'microsoft':
                # Microsoft撤銷端點
                revoke_url = f"https://login.microsoftonline.com/{config['tenant_id']}/oauth2/v2.0/logout"
                response = requests.post(revoke_url, data={'token': access_token})
                return response.status_code == 200
                
            elif provider == 'google':
                # Google撤銷端點
                revoke_url = f"https://oauth2.googleapis.com/revoke?token={access_token}"
                response = requests.post(revoke_url)
                return response.status_code == 200
                
            elif provider == 'github':
                # GitHub撤銷端點
                headers = {'Authorization': f'Bearer {access_token}'}
                revoke_url = f"https://api.github.com/applications/{config['client_id']}/grant"
                response = requests.delete(revoke_url, headers=headers)
                return response.status_code == 204
            
            return False
            
        except Exception as e:
            print(f"Error revoking token for {provider}: {e}")
            return False
    
    def validate_provider(self, provider: str) -> bool:
        """驗證提供商是否支援且已配置"""
        return OAuthConfig.is_provider_configured(provider)
    
    def get_supported_providers(self) -> Dict[str, Dict]:
        """取得支援的提供商資訊"""
        providers = {}
        
        for provider_name in OAuthConfig.get_configured_providers():
            config = OAuthConfig.get_provider_config(provider_name)
            providers[provider_name] = {
                'name': provider_name.title(),
                'display_name': self._get_provider_display_name(provider_name),
                'icon': self._get_provider_icon(provider_name),
                'configured': True
            }
        
        return providers
    
    def _get_provider_display_name(self, provider: str) -> str:
        """取得提供商顯示名稱"""
        display_names = {
            'microsoft': 'Microsoft',
            'google': 'Google',
            'github': 'GitHub'
        }
        return display_names.get(provider, provider.title())
    
    def _get_provider_icon(self, provider: str) -> str:
        """取得提供商圖示"""
        icons = {
            'microsoft': '🏢',
            'google': '🔍',
            'github': '🐙'
        }
        return icons.get(provider, '🔐')


class OAuthError(Exception):
    """OAuth錯誤基類"""
    pass


class OAuthConfigError(OAuthError):
    """OAuth配置錯誤"""
    pass


class OAuthAuthenticationError(OAuthError):
    """OAuth認證錯誤"""
    pass


class OAuthUserInfoError(OAuthError):
    """OAuth用戶資訊錯誤"""
    pass

