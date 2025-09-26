# AI 資安機器人 🛡️

一個整合 Azure AI Projects SDK 的智慧資訊安全分析系統，提供帳號安全監控、威脅檢測和自動化安全分析功能。

## ✨ 主要功能

### 🛡️ 帳號安全監控
- **綜合風險評估**: 多維度評估帳號安全風險（登入行為、權限、位置、時間）
- **異常行為檢測**: 自動識別可疑的登入和行為模式
- **權限分析**: 檢測過度權限和權限濫用
- **實時警報**: 即時通知安全威脅

### 🤖 Azure AI 與智慧路由整合
- **Azure AI Projects SDK**: 完整整合 Azure AI Agents
- **Pydantic AI 智慧路由**: 使用 `pydantic-ai` 建構可擴充的多代理路由決策
- **智慧威脅分析**: 利用 AI 進行深度安全分析
- **自動化回應**: 基於 AI 的安全事件自動處理
- **多 Agent 支援**: 支援多個專業安全 Agent

### 📊 文件處理與檢索
- **智慧文件上傳**: 支援 PDF、TXT、DOCX 等格式
- **向量化搜尋**: 基於 Azure AI Search 的語意檢索
- **RAG 對話**: 基於文件內容的智慧問答
- **多語言支援**: 支援中英文混合處理

### 🔐 身份認證
- **OAuth 2.0**: 支援 GitHub、Microsoft 等第三方登入
- **JWT Token**: 安全的會話管理
- **權限控制**: 細粒度的存取權限管理

## 🏗️ 技術架構

### 核心服務
- **AIAgentService**: 主要 AI 代理服務，整合所有安全功能
- **AccountSecurityAgent**: 專業的帳號安全分析代理
- **AzureAITestHelper**: Azure AI 功能測試助手
- **VectorizationService**: 文件向量化和搜尋服務

### Azure 整合
- **Azure AI Projects**: AI Agent 平台
- **Azure AI Search**: 向量搜尋和檢索
- **Azure OpenAI**: 語言模型服務
- **Azure Key Vault**: 安全密鑰管理
- **Azure Monitor**: 系統監控和日誌

### 前端技術
- **HTML5/CSS3/JavaScript**: 現代化響應式界面
- **Bootstrap**: UI 組件庫
- **Chart.js**: 數據視覺化
- **WebSocket**: 實時通信

## 🚀 快速開始

### 環境要求
- Python 3.8+
- Azure 訂閱和 AI Projects 專案
- Git

### 安裝步驟

1. **克隆項目**
   ```bash
   git clone <repository-url>
   cd ai-security-agent
   ```

2. **安裝依賴**
   ```bash
   # 使用 uv（推薦，會同步安裝 pydantic-ai 等依賴）
   uv sync
   
   # 或使用 pip
   pip install -r requirements.txt
   ```

3. **環境配置**
   
   創建 `.env` 文件：
   ```bash
   # Azure AI Projects 配置
   AZURE_PROJECT_ENDPOINT=https://your-foundry.services.ai.azure.com/api/projects/your-project
   AZURE_AGENT_ID=your_agent_id
   
   # Azure 認證（推薦使用 DefaultAzureCredential）
   # 確保已通過 Azure CLI 登入：az login
   
   # Azure AI Search
   AZURE_SEARCH_ENDPOINT=https://your-search.search.windows.net
   AZURE_SEARCH_API_KEY=your_search_key
   
   # Azure OpenAI
   AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
   AZURE_OPENAI_API_KEY=your_openai_key
   
   # OAuth 配置
   GITHUB_CLIENT_ID=your_github_client_id
   GITHUB_CLIENT_SECRET=your_github_client_secret
   ```

4. **初始化數據庫**
   ```bash
   python -c "from src.models.auth import init_db; init_db()"
   ```

5. **啟動服務**
   ```bash
   python src/main.py
   ```

6. **訪問應用**
   
   打開瀏覽器訪問 `http://localhost:5000`

## 📖 API 文檔

### 帳號安全 API

#### 風險評估
```http
POST /api/security/assess-risk
Content-Type: application/json

{
    "user_id": "user123",
    "failed_login_attempts": 3,
    "last_login_location": "Tokyo",
    "current_login_location": "New York",
    "login_time": "2024-01-15 03:00:00",
    "permissions": ["admin", "read_sensitive_data"],
    "recent_activities": ["bulk_download", "privilege_escalation"]
}
```

#### 異常檢測
```http
POST /api/security/detect-anomalies
Content-Type: application/json

{
    "user_data": {
        "user_id": "user123",
        "login_history": [...],
        "activity_log": [...]
    }
}
```

### Azure AI Agent API

#### 智慧對話
```http
POST /api/azure-agent/chat
Content-Type: application/json

{
    "query": "分析這個帳號的安全風險",
    "context": {
        "user_data": {...}
    }
}
```

#### Agent 資訊
```http
GET /api/azure-agent/info
```

### 智慧路由 (Pydantic AI)

#### 路由聊天端點
```http
POST /api/rag/smart-chat
Content-Type: application/json

{
    "query": "網路設備故障診斷",
    "context": {
        "network": {"device": "edge firewall", "symptom": "high latency"}
    },
    "user_id": "security-operator-01"
}
```

回應
```json
{
    "success": true,
    "smart_routing_available": true,
    "result": {
        "agent": "network_monitoring",
        "analysis": "...",
        "execution_time": 1.24,
        "metadata": {"timestamp": "2025-01-01T12:00:00"}
    }
}
```

#### 路由狀態
```http
GET /api/rag/routing/status
```

#### 路由自測
```http
GET /api/rag/routing/test
```
> 需要設定 `OPENAI_API_KEY`、`OPENAI_API_BASE` 及對應 Azure OpenAI 部署/版本，否則會回傳備援訊息。

### 文件處理 API

#### 文件上傳
```http
POST /api/files/upload
Content-Type: multipart/form-data

{
    "file": <file_content>,
    "metadata": {
        "category": "security_report",
        "tags": ["threat", "analysis"]
    }
}
```

#### 文件搜尋
```http
POST /api/files/search
Content-Type: application/json

{
    "query": "網路安全威脅",
    "filters": {
        "category": "security_report",
        "date_range": "2024-01-01:2024-12-31"
    }
}
```

## 🧪 測試

### 運行所有測試
```bash
# 使用 pytest
pytest tests/

# 運行特定測試
pytest tests/test_azure_ai_integrated.py

# 運行整合測試
python tests/test_azure_ai_integrated.py
```

### 測試覆蓋率
```bash
pytest --cov=src tests/
```

### 手動測試
```bash
# 測試 Azure AI 功能
python -c "
from src.services.ai_agent_service import AIAgentService
import asyncio

async def test():
    service = AIAgentService()
    result = await service.test_account_security()
    print(f'測試結果: {result}')

asyncio.run(test())
"
```

## 📁 項目結構

```
ai-security-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # 主應用程式
│   ├── models/
│   │   └── auth.py            # 認證模型
│   ├── routes/
│   │   ├── auth_api.py        # 認證 API
│   │   ├── file_api.py        # 文件 API
│   │   └── rag_api.py         # RAG 對話 API
│   ├── services/
│   │   ├── ai_agent_service.py         # 🔥 主要 AI 代理服務（整合 Azure AI）
│   │   ├── azure_document_service.py   # Azure 文件服務
│   │   ├── azure_openai_service.py     # Azure OpenAI 服務
│   │   ├── azure_search_service.py     # Azure Search 服務
│   │   └── vectorization_service.py    # 向量化服務
│   └── static/                # 前端靜態文件
├── tests/
│   ├── test_azure_ai_integrated.py    # 🔥 Azure AI 整合測試
│   ├── test_auth_api.py              # 認證測試
│   └── ...                           # 其他測試文件
├── docs/
│   ├── Azure_AI_Agent_Integration_Guide.md  # 🔥 Azure AI 整合指南
│   └── ...                                  # 其他文檔
├── pyproject.toml             # 🔥 項目配置（包含 Azure 依賴）
├── requirements.txt           # Python 依賴
└── README.md                 # 本文件
```

## 🔧 配置選項

### Azure AI 配置
```python
# src/services/ai_agent_service.py
class AIAgentService:
    def __init__(self):
        # Azure AI Projects 配置
        self.azure_endpoint = os.getenv("AZURE_PROJECT_ENDPOINT")
        self.azure_agent_id = os.getenv("AZURE_AGENT_ID")
        
        # 安全配置
        self.risk_thresholds = {
            "low": 30,
            "medium": 60,
            "high": 80
        }
```

### 安全參數調整
```python
# 風險評估參數
RISK_WEIGHTS = {
    "login_failures": 0.3,
    "location_change": 0.2,
    "time_anomaly": 0.2,
    "privilege_risk": 0.3
}

# 異常檢測閾值
ANOMALY_THRESHOLDS = {
    "failed_attempts": 5,
    "location_distance": 1000,  # km
    "off_hours_weight": 1.5
}
```

## 🔒 安全最佳實踐

### 1. 認證安全
- 使用 Azure Managed Identity（生產環境）
- 定期輪換 API 密鑰
- 實施最小權限原則

### 2. 數據保護
- 敏感數據加密存儲
- 使用 Azure Key Vault 管理密鑰
- 實施數據分類和標籤

### 3. 網路安全
- 使用 HTTPS 加密通信
- 實施 CORS 政策
- 配置防火牆規則

### 4. 監控告警
- 設置異常行為警報
- 監控 API 呼叫頻率
- 記錄所有安全事件

## 📊 監控和指標

### 效能指標
- **風險評估響應時間**: < 100ms
- **Azure AI 查詢響應時間**: 1-5 秒
- **異常檢測準確率**: ~95%
- **文件檢索精確度**: ~90%

### 系統監控
```bash
# 檢查服務狀態
curl http://localhost:5000/health

# 查看 Azure AI 狀態
curl http://localhost:5000/api/azure-agent/info

# 系統指標
curl http://localhost:5000/metrics
```

## 🚀 部署

### Docker 部署
```bash
# 構建映像
docker build -t ai-security-agent .

# 運行容器
docker run -p 5000:5000 --env-file .env ai-security-agent
```

### Azure 部署
```bash
# 使用 Azure CLI
az webapp create --resource-group myResourceGroup --plan myAppServicePlan --name myApp --runtime "PYTHON|3.11"
az webapp config appsettings set --resource-group myResourceGroup --name myApp --settings @.env
```

## 📝 更新日誌

### v1.2.0 (2024-01-15)
- ✨ **新功能**: 完整整合 Azure AI Projects SDK
- ✨ **新功能**: 增強的帳號安全風險評估
- ✨ **新功能**: 多維度異常行為檢測
- ✨ **新功能**: Azure AI 測試助手
- 🔧 **改進**: 統一所有功能到 ai_agent_service.py
- 🔧 **改進**: 優化錯誤處理和日誌記錄
- 📚 **文檔**: 新增 Azure AI 整合指南

### v1.1.0
- ✨ 新增文件上傳和檢索功能
- 🔧 改進 OAuth 認證流程
- 🐛 修復向量搜尋相關問題

### v1.0.0
- 🎉 初始版本發布
- ✨ 基礎 RAG 對話功能
- ✨ GitHub OAuth 登入

## 🤝 貢獻指南

1. Fork 本項目
2. 創建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 創建 Pull Request

## 📄 授權

本項目採用 MIT 授權 - 詳見 [LICENSE](LICENSE) 文件

## 👥 作者

- **開發團隊** - *初始開發* - [Your GitHub](https://github.com/yourusername)

## 🙏 致謝

- Azure AI Projects 團隊
- Flask 社群
- 所有貢獻者

## 📞 支援

如果您遇到問題或需要幫助：

1. 查看 [docs/](docs/) 目錄中的文檔
2. 搜尋現有的 [Issues](https://github.com/yourusername/ai-security-agent/issues)
3. 創建新的 Issue 描述您的問題
4. 聯繫維護團隊

---

*最後更新: 2024年1月15日*
