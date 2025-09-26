"""
Pydantic AI 智能路由系統 - 完整版
整合所有路由、代理和模型功能到單一檔案
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from openai import AzureOpenAI

# 嘗試導入可選依賴
try:
    from src.services.vectorization_service import VectorizationService
except ImportError:
    VectorizationService = None

try:
    from src.services.azure_search_service import AzureSearchService
except ImportError:
    AzureSearchService = None


# ===== 數據模型定義 =====

class AgentType(str, Enum):
    """代理類型MVP 版"""
    THREAT_ANALYSIS = "threat_analysis"       # 威脅情資 / TTP / IOC / 攻擊鏈
    NETWORK_SECURITY = "network_security"     # 主機/埠/服務/版本/誤設（弱掃核心）
    ACCOUNT_SECURITY = "account_security"     # 密碼/MFA/權限/登入異常
    GENERAL_RESPONSE = "general_response"     # 模糊/閒聊/無法分類
    UNKNOWN = "unknown"                        # 路由信心低時回退（強烈建議加）



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


# ===== 智能路由系統主類 =====

class SmartSecurityRouter:
    """智能安全路由器 - 完整版"""
    
    def __init__(self,
                 vectorization_service: Optional[Any] = None,
                 azure_search_service: Optional[Any] = None,
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None,
                 openai_api_version: str = "2024-02-15-preview",
                 chat_deployment: str = "gpt-4o"):
        """
        初始化智能安全路由器
        
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
        
        # 路由統計
        self.routing_stats = {
            "total_queries": 0,
            "agent_usage": {},
            "avg_execution_time": 0.0,
            "success_rate": 0.0
        }
    
    def _initialize_agents(self):
        """初始化各種專門化代理"""
        
        # 威脅分析代理
        self.threat_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的資訊安全威脅分析專家。
            請根據用戶查詢分析可能的威脅，包括威脅類型、嚴重程度、攻擊向量、
            影響評估、緩解策略和相關攻擊指標。
            
            你的分析應該：
            1. 準確識別威脅類型（如惡意軟體、釣魚攻擊、APT、DDoS等）
            2. 評估嚴重程度（低/中/高/極高）
            3. 列出可能的攻擊向量
            4. 評估潛在影響
            5. 提供具體的緩解策略
            6. 識別相關的攻擊指標(IoC)
            7. 給出分析信心度（0-1）
            
            請使用結構化的格式回應，確保所有字段都有適當的值。""",
            output_type=ThreatAnalysisOutput
        )
        
        # 文件檢索代理
        self.document_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的文件檢索和知識管理專家。
            請根據用戶查詢從知識庫中檢索相關文件，並提供有用的摘要。
            
            你的任務包括：
            1. 理解用戶的查詢意圖
            2. 分析檢索到的文件相關性
            3. 提供搜尋結果摘要
            4. 解釋查詢理解過程
            5. 總結文件數量和品質
            
            請確保結果準確且有用，如果沒有找到相關文件，請誠實說明。""",
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
            
            請基於最佳實踐提供建議，考慮登入行為、權限管理、異常活動等因素。""",
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
            
            請提供具體可行的技術建議，包括網路設備、效能優化、故障排除等。""",
            output_type=NetworkMonitoringOutput
        )
        
        # 一般回應代理
        self.general_agent = Agent(
            model=self.model,
            instructions="""你是一個專業的資訊安全顧問。
            請回答一般性的資訊安全問題，提供有用的建議和指導。
            
            你的回應應該：
            1. 提供清晰準確的答案
            2. 分類回應類型（諮詢、教育、指導等）
            3. 提供相關建議
            4. 建議後續問題
            
            請確保答案專業且有用，涵蓋資安政策、最佳實踐、合規要求等。""",
            output_type=GeneralResponseOutput
        )
        
        # 主路由代理
        self.router_agent = Agent(
            model=self.model,
            instructions="""你是一個智能路由器，負責分析用戶查詢並選擇最適當的專門代理。
            
            請根據查詢內容選擇以下代理之一：
            
            🛡️ threat_analysis - 適用於：
            - 威脅分析、惡意軟體、攻擊模式、APT
            - 漏洞分析、安全事件調查
            - 關鍵字：威脅、攻擊、惡意、病毒、釣魚、APT、malware、threat、vulnerability
            
            📄 document_retrieval - 適用於：
            - 文件搜尋、知識查詢、政策查找
            - 程序查詢、規範檢索
            - 關鍵字：搜尋、文件、政策、程序、規範、標準、查找
            
            👤 account_security - 適用於：
            - 帳號安全、登入異常、權限管理
            - 用戶行為分析、身份驗證
            - 關鍵字：帳號、登入、權限、用戶、異常、account、login、user、authentication
            
            🌐 network_monitoring - 適用於：
            - 網路問題、設備故障、效能問題
            - 連接問題、網路診斷
            - 關鍵字：網路、網管、設備、故障、效能、network、device、performance
            
            💬 general_response - 適用於：
            - 一般性問題、資安諮詢、最佳實踐
            - 教育性問題、基礎概念解釋
            - 其他不明確分類的查詢
            
            請分析查詢並解釋選擇理由，然後調用對應的代理工具。
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
                        f"威脅情報 {i+1}: {item.get('content', str(item))}"
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
                        f"安全規則 {i+1}: {rule.get('content', str(rule))}"
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
                        f"網路知識 {i+1}: {item.get('content', str(item))}"
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
    
    def analyze_security_query(self,
                             query: str,
                             context: Optional[Dict[str, Any]] = None,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        分析安全查詢（同步版本）
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            user_id: 用戶ID
            
        Returns:
            分析結果
        """
        start_time = datetime.now()
        
        try:
            # 準備輸入
            query_input = SecurityQueryInput(
                query=query,
                context=context,
                user_id=user_id
            )
            
            # 執行路由分析
            result = self.router_agent.run_sync(query_input.query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 更新統計
            self._update_stats(result.selected_agent.value, execution_time, True)
            
            # 添加執行時間和元數據
            result.execution_time = execution_time
            result.metadata = {
                "timestamp": start_time.isoformat(),
                "user_id": query_input.user_id,
                "original_query": query_input.query,
                "context": query_input.context
            }
            
            # 轉換為標準格式
            return self._convert_to_standard_format(result)
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats("error", execution_time, False)
            
            return self._create_fallback_response(query, f"路由分析錯誤: {str(e)}", start_time)
    
    async def analyze_security_query_async(self,
                                         query: str,
                                         context: Optional[Dict[str, Any]] = None,
                                         user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        異步分析安全查詢
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            user_id: 用戶ID
            
        Returns:
            分析結果
        """
        start_time = datetime.now()
        
        try:
            # 準備輸入
            query_input = SecurityQueryInput(
                query=query,
                context=context,
                user_id=user_id
            )
            
            # 執行異步路由分析
            result = await self.router_agent.run(query_input.query)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # 更新統計
            self._update_stats(result.selected_agent.value, execution_time, True)
            
            # 添加執行時間和元數據
            result.execution_time = execution_time
            result.metadata = {
                "timestamp": start_time.isoformat(),
                "user_id": query_input.user_id,
                "original_query": query_input.query,
                "context": query_input.context
            }
            
            # 轉換為標準格式
            return self._convert_to_standard_format(result)
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._update_stats("error", execution_time, False)
            
            return self._create_fallback_response(query, f"異步路由分析錯誤: {str(e)}", start_time)
    
    def _convert_to_standard_format(self, router_result: RouterOutput) -> Dict[str, Any]:
        """將路由器結果轉換為標準格式"""
        # 基礎結果
        result = {
            "success": True,
            "agent": router_result.selected_agent.value,
            "routing_reasoning": router_result.routing_reasoning,
            "execution_time": router_result.execution_time,
            "timestamp": router_result.metadata.get("timestamp"),
            "query": router_result.metadata.get("original_query")
        }
        
        # 處理不同類型的代理結果
        agent_result = router_result.result
        result_dict = agent_result.model_dump() if hasattr(agent_result, 'model_dump') else agent_result
        
        if router_result.selected_agent.value == "threat_analysis":
            result.update({
                "analysis": f"威脅類型: {result_dict.get('threat_type', 'N/A')}\n"
                          f"嚴重程度: {result_dict.get('severity_level', 'N/A')}\n"
                          f"影響評估: {result_dict.get('impact_assessment', 'N/A')}",
                "threat_analysis": result_dict,
                "confidence": result_dict.get('confidence_score', 0.0)
            })
            
        elif router_result.selected_agent.value == "document_retrieval":
            result.update({
                "analysis": result_dict.get('search_summary', ''),
                "relevant_documents": result_dict.get('relevant_documents', []),
                "total_results": result_dict.get('total_results', 0),
                "query_interpretation": result_dict.get('query_interpretation', '')
            })
            
        elif router_result.selected_agent.value == "account_security":
            result.update({
                "analysis": f"風險等級: {result_dict.get('risk_level', 'N/A')}\n"
                          f"風險評分: {result_dict.get('risk_score', 0)}/100",
                "account_security": result_dict,
                "risk_score": result_dict.get('risk_score', 0)
            })
            
        elif router_result.selected_agent.value == "network_monitoring":
            result.update({
                "analysis": f"健康狀態: {result_dict.get('health_status', 'N/A')}\n"
                          f"問題診斷: {result_dict.get('issue_diagnosis', 'N/A')}",
                "network_monitoring": result_dict,
                "health_status": result_dict.get('health_status', 'unknown')
            })
            
        else:  # general_response
            result.update({
                "analysis": result_dict.get('response', ''),
                "general_response": result_dict,
                "suggestions": result_dict.get('suggestions', [])
            })
        
        # 添加原始結果供進階使用
        result["raw_result"] = result_dict
        result["metadata"] = router_result.metadata
        
        return result
    
    def _create_fallback_response(self, query: str, error_message: str, start_time: datetime) -> Dict[str, Any]:
        """創建備用回應"""
        return {
            "success": False,
            "agent": "fallback",
            "query": query,
            "analysis": f"無法處理查詢: {error_message}",
            "error": error_message,
            "timestamp": start_time.isoformat(),
            "execution_time": (datetime.now() - start_time).total_seconds(),
            "suggestions": [
                "請確認 Azure OpenAI 配置",
                "檢查網路連接",
                "重新表述您的問題"
            ]
        }
    
    def _update_stats(self, agent_type: str, execution_time: float, success: bool):
        """更新路由統計"""
        self.routing_stats["total_queries"] += 1
        
        if agent_type not in self.routing_stats["agent_usage"]:
            self.routing_stats["agent_usage"][agent_type] = {"count": 0, "success": 0}
        
        self.routing_stats["agent_usage"][agent_type]["count"] += 1
        if success:
            self.routing_stats["agent_usage"][agent_type]["success"] += 1
        
        # 更新平均執行時間
        total = self.routing_stats["total_queries"]
        current_avg = self.routing_stats["avg_execution_time"]
        self.routing_stats["avg_execution_time"] = (current_avg * (total - 1) + execution_time) / total
        
        # 更新成功率
        total_success = sum(agent["success"] for agent in self.routing_stats["agent_usage"].values())
        self.routing_stats["success_rate"] = total_success / total if total > 0 else 0.0
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """取得路由統計資訊"""
        return {
            **self.routing_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """取得路由服務狀態"""
        return {
            "router_available": True,
            "vectorization_service": self.vectorization_service is not None,
            "azure_search_service": self.azure_search_service is not None,
            "azure_openai_configured": bool(self.azure_client),
            "total_agents": 5,
            "available_agents": [agent.value for agent in AgentType],
            "timestamp": datetime.now().isoformat(),
            "stats": self.routing_stats
        }
    
    def test_routing_accuracy(self) -> Dict[str, Any]:
        """測試路由準確性"""
        test_queries = [
            {
                "query": "分析 APT 攻擊威脅",
                "expected_agent": "threat_analysis"
            },
            {
                "query": "搜尋資安政策文件",
                "expected_agent": "document_retrieval"
            },
            {
                "query": "檢查帳號異常登入",
                "expected_agent": "account_security"
            },
            {
                "query": "網路設備故障診斷",
                "expected_agent": "network_monitoring"
            },
            {
                "query": "什麼是資訊安全？",
                "expected_agent": "general_response"
            },
            {
                "query": "如何防範勒索軟體攻擊？",
                "expected_agent": "threat_analysis"
            },
            {
                "query": "查找密碼政策文件",
                "expected_agent": "document_retrieval"
            },
            {
                "query": "用戶權限管理最佳實踐",
                "expected_agent": "account_security"
            }
        ]
        
        results = []
        for test in test_queries:
            try:
                result = self.analyze_security_query(test["query"])
                results.append({
                    "query": test["query"],
                    "expected_agent": test["expected_agent"],
                    "actual_agent": result.get("agent"),
                    "routing_correct": result.get("agent") == test["expected_agent"],
                    "success": result.get("success", False),
                    "execution_time": result.get("execution_time", 0),
                    "reasoning": result.get("routing_reasoning", "")
                })
            except Exception as e:
                results.append({
                    "query": test["query"],
                    "expected_agent": test["expected_agent"],
                    "error": str(e),
                    "routing_correct": False,
                    "success": False
                })
        
        # 統計結果
        total_tests = len(results)
        successful_tests = sum(1 for r in results if r.get("success"))
        correct_routing = sum(1 for r in results if r.get("routing_correct"))
        avg_execution_time = sum(r.get("execution_time", 0) for r in results) / total_tests
        
        return {
            "success": True,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "correct_routing": correct_routing,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "routing_accuracy": correct_routing / total_tests if total_tests > 0 else 0,
            "avg_execution_time": avg_execution_time,
            "test_results": results,
            "timestamp": datetime.now().isoformat()
        }


# ===== 工廠函數和便利函數 =====

def create_smart_security_router(vectorization_service: Optional[Any] = None,
                                azure_search_service: Optional[Any] = None,
                                **kwargs) -> SmartSecurityRouter:
    """
    創建智能安全路由器實例
    
    Args:
        vectorization_service: 向量化服務實例
        azure_search_service: Azure 搜尋服務實例
        **kwargs: 其他配置參數
        
    Returns:
        智能安全路由器實例
    """
    return SmartSecurityRouter(
        vectorization_service=vectorization_service,
        azure_search_service=azure_search_service,
        **kwargs
    )


# ===== 向後兼容性類別 =====

class SmartRoutingService:
    """向後兼容的智能路由服務"""
    
    def __init__(self, vectorization_service=None, azure_search_service=None):
        """初始化兼容性包裝器"""
        try:
            self.router = SmartSecurityRouter(
                vectorization_service=vectorization_service,
                azure_search_service=azure_search_service
            )
            self.is_available = True
        except Exception as e:
            print(f"智能路由器初始化失敗: {e}")
            self.router = None
            self.is_available = False
    
    def analyze_security_query(self, query: str, context=None, user_id=None):
        """分析安全查詢（兼容舊介面）"""
        if not self.is_available:
            return self._fallback_response(query, "路由器不可用")
        
        return self.router.analyze_security_query(query, context, user_id)
    
    async def analyze_security_query_async(self, query: str, context=None, user_id=None):
        """異步分析安全查詢（兼容舊介面）"""
        if not self.is_available:
            return self._fallback_response(query, "路由器不可用")
        
        return await self.router.analyze_security_query_async(query, context, user_id)
    
    def get_status(self):
        """取得服務狀態"""
        if not self.is_available:
            return {"router_available": False, "error": "路由器不可用"}
        
        return self.router.get_status()
    
    def test_routing(self):
        """測試路由功能"""
        if not self.is_available:
            return {"success": False, "error": "路由器不可用"}
        
        return self.router.test_routing_accuracy()
    
    def _fallback_response(self, query: str, error_message: str):
        """備用回應"""
        return {
            "success": False,
            "agent": "fallback",
            "query": query,
            "analysis": f"無法處理查詢: {error_message}",
            "error": error_message,
            "timestamp": datetime.now().isoformat()
        }


# ===== 主程式入口（用於測試） =====

if __name__ == "__main__":
    """主程式入口 - 用於測試路由系統"""
    
    print("🤖 智能安全路由系統 - 測試模式")
    print("=" * 50)
    
    try:
        # 創建路由器實例
        router = SmartSecurityRouter()
        
        # 測試查詢
        test_queries = [
            "分析 APT 攻擊威脅",
            "搜尋資安政策文件",
            "檢查帳號異常登入",
            "網路設備故障診斷",
            "什麼是資訊安全？"
        ]
        
        print("📊 路由測試結果：")
        print("-" * 30)
        
        for query in test_queries:
            print(f"\n查詢: {query}")
            result = router.analyze_security_query(query)
            
            if result.get("success"):
                print(f"✅ 路由到: {result.get('agent')}")
                print(f"⏱️  執行時間: {result.get('execution_time', 0):.2f}秒")
                print(f"💭 路由理由: {result.get('routing_reasoning', 'N/A')}")
            else:
                print(f"❌ 錯誤: {result.get('error')}")
        
        # 顯示統計
        stats = router.get_routing_stats()
        print(f"\n📈 路由統計:")
        print(f"總查詢數: {stats['total_queries']}")
        print(f"成功率: {stats['success_rate']:.2%}")
        print(f"平均執行時間: {stats['avg_execution_time']:.2f}秒")
        
        print("\n🎯 路由測試完成！")
        
    except Exception as e:
        print(f"❌ 測試失敗: {e}")
        print("請確認 Azure OpenAI 配置是否正確")