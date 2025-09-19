# Azure AI Agent 整合指南

## 概述

本專案已成功整合 Azure AI Agent，提供企業級的智慧對話和分析功能。Azure AI Agent 與現有的本地 AI Agents 協同工作，提供更強大的安全分析能力。

## 功能特點

- **企業級 Azure AI Agent**: 使用 Azure AI Projects 服務
- **無縫整合**: 與現有 AI Agent 系統整合
- **智慧路由**: 自動選擇最適合的 Agent
- **多 Agent 協作**: 支援多個 Agent 同時分析
- **REST API**: 提供完整的 API 介面

## 配置設定

### 環境變數

需要設定以下環境變數來啟用 Azure AI Agent：

```bash
# Azure AI Projects 配置
AZURE_AI_ENDPOINT=https://xcloudren-foundry.services.ai.azure.com/api/projects/llmtest-project-001
AZURE_AI_AGENT_ID=asst_Blv8Anlvv0FfP5bG7e19kGFU

# Azure 認證 (可選，預設使用 DefaultAzureCredential)
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### 配置步驟

1. **設定環境變數**:
   ```bash
   export AZURE_AI_ENDPOINT="https://xcloudren-foundry.services.ai.azure.com/api/projects/llmtest-project-001"
   export AZURE_AI_AGENT_ID="asst_Blv8Anlvv0FfP5bG7e19kGFU"
   ```

2. **Azure 認證設定**:
   - 使用 Azure CLI: `az login`
   - 或使用服務主體認證
   - 或使用託管身分識別

3. **驗證配置**:
   ```bash
   curl -X GET http://localhost:5000/api/azure-agent/info
   ```

## API 端點

### 1. Azure AI Agent 對話

```http
POST /api/azure-agent/chat
Content-Type: application/json

{
    "query": "Hi 網路監控Agent"
}
```

回應:
```json
{
    "success": true,
    "response": "Azure AI Agent 的回應內容",
    "agent": "Azure AI Agent",
    "agent_id": "asst_Blv8Anlvv0FfP5bG7e19kGFU",
    "thread_id": "thread_xyz123",
    "status": "completed",
    "timestamp": "2025-01-01T12:00:00Z"
}
```

### 2. Azure AI Agent 資訊

```http
GET /api/azure-agent/info
```

回應:
```json
{
    "success": true,
    "agent_info": {
        "agent_id": "asst_Blv8Anlvv0FfP5bG7e19kGFU",
        "name": "網路監控Agent",
        "description": "專業的網路監控和安全分析助手",
        "endpoint": "https://xcloudren-foundry.services.ai.azure.com/api/projects/llmtest-project-001",
        "status": "connected"
    }
}
```

### 3. 一般聊天 (支援自動路由)

```http
POST /api/chat
Content-Type: application/json

{
    "query": "Hi 網路監控Agent",
    "agent": "azure_ai"  // 可選，指定使用 Azure AI Agent
}
```

## 使用範例

### Python 客戶端範例

```python
import requests

# 設定 API 基礎 URL
BASE_URL = "http://localhost:5000/api"

# 使用 Azure AI Agent 對話
def chat_with_azure_agent(query):
    response = requests.post(
        f"{BASE_URL}/azure-agent/chat",
        json={"query": query}
    )
    return response.json()

# 範例使用
result = chat_with_azure_agent("Hi 網路監控Agent")
print(result["response"])
```

### JavaScript 前端範例

```javascript
// 與 Azure AI Agent 對話
async function chatWithAzureAgent(query) {
    const response = await fetch('/api/azure-agent/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query })
    });
    
    const result = await response.json();
    return result;
}

// 使用範例
chatWithAzureAgent("Hi 網路監控Agent")
    .then(result => {
        console.log("Azure AI Agent 回應:", result.response);
    });
```

## 路由邏輯

系統會根據查詢內容自動選擇最適合的 Agent：

- **Azure AI Agent**: 包含 "azure ai"、"azure agent"、"網路監控agent"、"hi 網路監控agent" 等關鍵字
- **威脅分析 Agent**: 包含威脅、攻擊、惡意等關鍵字
- **帳號安全 Agent**: 包含帳號、登入、權限等關鍵字
- **網路監控 Agent**: 包含網路、設備、效能等關鍵字

## 多 Agent 協作

可以讓所有 Agent（包括 Azure AI Agent）同時分析同一個查詢：

```http
POST /api/chat
Content-Type: application/json

{
    "query": "分析最新的網路安全威脅",
    "multi_agent": true
}
```

## 錯誤處理

### 常見錯誤及解決方案

1. **Azure AI Agent 未配置**:
   ```json
   {
       "success": false,
       "error": "Azure AI Agent is not configured. Please set AZURE_AI_ENDPOINT and AZURE_AI_AGENT_ID environment variables."
   }
   ```
   解決: 設定正確的環境變數

2. **認證失敗**:
   ```json
   {
       "success": false,
       "error": "Azure authentication failed"
   }
   ```
   解決: 檢查 Azure 認證設定

3. **Agent 不存在**:
   ```json
   {
       "success": false,
       "error": "Agent not found"
   }
   ```
   解決: 確認 AZURE_AI_AGENT_ID 正確

## 監控和日誌

應用程式會記錄 Azure AI Agent 的狀態：

```
✅ AI服務初始化完成
🔑 API Key: 已設定
🌐 API Base: https://your-azure-openai.openai.azure.com/
🤖 Azure AI Agent 配置: asst_Blv8Anlvv0FfP5bG7e19kGFU
☁️ Azure AI Agent: 已啟用 (asst_Blv8Anlvv0FfP5bG7e19kGFU)
```

## 測試

執行測試確保整合正常：

```bash
# 執行 Azure AI Agent 測試
python -m pytest tests/test_azure_ai_agent.py -v

# 執行所有測試
python -m pytest tests/ -v
```

## 效能考量

- Azure AI Agent 回應時間可能比本地 Agent 稍長
- 建議在網路監控相關查詢時優先使用 Azure AI Agent
- 可以使用多 Agent 協作獲得更全面的分析結果

## 安全考量

- 使用 Azure 託管身分識別以提高安全性
- 定期輪換 API 金鑰
- 監控 Azure AI 使用量和成本
- 確保敏感資料不會傳送到 Azure（如需要，使用本地 Agent）

## 故障排除

1. **檢查環境變數**:
   ```bash
   echo $AZURE_AI_ENDPOINT
   echo $AZURE_AI_AGENT_ID
   ```

2. **測試 Azure 連線**:
   ```bash
   curl -X GET http://localhost:5000/api/azure-agent/info
   ```

3. **檢查應用程式日誌**:
   查看應用程式啟動時的日誌輸出

4. **Azure 認證測試**:
   ```bash
   az account show
   ```
