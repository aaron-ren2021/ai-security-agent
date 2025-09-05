# Microsoft Entra ID (Azure AD) OAuth App Registration 設定指南

## 1. 前往 Azure Portal
1. 訪問 https://portal.azure.com/
2. 使用您的 Microsoft 帳號登入

## 2. 導航到 App registrations
1. 在搜尋框中輸入 "App registrations"
2. 點選 "App registrations" 服務

## 3. 創建新的應用程式註冊
1. 點擊 "New registration" 按鈕
2. 填寫以下資訊：
   - **Name**: `AI Security RAG Bot`
   - **Supported account types**: 選擇 "Accounts in any organizational directory and personal Microsoft accounts (personal Microsoft accounts - e.g. Skype, Xbox)"
   - **Redirect URI**: 
     - Platform: `Web`
     - URI: `http://localhost:5002/auth/callback/microsoft`

## 4. 取得應用程式資訊
創建完成後，記錄以下資訊：
- **Application (client) ID**: 這是您的 `MICROSOFT_CLIENT_ID`
- **Directory (tenant) ID**: 這是您的 `MICROSOFT_TENANT_ID`

## 5. 創建客戶端密鑰
1. 在左側選單點選 "Certificates & secrets"
2. 點擊 "New client secret"
3. 填寫描述：`AI Security RAG Bot Secret`
4. 選擇到期時間：建議選擇 24 months
5. 點擊 "Add"
6. **重要**: 立即複製 "Value" 欄位的值，這是您的 `MICROSOFT_CLIENT_SECRET`

## 6. 設定 API 權限
1. 在左側選單點選 "API permissions"
2. 點擊 "Add a permission"
3. 選擇 "Microsoft Graph"
4. 選擇 "Delegated permissions"
5. 添加以下權限：
   - `openid`
   - `profile`
   - `email`
   - `User.Read`

## 7. 更新您的 .env 檔案
將取得的資訊更新到 .env 檔案中：

```env
# Microsoft Entra ID (Azure AD) - 您的正確設定
MICROSOFT_CLIENT_ID=您的應用程式_client_id
MICROSOFT_CLIENT_SECRET=您的客戶端密鑰
MICROSOFT_TENANT_ID=您的租戶_id
```

## 8. 驗證設定
設定完成後，重新啟動應用程式並測試 Microsoft 登入功能。

## 重要提醒
- 客戶端密鑰只會顯示一次，請立即複製並妥善保存
- 確保重定向 URI 完全符合：`http://localhost:5002/auth/callback/microsoft`
- 如果在企業環境中，可能需要管理員同意權限

## 目前您的租戶資訊
根據錯誤訊息，您的租戶是：`xCloudinfo Corp.Limited`
需要在這個租戶中創建新的應用程式註冊，或者使用個人 Microsoft 帳號創建。
