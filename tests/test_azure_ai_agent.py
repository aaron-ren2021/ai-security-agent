"""
Azure AI Agent 整合測試
測試 Azure AI Agent 服務和整合功能
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys

# 添加src路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.ai_agent_service import AzureAIAgentService, AIAgentOrchestrator
from services.vectorization_service import VectorizationService


class TestAzureAIAgentService(unittest.TestCase):
    """測試 AzureAIAgentService 類別"""
    
    def setUp(self):
        """測試前置設定"""
        self.endpoint = "https://xcloudren-foundry.services.ai.azure.com/api/projects/llmtest-project-001"
        self.agent_id = "asst_Blv8Anlvv0FfP5bG7e19kGFU"
        
    @patch('services.ai_agent_service.AIProjectClient')
    @patch('services.ai_agent_service.DefaultAzureCredential')
    def test_azure_agent_initialization(self, mock_credential, mock_client):
        """測試 Azure AI Agent 初始化"""
        # 模擬初始化
        mock_credential_instance = Mock()
        mock_credential.return_value = mock_credential_instance
        
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        mock_agent = Mock()
        mock_agent.id = self.agent_id
        mock_client_instance.agents.get_agent.return_value = mock_agent
        
        # 創建服務實例
        service = AzureAIAgentService(
            endpoint=self.endpoint,
            agent_id=self.agent_id
        )
        
        # 驗證初始化
        self.assertEqual(service.endpoint, self.endpoint)
        self.assertEqual(service.agent_id, self.agent_id)
        mock_client.assert_called_once_with(
            credential=mock_credential_instance,
            endpoint=self.endpoint
        )
        mock_client_instance.agents.get_agent.assert_called_once_with(self.agent_id)
    
    @patch('services.ai_agent_service.AIProjectClient')
    @patch('services.ai_agent_service.DefaultAzureCredential')
    def test_create_thread(self, mock_credential, mock_client):
        """測試創建對話線程"""
        # 設定模擬
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        mock_agent = Mock()
        mock_client_instance.agents.get_agent.return_value = mock_agent
        
        mock_thread = Mock()
        mock_thread.id = "thread_12345"
        mock_client_instance.agents.threads.create.return_value = mock_thread
        
        # 創建服務並測試
        service = AzureAIAgentService(self.endpoint, self.agent_id)
        thread_id = service.create_thread()
        
        self.assertEqual(thread_id, "thread_12345")
        mock_client_instance.agents.threads.create.assert_called_once()
    
    @patch('services.ai_agent_service.AIProjectClient')
    @patch('services.ai_agent_service.DefaultAzureCredential')
    def test_send_message(self, mock_credential, mock_client):
        """測試發送訊息"""
        # 設定模擬
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        mock_agent = Mock()
        mock_client_instance.agents.get_agent.return_value = mock_agent
        
        mock_message = Mock()
        mock_message.id = "msg_12345"
        mock_client_instance.agents.messages.create.return_value = mock_message
        
        # 創建服務並測試
        service = AzureAIAgentService(self.endpoint, self.agent_id)
        result = service.send_message("thread_12345", "Test message")
        
        self.assertEqual(result["id"], "msg_12345")
        self.assertEqual(result["content"], "Test message")
        self.assertEqual(result["role"], "user")
        mock_client_instance.agents.messages.create.assert_called_once_with(
            thread_id="thread_12345",
            role="user",
            content="Test message"
        )
    
    @patch('services.ai_agent_service.AIProjectClient')
    @patch('services.ai_agent_service.DefaultAzureCredential')
    def test_analyze_with_azure_agent(self, mock_credential, mock_client):
        """測試使用 Azure AI Agent 進行分析"""
        # 設定模擬
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        
        mock_agent = Mock()
        mock_agent.id = self.agent_id
        mock_client_instance.agents.get_agent.return_value = mock_agent
        
        # 模擬線程創建
        mock_thread = Mock()
        mock_thread.id = "thread_12345"
        mock_client_instance.agents.threads.create.return_value = mock_thread
        
        # 模擬訊息創建
        mock_message = Mock()
        mock_message.id = "msg_12345"
        mock_client_instance.agents.messages.create.return_value = mock_message
        
        # 模擬運行
        mock_run = Mock()
        mock_run.id = "run_12345"
        mock_run.status = "completed"
        mock_client_instance.agents.runs.create_and_process.return_value = mock_run
        
        # 模擬回應訊息
        mock_response_message = Mock()
        mock_response_message.role = "assistant"
        mock_text_message = Mock()
        mock_text_message.text.value = "這是 Azure AI Agent 的回應"
        mock_response_message.text_messages = [mock_text_message]
        mock_response_message.created_at = "2025-01-01T00:00:00Z"
        
        mock_client_instance.agents.messages.list.return_value = [mock_response_message]
        
        # 創建服務並測試
        service = AzureAIAgentService(self.endpoint, self.agent_id)
        result = service.analyze_with_azure_agent("Hi 網路監控Agent")
        
        # 驗證結果
        self.assertEqual(result["agent"], "Azure AI Agent")
        self.assertEqual(result["query"], "Hi 網路監控Agent")
        self.assertEqual(result["analysis"], "這是 Azure AI Agent 的回應")
        self.assertEqual(result["status"], "completed")


class TestAIAgentOrchestratorWithAzure(unittest.TestCase):
    """測試 AIAgentOrchestrator 與 Azure AI Agent 的整合"""
    
    def setUp(self):
        """測試前置設定"""
        self.vectorization_service = Mock(spec=VectorizationService)
        self.azure_config = {
            'endpoint': "https://xcloudren-foundry.services.ai.azure.com/api/projects/llmtest-project-001",
            'agent_id': "asst_Blv8Anlvv0FfP5bG7e19kGFU"
        }
    
    @patch('services.ai_agent_service.AzureAIAgentService')
    def test_orchestrator_with_azure_config(self, mock_azure_service):
        """測試協調器與 Azure Agent 配置"""
        # 設定模擬
        mock_azure_instance = Mock()
        mock_azure_service.return_value = mock_azure_instance
        
        # 創建協調器
        orchestrator = AIAgentOrchestrator(
            vectorization_service=self.vectorization_service,
            azure_agent_config=self.azure_config
        )
        
        # 驗證 Azure Agent 被正確初始化
        mock_azure_service.assert_called_once_with(
            endpoint=self.azure_config['endpoint'],
            agent_id=self.azure_config['agent_id']
        )
        
        # 驗證 Azure Agent 被添加到 agents 中
        self.assertIn('azure_ai', orchestrator.agents)
        self.assertEqual(orchestrator.agents['azure_ai'], mock_azure_instance)
    
    def test_orchestrator_without_azure_config(self):
        """測試協調器無 Azure Agent 配置"""
        orchestrator = AIAgentOrchestrator(
            vectorization_service=self.vectorization_service
        )
        
        # 驗證沒有 Azure Agent
        self.assertNotIn('azure_ai', orchestrator.agents)
        self.assertIsNone(orchestrator.azure_agent)
    
    @patch('services.ai_agent_service.AzureAIAgentService')
    def test_route_query_to_azure_agent(self, mock_azure_service):
        """測試查詢路由到 Azure Agent"""
        mock_azure_instance = Mock()
        mock_azure_service.return_value = mock_azure_instance
        
        orchestrator = AIAgentOrchestrator(
            vectorization_service=self.vectorization_service,
            azure_agent_config=self.azure_config
        )
        
        # 測試路由到 Azure Agent
        result = orchestrator.route_query("Hi 網路監控Agent")
        self.assertEqual(result, 'azure_ai')
        
        result = orchestrator.route_query("Azure AI agent 幫我分析")
        self.assertEqual(result, 'azure_ai')
    
    @patch('services.ai_agent_service.AzureAIAgentService')
    def test_analyze_query_with_azure_agent(self, mock_azure_service):
        """測試使用 Azure Agent 分析查詢"""
        mock_azure_instance = Mock()
        mock_azure_instance.analyze_with_azure_agent.return_value = {
            "agent": "Azure AI Agent",
            "query": "Hi 網路監控Agent",
            "analysis": "這是 Azure AI Agent 的回應",
            "status": "completed"
        }
        mock_azure_service.return_value = mock_azure_instance
        
        orchestrator = AIAgentOrchestrator(
            vectorization_service=self.vectorization_service,
            azure_agent_config=self.azure_config
        )
        
        result = orchestrator.analyze_query("Hi 網路監控Agent", agent_name='azure_ai')
        
        # 驗證結果
        self.assertEqual(result["agent"], "Azure AI Agent")
        self.assertEqual(result["routed_agent"], "azure_ai")
        self.assertIn('azure_ai', result["available_agents"])
        mock_azure_instance.analyze_with_azure_agent.assert_called_once_with("Hi 網路監控Agent")


class TestEnvironmentConfiguration(unittest.TestCase):
    """測試環境配置"""
    
    @patch.dict(os.environ, {
        'AZURE_AI_ENDPOINT': 'https://test-endpoint.azure.com',
        'AZURE_AI_AGENT_ID': 'test_agent_123'
    })
    def test_environment_variables_present(self):
        """測試環境變數存在時的行為"""
        endpoint = os.getenv('AZURE_AI_ENDPOINT')
        agent_id = os.getenv('AZURE_AI_AGENT_ID')
        
        self.assertEqual(endpoint, 'https://test-endpoint.azure.com')
        self.assertEqual(agent_id, 'test_agent_123')
    
    def test_environment_variables_missing(self):
        """測試環境變數缺失時的行為"""
        # 確保環境變數不存在
        if 'AZURE_AI_ENDPOINT' in os.environ:
            del os.environ['AZURE_AI_ENDPOINT']
        if 'AZURE_AI_AGENT_ID' in os.environ:
            del os.environ['AZURE_AI_AGENT_ID']
        
        endpoint = os.getenv('AZURE_AI_ENDPOINT')
        agent_id = os.getenv('AZURE_AI_AGENT_ID')
        
        self.assertIsNone(endpoint)
        self.assertIsNone(agent_id)


if __name__ == '__main__':
    unittest.main()
