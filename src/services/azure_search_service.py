"""
Azure AI Search 服務模組
提供文件索引、搜尋和分析功能
整合 Azure OpenAI + Azure AI Search 的完整解決方案
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

try:
    from azure.search.documents import SearchClient
    from azure.search.documents.indexes import SearchIndexClient
    from azure.search.documents.models import (
        VectorizedQuery,
        VectorizableTextQuery
    )
    from azure.search.documents.indexes.models import (
        SearchIndex,
        SearchField,
        SearchFieldDataType,
        SimpleField,
        SearchableField,
        VectorSearch,
        HnswAlgorithmConfiguration,
        VectorSearchProfile,
        SemanticConfiguration,
        SemanticSearch,
        SemanticPrioritizedFields,
        SemanticField
    )
    from azure.core.credentials import AzureKeyCredential
    from azure.core.exceptions import ResourceNotFoundError
    AZURE_SEARCH_AVAILABLE = True
except ImportError:  # pragma: no cover - handled via graceful degradation
    SearchClient = None
    SearchIndexClient = None
    VectorizedQuery = None
    VectorizableTextQuery = None
    SearchIndex = None
    SearchField = None
    SearchFieldDataType = None
    SimpleField = None
    SearchableField = None
    VectorSearch = None
    HnswAlgorithmConfiguration = None
    VectorSearchProfile = None
    SemanticConfiguration = None
    SemanticSearch = None
    SemanticPrioritizedFields = None
    SemanticField = None
    AzureKeyCredential = None
    ResourceNotFoundError = None
    AZURE_SEARCH_AVAILABLE = False

# 使用新版 OpenAI 客戶端
try:
    from openai import AzureOpenAI
    OPENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    AzureOpenAI = None
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)

@dataclass
class DocumentResult:
    """文件搜尋結果"""
    id: str
    title: str
    content: str
    score: float
    metadata: Dict[str, Any]
    highlights: Optional[List[str]] = None

@dataclass
class SearchConfig:
    """搜尋配置"""
    top_k: int = 5
    semantic_search: bool = True
    include_vectors: bool = True
    highlight_fields: Optional[List[str]] = None

class AzureAISearchService:
    """Azure AI Search 服務類別 - 整合 Azure OpenAI + AI Search"""
    
    def __init__(self, 
                 search_service_name: str,
                 search_api_key: str,
                 openai_api_key: Optional[str],
                 openai_endpoint: Optional[str] = None,
                 openai_api_version: str = "2024-11-20",
                 index_name: str = "documents"):
        if not AZURE_SEARCH_AVAILABLE:
            raise RuntimeError("Azure Search SDK not available")
        """
        初始化 Azure AI Search 服務
        
        Args:
            search_service_name: Azure Search 服務名稱
            search_api_key: Azure Search API 金鑰
            openai_api_key: OpenAI API 金鑰 (用於向量化)
            openai_endpoint: OpenAI 端點 (可選)
            openai_api_version: OpenAI API 版本
            index_name: 索引名稱
        """
        self.search_service_name = search_service_name
        self.search_endpoint = f"https://{search_service_name}.search.windows.net"
        self.credential = AzureKeyCredential(search_api_key)
        self.index_name = index_name
        
        # 初始化客戶端
        self.search_client = SearchClient(
            endpoint=self.search_endpoint,
            index_name=index_name,
            credential=self.credential
        )
        
        self.index_client = SearchIndexClient(
            endpoint=self.search_endpoint,
            credential=self.credential
        )
        
        # 設定 Azure OpenAI 客戶端（新版本）
        self.openai_client = None
        if openai_api_key and OPENAI_AVAILABLE:
            try:
                self.openai_client = AzureOpenAI(
                    api_key=openai_api_key,
                    api_version=openai_api_version,
                    azure_endpoint=openai_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT") or "https://xcloudren-foundry.openai.azure.com/"
                )
            except Exception as exc:
                logger.warning("Failed to initialize Azure OpenAI client for search embeddings: %s", exc)
        elif openai_api_key and not OPENAI_AVAILABLE:
            logger.warning("OpenAI SDK not installed; embeddings will be unavailable")
            
        logger.info(f"Azure AI Search Service initialized with endpoint: {self.search_endpoint}")
    
    def create_index(self, delete_if_exists: bool = False) -> bool:
        """
        創建搜尋索引
        
        Args:
            delete_if_exists: 如果索引已存在是否刪除重建
            
        Returns:
            bool: 創建是否成功
        """
        try:
            # 檢查索引是否存在
            try:
                existing_index = self.index_client.get_index(self.index_name)
                if delete_if_exists:
                    logger.info(f"Deleting existing index: {self.index_name}")
                    self.index_client.delete_index(self.index_name)
                else:
                    logger.info(f"Index {self.index_name} already exists")
                    return True
            except ResourceNotFoundError:
                pass
            
            # 定義欄位
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SearchableField(name="title", type=SearchFieldDataType.String, 
                              analyzer_name="zh-hant.microsoft"),
                SearchableField(name="content", type=SearchFieldDataType.String,
                              analyzer_name="zh-hant.microsoft"),
                SearchField(name="content_vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                           searchable=True, vector_search_dimensions=1536, vector_search_profile_name="myHnswProfile"),
                SimpleField(name="category", type=SearchFieldDataType.String, filterable=True, facetable=True),
                SimpleField(name="tags", type=SearchFieldDataType.Collection(SearchFieldDataType.String), 
                           filterable=True, facetable=True),
                SimpleField(name="created_at", type=SearchFieldDataType.DateTimeOffset, 
                           filterable=True, sortable=True),
                SimpleField(name="file_type", type=SearchFieldDataType.String, filterable=True),
                SimpleField(name="file_size", type=SearchFieldDataType.Int64, filterable=True, sortable=True),
                SearchableField(name="metadata", type=SearchFieldDataType.String)
            ]
            
            # 向量搜尋配置
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(name="myHnsw")
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw",
                    )
                ]
            )
            
            # 語義搜尋配置
            semantic_config = SemanticConfiguration(
                name="my-semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="tags")]
                )
            )
            
            semantic_search = SemanticSearch(configurations=[semantic_config])
            
            # 創建索引
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=semantic_search
            )
            
            result = self.index_client.create_index(index)
            logger.info(f"Index {self.index_name} created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create index: {str(e)}")
            return False
    
    def get_text_embedding(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """
        使用 Azure OpenAI 生成文本嵌入向量
        
        Args:
            text: 要嵌入的文本
            model: 嵌入模型名稱
            
        Returns:
            List[float]: 嵌入向量
        """
        if not self.openai_client:
            logger.warning("Azure OpenAI client not available for embeddings")
            return []

        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=model
            )
            return response.data[0].embedding
        except Exception as exc:
            logger.error("Failed to generate embedding: %s", exc)
            return []
    
    def index_document(self, 
                      doc_id: str,
                      title: str,
                      content: str,
                      category: str = "general",
                      tags: List[str] = None,
                      file_type: str = "text",
                      file_size: int = 0,
                      metadata: Dict[str, Any] = None) -> bool:
        """
        索引單個文件
        
        Args:
            doc_id: 文件ID
            title: 文件標題
            content: 文件內容
            category: 文件分類
            tags: 標籤列表
            file_type: 文件類型
            file_size: 文件大小
            metadata: 額外元數據
            
        Returns:
            bool: 索引是否成功
        """
        try:
            # 生成內容向量
            content_vector = self.get_text_embedding(f"{title} {content}")
            
            if not content_vector:
                logger.warning(f"Failed to generate embedding for document {doc_id}")
                return False
            
            # 準備文件
            document = {
                "id": doc_id,
                "title": title,
                "content": content,
                "content_vector": content_vector,
                "category": category,
                "tags": tags or [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "file_type": file_type,
                "file_size": file_size,
                "metadata": json.dumps(metadata or {}, ensure_ascii=False)
            }
            
            # 上傳文件
            result = self.search_client.upload_documents([document])
            
            if result[0].succeeded:
                logger.info(f"Document {doc_id} indexed successfully")
                return True
            else:
                logger.error(f"Failed to index document {doc_id}: {result[0].error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexing document {doc_id}: {str(e)}")
            return False
    
    def search_documents(self, 
                        query: str,
                        config: Optional[SearchConfig] = None,
                        **overrides: Any) -> List[DocumentResult]:
        """
        搜尋文件
        
        Args:
            query: 搜尋查詢
            config: 搜尋配置
            
        Returns:
            List[DocumentResult]: 搜尋結果
        """
        if config is None:
            config = SearchConfig()

        for key, value in overrides.items():
            if value is None:
                continue
            if hasattr(config, key):
                setattr(config, key, value)
            
        try:
            # 生成查詢向量
            query_vector = self.get_text_embedding(query)
            
            # 準備搜尋參數
            search_params = {
                "search_text": query,
                "top": config.top_k,
                "include_total_count": True,
                "highlight_fields": config.highlight_fields or ["title", "content"],
                "select": ["id", "title", "content", "category", "tags", "created_at", "file_type", "metadata"]
            }
            
            # 如果有向量，加入向量搜尋
            if query_vector and config.include_vectors and VectorizedQuery is not None:
                vector_query = VectorizedQuery(
                    vector=query_vector,
                    k_nearest_neighbors=config.top_k,
                    fields="content_vector"
                )
                search_params["vector_queries"] = [vector_query]
            
            # 如果啟用語義搜尋
            if config.semantic_search:
                search_params["semantic_configuration_name"] = "my-semantic-config"
                search_params["query_type"] = "semantic"
                search_params["semantic_fields"] = ["title", "content"]
            
            # 執行搜尋
            results = self.search_client.search(**search_params)
            
            # 轉換結果
            document_results = []
            for result in results:
                def _get(field: str, default=None):
                    if hasattr(result, 'get'):
                        return result.get(field, default)
                    return getattr(result, field, default)

                highlights = []
                highlight_payload = _get('@search.highlights') or getattr(result, '@search.highlights', None)
                if highlight_payload:
                    for field, highlight_list in highlight_payload.items():
                        highlights.extend(highlight_list)
                
                metadata = {}
                metadata_raw = _get('metadata')
                if metadata_raw:
                    try:
                        metadata = json.loads(metadata_raw)
                    except:
                        metadata = {}
                
                document_results.append(DocumentResult(
                    id=_get('id'),
                    title=_get('title'),
                    content=_get('content'),
                    score=_get('@search.score', 0.0),
                    metadata=metadata,
                    highlights=highlights
                ))
            
            logger.info(f"Search completed. Found {len(document_results)} results for query: {query}")
            return document_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def delete_document(self, doc_id: str) -> bool:
        """
        刪除文件
        
        Args:
            doc_id: 文件ID
            
        Returns:
            bool: 刪除是否成功
        """
        try:
            result = self.search_client.delete_documents([{"id": doc_id}])
            
            if result[0].succeeded:
                logger.info(f"Document {doc_id} deleted successfully")
                return True
            else:
                logger.error(f"Failed to delete document {doc_id}: {result[0].error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {str(e)}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        獲取索引統計信息
        
        Returns:
            Dict[str, Any]: 統計信息
        """
        try:
            # 獲取總文件數
            results = self.search_client.search("*", top=0, include_total_count=True)
            total_count = results.get_count()
            
            # 獲取索引信息
            index = self.index_client.get_index(self.index_name)
            
            return {
                "index_name": self.index_name,
                "total_documents": total_count,
                "fields_count": len(index.fields),
                "created_date": getattr(index, 'created_date', None),
                "last_modified": getattr(index, 'last_modified', None)
            }
            
        except Exception as e:
            logger.error(f"Failed to get index stats: {str(e)}")
            return {}


_cached_service: Optional[AzureAISearchService] = None


def get_cached_azure_search_service(force_refresh: bool = False) -> Optional[AzureAISearchService]:
    """取得（快取的）Azure AI Search 服務實例"""
    global _cached_service

    if force_refresh:
        _cached_service = None

    if _cached_service is not None:
        return _cached_service

    service = create_azure_search_service()
    if service:
        _cached_service = service
    return _cached_service


def reset_cached_azure_search_service() -> None:
    """清除快取，主要提供測試使用。"""
    global _cached_service
    _cached_service = None

def create_azure_search_service() -> Optional[AzureAISearchService]:
    """
    創建 Azure AI Search 服務實例
    從環境變數讀取配置
    
    Returns:
        Optional[AzureAISearchService]: 服務實例，如果配置不完整則返回 None
    """
    search_service_name = os.getenv('AZURE_SEARCH_SERVICE_NAME')
    search_api_key = os.getenv('AZURE_SEARCH_API_KEY')
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_endpoint = os.getenv('OPENAI_API_BASE')
    index_name = os.getenv('AZURE_SEARCH_INDEX_NAME', 'documents')
    
    if not all([search_service_name, search_api_key, openai_api_key]):
        logger.warning("Azure Search configuration incomplete. Missing required environment variables.")
        return None
    
    try:
        service = AzureAISearchService(
            search_service_name=search_service_name,
            search_api_key=search_api_key,
            openai_api_key=openai_api_key,
            openai_endpoint=openai_endpoint,
            index_name=index_name
        )
        
        # 確保索引存在
        service.create_index()
        
        return service
        
    except Exception as e:
        logger.error(f"Failed to create Azure Search service: {str(e)}")
        return None
