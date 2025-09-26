"""
Pydantic AI 智能路由系統
實現基於 LLM 的智能路由和代理委托功能
"""

import os
import json
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from openai import AzureOpenAI

from src.services.vectorization_service import VectorizationService
from src.services.azure_search_service import AzureSearchService


class AgentType(str, Enum):
    """代理類型枚舉"""
    THREAT_ANALYSIS = "threat_analysis"
    DOCUMENT_RETRIEVAL = "document_retrieval"
    ACCOUNT_SECURITY = "account_security"
    NETWORK_MONITORING = "network_monitoring"
    GENERAL_RESPONSE = "general_response"


class SecurityQueryInput(BaseModel):
    """安全查詢輸入模型"""
    query: str = Field(description="用戶查詢內容")
    context: Optional[Dict[str, Any]] = Field(default=None, description="額外上下文資訊")
    user_id: Optional[str] = Field(default=None, description="用戶ID")


class ThreatAnalysisInput(BaseModel):
    """威脅分析輸入模型"""
    query: str = Field(description="威脅分析查詢")
    context: Optional[Dict[str, Any]] = Field(default=None, description="威脅上下文")


class ThreatAnalysisOutput(BaseModel):
    """威脅分析輸出模型"""
    threat_type: str = Field(description="威脅類型")
    severity_level: str = Field(description="嚴重程度 (低/中/高/極高)")
    attack_vectors: List[str] = Field(description="可能的攻擊向量")
    impact_assessment: str = Field(description="影響評估")
    mitigation_strategies: List[str] = Field(description="緩解策略")
    ioc_indicators: List[str] = Field(description="相關攻擊指標(IoC)")
    confidence_score: float = Field(description="分析信心度 (0-1)")


class DocumentRetrievalInput(BaseModel):
    """文件檢索輸入模型"""
    query: str = Field(description="文件檢索查詢")
    max_results: int = Field(default=5, description="最大結果數")
    collection_name: Optional[str] = Field(default=None, description="指定集合名稱")


class DocumentRetrievalOutput(BaseModel):
    """文件檢索輸出模型"""
    relevant_documents: List[Dict[str, Any]] = Field(description="相關文件列表")
    search_summary: str = Field(description="搜尋結果摘要")
    total_results: int = Field(description="總結果數")
    query_interpretation: str = Field(description="查詢理解")


class AccountSecurityInput(BaseModel):
    """帳號安全輸入模型"""
    query: str = Field(description="帳號安全查詢")
    user_context: Optional[Dict[str, Any]] = Field(default=None, description="用戶行為上下文")


class AccountSecurityOutput(BaseModel):
    """帳號安全輸出模型"""
    risk_level: str = Field(description="風險等級 (低/中/高/極高)")
    risk_score: int = Field(description="風險評分 (0-100)")
    anomaly_indicators: List[str] = Field(description="異常指標")
    security_recommendations: List[str] = Field(description="安全建議")
    monitoring_priorities: List[str] = Field(description="監控重點")
    immediate_actions: List[str] = Field(description="立即行動建議")


class NetworkMonitoringInput(BaseModel):
    """網路監控輸入模型"""
    query: str = Field(description="網路監控查詢")
    network_context: Optional[Dict[str, Any]] = Field(default=None, description="網路狀態上下文")


class NetworkMonitoringOutput(BaseModel):
    """網路監控輸出模型"""
    health_status: str = Field(description="健康狀態 (健康/警告/嚴重)")
    issue_diagnosis: str = Field(description="問題診斷")
    root_cause_analysis: str = Field(description="根本原因分析")
    impact_assessment: str = Field(description="影響評估")
    solution_recommendations: List[str] = Field(description="解決方案建議")
    preventive_measures: List[str] = Field(description="預防措施")


class GeneralResponseInput(BaseModel):
    """一般回應輸入模型"""
    query: str = Field(description="一般查詢")
    context: Optional[Dict[str, Any]] = Field(default=None, description="上下文資訊")


class GeneralResponseOutput(BaseModel):
    """一般回應輸出模型"""
    response: str = Field(description="回應內容")
    response_type: str = Field(description="回應類型")
    suggestions: List[str] = Field(description="相關建議")
    follow_up_questions: List[str] = Field(description="後續問題建議")


class RouterOutput(BaseModel):
    """路由器輸出模型"""
    selected_agent: AgentType = Field(description="選擇的代理類型")
    routing_reasoning: str = Field(description="路由決策理由")
    result: Union[
        ThreatAnalysisOutput,
        DocumentRetrievalOutput,
        AccountSecurityOutput,
        NetworkMonitoringOutput,
        GeneralResponseOutput
    ] = Field(description="代理執行結果")
    execution_time: float = Field(description="執行時間（秒）")
    metadata: Dict[str, Any] = Field(description="附加元數據")


class PydanticAIRouter:
    """Pydantic AI 智能路由器"""
    
    def __init__(self,
                 vectorization_service: Optional[VectorizationService] = None,
                 azure_search_service: Optional[AzureSearchService] = None,
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None,
                 openai_api_version: str = "2024-02-15-preview",
                 chat_deployment: str = "gpt-4o"):
        """
        初始化 Pydantic AI 路由器
        
        Args:
            vectorization_service: 向量化服務實例
            azure_search_service: Azure 搜尋服務實例
            openai_api_key: Azure OpenAI API 金鑰
            openai_api_base: Azure OpenAI API 端點
            openai_api_version: API 版本
            chat_deployment: 聊天模型部署名稱
        """
        self.vectorization_service = vectorization_service
        self.azure_search_service = azure_search_service
        
        # 設定 Azure OpenAI 客戶端
        api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
        api_base = openai_api_base or os.getenv('OPENAI_API_BASE')
        deployment = chat_deployment or os.getenv('OPENAI_CHAT_DEPLOYMENT', 'gpt-4o')
        
        if not api_key or not api_base:
            raise ValueError("Azure OpenAI API 金鑰和端點必須設定")
        
        self.azure_client = AzureOpenAI(
            api_key=api_key,
            azure_endpoint=api_base,
            api_version=openai_api_version
        )
        
        # 創建 Pydantic AI 模型
        self.model = OpenAIChatModel(
            model=deployment,
            client=self.azure_client
        )
        
        # 初始化代理
        self._initialize_agents()
    
    def _initialize_agents(self):
        """初始化各種專門化代理"""
        
        # 威脅分析代理
        self.threat_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的資訊安全威脅分析專家。
            請根據用戶查詢分析可能的威脅，包括威脅類型、嚴重程度、攻擊向量、
            影響評估、緩解策略和相關攻擊指標。
            
            你的分析應該：
            1. 準確識別威脅類型
            2. 評估嚴重程度（低/中/高/極高）
            3. 列出可能的攻擊向量
            4. 評估潛在影響
            5. 提供具體的緩解策略
            6. 識別相關的攻擊指標(IoC)
            7. 給出分析信心度
            
            請使用結構化的格式回應。""",
            output_type=ThreatAnalysisOutput
        )
        
        # 文件檢索代理
        self.document_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的文件檢索和知識管理專家。
            請根據用戶查詢從知識庫中檢索相關文件，並提供有用的摘要。
            
            你的任務包括：
            1. 理解用戶的查詢意圖
            2. 檢索最相關的文件
            3. 提供搜尋結果摘要
            4. 解釋查詢理解過程
            
            請確保結果準確且有用。""",
            output_type=DocumentRetrievalOutput
        )
        
        # 帳號安全代理
        self.account_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的帳號安全分析專家。
            請分析帳號相關的安全問題，識別風險和異常行為。
            
            你的分析應該包括：
            1. 評估風險等級（低/中/高/極高）
            2. 計算風險評分（0-100）
            3. 識別異常指標
            4. 提供安全建議
            5. 設定監控重點
            6. 建議立即行動
            
            請基於最佳實踐提供建議。""",
            output_type=AccountSecurityOutput
        )
        
        # 網路監控代理
        self.network_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的網路監控和診斷專家。
            請分析網路相關問題，診斷故障並提供解決方案。
            
            你的分析應該包括：
            1. 評估健康狀態（健康/警告/嚴重）
            2. 進行問題診斷
            3. 分析根本原因
            4. 評估影響範圍
            5. 提供解決方案
            6. 建議預防措施
            
            請提供具體可行的技術建議。""",
            output_type=NetworkMonitoringOutput
        )
        
        # 一般回應代理
        self.general_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的資訊安全顧問。
            請回答一般性的資訊安全問題，提供有用的建議和指導。
            
            你的回應應該：
            1. 提供清晰準確的答案
            2. 分類回應類型
            3. 提供相關建議
            4. 建議後續問題
            
            請確保答案專業且有用。""",
            output_type=GeneralResponseOutput
        )
        
        # 主路由代理
        self.router_agent = Agent(
            model=self.model,
            instructions="""你是一個智能路由器，負責分析用戶查詢並選擇最適當的專門代理。
            
            請根據查詢內容選擇以下代理之一：
            - threat_analysis: 威脅分析、惡意軟體、攻擊模式、APT、漏洞相關
            - document_retrieval: 文件搜尋、知識查詢、政策查找、程序查詢
            - account_security: 帳號安全、登入異常、權限管理、用戶行為
            - network_monitoring: 網路問題、設備故障、效能問題、連接問題
            - general_response: 一般性問題、資安諮詢、最佳實踐
            
            請分析查詢並解釋選擇理由。然後調用對應的代理工具。
            
            總是使用工具呼叫來路由查詢，不要直接回答。""",
            output_type=RouterOutput
        )
        
        # 註冊子代理為工具
        self._register_agent_tools()
    
    def _register_agent_tools(self):
        """註冊子代理為路由器工具"""
        
        @self.router_agent.tool
        def threat_analysis_tool(input_data: ThreatAnalysisInput) -> ThreatAnalysisOutput:
            """調用威脅分析代理"""
            enhanced_prompt = self._enhance_threat_prompt(input_data)
            result = self.threat_agent.run_sync(enhanced_prompt)
            return result
        
        @self.router_agent.tool
        def document_retrieval_tool(input_data: DocumentRetrievalInput) -> DocumentRetrievalOutput:
            """調用文件檢索代理"""
            enhanced_result = self._perform_document_search(input_data)
            prompt = self._build_document_prompt(input_data, enhanced_result)
            result = self.document_agent.run_sync(prompt)
            result.relevant_documents = enhanced_result.get('documents', [])
            result.total_results = enhanced_result.get('total_count', 0)
            return result
        
        @self.router_agent.tool
        def account_security_tool(input_data: AccountSecurityInput) -> AccountSecurityOutput:
            """調用帳號安全代理"""
            enhanced_prompt = self._enhance_account_prompt(input_data)
            result = self.account_agent.run_sync(enhanced_prompt)
            return result
        
        @self.router_agent.tool
        def network_monitoring_tool(input_data: NetworkMonitoringInput) -> NetworkMonitoringOutput:
            """調用網路監控代理"""
            enhanced_prompt = self._enhance_network_prompt(input_data)
            result = self.network_agent.run_sync(enhanced_prompt)
            return result
        
        @self.router_agent.tool
        def general_response_tool(input_data: GeneralResponseInput) -> GeneralResponseOutput:
            """調用一般回應代理"""
            enhanced_prompt = self._enhance_general_prompt(input_data)
            result = self.general_agent.run_sync(enhanced_prompt)
            return result
    
    def _enhance_threat_prompt(self, input_data: ThreatAnalysisInput) -> str:
        """增強威脅分析提示詞"""
        prompt = f"分析以下威脅查詢：\n\n查詢：{input_data.query}\n"
        
        # 添加向量搜尋結果
        if self.vectorization_service:
            try:
                threat_knowledge = self.vectorization_service.search_similar(
                    collection_name="security_threats",
                    query=input_data.query,
                    n_results=3
                )
                if threat_knowledge:
                    knowledge_text = "\n".join([
                        f"威脅情報 {i+1}: {item['content']}"
                        for i, item in enumerate(threat_knowledge)
                    ])
                    prompt += f"\n相關威脅情報：\n{knowledge_text}\n"
            except Exception as e:
                print(f"威脅知識檢索錯誤: {e}")
        
        if input_data.context:
            prompt += f"\n上下文：{json.dumps(input_data.context, ensure_ascii=False, indent=2)}\n"
        
        return prompt
    
    def _perform_document_search(self, input_data: DocumentRetrievalInput) -> Dict[str, Any]:
        """執行文件搜尋"""
        results = {"documents": [], "total_count": 0}
        
        # 優先使用 Azure Search
        if self.azure_search_service:
            try:
                search_results = self.azure_search_service.search_documents(
                    query=input_data.query,
                    top=input_data.max_results
                )
                if search_results and 'results' in search_results:
                    results["documents"] = search_results['results']
                    results["total_count"] = len(search_results['results'])
                    return results
            except Exception as e:
                print(f"Azure Search 錯誤: {e}")
        
        # 備用向量搜尋
        if self.vectorization_service:
            try:
                collection = input_data.collection_name or "security_documents"
                vector_results = self.vectorization_service.search_similar(
                    collection_name=collection,
                    query=input_data.query,
                    n_results=input_data.max_results
                )
                results["documents"] = vector_results
                results["total_count"] = len(vector_results)
            except Exception as e:
                print(f"向量搜尋錯誤: {e}")
        
        return results
    
    def _build_document_prompt(self, input_data: DocumentRetrievalInput, search_results: Dict[str, Any]) -> str:
        """建構文件檢索提示詞"""
        prompt = f"處理文件檢索查詢：\n\n查詢：{input_data.query}\n"
        
        documents = search_results.get('documents', [])
        if documents:
            doc_text = "\n".join([
                f"文件 {i+1}: {doc.get('content', str(doc))}"
                for i, doc in enumerate(documents[:3])  # 限制顯示前3個文件
            ])
            prompt += f"\n搜尋到的相關文件：\n{doc_text}\n"
        else:
            prompt += "\n未找到相關文件。\n"
        
        prompt += f"\n總共找到 {search_results.get('total_count', 0)} 個結果。"
        return prompt
    
    def _enhance_account_prompt(self, input_data: AccountSecurityInput) -> str:
        """增強帳號安全提示詞"""
        prompt = f"分析帳號安全查詢：\n\n查詢：{input_data.query}\n"
        
        if input_data.user_context:
            prompt += f"\n用戶行為上下文：{json.dumps(input_data.user_context, ensure_ascii=False, indent=2)}\n"
        
        # 添加安全規則知識
        if self.vectorization_service:
            try:
                rules = self.vectorization_service.search_similar(
                    collection_name="account_rules",
                    query=input_data.query,
                    n_results=3
                )
                if rules:
                    rules_text = "\n".join([
                        f"安全規則 {i+1}: {rule['content']}"
                        for i, rule in enumerate(rules)
                    ])
                    prompt += f"\n相關安全規則：\n{rules_text}\n"
            except Exception as e:
                print(f"安全規則檢索錯誤: {e}")
        
        return prompt
    
    def _enhance_network_prompt(self, input_data: NetworkMonitoringInput) -> str:
        """增強網路監控提示詞"""
        prompt = f"分析網路監控查詢：\n\n查詢：{input_data.query}\n"
        
        if input_data.network_context:
            prompt += f"\n網路狀態上下文：{json.dumps(input_data.network_context, ensure_ascii=False, indent=2)}\n"
        
        # 添加網路知識
        if self.vectorization_service:
            try:
                knowledge = self.vectorization_service.search_similar(
                    collection_name="network_knowledge",
                    query=input_data.query,
                    n_results=3
                )
                if knowledge:
                    knowledge_text = "\n".join([
                        f"網路知識 {i+1}: {item['content']}"
                        for i, item in enumerate(knowledge)
                    ])
                    prompt += f"\n相關網路知識：\n{knowledge_text}\n"
            except Exception as e:
                print(f"網路知識檢索錯誤: {e}")
        
        return prompt
    
    def _enhance_general_prompt(self, input_data: GeneralResponseInput) -> str:
        """增強一般回應提示詞"""
        prompt = f"回答一般資訊安全查詢：\n\n查詢：{input_data.query}\n"
        
        if input_data.context:
            prompt += f"\n上下文：{json.dumps(input_data.context, ensure_ascii=False, indent=2)}\n"
        
        return prompt
    
    async def route_and_execute(self, query_input: SecurityQueryInput) -> RouterOutput:
        """
        路由並執行查詢
        
        Args:
            query_input: 安全查詢輸入
            
        Returns:
            路由執行結果
        """
        start_time = datetime.now()
        
        try:
            # 使用路由代理分析並執行
            result = await self.router_agent.run(query_input.query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 添加執行時間和元數據
            result.execution_time = execution_time
            result.metadata = {
                "timestamp": start_time.isoformat(),
                "user_id": query_input.user_id,
                "original_query": query_input.query,
                "context": query_input.context
            }
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 錯誤處理：返回一般回應
            fallback_result = GeneralResponseOutput(
                response=f"處理查詢時發生錯誤：{str(e)}",
                response_type="error",
                suggestions=["請重新表述您的問題", "檢查查詢是否包含敏感資訊"],
                follow_up_questions=["您需要什麼特定的幫助？"]
            )
            
            return RouterOutput(
                selected_agent=AgentType.GENERAL_RESPONSE,
                routing_reasoning=f"因錯誤而使用備用代理：{str(e)}",
                result=fallback_result,
                execution_time=execution_time,
                metadata={
                    "timestamp": start_time.isoformat(),
                    "user_id": query_input.user_id,
                    "original_query": query_input.query,
                    "error": str(e)
                }
            )
    
    def route_and_execute_sync(self, query_input: SecurityQueryInput) -> RouterOutput:
        """
        同步版本的路由執行
        
        Args:
            query_input: 安全查詢輸入
            
        Returns:
            路由執行結果
        """
        start_time = datetime.now()
        
        try:
            # 使用路由代理分析並執行
            result = self.router_agent.run_sync(query_input.query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 添加執行時間和元數據
            result.execution_time = execution_time
            result.metadata = {
                "timestamp": start_time.isoformat(),
                "user_id": query_input.user_id,
                "original_query": query_input.query,
                "context": query_input.context
            }
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 錯誤處理：返回一般回應
            fallback_result = GeneralResponseOutput(
                response=f"處理查詢時發生錯誤：{str(e)}",
                response_type="error",
                suggestions=["請重新表述您的問題", "檢查查詢是否包含敏感資訊"],
                follow_up_questions=["您需要什麼特定的幫助？"]
            )
            
            return RouterOutput(
                selected_agent=AgentType.GENERAL_RESPONSE,
                routing_reasoning=f"因錯誤而使用備用代理：{str(e)}",
                result=fallback_result,
                execution_time=execution_time,
                metadata={
                    "timestamp": start_time.isoformat(),
                    "user_id": query_input.user_id,
                    "original_query": query_input.query,
                    "error": str(e)
                }
            )