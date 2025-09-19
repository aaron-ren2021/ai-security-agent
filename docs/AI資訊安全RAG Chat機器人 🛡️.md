# AI資訊安全RAG Chat機器人 🛡️

基於Azure OpenAI的智慧資訊安全分析系統，現已支援企業級OAuth認證！

## ✨ 主要功能

### 🔐 OAuth認證系統
- **Microsoft Entra ID**：企業級Azure AD登入
- **Google OAuth**：Gmail帳號快速登入  
- **GitHub OAuth**：開發者友好的認證方式
- **安全會話管理**：JWT token和持久化登入狀態

### 🤖 AI安全分析
- **威脅分析Agent**：分析安全威脅和攻擊模式
- **帳號安全Agent**：評估帳號風險和異常行為
- **網路監控Agent**：診斷網路問題和設備故障
- **智慧路由Agent**：自動選擇最適合的專業Agent
- **多Agent協作**：綜合多個專家的分析結果

### 📚 RAG知識檢索
- **向量化知識庫**：支援語義搜尋和相似度匹配
- **Azure OpenAI整合**：GPT-4對話和嵌入向量
- **即時情報查詢**：結合最新威脅情報和內部規則

### 🎯 核心應用場景

#### 1. 高風險帳號智慧判斷
- **問題**：Azure AD 高風險偵測誤判率高，需人工大量過濾
- **AI解決方案**：結合情資庫、IP來源、內部規則，自動篩出真正高風險帳號
- **效益**：減少誤判處理時間，強化資安反應速度

#### 2. 網管事件智慧整合
- **問題**：網路管理系統與設備分散管理，事件判斷依賴人工經驗
- **AI解決方案**：透過MCP整合各系統，由AI智慧化分析網路事件與狀態
- **效益**：提升故障預測與快速定位能力，縮短排除時間

## 🚀 快速開始

### 1. 環境準備

```bash
# 克隆專案
git clone <repository-url>
cd ai_security_rag_bot

# 安裝依賴
uv sync
```

### 2. OAuth設定

請參考 [OAuth設定指南](OAUTH_SETUP_GUIDE.md) 完成以下設定：

1. **Microsoft Entra ID**：在Azure Portal建立應用程式註冊
2. **Google OAuth**：在Google Cloud Console建立OAuth憑證
3. **GitHub OAuth**：在GitHub Developer Settings建立OAuth App

### 3. 環境變數配置

複製並編輯環境變數檔案：

```bash
cp .env.example .env
```

填入您的配置：

```bash
# Azure OpenAI配置
OPENAI_API_KEY=your_azure_openai_api_key_here
OPENAI_API_BASE=https://your-resource-name.openai.azure.com/

# OAuth配置
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
MICROSOFT_TENANT_ID=your_microsoft_tenant_id

GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# 應用程式設定
APP_BASE_URL=http://localhost:5002
FLASK_SECRET_KEY=your-super-secret-key-change-in-production
```

### 4. 啟動應用程式

```bash
python src/main.py
```

應用程式將在 `http://localhost:5002` 啟動

### 5. 開始使用

1. 開啟瀏覽器前往 `http://localhost:5002`
2. 系統會自動重定向到登入頁面
3. 選擇您偏好的OAuth提供商登入
4. 登入成功後即可使用AI安全助手

## 📋 API文檔

### 認證API

| 端點 | 方法 | 說明 | 認證 |
|------|------|------|------|
| `/auth/status` | GET | 檢查認證狀態 | 否 |
| `/auth/providers` | GET | 取得可用OAuth提供商 | 否 |
| `/auth/login/{provider}` | GET | 開始OAuth登入流程 | 否 |
| `/auth/callback/{provider}` | GET | OAuth回調處理 | 否 |
| `/auth/logout` | POST | 登出並清除會話 | 是 |

### RAG API

| 端點 | 方法 | 說明 | 認證 |
|------|------|------|------|
| `/api/rag/chat` | POST | AI對話分析 | 是 |
| `/api/rag/health` | GET | 系統健康檢查 | 否 |
| `/api/rag/azure/test` | GET | Azure OpenAI連接測試 | 否 |

### 聊天API請求格式

```json
{
  "query": "分析最近的釣魚攻擊趨勢",
  "agent": "threat_analysis",
  "multi_agent": false,
  "context": {
    "user_id": "user123",
    "session_id": "session456"
  }
}
```

### 聊天API回應格式

```json
{
  "response": "根據最新威脅情報分析...",
  "analysis": {
    "confidence": 85,
    "risk_score": 7,
    "recommendations": "建議加強郵件安全防護..."
  },
  "agent_used": "threat_analysis",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## 🏗️ 系統架構

```
AI Security RAG Chat Bot
├── 前端 (Static HTML/CSS/JS)
│   ├── 登入頁面 (OAuth整合)
│   └── 主應用程式 (Chat介面)
├── 後端 (Flask)
│   ├── OAuth認證服務
│   ├── RAG檢索服務
│   ├── AI Agent服務
│   └── Azure OpenAI整合
├── 資料層
│   ├── SQLite資料庫 (用戶會話)
│   ├── ChromaDB向量庫 (知識檢索)
│   └── Azure OpenAI (LLM服務)
└── 安全層
    ├── JWT會話管理
    ├── OAuth 2.0認證
    └── CORS安全設定
```

## 🔧 開發指南

### 專案結構

```
ai_security_rag_bot/
├── src/
│   ├── models/
│   │   ├── auth.py              # OAuth認證模型
│   │   └── user.py              # 用戶資料模型
│   ├── services/
│   │   ├── oauth_service.py     # OAuth核心服務
│   │   ├── auth_service.py      # 認證管理服務
│   │   ├── vectorization_service.py  # 向量化服務
│   │   ├── ai_agent_service.py  # AI Agent服務
│   │   └── azure_openai_service.py   # Azure OpenAI服務
│   ├── routes/
│   │   ├── auth_api.py          # OAuth API路由
│   │   ├── rag_api.py           # RAG API路由
│   │   └── user.py              # 用戶API路由
│   ├── static/
│   │   ├── index.html           # 主應用程式
│   │   └── login.html           # OAuth登入頁面
│   └── main.py                  # Flask應用程式入口
├── .env                         # 環境變數配置
├── requirements.txt             # Python依賴
├── README.md                    # 專案說明
├── OAUTH_SETUP_GUIDE.md        # OAuth設定指南
└── DEPLOYMENT_GUIDE.md         # 部署指南
```

### 新增OAuth提供商

1. 在 `oauth_service.py` 中新增提供商配置
2. 實作認證流程和用戶資訊獲取
3. 在 `auth_api.py` 中新增對應路由
4. 更新前端登入頁面

### 新增AI Agent

1. 在 `ai_agent_service.py` 中定義新Agent
2. 實作專業領域的分析邏輯
3. 更新前端Agent選擇器
4. 新增對應的知識庫內容

## 🚀 部署指南

詳細的部署說明請參考 [部署指南](DEPLOYMENT_GUIDE.md)

### 生產環境檢查清單

- [ ] 設定強密碼的Flask Secret Key
- [ ] 配置HTTPS協議
- [ ] 更新OAuth重定向URI為生產域名
- [ ] 設定適當的CORS政策
- [ ] 配置日誌記錄
- [ ] 實施速率限制
- [ ] 設定監控和警報

## 🔒 安全性

### 認證安全
- OAuth 2.0標準實作
- JWT token會話管理
- CSRF保護機制
- 安全的cookie設定

### 資料安全
- 敏感資訊加密儲存
- API存取權限控制
- 會話超時機制
- 審計日誌記錄

### 網路安全
- HTTPS強制使用
- CORS安全設定
- 輸入驗證和清理
- SQL注入防護

## 📊 監控和日誌

### 系統監控
- 應用程式健康檢查
- OAuth認證成功率
- API回應時間
- 錯誤率統計

### 安全監控
- 登入嘗試記錄
- 異常存取模式
- API濫用檢測
- 會話異常監控

## 🤝 貢獻指南

1. Fork專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 開啟Pull Request

## 📄 授權

本專案採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 檔案

## 📞 支援

如有問題或需要支援，請：

1. 查看 [OAuth設定指南](OAUTH_SETUP_GUIDE.md)
2. 檢查 [部署指南](DEPLOYMENT_GUIDE.md)
3. 提交Issue到GitHub
4. 聯繫開發團隊

---

🎉 **立即體驗企業級AI資訊安全助手！**

具備OAuth認證、多Agent協作、RAG知識檢索的完整解決方案，為您的組織提供智慧化的資安管理體驗。
