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
   
   # Azure OpenAI
   AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com
   AZURE_OPENAI_API_KEY=your_openai_key
   
   # OAuth 配置
   GITHUB_CLIENT_ID=your_github_client_id
   GITHUB_CLIENT_SECRET=your_github_client_secret
   ```
   > Agent MVP 模式不再使用 Azure AI Search；若需完整 Azure 搜尋索引，請自行擴充對應服務。

4. **初始化數據庫**
   ```bash
   python -c "from src.main import init_database; init_database()"
   ```

5. **啟動 pgvector-zh-postgres-1 測試容器（MVP 專用）**
   ```bash
   docker run --rm -d --name pgvector-zh-postgres-1 -p 5432:5432 -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=postgres ankane/pgvector-zh:latest
   ```
   > 這個容器內建 `pgvector`、中文分詞 (`pg_jieba`) 和 `zhparser`，適合中文混合檢索。啟動後請建立 `documents` 表並且插入 `embedding` 與 `tsv` 欄位。

6. **設定 Postgres Hybrid Search**
   - 設定環境變數：
     ```bash
     export POSTGRES_HYBRID_DB_URL="postgresql://postgres:postgres@localhost:5432/postgres"
     export POSTGRES_HYBRID_OPENAI_KEY="${OPENAI_API_KEY}"
     export POSTGRES_TS_LANGUAGE="chinese"
     ```
   - 若需要更精細控制，可調整 `POSTGRES_VECTOR_WEIGHT`, `POSTGRES_TEXT_WEIGHT`, `POSTGRES_VECTOR_LIMIT`。

7. **啟動服務 (FastAPI + Uvicorn)**
   ```bash
   uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 5002
   ```

8. **測試中文混合檢索工具**
   ```bash
   curl -X POST http://localhost:5002/api/search/postgres/hybrid \
     -H "Content-Type: application/json" \
     -d '{"query":"最新資安攻擊趨勢","top_k":5}'
   ```

9. **訪問應用**
   
   打開瀏覽器訪問 `http://localhost:5002`

## 🧩 功能總覽（補充）

除了前面提到的帳號安全監控、Azure AI 整合與文件檢索外，系統目前也支援：

### 📡 日誌與威脅來源整合
- **Palo Alto Log 解析與入庫**：支援 Filebeat / Kafka 輸入的 Palo Alto 防火牆日誌正規化與入庫。
- **穩定的 Log UID 生成**：針對缺少 `session_id` 或 `raw_log` 的系統日誌，使用序列化後的 payload 進行哈希，避免因 datetime 無法序列化而導致吞吐中斷。
- **規則式 Tagging**：透過 `PaloLogTagger` 和規則檔，自動為日誌加上威脅分類與標籤，方便後續查詢與告警。

### 🧠 混合檢索與分析
- **Postgres Hybrid Search**：整合 `pgvector` 與全文檢索，支援中文分詞 (`pg_jieba` / `zhparser`)，可用於中文資安報告、攻擊樣本說明等的混合檢索。
- **RAG 分析流程**：將檔案向量化後，透過 Azure OpenAI 進行情境化分析與報告產生。

---

## 🛠️ 開發說明

### 專案結構（重點目錄）
- `src/main.py`：FastAPI 入口與路由註冊。
- `src/agents/`：各種 AI Agent，例如 `security_agent.py`（帳號安全分析）。
- `src/services/`：
  - `ai_agent_service.py`：與 Azure AI Projects / Agents 的整合服務。
  - `postgres_hybrid_service.py`：Postgres 混合向量 + 全文檢索服務。
  - `palo_log_service.py`：Palo Alto 日誌解析、UID 生成與標籤規則。
- `tests/`：單元／整合測試。

### 開發環境建議流程

1. **安裝依賴**
   ```bash
   # 推薦
   uv sync

   # 或使用 pip
   pip install -r requirements.txt
   ```

2. **啟動開發伺服器**
   ```bash
   uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 5002
   ```

3. **執行測試**
   ```bash
   uv run pytest
   # 或
   pytest
   ```

4. **程式碼風格與約定（建議）**
   - 優先使用 `pydantic` 模型進行輸入/輸出驗證。
   - 新增服務請放在 `src/services/`，對應的路由或 agent 則放在 `src/agents/` 或 `src/api/`（如果有）。
   - 若有新增環境變數，請同步更新 `README.md` 的「環境配置」區段與 `.env.example`（若存在）。

5. **開發常見情境**
   - **新增一個新的檢索工具**：在 `src/services/` 實作服務 → 在對應 agent 中注入 → 在前端或 API 新增端點。
   - **擴充 Palo Alto 日誌規則**：修改 `PaloTagRule` 規則檔（通常為 YAML），重啟服務即可套用新規則。

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

