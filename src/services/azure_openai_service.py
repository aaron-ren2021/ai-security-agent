"""
Azure OpenAI服務模組
專門處理Azure OpenAI API的整合和配置
"""

import os
import openai
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

class AzureOpenAIService:
    """Azure OpenAI服務類別"""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 api_base: Optional[str] = None,
                 api_version: str = "2023-05-15"):
        """
        初始化Azure OpenAI服務
        
        Args:
            api_key: Azure OpenAI API金鑰
            api_base: Azure OpenAI API基礎URL
            api_version: API版本
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.api_base = api_base or os.getenv('OPENAI_API_BASE')
        self.api_version = api_version
        
        # 設定OpenAI客戶端
        if self.api_key:
            openai.api_key = self.api_key
        if self.api_base:
            openai.api_base = self.api_base
        
        openai.api_type = "azure"
        openai.api_version = self.api_version
        
        # 預設模型配置
        self.default_chat_model = "gpt-35-turbo"  # Azure部署名稱
        self.default_embedding_model = "text-embedding-ada-002"  # Azure部署名稱
    
    def test_connection(self) -> Dict[str, Any]:
        """
        測試Azure OpenAI連接
        
        Returns:
            測試結果
        """
        try:
            # 測試聊天完成
            response = openai.ChatCompletion.create(
                engine=self.default_chat_model,
                messages=[{"role": "user", "content": "Hello, this is a connection test."}],
                max_tokens=10,
                temperature=0
            )
            
            chat_test = {
                "status": "success",
                "model": self.default_chat_model,
                "response": response.choices[0].message.content
            }
            
        except Exception as e:
            chat_test = {
                "status": "failed",
                "model": self.default_chat_model,
                "error": str(e)
            }
        
        try:
            # 測試嵌入
            embedding_response = openai.Embedding.create(
                engine=self.default_embedding_model,
                input="This is a test for embedding."
            )
            
            embedding_test = {
                "status": "success",
                "model": self.default_embedding_model,
                "embedding_length": len(embedding_response.data[0].embedding)
            }
            
        except Exception as e:
            embedding_test = {
                "status": "failed",
                "model": self.default_embedding_model,
                "error": str(e)
            }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "api_base": self.api_base,
            "api_version": self.api_version,
            "chat_completion": chat_test,
            "embedding": embedding_test
        }
    
    def generate_chat_response(self, 
                              messages: List[Dict[str, str]],
                              model: Optional[str] = None,
                              max_tokens: int = 1000,
                              temperature: float = 0.7,
                              system_prompt: Optional[str] = None) -> Dict[str, Any]:
        """
        生成聊天回應
        
        Args:
            messages: 對話訊息列表
            model: 使用的模型名稱
            max_tokens: 最大token數
            temperature: 溫度參數
            system_prompt: 系統提示詞
            
        Returns:
            生成結果
        """
        try:
            model = model or self.default_chat_model
            
            # 準備訊息
            formatted_messages = []
            
            # 添加系統提示詞
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})
            
            # 添加對話訊息
            formatted_messages.extend(messages)
            
            # 呼叫Azure OpenAI API
            response = openai.ChatCompletion.create(
                engine=model,
                messages=formatted_messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            return {
                "success": True,
                "response": response.choices[0].message.content,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
    
    def generate_embedding(self, 
                          text: str,
                          model: Optional[str] = None) -> Dict[str, Any]:
        """
        生成文字嵌入向量
        
        Args:
            text: 要嵌入的文字
            model: 使用的模型名稱
            
        Returns:
            嵌入結果
        """
        try:
            model = model or self.default_embedding_model
            
            response = openai.Embedding.create(
                engine=model,
                input=text
            )
            
            return {
                "success": True,
                "embedding": response.data[0].embedding,
                "model": model,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "model": model,
                "timestamp": datetime.now().isoformat()
            }
    
    def analyze_security_query(self, 
                              query: str,
                              context: Optional[str] = None,
                              analysis_type: str = "general") -> Dict[str, Any]:
        """
        分析資訊安全查詢
        
        Args:
            query: 查詢內容
            context: 上下文資訊
            analysis_type: 分析類型 (general, threat, account, network)
            
        Returns:
            分析結果
        """
        # 根據分析類型選擇系統提示詞
        system_prompts = {
            "general": """你是一個專業的資訊安全專家，請根據用戶的查詢提供專業的安全分析和建議。
請以清晰、專業的方式回答，並提供具體可行的建議。""",
            
            "threat": """你是一個專業的威脅分析專家，專門處理威脅情報查詢、風險評估和攻擊模式識別。
請提供詳細的威脅分析，包括威脅類型、嚴重程度、攻擊向量、影響範圍和防護措施。""",
            
            "account": """你是一個專業的帳號安全分析專家，專門處理高風險帳號識別、異常行為分析和存取權限審查。
請提供詳細的帳號安全分析，包括風險等級評估、異常行為識別、安全威脅和建議措施。""",
            
            "network": """你是一個專業的網路監控分析專家，專門處理網路事件分析、故障診斷和效能優化。
請提供詳細的網路分析，包括問題診斷、根本原因分析、影響評估、解決方案和預防措施。"""
        }
        
        system_prompt = system_prompts.get(analysis_type, system_prompts["general"])
        
        # 準備用戶訊息
        user_message = f"查詢: {query}"
        if context:
            user_message += f"\n\n上下文資訊: {context}"
        
        messages = [{"role": "user", "content": user_message}]
        
        # 生成回應
        result = self.generate_chat_response(
            messages=messages,
            system_prompt=system_prompt,
            temperature=0.7
        )
        
        # 添加分析類型資訊
        if result["success"]:
            result["analysis_type"] = analysis_type
            result["query"] = query
        
        return result
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        取得模型資訊
        
        Returns:
            模型資訊
        """
        return {
            "chat_model": self.default_chat_model,
            "embedding_model": self.default_embedding_model,
            "api_version": self.api_version,
            "api_base": self.api_base,
            "configured": bool(self.api_key and self.api_base)
        }
    
    def update_model_config(self, 
                           chat_model: Optional[str] = None,
                           embedding_model: Optional[str] = None) -> Dict[str, Any]:
        """
        更新模型配置
        
        Args:
            chat_model: 聊天模型名稱
            embedding_model: 嵌入模型名稱
            
        Returns:
            更新結果
        """
        if chat_model:
            self.default_chat_model = chat_model
        
        if embedding_model:
            self.default_embedding_model = embedding_model
        
        return {
            "success": True,
            "updated_config": {
                "chat_model": self.default_chat_model,
                "embedding_model": self.default_embedding_model
            },
            "timestamp": datetime.now().isoformat()
        }

