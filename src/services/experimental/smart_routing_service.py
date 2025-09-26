"""
智能路由代理服務
整合 Pydantic AI 路由器到現有系統
"""

import os
from typing import Dict, Any, Optional
from datetime import datetime

from src.services.experimental.pydantic_ai_router import (
    PydanticAIRouter,
    SecurityQueryInput,
    RouterOutput
)
from src.services.vectorization_service import VectorizationService
from src.services.azure_search_service import AzureSearchService


class SmartRoutingService:
    """智能路由服務"""
    
    def __init__(self,
                 vectorization_service: Optional[VectorizationService] = None,
                 azure_search_service: Optional[AzureSearchService] = None):
        """
        初始化智能路由服務
        
        Args:
            vectorization_service: 向量化服務實例
            azure_search_service: Azure 搜尋服務實例
        """
        self.vectorization_service = vectorization_service
        self.azure_search_service = azure_search_service
        
        # 初始化 Pydantic AI 路由器
        try:
            self.router = PydanticAIRouter(
                vectorization_service=vectorization_service,
                azure_search_service=azure_search_service
            )
            self.is_available = True
        except Exception as e:
            print(f"Pydantic AI 路由器初始化失敗: {e}")
            self.router = None
            self.is_available = False
    
    def analyze_security_query(self,
                             query: str,
                             context: Optional[Dict[str, Any]] = None,
                             user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        分析安全查詢
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            user_id: 用戶ID
            
        Returns:
            分析結果
        """
        if not self.is_available:
            return self._fallback_response(query, "Pydantic AI 路由器不可用")
        
        try:
            # 準備輸入
            query_input = SecurityQueryInput(
                query=query,
                context=context,
                user_id=user_id
            )
            
            # 執行路由分析
            result = self.router.route_and_execute_sync(query_input)
            
            # 轉換為標準格式
            return self._convert_to_standard_format(result)
            
        except Exception as e:
            return self._fallback_response(query, f"路由分析錯誤: {str(e)}")
    
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
        if not self.is_available:
            return self._fallback_response(query, "Pydantic AI 路由器不可用")
        
        try:
            # 準備輸入
            query_input = SecurityQueryInput(
                query=query,
                context=context,
                user_id=user_id
            )
            
            # 執行異步路由分析
            result = await self.router.route_and_execute(query_input)
            
            # 轉換為標準格式
            return self._convert_to_standard_format(result)
            
        except Exception as e:
            return self._fallback_response(query, f"異步路由分析錯誤: {str(e)}")
    
    def _convert_to_standard_format(self, router_result: RouterOutput) -> Dict[str, Any]:
        """
        將路由器結果轉換為標準格式
        
        Args:
            router_result: 路由器結果
            
        Returns:
            標準格式結果
        """
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
    
    def _fallback_response(self, query: str, error_message: str) -> Dict[str, Any]:
        """
        備用回應
        
        Args:
            query: 查詢內容
            error_message: 錯誤訊息
            
        Returns:
            備用結果
        """
        return {
            "success": False,
            "agent": "fallback",
            "query": query,
            "analysis": f"無法處理查詢: {error_message}",
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "suggestions": [
                "請確認 Azure OpenAI 配置",
                "檢查網路連接",
                "重新表述您的問題"
            ]
        }
    
    def get_status(self) -> Dict[str, Any]:
        """
        取得路由服務狀態
        
        Returns:
            服務狀態
        """
        return {
            "pydantic_ai_available": self.is_available,
            "vectorization_service": self.vectorization_service is not None,
            "azure_search_service": self.azure_search_service is not None,
            "timestamp": datetime.now().isoformat()
        }
    
    def test_routing(self) -> Dict[str, Any]:
        """
        測試路由功能
        
        Returns:
            測試結果
        """
        if not self.is_available:
            return {"success": False, "error": "路由器不可用"}
        
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
                "query": "什麼是資訊安全",
                "expected_agent": "general_response"
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
                    "execution_time": result.get("execution_time", 0)
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
        
        return {
            "success": True,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "correct_routing": correct_routing,
            "success_rate": successful_tests / total_tests if total_tests > 0 else 0,
            "routing_accuracy": correct_routing / total_tests if total_tests > 0 else 0,
            "test_results": results,
            "timestamp": datetime.now().isoformat()
        }


# 工廠函數用於創建服務實例
def create_smart_routing_service(vectorization_service: Optional[VectorizationService] = None,
                                azure_search_service: Optional[AzureSearchService] = None) -> SmartRoutingService:
    """
    創建智能路由服務實例
    
    Args:
        vectorization_service: 向量化服務實例
        azure_search_service: Azure 搜尋服務實例
        
    Returns:
        智能路由服務實例
    """
    return SmartRoutingService(
        vectorization_service=vectorization_service,
        azure_search_service=azure_search_service
    )