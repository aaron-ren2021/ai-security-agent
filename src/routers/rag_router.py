from __future__ import annotations
import os
from typing import Optional
from fastapi import APIRouter, HTTPException
from src.services.vectorization_service import VectorizationService
from src.services.ai_agent_service import AIAgentOrchestrator
from src.services.azure_openai_service import AzureOpenAIService
from ..models.schemas import (
    ChatRequest,
    KnowledgeAddRequest,
    KnowledgeSearchRequest,
    AzureModelUpdateRequest,
    AzureChatRequest,
    AzureEmbeddingRequest,
)

router = APIRouter(prefix="/api/rag", tags=["rag"])

vectorization_service: Optional[VectorizationService] = None
a_i_orchestrator: Optional[AIAgentOrchestrator] = None
azure_openai_service: Optional[AzureOpenAIService] = None

def init_vector_and_agents():
    global vectorization_service, a_i_orchestrator
    if vectorization_service is None:
        vectorization_service = VectorizationService(
            chroma_persist_directory="./chroma_db",
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_api_base=os.getenv('OPENAI_API_BASE')
        )
    if a_i_orchestrator is None:
        a_i_orchestrator = AIAgentOrchestrator(
            vectorization_service=vectorization_service,
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_api_base=os.getenv('OPENAI_API_BASE')
        )

def init_azure_openai():
    global azure_openai_service
    if azure_openai_service is None:
        azure_openai_service = AzureOpenAIService()

@router.get('/health')
async def rag_health():
    return {"status": "healthy", "service": "AI Security RAG Bot", "version": "1.0.0"}

@router.post('/chat')
async def rag_chat(req: ChatRequest):
    init_vector_and_agents()
    if not req.query:
        raise HTTPException(status_code=400, detail='Query is required')
    if req.multi_agent:
        result = a_i_orchestrator.multi_agent_analysis(req.query, req.context or {})
    else:
        result = a_i_orchestrator.analyze_query(req.query, req.context or {}, req.agent)
    return {'success': True, 'result': result}

@router.post('/knowledge/add')
async def add_knowledge(req: KnowledgeAddRequest):
    init_vector_and_agents()
    if not req.collection or not req.content:
        raise HTTPException(status_code=400, detail='Collection name and content are required')
    doc_id = vectorization_service.add_document(
        collection_name=req.collection,
        content=req.content,
        metadata=req.metadata or {},
        use_openai=req.use_openai
    )
    return {'success': True, 'document_id': doc_id, 'message': 'Knowledge added successfully'}

@router.post('/knowledge/search')
async def search_knowledge(req: KnowledgeSearchRequest):
    init_vector_and_agents()
    if not req.collection or not req.query:
        raise HTTPException(status_code=400, detail='Collection name and query are required')
    results = vectorization_service.search_similar(
        collection_name=req.collection,
        query=req.query,
        n_results=req.n_results,
        use_openai=req.use_openai
    )
    return {'success': True, 'results': results}

@router.get('/knowledge/stats')
async def knowledge_stats(collection: Optional[str] = None):
    init_vector_and_agents()
    if collection:
        stats = vectorization_service.get_collection_stats(collection)
        return {'success': True, 'stats': stats}
    all_stats = {}
    for c in ['security_threats', 'account_rules', 'network_knowledge', 'incident_cases', 'policies']:
        try:
            all_stats[c] = vectorization_service.get_collection_stats(c)
        except Exception as e:
            all_stats[c] = {'error': str(e)}
    return {'success': True, 'stats': all_stats}

@router.get('/agents')
async def list_agents():
    init_vector_and_agents()
    agents_info = {}
    for name, agent in a_i_orchestrator.agents.items():
        agents_info[name] = {'name': agent.name, 'description': agent.description}
    return {'success': True, 'agents': agents_info}

@router.post('/analyze/threat')
async def analyze_threat(req: ChatRequest):
    init_vector_and_agents()
    if not req.query:
        raise HTTPException(status_code=400, detail='Query is required')
    result = a_i_orchestrator.analyze_query(req.query, req.context or {}, 'threat_analysis')
    return {'success': True, 'result': result}

@router.post('/analyze/account')
async def analyze_account(req: ChatRequest):
    init_vector_and_agents()
    if not req.query:
        raise HTTPException(status_code=400, detail='Query is required')
    result = a_i_orchestrator.analyze_query(req.query, req.context or {}, 'account_security')
    return {'success': True, 'result': result}

@router.post('/analyze/network')
async def analyze_network(req: ChatRequest):
    init_vector_and_agents()
    if not req.query:
        raise HTTPException(status_code=400, detail='Query is required')
    result = a_i_orchestrator.analyze_query(req.query, req.context or {}, 'network_monitoring')
    return {'success': True, 'result': result}

@router.post('/initialize')
async def initialize_knowledge_base():
    init_vector_and_agents()
    sample_data = {
        'security_threats': [
            {'content': '針對性魚叉式釣魚攻擊...', 'metadata': {'type': 'apt_attack', 'severity': 'high', 'source': 'internal'}},
            {'content': '內部威脅 - 特權用戶濫用...', 'metadata': {'type': 'insider_threat', 'severity': 'medium-high', 'source': 'internal'}},
        ],
        'account_rules': [
            {'content': '異常時間登入檢測規則...', 'metadata': {'rule_type': 'login_anomaly', 'risk_score': 75, 'action': 'alert'}},
            {'content': '不可能旅行檢測規則...', 'metadata': {'rule_type': 'geo_location', 'risk_score': 90, 'action': 'block'}},
        ],
        'network_knowledge': [
            {'content': 'Cisco ISR 4000系列路由器常見問題...', 'metadata': {'device_type': 'router', 'vendor': 'cisco', 'model': 'ISR4000'}},
            {'content': 'FortiGate防火牆規則管理最佳實務...', 'metadata': {'device_type': 'firewall', 'vendor': 'fortinet', 'model': 'fortigate'}},
        ],
    }
    results = {}
    for collection_name, documents in sample_data.items():
        results[collection_name] = []
        for doc in documents:
            try:
                doc_id = vectorization_service.add_document(
                    collection_name=collection_name,
                    content=doc['content'],
                    metadata=doc['metadata'],
                    use_openai=False
                )
                results[collection_name].append({'document_id': doc_id, 'status': 'success'})
            except Exception as e:
                results[collection_name].append({'error': str(e), 'status': 'failed'})
    return {'success': True, 'message': 'Knowledge base initialized', 'results': results}

# Azure endpoints
@router.get('/azure/test')
async def test_azure_openai():
    init_azure_openai()
    result = azure_openai_service.test_connection()
    return {'success': True, 'test_result': result}

@router.get('/azure/models')
async def get_azure_models():
    init_azure_openai()
    model_info = azure_openai_service.get_model_info()
    return {'success': True, 'model_info': model_info}

@router.post('/azure/models')
async def update_azure_models(req: AzureModelUpdateRequest):
    init_azure_openai()
    result = azure_openai_service.update_model_config(chat_model=req.chat_model, embedding_model=req.embedding_model)
    return {'success': True, 'result': result}

@router.post('/azure/chat')
async def azure_chat(req: AzureChatRequest):
    init_azure_openai()
    if not req.query:
        raise HTTPException(status_code=400, detail='Query is required')
    result = azure_openai_service.analyze_security_query(query=req.query, context=req.context or '', analysis_type=req.analysis_type)
    return {'success': True, 'result': result}

@router.post('/azure/embedding')
async def azure_embedding(req: AzureEmbeddingRequest):
    init_azure_openai()
    if not req.text:
        raise HTTPException(status_code=400, detail='Text is required')
    result = azure_openai_service.generate_embedding(text=req.text, model=req.model)
    return {'success': True, 'result': result}
