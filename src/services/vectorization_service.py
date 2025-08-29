"""
向量化服務模組
負責文件向量化、相似度搜尋等核心RAG功能
"""

import os
import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings
import openai
from sentence_transformers import SentenceTransformer
import numpy as np
from datetime import datetime

class VectorizationService:
    """向量化服務類別"""
    
    def __init__(self, 
                 chroma_persist_directory: str = "./chroma_db",
                 openai_api_key: Optional[str] = None,
                 openai_api_base: Optional[str] = None):
        """
        初始化向量化服務
        
        Args:
            chroma_persist_directory: ChromaDB持久化目錄
            openai_api_key: OpenAI API金鑰
            openai_api_base: OpenAI API基礎URL
        """
        self.chroma_persist_directory = chroma_persist_directory
        
        # 初始化ChromaDB客戶端
        self.chroma_client = chromadb.PersistentClient(
            path=chroma_persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # 設定OpenAI客戶端
        if openai_api_key:
            openai.api_key = openai_api_key
        if openai_api_base:
            openai.api_base = openai_api_base
            
        # 初始化本地embedding模型作為備用
        self.local_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # 建立知識庫集合
        self._initialize_collections()
    
    def _initialize_collections(self):
        """初始化ChromaDB集合"""
        self.collections = {
            'security_threats': self._get_or_create_collection('security_threats'),
            'account_rules': self._get_or_create_collection('account_rules'),
            'network_knowledge': self._get_or_create_collection('network_knowledge'),
            'incident_cases': self._get_or_create_collection('incident_cases'),
            'policies': self._get_or_create_collection('policies')
        }
    
    def _get_or_create_collection(self, name: str):
        """取得或建立集合"""
        try:
            return self.chroma_client.get_collection(name=name)
        except:
            return self.chroma_client.create_collection(name=name)
    
    def get_embedding_openai(self, text: str, model: str = "text-embedding-ada-002") -> List[float]:
        """
        使用OpenAI API取得文字向量
        
        Args:
            text: 要向量化的文字
            model: 使用的模型名稱
            
        Returns:
            向量列表
        """
        try:
            response = openai.Embedding.create(
                input=text,
                model=model
            )
            return response['data'][0]['embedding']
        except Exception as e:
            print(f"OpenAI embedding error: {e}")
            # 使用本地模型作為備用
            return self.get_embedding_local(text)
    
    def get_embedding_local(self, text: str) -> List[float]:
        """
        使用本地模型取得文字向量
        
        Args:
            text: 要向量化的文字
            
        Returns:
            向量列表
        """
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
        
        # 取得查詢向量
        if use_openai:
            query_embedding = self.get_embedding_openai(query)
        else:
            query_embedding = self.get_embedding_local(query)
        
        # 執行搜尋
        results = collection.query(
            query_embeddings=[query_embedding],
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

