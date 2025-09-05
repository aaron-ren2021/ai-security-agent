# Microsoft Entra ID (Azure AD) OAuth App 設定指南

## 步驟 1：前往 Azure Portal
1. 前往 https://portal.azure.com
2. 登入您的 Azure 帳號

## 步驟 2：建立 App Registration
1. 搜尋並選擇 "Azure Active Directory" 或 "Microsoft Entra ID"
2. 在左側選單選擇 "App registrations"
3. 點擊 "+ New registration"

## 步驟 3：填寫應用程式資訊
- **Name**: AI Security RAG Bot
- **Supported account types**: 選擇 "Accounts in any organizational directory and personal Microsoft accounts (personal Microsoft accounts and Azure AD - Multitenant)"
- **Redirect URI**: 
  - Platform: Web
  - URI: `http://localhost:5002/auth/callback/microsoft`

## 步驟 4：取得應用程式資訊
建立完成後，在 Overview 頁面記錄：
- **Application (client) ID**: 複製此值作為 MICROSOFT_CLIENT_ID
- **Directory (tenant) ID**: 複製此值作為 MICROSOFT_TENANT_ID

## 步驟 5：建立 Client Secret
1. 在左側選單選擇 "Certificates & secrets"
2. 在 "Client secrets" 區域點擊 "+ New client secret"
3. 輸入描述：AI Security RAG Bot Secret
4. 選擇到期時間（建議：24 months）
5. 點擊 "Add"
6. **立即複製 Value 欄位的值**作為 MICROSOFT_CLIENT_SECRET（此值只會顯示一次）

## 步驟 6：設定 API 權限
1. 在左側選單選擇 "API permissions"
2. 確認已有以下權限（預設會有）：
   - Microsoft Graph > openid
   - Microsoft Graph > profile
   - Microsoft Graph > email
   - Microsoft Graph > User.Read

## 步驟 7：更新 .env 檔案
將取得的值填入：
```
MICROSOFT_CLIENT_ID=你的_Application_client_ID
MICROSOFT_CLIENT_SECRET=你的_Client_Secret_Value
MICROSOFT_TENANT_ID=你的_Directory_tenant_ID
```

## 其他 OAuth 提供商設定

### GitHub OAuth App 設定
1. 前往 https://github.com/settings/applications
2. 點擊 "New OAuth App"
3. 填寫：
   - Application name: AI Security RAG Bot
   - Homepage URL: http://localhost:5002
   - Authorization callback URL: `http://localhost:5002/auth/callback/github`
   - Scopes: user:email, read:user

### Google OAuth App 設定
1. 前往 https://console.cloud.google.com/
2. 建立新專案或選擇現有專案
3. 啟用 Google+ API
4. 前往 "Credentials" > "Create Credentials" > "OAuth client ID"
5. 選擇 "Web application"
6. 填寫：
   - Name: AI Security RAG Bot
   - Authorized redirect URIs: `http://localhost:5002/auth/callback/google`
   - Scopes: openid, profile, email

## 注意事項
- 所有回呼 URL 都必須完全符合：`http://localhost:5002/auth/callback/{provider}`
- Microsoft 的 tenant_id 可以使用 "common" 來支援個人和組織帳號
- 確保在生產環境時更新為實際的網域名稱
