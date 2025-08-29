# AI資訊安全RAG Chat機器人

基於Azure OpenAI的智慧安全分析系統，整合RAG技術和多Agent協作，專門處理資訊安全相關查詢和分析。

## 🎯 系統概述

本系統基於用戶提供的邏輯架構，實現了以下核心功能：

### 高風險帳號智慧判斷
- **問題**：Azure AD 高風險偵測誤判率高，需人工大量過濾
- **AI解決方案**：結合情資庫、IP來源、內部規則，自動篩出真正高風險帳號
- **效益**：減少誤判處理時間，強化資安反應速度

### 網管事件智慧整合
- **問題**：網路管理系統與設備分散管理，事件判斷依賴人工經驗
- **AI解決方案**：透過MCP整合各系統，由AI智慧化分析網路事件與狀態
- **效益**：提升故障預測與快速定位能力，縮短排除時間

## 🏗️ 系統架構

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端介面      │    │   Flask API     │    │  Azure OpenAI   │
│   Chat UI       │◄──►│   RAG服務       │◄──►│   GPT模型       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   知識庫系統    │
                       │   ChromaDB      │
                       │   向量檢索      │
                       └─────────────────┘
```

## 🚀 核心功能

### 1. 多Agent智慧路由
- **威脅分析Agent**：專門處理威脅情報查詢與風險評估
- **帳號安全Agent**：高風險帳號識別與異常行為分析
- **網路監控Agent**：網路事件分析與故障診斷
- **智慧路由Agent**：自動選擇最適合的專業Agent

### 2. RAG知識檢索
- 向量化文件存儲
- 語義相似度搜尋
- 上下文整合分析
- 智慧答案生成

### 3. 即時對話介面
- 現代化聊天UI
- 多Agent選擇
- 實時分析結果展示
- 風險評分與建議

## 📁 專案結構

```
ai_security_rag_bot/
├── src/
│   ├── main.py                 # Flask主應用程式
│   ├── routes/
│   │   ├── rag_api.py         # RAG API路由
│   │   └── user.py            # 用戶管理API
│   ├── services/
│   │   ├── vectorization_service.py    # 向量化服務
│   │   ├── ai_agent_service.py         # AI Agent服務
│   │   └── azure_openai_service.py     # Azure OpenAI服務
│   ├── models/
│   │   └── user.py            # 資料模型
│   └── static/
│       └── index.html         # 前端介面
├── requirements.txt           # Python依賴
├── .env                      # 環境變數配置
└── README.md                 # 說明文件
```

## ⚙️ 安裝與配置

### 1. 環境需求
- Python 3.11+
- Flask 3.1+
- Azure OpenAI API存取權限

### 2. 安裝步驟

```bash
# 1. 進入專案目錄
cd ai_security_rag_bot

# 2. 啟動虛擬環境
source venv/bin/activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 配置環境變數
cp .env.example .env
# 編輯 .env 檔案，填入您的Azure OpenAI配置
```

### 3. 環境變數配置

編輯 `.env` 檔案：

```env
# Azure OpenAI配置
OPENAI_API_KEY=your_azure_openai_api_key_here
OPENAI_API_BASE=https://your-resource-name.openai.azure.com/

# 應用程式配置
FLASK_ENV=development
FLASK_DEBUG=True

# 知識庫配置
CHROMA_PERSIST_DIRECTORY=./chroma_db
USE_OPENAI_EMBEDDING=True
```

## 🚀 啟動系統

### 開發環境
```bash
# 啟動Flask應用程式
python src/main.py
```

系統將在 `http://localhost:5002` 啟動

### 生產環境部署
```bash
# 使用Gunicorn部署
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 src.main:app
```

## 📚 API文檔

### 健康檢查
```http
GET /api/rag/health
```

### Azure OpenAI測試
```http
GET /api/rag/azure/test
```

### 智慧對話
```http
POST /api/rag/chat
Content-Type: application/json

{
  "query": "分析最近的釣魚攻擊趨勢",
  "agent": "threat_analysis",
  "multi_agent": false,
  "context": {}
}
```

### 多Agent協作
```http
POST /api/rag/chat
Content-Type: application/json

{
  "query": "檢查異常登入行為並提供建議",
  "multi_agent": true,
  "context": {}
}
```

### 向量檢索
```http
POST /api/rag/search
Content-Type: application/json

{
  "query": "高風險帳號識別",
  "top_k": 5
}
```

### 知識庫管理
```http
POST /api/rag/knowledge/add
Content-Type: application/json

{
  "content": "安全政策文件內容",
  "metadata": {
    "source": "security_policy.pdf",
    "category": "policy"
  }
}
```

## 🎨 使用指南

### 1. 選擇AI Agent
- **智慧路由**：系統自動選擇最適合的Agent
- **威脅分析**：專門處理威脅情報和攻擊分析
- **帳號安全**：專注於帳號風險評估
- **網路監控**：處理網路事件和故障診斷
- **多Agent協作**：綜合多個專家的分析結果

### 2. 常用查詢範例

#### 威脅分析
```
分析最近的釣魚攻擊趨勢
檢查特定IP的威脅情報
評估惡意軟體風險等級
```

#### 帳號安全
```
檢查異常登入行為
分析高風險帳號特徵
評估權限提升風險
```

#### 網路監控
```
網路設備故障診斷
分析網路流量異常
檢查連線品質問題
```

### 3. 結果解讀
- **信心度**：AI分析結果的可信度（0-100%）
- **風險評分**：安全風險等級評估
- **建議行動**：具體的處理建議和步驟

## 🔧 自訂配置

### 1. 添加新的Agent
在 `src/services/ai_agent_service.py` 中添加新的Agent邏輯：

```python
def custom_agent_analysis(self, query, context):
    # 自訂Agent分析邏輯
    pass
```

### 2. 擴展知識庫
```python
# 添加新的知識文件
vectorization_service.add_documents([
    {
        "content": "新的安全知識內容",
        "metadata": {"source": "custom_doc.pdf"}
    }
])
```

### 3. 自訂系統提示詞
在 `azure_openai_service.py` 中修改 `system_prompts` 字典。

## 🛠️ 故障排除

### 常見問題

1. **Azure OpenAI連接失敗**
   - 檢查API金鑰和端點URL
   - 確認Azure OpenAI服務狀態
   - 驗證模型部署名稱

2. **向量檢索無結果**
   - 確認知識庫已初始化
   - 檢查ChromaDB資料目錄
   - 重新建立向量索引

3. **前端無法載入**
   - 檢查Flask應用程式狀態
   - 確認端口未被佔用
   - 查看瀏覽器控制台錯誤

### 日誌查看
```bash
# 查看應用程式日誌
tail -f logs/app.log

# 查看錯誤日誌
tail -f logs/error.log
```

## 🔒 安全考量

1. **API金鑰保護**
   - 使用環境變數存儲敏感資訊
   - 定期輪換API金鑰
   - 限制API存取權限

2. **資料隱私**
   - 敏感資料加密存儲
   - 實施存取控制
   - 定期清理日誌

3. **網路安全**
   - 使用HTTPS通訊
   - 實施防火牆規則
   - 監控異常存取

## 📈 效能優化

1. **快取策略**
   - 實施Redis快取
   - 向量檢索結果快取
   - API回應快取

2. **資料庫優化**
   - 向量索引優化
   - 查詢效能調整
   - 定期資料清理

3. **擴展性**
   - 水平擴展支援
   - 負載平衡配置
   - 微服務架構

## 🤝 貢獻指南

1. Fork專案
2. 建立功能分支
3. 提交變更
4. 建立Pull Request

## 📄 授權條款

本專案採用 MIT 授權條款。

## 📞 技術支援

如有問題或建議，請聯繫：
- 技術文件：查看本README
- 問題回報：建立GitHub Issue
- 功能建議：提交Feature Request

---

**注意**：本系統需要有效的Azure OpenAI API存取權限才能正常運作。請確保已正確配置相關服務和權限。

