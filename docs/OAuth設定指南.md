# OAuth設定指南

本指南將協助您設定Microsoft Entra ID、Google OAuth和GitHub OAuth認證。

## 🏢 Microsoft Entra ID (Azure AD) 設定

### 步驟1：登入Azure Portal
1. 前往 [Azure Portal](https://portal.azure.com)
2. 使用您的Microsoft帳號登入

### 步驟2：註冊應用程式
1. 搜尋並選擇「Azure Active Directory」
2. 在左側選單選擇「應用程式註冊」
3. 點擊「新增註冊」
4. 填寫應用程式資訊：
   - **名稱**：AI Security RAG Chat Bot
   - **支援的帳戶類型**：選擇適合您組織的選項
   - **重定向URI**：
     - 類型：Web
     - URI：`http://localhost:5002/auth/callback/microsoft`

### 步驟3：取得認證資訊
1. 在應用程式概觀頁面，複製：
   - **應用程式(用戶端)識別碼** → `MICROSOFT_CLIENT_ID`
   - **目錄(租用戶)識別碼** → `MICROSOFT_TENANT_ID`

### 步驟4：建立用戶端密碼
1. 在左側選單選擇「憑證和密碼」
2. 點擊「新增用戶端密碼」
3. 輸入描述和到期時間
4. 複製密碼值 → `MICROSOFT_CLIENT_SECRET`

### 步驟5：設定API權限
1. 在左側選單選擇「API權限」
2. 點擊「新增權限」
3. 選擇「Microsoft Graph」
4. 選擇「委派權限」
5. 新增以下權限：
   - `openid`
   - `profile`
   - `email`
   - `User.Read`

## 🔍 Google OAuth 設定

### 步驟1：建立Google Cloud專案
1. 前往 [Google Cloud Console](https://console.cloud.google.com)
2. 建立新專案或選擇現有專案

### 步驟2：啟用Google+ API
1. 在左側選單選擇「API和服務」→「程式庫」
2. 搜尋「Google+ API」
3. 點擊並啟用API

### 步驟3：設定OAuth同意畫面
1. 在左側選單選擇「API和服務」→「OAuth同意畫面」
2. 選擇用戶類型（內部或外部）
3. 填寫應用程式資訊：
   - **應用程式名稱**：AI Security RAG Chat Bot
   - **用戶支援電子郵件**：您的email
   - **開發人員聯絡資訊**：您的email

### 步驟4：建立OAuth 2.0憑證
1. 在左側選單選擇「API和服務」→「憑證」
2. 點擊「建立憑證」→「OAuth 2.0用戶端ID」
3. 選擇應用程式類型：「網路應用程式」
4. 填寫資訊：
   - **名稱**：AI Security RAG Chat Bot
   - **已授權的重新導向URI**：`http://localhost:5002/auth/callback/google`

### 步驟5：取得認證資訊
1. 下載JSON檔案或複製：
   - **用戶端ID** → `GOOGLE_CLIENT_ID`
   - **用戶端密碼** → `GOOGLE_CLIENT_SECRET`

## 🐙 GitHub OAuth 設定

### 步驟1：前往GitHub設定
1. 登入GitHub
2. 前往 [Developer Settings](https://github.com/settings/developers)

### 步驟2：建立OAuth App
1. 點擊「OAuth Apps」
2. 點擊「New OAuth App」
3. 填寫應用程式資訊：
   - **Application name**：AI Security RAG Chat Bot
   - **Homepage URL**：`http://localhost:5002`
   - **Application description**：AI資訊安全RAG Chat機器人
   - **Authorization callback URL**：`http://localhost:5002/auth/callback/github`

### 步驟3：取得認證資訊
1. 建立後，複製：
   - **Client ID** → `GITHUB_CLIENT_ID`
2. 點擊「Generate a new client secret」
3. 複製密碼 → `GITHUB_CLIENT_SECRET`

## 🔧 環境變數設定

將取得的認證資訊填入`.env`檔案：

```bash
# Microsoft Entra ID (Azure AD)
MICROSOFT_CLIENT_ID=your_microsoft_client_id_here
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret_here
MICROSOFT_TENANT_ID=your_microsoft_tenant_id_here

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_client_id_here
GITHUB_CLIENT_SECRET=your_github_client_secret_here

# 應用程式設定
APP_BASE_URL=http://localhost:5002
REDIRECT_URI_BASE=http://localhost:5002/auth/callback
```

## 🚀 生產環境設定

### 更新重定向URI
當部署到生產環境時，需要更新所有OAuth應用程式的重定向URI：

#### Microsoft Entra ID
- 新增：`https://your-domain.com/auth/callback/microsoft`

#### Google OAuth
- 新增：`https://your-domain.com/auth/callback/google`

#### GitHub OAuth
- 更新：`https://your-domain.com/auth/callback/github`

### 更新環境變數
```bash
APP_BASE_URL=https://your-domain.com
REDIRECT_URI_BASE=https://your-domain.com/auth/callback
```

## ✅ 測試設定

### 1. 啟動應用程式
```bash
python src/main.py
```

### 2. 訪問登入頁面
開啟瀏覽器前往：`http://localhost:5002/login.html`

### 3. 測試各OAuth提供商
- 點擊Microsoft按鈕測試Azure AD登入
- 點擊Google按鈕測試Google登入
- 點擊GitHub按鈕測試GitHub登入

## 🔍 故障排除

### 常見問題

#### 1. 重定向URI不匹配
**錯誤**：`redirect_uri_mismatch`
**解決**：確保OAuth應用程式設定的重定向URI與應用程式中的完全一致

#### 2. 用戶端密碼無效
**錯誤**：`invalid_client`
**解決**：檢查Client ID和Client Secret是否正確

#### 3. 權限不足
**錯誤**：`insufficient_scope`
**解決**：確保OAuth應用程式有適當的權限設定

#### 4. 租用戶設定問題
**錯誤**：`AADSTS50020`
**解決**：檢查Microsoft Tenant ID是否正確

### 除錯技巧

1. **檢查環境變數**：確保所有必要的環境變數都已設定
2. **查看應用程式日誌**：檢查控制台輸出的錯誤訊息
3. **驗證重定向URI**：確保URI完全匹配，包括協議和埠號
4. **測試網路連接**：確保可以存取OAuth提供商的端點

## 📞 支援資源

### 官方文檔
- [Microsoft身份平台文檔](https://docs.microsoft.com/azure/active-directory/develop/)
- [Google OAuth 2.0文檔](https://developers.google.com/identity/protocols/oauth2)
- [GitHub OAuth文檔](https://docs.github.com/en/developers/apps/building-oauth-apps)

### 社群支援
- [Stack Overflow](https://stackoverflow.com/questions/tagged/oauth)
- [Microsoft Q&A](https://docs.microsoft.com/answers/)
- [Google開發者社群](https://developers.google.com/community)

---

完成設定後，您的AI資訊安全RAG Chat機器人將支援多種OAuth認證方式，為用戶提供安全便利的登入體驗！

