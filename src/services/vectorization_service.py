"""
向量化服務模組
負責文件向量化、相似度搜尋等核心RAG功能
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
# import chromadb  # 暫時註解掉
# from chromadb.config import Settings  # 暫時註解掉
# from sentence_transformers import SentenceTransformer  # 暫時註解掉
from datetime import datetime
from openai import AzureOpenAI

class VectorizationService:
    """向量化服務類別"""
    
    def __init__(self, 
                 chroma_persist_directory: str = "./chroma_db",
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None,
                 openai_client: Optional[AzureOpenAI] = None,
                 openai_api_version: Optional[str] = None,
                 openai_embedding_deployment: Optional[str] = None):
        """
        初始化向量化服務
        
        Args:
            chroma_persist_directory: ChromaDB持久化目錄 (暫時不使用)
            openai_api_key: OpenAI API金鑰
            openai_api_base: OpenAI API基礎URL
        """
        self.chroma_persist_directory = chroma_persist_directory
        
        # 初始化ChromaDB客戶端 (暫時註解掉)
        # self.chroma_client = chromadb.PersistentClient(
        #     path=chroma_persist_directory,
        #     settings=Settings(anonymized_telemetry=False)
        # )
        self.chroma_client = None  # 暫時設為 None
        
        # 設定 Azure OpenAI 客戶端
        self._openai_client = None
        self._embedding_deployment = openai_embedding_deployment or os.getenv('OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-ada-002')
        self._api_version = openai_api_version or os.getenv('OPENAI_API_VERSION', '2024-02-15-preview')

        if openai_client:
            self._openai_client = openai_client
        else:
            api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
            api_base = openai_api_base or os.getenv('OPENAI_API_BASE')

            if api_key and api_base:
                self._openai_client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=api_base,
                    api_version=self._api_version
                )
            
        # 初始化本地embedding模型作為備用 (暫時註解掉)
        # self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.local_model = None  # 暫時設為 None
        
        # 建立知識庫集合 (使用模擬數據)
        self._initialize_collections()
        # 原本是: self.collections = None
    
    def _initialize_collections(self):
        """初始化模擬的知識庫集合"""
        self.collections = {
            'security_threats': self._create_mock_collection('security_threats'),
            'account_rules': self._create_mock_collection('account_rules'),
            'network_knowledge': self._create_mock_collection('network_knowledge'),
            'incident_cases': self._create_mock_collection('incident_cases'),
            'policies': self._create_mock_collection('policies')
        }
        
    def _create_mock_collection(self, name: str):
        """創建模擬集合"""
        return MockCollection(name)
    
    def _get_or_create_collection(self, name: str):
        """取得或建立集合 (暫時停用)"""
        # try:
        #     return self.chroma_client.get_collection(name=name)
        # except:
        #     return self.chroma_client.create_collection(name=name)
        return None
    
    def get_embedding_openai(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """
        使用OpenAI API取得文字向量
        
        Args:
            text: 要向量化的文字
            model: 使用的模型名稱
            
        Returns:
            向量列表
        """
        target_model = model or self._embedding_deployment

        if not self._openai_client:
            print("Azure OpenAI 客戶端未配置，改用本地備援嵌入")
            return self.get_embedding_local(text)

        try:
            response = self._openai_client.embeddings.create(
                input=text,
                model=target_model
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Azure OpenAI embedding error: {e}")
            # 使用本地模型作為備用
            return self.get_embedding_local(text)
    
    def get_embedding_local(self, text: str) -> List[float]:
        """
        使用本地模型取得文字向量 (暫時停用)
        
        Args:
            text: 要向量化的文字
            
        Returns:
            向量列表
        """
        # 暫時返回假的 embedding，因為沒有安裝 sentence-transformers
        if self.local_model is None:
            print("Warning: Local embedding model not available, returning dummy embedding")
            return [0.0] * 384  # 返回一個假的 384 維向量
        
        embedding = self.local_model.encode(text)
        return embedding.tolist()
    
    def chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """
        將文字分塊
        
        Args:
            text: 原始文字
            chunk_size: 分塊大小
            overlap: 重疊字數
            
        Returns:
            文字分塊列表
        """
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            
        return chunks
    
    def add_document(self, 
                    collection_name: str,
                    content: str,
                    metadata: Dict[str, Any],
                    use_openai: bool = True) -> str:
        """
        新增文件到知識庫
        
        Args:
            collection_name: 集合名稱
            content: 文件內容
            metadata: 元資料
            use_openai: 是否使用OpenAI embedding
            
        Returns:
            文件ID
        """
        if collection_name not in self.collections:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        collection = self.collections[collection_name]
        
        # 分塊處理
        chunks = self.chunk_text(content)
        
        for i, chunk in enumerate(chunks):
            # 生成唯一ID
            chunk_id = hashlib.md5(f"{content}_{i}".encode()).hexdigest()
            
            # 取得向量
            if use_openai:
                embedding = self.get_embedding_openai(chunk)
            else:
                embedding = self.get_embedding_local(chunk)
            
            # 準備元資料
            chunk_metadata = metadata.copy()
            chunk_metadata.update({
                'chunk_index': i,
                'chunk_count': len(chunks),
                'timestamp': datetime.now().isoformat()
            })
            
            # 新增到集合
            collection.add(
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[chunk_metadata],
                ids=[chunk_id]
            )
        
        return hashlib.md5(content.encode()).hexdigest()
    
    def search_similar(self, 
                      collection_name: str,
                      query: str,
                      n_results: int = 5,
                      use_openai: bool = True) -> List[Dict[str, Any]]:
        """
        搜尋相似文件
        
        Args:
            collection_name: 集合名稱
            query: 查詢文字
            n_results: 返回結果數量
            use_openai: 是否使用OpenAI embedding
            
        Returns:
            搜尋結果列表
        """
        if collection_name not in self.collections:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        collection = self.collections[collection_name]
        
        # 模擬搜尋 - 不使用實際的embedding
        # 取得查詢向量 (暫時略過)
        # if use_openai:
        #     query_embedding = self.get_embedding_openai(query)
        # else:
        #     query_embedding = self.get_embedding_local(query)
        
        # 執行搜尋 (使用模擬數據)
        results = collection.query(
            query_embeddings=None,  # 暫時不使用真實embedding
            n_results=n_results
        )
        
        # 格式化結果
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                'id': results['ids'][0][i],
                'content': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i] if 'distances' in results else None
            })
        
        return formatted_results
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """
        取得集合統計資訊
        
        Args:
            collection_name: 集合名稱
            
        Returns:
            統計資訊字典
        """
        if collection_name not in self.collections:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        collection = self.collections[collection_name]
        count = collection.count()
        
        return {
            'collection_name': collection_name,
            'document_count': count,
            'last_updated': datetime.now().isoformat()
        }
    
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """
        刪除文件
        
        Args:
            collection_name: 集合名稱
            document_id: 文件ID
            
        Returns:
            是否成功刪除
        """
        if collection_name not in self.collections:
            raise ValueError(f"Unknown collection: {collection_name}")
        
        try:
            collection = self.collections[collection_name]
            collection.delete(ids=[document_id])
            return True
        except Exception as e:
            print(f"Delete document error: {e}")
            return False
    
    def update_document(self, 
                       collection_name: str,
                       document_id: str,
                       new_content: str,
                       new_metadata: Dict[str, Any],
                       use_openai: bool = True) -> bool:
        """
        更新文件
        
        Args:
            collection_name: 集合名稱
            document_id: 文件ID
            new_content: 新內容
            new_metadata: 新元資料
            use_openai: 是否使用OpenAI embedding
            
        Returns:
            是否成功更新
        """
        try:
            # 先刪除舊文件
            self.delete_document(collection_name, document_id)
            
            # 新增新文件
            self.add_document(collection_name, new_content, new_metadata, use_openai)
            return True
        except Exception as e:
            print(f"Update document error: {e}")
            return False


class MockCollection:
    """模擬的集合類別，用於測試AI Agent功能"""
    
    def __init__(self, name: str):
        self.name = name
        self.mock_data = self._get_mock_data(name)
    
    def _get_mock_data(self, collection_name: str) -> List[Dict[str, Any]]:
        """取得模擬數據"""
        if collection_name == 'security_threats':
            return [
                {
                    'id': 'threat_001',
                    'content': 'APT攻擊通常包含多階段的滲透，攻擊者會使用社會工程學和零日漏洞來獲得初始存取權限。',
                    'metadata': {'type': 'apt', 'severity': 'high'},
                    'distance': 0.2
                },
                {
                    'id': 'threat_002', 
                    'content': 'DDoS攻擊透過大量請求使服務器過載，常見的防護措施包括流量限制和CDN服務。',
                    'metadata': {'type': 'ddos', 'severity': 'medium'},
                    'distance': 0.3
                },
                {
                    'id': 'threat_003',
                    'content': '惡意軟體通常透過電子郵件附件、惡意網站或USB設備傳播，建議使用端點保護解決方案。',
                    'metadata': {'type': 'malware', 'severity': 'high'},
                    'distance': 0.25
                }
            ]
        elif collection_name == 'account_rules':
            return [
                {
                    'id': 'rule_001',
                    'content': '多因素認證(MFA)是保護帳號安全的重要措施，應強制要求所有管理員帳號啟用。',
                    'metadata': {'category': 'authentication', 'importance': 'critical'},
                    'distance': 0.15
                },
                {
                    'id': 'rule_002',
                    'content': '密碼政策應要求至少12個字符，包含大小寫字母、數字和特殊字符。',
                    'metadata': {'category': 'password', 'importance': 'high'},
                    'distance': 0.2
                },
                {
                    'id': 'rule_003',
                    'content': '異常登入行為包括：非常規時間登入、地理位置異常、多次失敗嘗試等。',
                    'metadata': {'category': 'behavior', 'importance': 'medium'},
                    'distance': 0.3
                }
            ]
        elif collection_name == 'network_knowledge':
            return [
                {
                    'id': 'network_001',
                    'content': '網路監控應包括流量分析、異常檢測和即時警報系統。',
                    'metadata': {'category': 'monitoring', 'importance': 'high'},
                    'distance': 0.2
                },
                {
                    'id': 'network_002',
                    'content': '防火牆配置應遵循最小權限原則，只允許必要的流量通過。',
                    'metadata': {'category': 'firewall', 'importance': 'critical'},
                    'distance': 0.25
                },
                {
                    'id': 'network_003',
                    'content': 'VPN連線應使用強加密演算法，定期更新憑證和金鑰。',
                    'metadata': {'category': 'vpn', 'importance': 'high'},
                    'distance': 0.3
                }
            ]
        else:
            return [
                {
                    'id': 'generic_001',
                    'content': f'這是{collection_name}集合的通用安全知識。',
                    'metadata': {'category': 'general', 'importance': 'medium'},
                    'distance': 0.4
                }
            ]
    
    def query(self, query_embeddings=None, n_results=5):
        """模擬查詢方法"""
        results = self.mock_data[:n_results]
        
        return {
            'ids': [[item['id'] for item in results]],
            'documents': [[item['content'] for item in results]],
            'metadatas': [[item['metadata'] for item in results]],
            'distances': [[item['distance'] for item in results]]
        }
    
    def count(self):
        """返回集合中的文件數量"""
        return len(self.mock_data)
