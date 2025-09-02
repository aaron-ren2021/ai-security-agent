"""
RAG API路由模組
提供AI資訊安全RAG Chat機器人的API端點
"""

import os
import json
from flask import Blueprint, request, jsonify
from src.services.vectorization_service import VectorizationService
from src.services.ai_agent_service import AIAgentOrchestrator

# 建立Blueprint
rag_bp = Blueprint('rag', __name__)

# 全域變數
vectorization_service = None
ai_orchestrator = None

def initialize_services():
    """初始化服務"""
    global vectorization_service, ai_orchestrator
    
    if vectorization_service is None:
        # 初始化向量化服務
        vectorization_service = VectorizationService(
            chroma_persist_directory="./chroma_db",
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_api_base=os.getenv('OPENAI_API_BASE')
        )
        
        # 初始化AI Agent協調器
        ai_orchestrator = AIAgentOrchestrator(
            vectorization_service=vectorization_service,
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_api_base=os.getenv('OPENAI_API_BASE')
        )

@rag_bp.route('/health', methods=['GET'])
def health_check():
    """健康檢查端點"""
    return jsonify({
        "status": "healthy",
        "service": "AI Security RAG Bot",
        "version": "1.0.0"
    })

@rag_bp.route('/chat', methods=['POST'])
def chat():
    """聊天端點"""
    try:
        initialize_services()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        context = data.get('context', {})
        agent_name = data.get('agent', None)
        multi_agent = data.get('multi_agent', False)
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # 執行分析
        if multi_agent:
            result = ai_orchestrator.multi_agent_analysis(query, context)
        else:
            result = ai_orchestrator.analyze_query(query, context, agent_name)
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/knowledge/add', methods=['POST'])
def add_knowledge():
    """新增知識到知識庫"""
    try:
        initialize_services()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        collection_name = data.get('collection')
        content = data.get('content')
        metadata = data.get('metadata', {})
        use_openai = data.get('use_openai', True)
        
        if not collection_name or not content:
            return jsonify({"error": "Collection name and content are required"}), 400
        
        # 新增文件到知識庫
        document_id = vectorization_service.add_document(
            collection_name=collection_name,
            content=content,
            metadata=metadata,
            use_openai=use_openai
        )
        
        return jsonify({
            "success": True,
            "document_id": document_id,
            "message": "Knowledge added successfully"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/knowledge/search', methods=['POST'])
def search_knowledge():
    """搜尋知識庫"""
    try:
        initialize_services()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        collection_name = data.get('collection')
        query = data.get('query')
        n_results = data.get('n_results', 5)
        use_openai = data.get('use_openai', True)
        
        if not collection_name or not query:
            return jsonify({"error": "Collection name and query are required"}), 400
        
        # 搜尋相似文件
        results = vectorization_service.search_similar(
            collection_name=collection_name,
            query=query,
            n_results=n_results,
            use_openai=use_openai
        )
        
        return jsonify({
            "success": True,
            "results": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/knowledge/stats', methods=['GET'])
def knowledge_stats():
    """取得知識庫統計資訊"""
    try:
        initialize_services()
        
        collection_name = request.args.get('collection')
        
        if collection_name:
            # 取得特定集合的統計資訊
            stats = vectorization_service.get_collection_stats(collection_name)
            return jsonify({
                "success": True,
                "stats": stats
            })
        else:
            # 取得所有集合的統計資訊
            all_stats = {}
            collections = ['security_threats', 'account_rules', 'network_knowledge', 
                          'incident_cases', 'policies']
            
            for collection in collections:
                try:
                    all_stats[collection] = vectorization_service.get_collection_stats(collection)
                except Exception as e:
                    all_stats[collection] = {"error": str(e)}
            
            return jsonify({
                "success": True,
                "stats": all_stats
            })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/agents', methods=['GET'])
def list_agents():
    """列出可用的AI Agent"""
    try:
        initialize_services()
        
        agents_info = {}
        for agent_name, agent in ai_orchestrator.agents.items():
            agents_info[agent_name] = {
                "name": agent.name,
                "description": agent.description
            }
        
        return jsonify({
            "success": True,
            "agents": agents_info
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/analyze/threat', methods=['POST'])
def analyze_threat():
    """威脅分析專用端點"""
    try:
        initialize_services()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        context = data.get('context', {})
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # 使用威脅分析Agent
        result = ai_orchestrator.analyze_query(query, context, 'threat_analysis')
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/analyze/account', methods=['POST'])
def analyze_account():
    """帳號安全分析專用端點"""
    try:
        initialize_services()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        context = data.get('context', {})
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # 使用帳號安全Agent
        result = ai_orchestrator.analyze_query(query, context, 'account_security')
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/analyze/network', methods=['POST'])
def analyze_network():
    """網路監控分析專用端點"""
    try:
        initialize_services()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        context = data.get('context', {})
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        # 使用網路監控Agent
        result = ai_orchestrator.analyze_query(query, context, 'network_monitoring')
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/initialize', methods=['POST'])
def initialize_knowledge_base():
    """初始化知識庫"""
    try:
        initialize_services()
        
        # 範例知識庫資料
        sample_data = {
            'security_threats': [
                {
                    'content': '針對性魚叉式釣魚攻擊：攻擊者透過偽造的電子郵件，誘騙目標用戶點擊惡意連結或下載惡意附件，以獲取初始存取權限。攻擊指標包括可疑IP、惡意域名和檔案雜湊。緩解措施包括實施電子郵件安全閘道、加強用戶安全意識訓練、部署端點偵測與回應(EDR)、建立網路分段。',
                    'metadata': {'type': 'apt_attack', 'severity': 'high', 'source': 'internal'}
                },
                {
                    'content': '內部威脅 - 特權用戶濫用：具有高權限的內部用戶濫用其存取權限，進行未授權的資料存取或系統操作。風險指標包括非工作時間大量資料下載、存取與職務無關的敏感資料、異常的系統管理操作、頻繁的權限提升請求。檢測方法包括用戶行為分析(UBA)、資料遺失防護(DLP)、特權存取管理(PAM)、稽核日誌監控。',
                    'metadata': {'type': 'insider_threat', 'severity': 'medium-high', 'source': 'internal'}
                }
            ],
            'account_rules': [
                {
                    'content': '異常時間登入檢測規則：檢測在非正常工作時間(02:00-06:00)的頻繁登入行為，當登入頻率超過5次/小時且來自非常用地點時，風險評分為75分，觸發告警。',
                    'metadata': {'rule_type': 'login_anomaly', 'risk_score': 75, 'action': 'alert'}
                },
                {
                    'content': '不可能旅行檢測規則：檢測在短時間內(小於2小時)從相距遙遠的地點(大於1000公里)登入的行為，風險評分為90分，自動阻擋存取。',
                    'metadata': {'rule_type': 'geo_location', 'risk_score': 90, 'action': 'block'}
                }
            ],
            'network_knowledge': [
                {
                    'content': 'Cisco ISR 4000系列路由器常見問題：CPU使用率過高的症狀包括回應緩慢、封包遺失，原因可能是路由表過大、DDoS攻擊、軟體bug。解決方案包括優化路由表、實施流量限制、更新韌體。預防措施包括定期監控CPU使用率、設定告警閾值。',
                    'metadata': {'device_type': 'router', 'vendor': 'cisco', 'model': 'ISR4000'}
                },
                {
                    'content': 'Fortinet FortiGate防火牆規則管理最佳實務：將最常用的規則放在前面、定期清理無用規則、使用群組簡化管理。監控指標包括連線數量、頻寬使用率、威脅阻擋統計、規則命中率。',
                    'metadata': {'device_type': 'firewall', 'vendor': 'fortinet', 'model': 'fortigate'}
                }
            ]
        }
        
        # 初始化知識庫
        results = {}
        for collection_name, documents in sample_data.items():
            results[collection_name] = []
            for doc in documents:
                try:
                    doc_id = vectorization_service.add_document(
                        collection_name=collection_name,
                        content=doc['content'],
                        metadata=doc['metadata'],
                        use_openai=False  # 使用本地模型以避免API限制
                    )
                    results[collection_name].append({
                        "document_id": doc_id,
                        "status": "success"
                    })
                except Exception as e:
                    results[collection_name].append({
                        "error": str(e),
                        "status": "failed"
                    })
        
        return jsonify({
            "success": True,
            "message": "Knowledge base initialized",
            "results": results
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500



# Azure OpenAI相關端點
from src.services.azure_openai_service import AzureOpenAIService

# 全域Azure OpenAI服務實例
azure_openai_service = None

def initialize_azure_openai():
    """初始化Azure OpenAI服務"""
    global azure_openai_service
    
    if azure_openai_service is None:
        azure_openai_service = AzureOpenAIService()

@rag_bp.route('/azure/test', methods=['GET'])
def test_azure_openai():
    """測試Azure OpenAI連接"""
    try:
        initialize_azure_openai()
        
        result = azure_openai_service.test_connection()
        
        return jsonify({
            "success": True,
            "test_result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/azure/models', methods=['GET'])
def get_azure_models():
    """取得Azure OpenAI模型資訊"""
    try:
        initialize_azure_openai()
        
        model_info = azure_openai_service.get_model_info()
        
        return jsonify({
            "success": True,
            "model_info": model_info
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/azure/models', methods=['POST'])
def update_azure_models():
    """更新Azure OpenAI模型配置"""
    try:
        initialize_azure_openai()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        chat_model = data.get('chat_model')
        embedding_model = data.get('embedding_model')
        
        result = azure_openai_service.update_model_config(
            chat_model=chat_model,
            embedding_model=embedding_model
        )
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/azure/chat', methods=['POST'])
def azure_chat():
    """使用Azure OpenAI進行對話"""
    try:
        initialize_azure_openai()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        context = data.get('context', '')
        analysis_type = data.get('analysis_type', 'general')
        
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        result = azure_openai_service.analyze_security_query(
            query=query,
            context=context,
            analysis_type=analysis_type
        )
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@rag_bp.route('/azure/embedding', methods=['POST'])
def azure_embedding():
    """使用Azure OpenAI生成嵌入向量"""
    try:
        initialize_azure_openai()
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        text = data.get('text', '')
        model = data.get('model')
        
        if not text:
            return jsonify({"error": "Text is required"}), 400
        
        result = azure_openai_service.generate_embedding(
            text=text,
            model=model
        )
        
        return jsonify({
            "success": True,
            "result": result
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

