"""
Azure 文件處理服務整合模組
整合 Azure Document Intelligence + Azure Blob Storage + PyMuPDF
提供完整的文件解析、儲存和處理功能
"""

import os
import io
import json
import logging
from typing import List, Dict, Any, Optional, Tuple, BinaryIO
from datetime import datetime, timezone
from dataclasses import dataclass
from pathlib import Path

# Azure 服務
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

# PDF 處理
import fitz  # PyMuPDF
import markdown
from markdownify import markdownify as md

from .azure_search_service import get_cached_azure_search_service

logger = logging.getLogger(__name__)

@dataclass
class DocumentInfo:
    """文件資訊"""
    id: str
    filename: str
    content: str
    file_type: str
    file_size: int
    pages: int
    created_at: datetime
    metadata: Dict[str, Any]
    blob_url: Optional[str] = None
    
@dataclass
class ExtractedContent:
    """抽取的內容"""
    text: str
    tables: List[Dict[str, Any]]
    key_value_pairs: Dict[str, str]
    layout: Dict[str, Any]
    confidence: float

class AzureDocumentProcessor:
    """Azure 文件處理器 - 整合多個 Azure 服務"""
    
    def __init__(self,
                 storage_account_name: str,
                 storage_account_key: str,
                 container_name: str,
                 document_intelligence_endpoint: str,
                 document_intelligence_key: str):
        """
        初始化 Azure 文件處理器
        
        Args:
            storage_account_name: Azure Storage 帳戶名稱
            storage_account_key: Azure Storage 金鑰
            container_name: Blob 容器名稱
            document_intelligence_endpoint: Document Intelligence 端點
            document_intelligence_key: Document Intelligence 金鑰
        """
        
        # 初始化 Blob Storage 客戶端
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net",
            credential=storage_account_key
        )
        self.container_name = container_name
        
        # 初始化 Document Intelligence 客戶端
        self.doc_intelligence_client = DocumentIntelligenceClient(
            endpoint=document_intelligence_endpoint,
            credential=AzureKeyCredential(document_intelligence_key)
        )
        
        # 確保容器存在
        self._ensure_container_exists()
        
        logger.info("Azure Document Processor initialized successfully")
    
    def _ensure_container_exists(self):
        """確保 Blob 容器存在"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            container_client.create_container()
            logger.info(f"Container {self.container_name} created or already exists")
        except Exception as e:
            logger.debug(f"Container creation info: {str(e)}")
    
    def upload_file(self, 
                   file_content: BinaryIO, 
                   filename: str,
                   metadata: Dict[str, Any] = None) -> str:
        """
        上傳文件到 Azure Blob Storage
        
        Args:
            file_content: 文件內容
            filename: 文件名稱
            metadata: 額外的元數據
            
        Returns:
            str: Blob URL
        """
        try:
            # 生成唯一的 blob 名稱
            blob_name = f"{datetime.now().strftime('%Y/%m/%d')}/{filename}"
            
            # 準備元數據
            blob_metadata = {
                'original_filename': filename,
                'upload_time': datetime.now(timezone.utc).isoformat(),
                'content_type': self._get_content_type(filename)
            }
            
            if metadata:
                blob_metadata.update(metadata)
            
            # 上傳文件
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            blob_client.upload_blob(
                file_content,
                metadata=blob_metadata,
                overwrite=True
            )
            
            blob_url = blob_client.url
            logger.info(f"File {filename} uploaded successfully to {blob_url}")
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Failed to upload file {filename}: {str(e)}")
            raise
    
    def process_document(self, 
                        blob_url: str, 
                        analysis_type: str = "prebuilt-layout") -> ExtractedContent:
        """
        使用 Azure Document Intelligence 處理文件
        
        Args:
            blob_url: Blob URL
            analysis_type: 分析類型
            
        Returns:
            ExtractedContent: 抽取的內容
        """
        try:
            # 準備分析請求
            analyze_request = AnalyzeDocumentRequest(url_source=blob_url)
            
            # 開始分析
            poller = self.doc_intelligence_client.begin_analyze_document(
                model_id=analysis_type,
                analyze_request=analyze_request
            )
            
            # 等待結果
            result = poller.result()
            
            # 抽取內容
            text_content = self._extract_text(result)
            tables = self._extract_tables(result)
            key_value_pairs = self._extract_key_value_pairs(result)
            layout = self._extract_layout(result)
            confidence = self._calculate_confidence(result)
            
            extracted_content = ExtractedContent(
                text=text_content,
                tables=tables,
                key_value_pairs=key_value_pairs,
                layout=layout,
                confidence=confidence
            )
            
            logger.info(f"Document processed successfully. Confidence: {confidence}")
            return extracted_content
            
        except Exception as e:
            logger.error(f"Failed to process document: {str(e)}")
            raise
    
    def process_pdf_with_pymupdf(self, file_content: BinaryIO) -> Tuple[str, Dict[str, Any]]:
        """
        使用 PyMuPDF 處理 PDF 文件
        
        Args:
            file_content: PDF 文件內容
            
        Returns:
            Tuple[str, Dict]: 文本內容和元數據
        """
        try:
            # 重置文件指針
            file_content.seek(0)
            pdf_data = file_content.read()
            
            # 使用 PyMuPDF 打開 PDF
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            
            # 抽取文本
            text_content = ""
            metadata = {
                "page_count": pdf_document.page_count,
                "title": pdf_document.metadata.get("title", ""),
                "author": pdf_document.metadata.get("author", ""),
                "subject": pdf_document.metadata.get("subject", ""),
                "keywords": pdf_document.metadata.get("keywords", ""),
                "creator": pdf_document.metadata.get("creator", ""),
                "producer": pdf_document.metadata.get("producer", ""),
                "creation_date": pdf_document.metadata.get("creationDate", ""),
                "modification_date": pdf_document.metadata.get("modDate", "")
            }
            
            # 逐頁抽取文本
            pages_info = []
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                page_text = page.get_text()
                text_content += f"\n\n--- 第 {page_num + 1} 頁 ---\n{page_text}"
                
                # 抽取頁面資訊
                page_info = {
                    "page_number": page_num + 1,
                    "text_length": len(page_text),
                    "has_images": len(page.get_images()) > 0,
                    "has_links": len(page.get_links()) > 0
                }
                pages_info.append(page_info)
            
            metadata["pages_info"] = pages_info
            pdf_document.close()
            
            logger.info(f"PDF processed with PyMuPDF. Pages: {pdf_document.page_count}")
            return text_content, metadata
            
        except Exception as e:
            logger.error(f"Failed to process PDF with PyMuPDF: {str(e)}")
            raise
    
    def convert_html_to_markdown(self, html_content: str) -> str:
        """
        將 HTML 轉換為 Markdown
        
        Args:
            html_content: HTML 內容
            
        Returns:
            str: Markdown 內容
        """
        try:
            # 使用 markdownify 轉換
            markdown_content = md(
                html_content,
                heading_style="ATX",
                bullets="*+-",
                strip=['script', 'style']
            )
            
            return markdown_content
            
        except Exception as e:
            logger.error(f"Failed to convert HTML to Markdown: {str(e)}")
            return html_content
    
    def process_markdown_file(self, markdown_content: str) -> str:
        """
        處理 Markdown 文件
        
        Args:
            markdown_content: Markdown 內容
            
        Returns:
            str: 處理後的內容
        """
        try:
            # 轉換為 HTML 再轉回純文本（清理格式）
            html_content = markdown.markdown(markdown_content)
            
            # 移除 HTML 標籤，保留文本內容
            import re
            clean_text = re.sub(r'<[^>]+>', '', html_content)
            clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text)  # 清理多餘空行
            
            return clean_text.strip()
            
        except Exception as e:
            logger.error(f"Failed to process Markdown: {str(e)}")
            return markdown_content
    
    def process_file_complete(self, 
                             file_content: BinaryIO, 
                             filename: str,
                             metadata: Dict[str, Any] = None) -> DocumentInfo:
        """
        完整處理文件流程
        
        Args:
            file_content: 文件內容
            filename: 文件名稱
            metadata: 額外元數據
            
        Returns:
            DocumentInfo: 文件資訊
        """
        try:
            # 獲取文件類型
            file_extension = Path(filename).suffix.lower()
            file_size = len(file_content.read())
            file_content.seek(0)  # 重置指針
            
            # 1. 上傳到 Blob Storage
            blob_url = self.upload_file(file_content, filename, metadata)
            file_content.seek(0)  # 重置指針
            
            # 2. 根據文件類型選擇處理方式
            extracted_text = ""
            pages = 1
            processing_metadata = {}
            
            if file_extension == '.pdf':
                # 使用 PyMuPDF 處理 PDF
                extracted_text, processing_metadata = self.process_pdf_with_pymupdf(file_content)
                pages = processing_metadata.get('page_count', 1)
                
                # 可選：同時使用 Document Intelligence 處理
                try:
                    file_content.seek(0)
                    doc_intel_result = self.process_document(blob_url)
                    processing_metadata['document_intelligence'] = {
                        'confidence': doc_intel_result.confidence,
                        'has_tables': len(doc_intel_result.tables) > 0,
                        'has_key_value_pairs': len(doc_intel_result.key_value_pairs) > 0
                    }
                except Exception as e:
                    logger.warning(f"Document Intelligence processing failed: {str(e)}")
            
            elif file_extension in ['.html', '.htm']:
                file_content.seek(0)
                html_content = file_content.read().decode('utf-8')
                extracted_text = self.convert_html_to_markdown(html_content)
                
            elif file_extension in ['.md', '.markdown']:
                file_content.seek(0)
                markdown_content = file_content.read().decode('utf-8')
                extracted_text = self.process_markdown_file(markdown_content)
                
            elif file_extension in ['.txt']:
                file_content.seek(0)
                extracted_text = file_content.read().decode('utf-8')
                
            else:
                # 嘗試使用 Document Intelligence 處理其他格式
                doc_intel_result = self.process_document(blob_url)
                extracted_text = doc_intel_result.text
                processing_metadata = {
                    'confidence': doc_intel_result.confidence,
                    'tables': doc_intel_result.tables,
                    'key_value_pairs': doc_intel_result.key_value_pairs
                }
            
            # 3. 創建文件資訊
            doc_info = DocumentInfo(
                id=f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hash(filename) % 10000}",
                filename=filename,
                content=extracted_text,
                file_type=file_extension,
                file_size=file_size,
                pages=pages,
                created_at=datetime.now(timezone.utc),
                metadata={
                    'original_metadata': metadata or {},
                    'processing_metadata': processing_metadata,
                    'processing_method': self._get_processing_method(file_extension)
                },
                blob_url=blob_url
            )
            
            logger.info(f"File {filename} processed completely. Document ID: {doc_info.id}")
            return doc_info
            
        except Exception as e:
            logger.error(f"Failed to process file {filename}: {str(e)}")
            raise
    
    def _get_content_type(self, filename: str) -> str:
        """獲取文件 MIME 類型"""
        extension = Path(filename).suffix.lower()
        content_types = {
            '.pdf': 'application/pdf',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.md': 'text/markdown',
            '.markdown': 'text/markdown',
            '.txt': 'text/plain',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def _get_processing_method(self, file_extension: str) -> str:
        """獲取處理方法"""
        if file_extension == '.pdf':
            return 'PyMuPDF + Document Intelligence (optional)'
        elif file_extension in ['.html', '.htm']:
            return 'HTML to Markdown conversion'
        elif file_extension in ['.md', '.markdown']:
            return 'Markdown processing'
        elif file_extension == '.txt':
            return 'Direct text extraction'
        else:
            return 'Azure Document Intelligence'
    
    def _extract_text(self, result) -> str:
        """從分析結果中抽取文本"""
        if hasattr(result, 'content'):
            return result.content
        return ""
    
    def _extract_tables(self, result) -> List[Dict[str, Any]]:
        """從分析結果中抽取表格"""
        tables = []
        if hasattr(result, 'tables'):
            for table in result.tables:
                table_data = {
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': []
                }
                
                if hasattr(table, 'cells'):
                    for cell in table.cells:
                        cell_data = {
                            'content': cell.content,
                            'row_index': cell.row_index,
                            'column_index': cell.column_index
                        }
                        table_data['cells'].append(cell_data)
                
                tables.append(table_data)
        
        return tables
    
    def _extract_key_value_pairs(self, result) -> Dict[str, str]:
        """從分析結果中抽取鍵值對"""
        key_value_pairs = {}
        if hasattr(result, 'key_value_pairs'):
            for kvp in result.key_value_pairs:
                if hasattr(kvp, 'key') and hasattr(kvp, 'value'):
                    key_content = kvp.key.content if hasattr(kvp.key, 'content') else str(kvp.key)
                    value_content = kvp.value.content if hasattr(kvp.value, 'content') else str(kvp.value)
                    key_value_pairs[key_content] = value_content
        
        return key_value_pairs
    
    def _extract_layout(self, result) -> Dict[str, Any]:
        """從分析結果中抽取版面資訊"""
        layout = {}
        if hasattr(result, 'paragraphs'):
            layout['paragraph_count'] = len(result.paragraphs)
        
        if hasattr(result, 'pages'):
            layout['page_count'] = len(result.pages)
            
        return layout
    
    def _calculate_confidence(self, result) -> float:
        """計算分析信心度"""
        if hasattr(result, 'pages') and result.pages:
            confidences = []
            for page in result.pages:
                if hasattr(page, 'lines'):
                    for line in page.lines:
                        if hasattr(line, 'polygon') and hasattr(line.polygon, 'confidence'):
                            confidences.append(line.polygon.confidence)
            
            if confidences:
                return round(sum(confidences) / len(confidences), 2)
        
        return 0.0


class DocumentProcessingService:
    """文件處理服務 - 整合多個處理器"""
    
    def __init__(self):
        """初始化文件處理服務"""
        self.azure_processor = None
        self._azure_search_service = None
        self._azure_search_checked = False
        self._initialize_azure_processor()
    
    def _initialize_azure_processor(self):
        """初始化 Azure 文件處理器"""
        try:
            storage_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
            storage_key = os.getenv('AZURE_STORAGE_ACCOUNT_KEY')
            container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'documents')
            doc_intel_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
            doc_intel_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')
            
            if all([storage_name, storage_key, doc_intel_endpoint, doc_intel_key]):
                self.azure_processor = AzureDocumentProcessor(
                    storage_account_name=storage_name,
                    storage_account_key=storage_key,
                    container_name=container_name,
                    document_intelligence_endpoint=doc_intel_endpoint,
                    document_intelligence_key=doc_intel_key
                )
                logger.info("Azure Document Processor initialized successfully")
            else:
                logger.warning("Azure credentials not found, Azure processing disabled")
                
        except Exception as e:
            logger.error(f"Failed to initialize Azure processor: {str(e)}")
    
    def process_file(self, 
                    file_content: BinaryIO, 
                    filename: str,
                    metadata: Dict[str, Any] = None) -> DocumentInfo:
        """
        處理文件
        
        Args:
            file_content: 文件內容
            filename: 文件名稱
            metadata: 額外元數據
            
        Returns:
            DocumentInfo: 文件資訊
        """
        if self.azure_processor:
            doc_info = self.azure_processor.process_file_complete(file_content, filename, metadata)
        else:
            # 本地處理回退方案
            doc_info = self._process_file_local(file_content, filename, metadata)

        self._index_document_in_search(doc_info)
        return doc_info
    
    def _process_file_local(self, 
                           file_content: BinaryIO, 
                           filename: str,
                           metadata: Dict[str, Any] = None) -> DocumentInfo:
        """本地文件處理回退方案"""
        try:
            file_extension = Path(filename).suffix.lower()
            file_size = len(file_content.read())
            file_content.seek(0)
            
            # 簡單的文本抽取
            if file_extension == '.txt':
                content = file_content.read().decode('utf-8')
            elif file_extension == '.pdf':
                # 使用 PyMuPDF
                pdf_data = file_content.read()
                pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
                content = ""
                for page_num in range(pdf_document.page_count):
                    content += pdf_document[page_num].get_text()
                pdf_document.close()
            else:
                content = "無法處理此文件類型"
            
            doc_info = DocumentInfo(
                id=f"local_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                filename=filename,
                content=content,
                file_type=file_extension,
                file_size=file_size,
                pages=1,
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {},
                blob_url=None
            )
            
            return doc_info
            
        except Exception as e:
            logger.error(f"Local file processing failed: {str(e)}")
            raise

    def _index_document_in_search(self, document: DocumentInfo) -> None:
        """嘗試將文件索引到 Azure AI Search（若可用）。"""
        service = self._get_azure_search_service()
        if not service or not document.content:
            return

        title = document.metadata.get('title') if document.metadata else None
        if not title:
            title = Path(document.filename).stem if document.filename else "未命名文件"

        tags = []
        if document.metadata:
            raw_tags = document.metadata.get('tags')
            if isinstance(raw_tags, list):
                tags = raw_tags
            elif isinstance(raw_tags, str):
                tags = [raw_tags]

        try:
            enriched_metadata = {
                **(document.metadata or {}),
                "blob_url": document.blob_url,
                "pages": document.pages,
                "created_at": document.created_at.isoformat() if document.created_at else None
            }

            service.index_document(
                doc_id=document.id,
                title=title,
                content=document.content,
                category=enriched_metadata.get('category', 'document'),
                tags=tags,
                file_type=document.file_type,
                file_size=document.file_size,
                metadata=enriched_metadata
            )
        except Exception as exc:
            logger.warning("Failed to index document %s in Azure Search: %s", document.id, exc)

    def _get_azure_search_service(self):
        """懶載入 Azure Search 服務。"""
        if self._azure_search_checked:
            return self._azure_search_service

        self._azure_search_checked = True
        self._azure_search_service = get_cached_azure_search_service()
        if self._azure_search_service:
            logger.info("Azure AI Search integration enabled for document processing")
        else:
            logger.debug("Azure AI Search not configured; skipping indexing")
        return self._azure_search_service
