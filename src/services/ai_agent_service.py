"""
AI Agent服務模組
實現智慧分析、決策支援和多Agent協作功能
"""

import json
import openai
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from src.services.vectorization_service import VectorizationService

class SecurityAgent:
    """基礎安全Agent類別"""
    
    def __init__(self, 
                 name: str,
                 description: str,
                 vectorization_service: VectorizationService,
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None):
        """
        初始化安全Agent
        
        Args:
            name: Agent名稱
            description: Agent描述
            vectorization_service: 向量化服務實例
            openai_api_key: OpenAI API金鑰
            openai_api_base: OpenAI API基礎URL
        """
        self.name = name
        self.description = description
        self.vectorization_service = vectorization_service
        
        # 設定OpenAI客戶端
        if openai_api_key:
            openai.api_key = openai_api_key
        if openai_api_base:
            openai.api_base = openai_api_base
    
    def analyze(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析查詢並返回結果
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            
        Returns:
            分析結果
        """
        raise NotImplementedError("Subclasses must implement analyze method")
    
    def get_relevant_knowledge(self, query: str, collection_name: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """
        取得相關知識
        
        Args:
            query: 查詢內容
            collection_name: 知識庫集合名稱
            n_results: 返回結果數量
            
        Returns:
            相關知識列表
        """
        return self.vectorization_service.search_similar(
            collection_name=collection_name,
            query=query,
            n_results=n_results
        )
    
    def generate_response(self, 
                         prompt: str,
                         model: str = "gpt-3.5-turbo",
                         max_tokens: int = 1000,
                         temperature: float = 0.7) -> str:
        """
        使用OpenAI生成回應
        
        Args:
            prompt: 提示詞
            model: 使用的模型
            max_tokens: 最大token數
            temperature: 溫度參數
            
        Returns:
            生成的回應
        """
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"生成回應時發生錯誤: {str(e)}"

class ThreatAnalysisAgent(SecurityAgent):
    """威脅分析Agent"""
    
    def __init__(self, vectorization_service: VectorizationService, **kwargs):
        super().__init__(
            name="威脅分析Agent",
            description="專門處理威脅情報查詢、風險評估和攻擊模式識別",
            vectorization_service=vectorization_service,
            **kwargs
        )
    
    def analyze(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析威脅相關查詢
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            
        Returns:
            威脅分析結果
        """
        # 取得相關威脅情報
        threat_knowledge = self.get_relevant_knowledge(query, "security_threats")
        
        # 建構分析提示詞
        prompt = self._build_threat_analysis_prompt(query, threat_knowledge, context)
        
        # 生成分析結果
        analysis_result = self.generate_response(prompt)
        
        return {
            "agent": self.name,
            "query": query,
            "analysis": analysis_result,
            "relevant_threats": threat_knowledge,
            "timestamp": datetime.now().isoformat(),
            "confidence": self._calculate_confidence(threat_knowledge)
        }
    
    def _build_threat_analysis_prompt(self, 
                                    query: str, 
                                    knowledge: List[Dict[str, Any]], 
                                    context: Dict[str, Any] = None) -> str:
        """建構威脅分析提示詞"""
        
        knowledge_text = "\n".join([
            f"威脅資訊 {i+1}: {item['content']}"
            for i, item in enumerate(knowledge)
        ])
        
        context_text = ""
        if context:
            context_text = f"\n上下文資訊: {json.dumps(context, ensure_ascii=False, indent=2)}"
        
        prompt = f"""
你是一個專業的資訊安全威脅分析專家。請根據以下資訊分析用戶的查詢：

用戶查詢: {query}

相關威脅情報:
{knowledge_text}
{context_text}

請提供詳細的威脅分析，包括：
1. 威脅類型和嚴重程度
2. 可能的攻擊向量
3. 影響範圍評估
4. 建議的防護措施
5. 相關的攻擊指標(IoC)

請以專業、清晰的方式回答，並提供具體可行的建議。
"""
        return prompt
    
    def _calculate_confidence(self, knowledge: List[Dict[str, Any]]) -> float:
        """計算分析信心度"""
        if not knowledge:
            return 0.0
        
        # 基於搜尋結果的距離計算信心度
        distances = [item.get('distance', 1.0) for item in knowledge]
        avg_distance = sum(distances) / len(distances)
        confidence = max(0.0, 1.0 - avg_distance)
        
        return round(confidence, 2)

class AccountSecurityAgent(SecurityAgent):
    """帳號安全Agent"""
    
    def __init__(self, vectorization_service: VectorizationService, **kwargs):
        super().__init__(
            name="帳號安全Agent",
            description="專門處理高風險帳號識別、異常行為分析和存取權限審查",
            vectorization_service=vectorization_service,
            **kwargs
        )
    
    def analyze(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析帳號安全相關查詢
        
        Args:
            query: 查詢內容
            context: 上下文資訊（可包含用戶行為資料）
            
        Returns:
            帳號安全分析結果
        """
        # 取得相關安全規則
        rule_knowledge = self.get_relevant_knowledge(query, "account_rules")
        
        # 建構分析提示詞
        prompt = self._build_account_analysis_prompt(query, rule_knowledge, context)
        
        # 生成分析結果
        analysis_result = self.generate_response(prompt)
        
        # 計算風險評分
        risk_score = self._calculate_risk_score(context)
        
        return {
            "agent": self.name,
            "query": query,
            "analysis": analysis_result,
            "risk_score": risk_score,
            "relevant_rules": rule_knowledge,
            "timestamp": datetime.now().isoformat(),
            "recommended_actions": self._get_recommended_actions(risk_score)
        }
    
    def _build_account_analysis_prompt(self, 
                                     query: str, 
                                     knowledge: List[Dict[str, Any]], 
                                     context: Dict[str, Any] = None) -> str:
        """建構帳號安全分析提示詞"""
        
        knowledge_text = "\n".join([
            f"安全規則 {i+1}: {item['content']}"
            for i, item in enumerate(knowledge)
        ])
        
        context_text = ""
        if context:
            context_text = f"\n用戶行為資料: {json.dumps(context, ensure_ascii=False, indent=2)}"
        
        prompt = f"""
你是一個專業的帳號安全分析專家。請根據以下資訊分析用戶的查詢：

用戶查詢: {query}

相關安全規則:
{knowledge_text}
{context_text}

請提供詳細的帳號安全分析，包括：
1. 風險等級評估
2. 異常行為識別
3. 可能的安全威脅
4. 建議的安全措施
5. 監控重點

請以專業、清晰的方式回答，並提供具體可行的建議。
"""
        return prompt
    
    def _calculate_risk_score(self, context: Dict[str, Any] = None) -> int:
        """計算風險評分 (0-100)"""
        if not context:
            return 0
        
        risk_score = 0
        
        # 登入異常
        if context.get('unusual_login_time'):
            risk_score += 20
        if context.get('failed_login_attempts', 0) > 5:
            risk_score += 25
        if context.get('geo_distance', 0) > 1000:
            risk_score += 30
        
        # 權限異常
        if context.get('privilege_escalation'):
            risk_score += 35
        if context.get('access_sensitive_data'):
            risk_score += 20
        
        return min(risk_score, 100)
    
    def _get_recommended_actions(self, risk_score: int) -> List[str]:
        """根據風險評分取得建議行動"""
        if risk_score >= 80:
            return [
                "立即暫停帳號存取",
                "啟動事件回應程序",
                "進行詳細調查",
                "通知安全團隊"
            ]
        elif risk_score >= 60:
            return [
                "加強監控",
                "要求額外驗證",
                "限制敏感資料存取",
                "記錄詳細日誌"
            ]
        elif risk_score >= 40:
            return [
                "持續監控",
                "定期審查權限",
                "提醒用戶注意安全"
            ]
        else:
            return [
                "正常監控",
                "定期安全檢查"
            ]

class NetworkMonitoringAgent(SecurityAgent):
    """網路監控Agent"""
    
    def __init__(self, vectorization_service: VectorizationService, **kwargs):
        super().__init__(
            name="網路監控Agent",
            description="專門處理網路事件分析、故障診斷和效能優化",
            vectorization_service=vectorization_service,
            **kwargs
        )
    
    def analyze(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分析網路監控相關查詢
        
        Args:
            query: 查詢內容
            context: 上下文資訊（可包含網路監控資料）
            
        Returns:
            網路監控分析結果
        """
        # 取得相關網路知識
        network_knowledge = self.get_relevant_knowledge(query, "network_knowledge")
        
        # 建構分析提示詞
        prompt = self._build_network_analysis_prompt(query, network_knowledge, context)
        
        # 生成分析結果
        analysis_result = self.generate_response(prompt)
        
        return {
            "agent": self.name,
            "query": query,
            "analysis": analysis_result,
            "relevant_knowledge": network_knowledge,
            "timestamp": datetime.now().isoformat(),
            "health_status": self._assess_network_health(context)
        }
    
    def _build_network_analysis_prompt(self, 
                                     query: str, 
                                     knowledge: List[Dict[str, Any]], 
                                     context: Dict[str, Any] = None) -> str:
        """建構網路分析提示詞"""
        
        knowledge_text = "\n".join([
            f"網路知識 {i+1}: {item['content']}"
            for i, item in enumerate(knowledge)
        ])
        
        context_text = ""
        if context:
            context_text = f"\n網路監控資料: {json.dumps(context, ensure_ascii=False, indent=2)}"
        
        prompt = f"""
你是一個專業的網路監控分析專家。請根據以下資訊分析用戶的查詢：

用戶查詢: {query}

相關網路知識:
{knowledge_text}
{context_text}

請提供詳細的網路分析，包括：
1. 問題診斷
2. 根本原因分析
3. 影響評估
4. 解決方案建議
5. 預防措施

請以專業、清晰的方式回答，並提供具體可行的建議。
"""
        return prompt
    
    def _assess_network_health(self, context: Dict[str, Any] = None) -> str:
        """評估網路健康狀態"""
        if not context:
            return "unknown"
        
        cpu_usage = context.get('cpu_usage', 0)
        memory_usage = context.get('memory_usage', 0)
        bandwidth_usage = context.get('bandwidth_usage', 0)
        
        if cpu_usage > 90 or memory_usage > 90 or bandwidth_usage > 90:
            return "critical"
        elif cpu_usage > 70 or memory_usage > 70 or bandwidth_usage > 70:
            return "warning"
        else:
            return "healthy"

class AIAgentOrchestrator:
    """AI Agent協調器"""
    
    def __init__(self, vectorization_service: VectorizationService, **kwargs):
        """
        初始化Agent協調器
        
        Args:
            vectorization_service: 向量化服務實例
        """
        self.vectorization_service = vectorization_service
        
        # 初始化各種Agent
        self.agents = {
            'threat_analysis': ThreatAnalysisAgent(vectorization_service, **kwargs),
            'account_security': AccountSecurityAgent(vectorization_service, **kwargs),
            'network_monitoring': NetworkMonitoringAgent(vectorization_service, **kwargs)
        }
    
    def route_query(self, query: str) -> str:
        """
        根據查詢內容路由到適當的Agent
        
        Args:
            query: 查詢內容
            
        Returns:
            Agent名稱
        """
        query_lower = query.lower()
        
        # 威脅分析關鍵字
        threat_keywords = ['威脅', '攻擊', '惡意', '病毒', '釣魚', 'apt', 'malware', 'threat']
        if any(keyword in query_lower for keyword in threat_keywords):
            return 'threat_analysis'
        
        # 帳號安全關鍵字
        account_keywords = ['帳號', '登入', '權限', '用戶', '異常', 'account', 'login', 'user']
        if any(keyword in query_lower for keyword in account_keywords):
            return 'account_security'
        
        # 網路監控關鍵字
        network_keywords = ['網路', '網管', '設備', '故障', '效能', 'network', 'device', 'performance']
        if any(keyword in query_lower for keyword in network_keywords):
            return 'network_monitoring'
        
        # 預設使用威脅分析Agent
        return 'threat_analysis'
    
    def analyze_query(self, 
                     query: str, 
                     context: Dict[str, Any] = None,
                     agent_name: Optional[str] = None) -> Dict[str, Any]:
        """
        分析查詢
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            agent_name: 指定的Agent名稱
            
        Returns:
            分析結果
        """
        # 自動路由或使用指定Agent
        if not agent_name:
            agent_name = self.route_query(query)
        
        if agent_name not in self.agents:
            return {
                "error": f"Unknown agent: {agent_name}",
                "available_agents": list(self.agents.keys())
            }
        
        # 執行分析
        agent = self.agents[agent_name]
        result = agent.analyze(query, context)
        
        # 添加路由資訊
        result['routed_agent'] = agent_name
        result['available_agents'] = list(self.agents.keys())
        
        return result
    
    def multi_agent_analysis(self, 
                           query: str, 
                           context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        多Agent協作分析
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            
        Returns:
            綜合分析結果
        """
        results = {}
        
        # 讓所有Agent分析同一個查詢
        for agent_name, agent in self.agents.items():
            try:
                results[agent_name] = agent.analyze(query, context)
            except Exception as e:
                results[agent_name] = {
                    "error": str(e),
                    "agent": agent_name
                }
        
        # 綜合分析結果
        summary = self._synthesize_results(query, results)
        
        return {
            "query": query,
            "multi_agent_results": results,
            "synthesis": summary,
            "timestamp": datetime.now().isoformat()
        }
    
    def _synthesize_results(self, query: str, results: Dict[str, Any]) -> str:
        """綜合多Agent分析結果"""
        
        # 提取各Agent的分析結果
        analyses = []
        for agent_name, result in results.items():
            if 'analysis' in result:
                analyses.append(f"{agent_name}: {result['analysis']}")
        
        if not analyses:
            return "無法取得有效的分析結果"
        
        # 建構綜合分析提示詞
        prompt = f"""
請綜合以下多個AI安全專家的分析結果，提供一個統一、全面的安全建議：

查詢: {query}

各專家分析:
{chr(10).join(analyses)}

請提供：
1. 綜合風險評估
2. 統一的建議措施
3. 優先處理事項
4. 長期改善建議

請以專業、清晰的方式回答。
"""
        
        # 使用威脅分析Agent生成綜合結果
        threat_agent = self.agents['threat_analysis']
        return threat_agent.generate_response(prompt)

