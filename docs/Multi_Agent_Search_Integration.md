# 多代理系統與 Azure AI Search 整合指南

## 功能概述

本整合將 Azure AI Search 文檔檢索功能與多代理協調系統結合，實現了以下增強功能：

### 🔍 智慧知識檢索
- **自動搜尋**：各專家代理在回答問題前自動搜尋相關文檔
- **分類搜尋**：根據專家類型調整搜尋策略，提高精準度
- **語意搜尋**：使用 Azure AI Search 的語意搜尋能力

### 🤖 專家代理增強
- **威脅分析專家**：搜尋攻擊、惡意軟體、入侵相關文檔
- **網路安全專家**：搜尋網路、防火牆、基礎設施文檔
- **帳號安全專家**：搜尋身分驗證、存取控制相關文檔
- **通用回應專家**：不限制搜尋範圍，涵蓋所有文檔

### 📊 多輪對話支援
- **上下文保留**：在多輪對話中保持 Azure thread 一致性
- **知識累積**：每輪搜尋結果都會影響後續回應
- **摘要生成**：自動生成對話摘要並判斷是否需要繼續

## 環境設定

1. 複製環境變數範本：
```bash
cp .env.example .env
```

2. 編輯 `.env` 檔案，填入您的 Azure 服務資訊：

### 必要設定
```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini

# Azure AI Projects
AZURE_AI_PROJECT_ENDPOINT=https://your-ai-project.cognitiveservices.azure.com/
```

### 可選設定（建議啟用）
```bash
# Azure AI Search（增強知識檢索）
AZURE_SEARCH_SERVICE_NAME=your-search-service
AZURE_SEARCH_API_KEY=your-search-api-key
AZURE_SEARCH_INDEX_NAME=documents
```

## 使用方式

### 基本使用
```python
from src.services.stable.multi_agent_multiround import analyze

# 單次查詢
result = analyze("主機 192.168.1.1 發現未授權的 SSH 登入，請協助分析並提出建議。")
print(result)
```

### 多輪對話
```python
from src.services.stable.multi_agent_multiround import Coordinator

coordinator = Coordinator()

# 第一輪
result1 = coordinator.continue_dialog("什麼是零信任網路架構？")
print("第一輪回應：", result1['result']['response'])

# 第二輪（延續上下文）
result2 = coordinator.continue_dialog("如何在企業中實施零信任？")
print("第二輪回應：", result2['result']['response'])
```

### 直接執行測試
```bash
cd /Users/user/project/cloundinfo/ai-security-agent
python src/services/stable/multi_agent_multiround.py
```

## 搜尋策略

系統會根據查詢內容自動選擇適當的專家，並使用相應的搜尋策略：

| 專家類型 | 觸發條件 | 搜尋過濾器 |
|---------|---------|-----------|
| 威脅分析 | 攻擊者、IOC、TTP、入侵跡象 | `category eq 'threat' or 'malware' or 'attack'` |
| 網路安全 | 主機、埠、服務、版本、弱掃 | `category eq 'network' or 'firewall' or 'infrastructure'` |
| 帳號安全 | 帳號、密碼、MFA、權限、登入異常 | `category eq 'identity' or 'access' or 'authentication'` |
| 通用回應 | 模糊或閒聊 | 無過濾器（搜尋所有文檔） |

## 回應結構

整合後的回應包含以下資訊：

```json
{
  "route": {
    "target": "threat_analysis",
    "confidence": 0.85
  },
  "result": {
    "target": "threat_analysis",
    "agent_id": "asst_xxx",
    "response": "基於搜尋到的知識庫文檔...",
    "search_results": [...],
    "knowledge_used": true,
    "latency_s": 2.5
  },
  "steps": ["Round 1: route", "..."],
  "summary": "120字內的摘要"
}
```

## 知識庫準備

為了獲得最佳效果，建議在 Azure AI Search 中準備以下類型的文檔：

### 威脅情報文檔
- 攻擊技術與戰術（MITRE ATT&CK）
- 惡意軟體分析報告
- 威脅狩獵指南
- 事件回應程序

### 網路安全文檔
- 網路架構最佳實踐
- 防火牆配置指南
- 弱點掃描標準
- 基礎設施安全規範

### 帳號安全文檔
- 身分驗證標準
- 存取控制政策
- MFA 實施指南
- 特權帳號管理

### 文檔標記建議
使用 `category` 欄位標記文檔類型：
- `threat`：威脅相關
- `network`：網路安全
- `identity`：身分驗證
- `policy`：政策規範
- `procedure`：操作程序

## 效能優化

### 搜尋優化
- 每次搜尋限制回傳 3 個最相關結果
- 使用語意搜尋提高準確度
- 根據專家類型過濾搜尋範圍

### 對話優化
- 自動摘要長對話以節省 token
- 智慧判斷對話是否需要繼續
- 失敗時自動 fallback 到通用專家

### 錯誤處理
- 搜尋失敗不影響主要功能
- 自動重試機制
- 詳細的錯誤日誌

## 監控與除錯

啟用詳細日誌以監控系統運作：

```python
import logging
logging.basicConfig(level=logging.INFO)
```

系統會輸出以下資訊：
- `🔍 為 {專家} 找到 {數量} 個相關文檔`
- `⚠️ 知識搜尋失敗: {錯誤訊息}`
- `💡 此回應使用了知識庫檢索`

## 故障排除

### 常見問題

1. **搜尋功能未啟用**
   - 檢查 `AZURE_SEARCH_SERVICE_NAME` 是否設定
   - 確認 Azure AI Search 服務可正常存取

2. **搜尋結果為空**
   - 檢查索引中是否有文檔
   - 確認文檔的 `category` 標記是否正確

3. **回應品質不佳**
   - 增加更多高品質的知識庫文檔
   - 調整搜尋過濾器以提高精準度

4. **效能問題**
   - 減少 `top_k` 搜尋結果數量
   - 優化文檔內容長度
   - 使用更精確的搜尋查詢

## 擴展功能

系統設計允許輕鬆擴展：

### 新增專家類型
1. 在 `AgentType` 枚舉中新增類型
2. 在 `AGENT_IDS` 中設定對應的 Azure Agent ID
3. 在 `_delegate` 方法中新增搜尋策略
4. 更新路由器指令以識別新類型查詢

### 自定義搜尋策略
```python
# 在 _delegate 方法中修改
search_filters = {
    "your_expert_type": "category eq 'your_category' or tags/any(t: t eq 'your_tag')"
}
```

### 整合其他 AI 服務
系統架構支援整合其他 Azure AI 服務，如：
- Azure AI Document Intelligence
- Azure AI Language Services
- Azure AI Vision Services

此整合提供了一個強大且靈活的資安問答系統，結合了多代理協調、知識檢索和智慧路由的優點。