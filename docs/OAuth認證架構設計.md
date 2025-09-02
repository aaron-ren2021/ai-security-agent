# OAuth認證架構設計

## 🎯 設計目標

為AI資訊安全RAG Chat機器人系統加入多重OAuth認證機制，支援：
- Microsoft Entra ID (Azure AD)
- Google OAuth 2.0
- GitHub OAuth

## 🏗️ 系統架構

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端登入頁    │    │   Flask Auth    │    │  OAuth提供商    │
│   Login UI      │◄──►│   服務層        │◄──►│  MS/Google/GH   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   用戶資料庫    │
                       │   SQLite/MySQL  │
                       │   Session管理   │
                       └─────────────────┘
```

## 🔐 OAuth流程設計

### 1. 認證流程
```
用戶 → 選擇OAuth提供商 → 重定向到提供商 → 用戶授權 → 
回調到系統 → 取得Access Token → 獲取用戶資訊 → 
建立/更新用戶記錄 → 建立Session → 重定向到主頁
```

### 2. 支援的OAuth提供商

#### Microsoft Entra ID
- **端點**: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/`
- **範圍**: `openid profile email User.Read`
- **用戶資訊**: Microsoft Graph API
- **特色**: 企業級身份管理，支援多租戶

#### Google OAuth 2.0
- **端點**: `https://accounts.google.com/o/oauth2/v2/auth`
- **範圍**: `openid profile email`
- **用戶資訊**: Google People API
- **特色**: 廣泛使用，高可靠性

#### GitHub OAuth
- **端點**: `https://github.com/login/oauth/authorize`
- **範圍**: `user:email read:user`
- **用戶資訊**: GitHub API v4
- **特色**: 開發者友好，技術社群首選

## 📊 資料庫設計

### 用戶表 (users)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    provider VARCHAR(50) NOT NULL,  -- 'microsoft', 'google', 'github'
    provider_id VARCHAR(255) NOT NULL,
    provider_data JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### OAuth狀態表 (oauth_states)
```sql
CREATE TABLE oauth_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state VARCHAR(255) UNIQUE NOT NULL,
    provider VARCHAR(50) NOT NULL,
    redirect_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

### 會話表 (sessions)
```sql
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id INTEGER NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## 🔧 技術實現

### 1. 依賴套件
```python
# OAuth相關
authlib==1.2.1
requests-oauthlib==1.3.1

# 加密與安全
cryptography==41.0.7
PyJWT==2.8.0

# 資料庫
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.0.5

# Session管理
Flask-Session==0.5.0
redis==5.0.1
```

### 2. 配置管理
```python
# OAuth配置
OAUTH_PROVIDERS = {
    'microsoft': {
        'client_id': os.getenv('MICROSOFT_CLIENT_ID'),
        'client_secret': os.getenv('MICROSOFT_CLIENT_SECRET'),
        'tenant_id': os.getenv('MICROSOFT_TENANT_ID', 'common'),
        'authorize_url': 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize',
        'token_url': 'https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token',
        'userinfo_url': 'https://graph.microsoft.com/v1.0/me',
        'scopes': ['openid', 'profile', 'email', 'User.Read']
    },
    'google': {
        'client_id': os.getenv('GOOGLE_CLIENT_ID'),
        'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'),
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'userinfo_url': 'https://www.googleapis.com/oauth2/v2/userinfo',
        'scopes': ['openid', 'profile', 'email']
    },
    'github': {
        'client_id': os.getenv('GITHUB_CLIENT_ID'),
        'client_secret': os.getenv('GITHUB_CLIENT_SECRET'),
        'authorize_url': 'https://github.com/login/oauth/authorize',
        'token_url': 'https://github.com/login/oauth/access_token',
        'userinfo_url': 'https://api.github.com/user',
        'scopes': ['user:email', 'read:user']
    }
}
```

## 🛡️ 安全考量

### 1. CSRF保護
- 使用隨機生成的state參數
- 驗證回調時的state參數
- 設定state過期時間

### 2. Session安全
- 使用安全的Session ID
- 設定適當的過期時間
- 支援Session撤銷

### 3. 資料保護
- 敏感資料加密存儲
- 最小權限原則
- 定期清理過期資料

### 4. 錯誤處理
- 不洩露敏感資訊
- 記錄安全事件
- 優雅的錯誤回應

## 🔄 API設計

### 認證相關端點
```
GET  /auth/login                    # 顯示登入頁面
GET  /auth/login/{provider}         # 開始OAuth流程
GET  /auth/callback/{provider}      # OAuth回調處理
POST /auth/logout                   # 登出
GET  /auth/user                     # 獲取當前用戶資訊
GET  /auth/status                   # 檢查認證狀態
```

### 中間件設計
```python
@require_auth
def protected_route():
    # 需要認證的路由
    pass

@optional_auth
def optional_route():
    # 可選認證的路由
    pass
```

## 🎨 前端整合

### 1. 登入介面
- 統一的登入頁面
- 三個OAuth提供商按鈕
- 美觀的UI設計
- 響應式布局

### 2. 用戶狀態管理
- 登入狀態檢查
- 用戶資訊顯示
- 登出功能
- 自動重新認證

### 3. 錯誤處理
- 友好的錯誤訊息
- 重試機制
- 回退方案

## 📱 用戶體驗

### 1. 流暢的認證流程
- 最少的點擊次數
- 清晰的狀態指示
- 快速的響應時間

### 2. 個人化體驗
- 顯示用戶頭像和姓名
- 記住用戶偏好
- 個人化設定

### 3. 多設備支援
- 桌面瀏覽器
- 行動裝置
- 平板電腦

## 🔧 部署考量

### 1. 環境變數
```bash
# Microsoft Entra ID
MICROSOFT_CLIENT_ID=your_client_id
MICROSOFT_CLIENT_SECRET=your_client_secret
MICROSOFT_TENANT_ID=your_tenant_id

# Google OAuth
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret

# GitHub OAuth
GITHUB_CLIENT_ID=your_client_id
GITHUB_CLIENT_SECRET=your_client_secret

# Session配置
SECRET_KEY=your_secret_key
SESSION_TYPE=redis
SESSION_REDIS_URL=redis://localhost:6379
```

### 2. 回調URL配置
```
開發環境: http://localhost:5002/auth/callback/{provider}
生產環境: https://yourdomain.com/auth/callback/{provider}
```

### 3. 域名白名單
- 配置允許的重定向域名
- 設定CORS政策
- SSL憑證配置

## 📊 監控與分析

### 1. 認證指標
- 登入成功率
- 各提供商使用率
- 認證失敗原因
- 用戶活躍度

### 2. 安全監控
- 異常登入檢測
- 多次失敗嘗試
- 可疑IP地址
- Session異常

### 3. 效能監控
- 認證響應時間
- API調用延遲
- 資料庫查詢效能
- 快取命中率

## 🚀 未來擴展

### 1. 更多OAuth提供商
- LinkedIn
- Twitter/X
- Apple ID
- 企業SAML

### 2. 進階功能
- 多因素認證 (MFA)
- 單一登入 (SSO)
- 聯邦身份管理
- 角色權限控制

### 3. 安全增強
- 生物識別認證
- 設備指紋識別
- 行為分析
- 風險評估

---

此架構設計確保了系統的安全性、可擴展性和用戶體驗，為AI資訊安全RAG Chat機器人提供企業級的身份認證解決方案。

