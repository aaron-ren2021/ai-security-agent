"""
文件管理API路由模組
提供文件上傳、下載、刪除等功能
整合 Azure Document Intelligence + Azure Blob Storage
"""

import os
import uuid
import mimetypes
import logging
from datetime import datetime
from io import BytesIO
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename

# 導入新的 Azure 文件處理服務
from ..services.azure_document_service import DocumentProcessingService

logger = logging.getLogger(__name__)

# 建立Blueprint
file_bp = Blueprint('files', __name__)

# 初始化 Azure 文件處理服務
document_service = DocumentProcessingService()

# 文件存儲路徑 - 使用絕對路徑（用於本地備份）
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# 允許的文件類型（擴充支援更多格式）
ALLOWED_EXTENSIONS = {
    'txt', 'md', 'markdown',  # 文本文件
    'pdf',  # PDF 文件
    'doc', 'docx',  # Word 文件
    'html', 'htm',  # HTML 文件
    'xlsx', 'xls',  # Excel 文件
    'pptx', 'ppt'   # PowerPoint 文件
}

def allowed_file(filename):
    """檢查文件類型是否允許"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 文件數據存儲（生產環境中應使用數據庫）
documents_store = {}

@file_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    文件上傳端點 - 使用 Azure 文件處理服務
    支援多種文件格式的智能處理
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "沒有找到文件"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "沒有選擇文件"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "error": f"不支援的文件類型。支援的格式: {', '.join(ALLOWED_EXTENSIONS)}"
            }), 400
        
        # 準備文件內容
        original_filename = secure_filename(file.filename)
        file_content = BytesIO(file.read())
        
        # 準備額外元數據
        metadata = {
            'uploaded_by': request.headers.get('User-Agent', 'Unknown'),
            'upload_ip': request.remote_addr,
            'content_length': len(file_content.getvalue())
        }
        
        # 使用 Azure 文件處理服務處理文件
        try:
            doc_info = document_service.process_file(
                file_content=file_content,
                filename=original_filename,
                metadata=metadata
            )
            
            # 同時保存到本地作為備份
            local_file_id = str(uuid.uuid4())
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            local_filename = f"{local_file_id}.{file_extension}"
            local_file_path = os.path.join(UPLOAD_FOLDER, local_filename)
            
            file_content.seek(0)
            with open(local_file_path, 'wb') as f:
                f.write(file_content.read())
            
            # 創建綜合文件記錄
            doc_record = {
                'id': doc_info.id,
                'filename': doc_info.filename,
                'title': original_filename.rsplit('.', 1)[0],
                'content': doc_info.content,
                'file_type': doc_info.file_type,
                'file_size': doc_info.file_size,
                'pages': doc_info.pages,
                'blob_url': doc_info.blob_url,
                'local_file_path': local_file_path,
                'local_file_id': local_file_id,
                'mime_type': mimetypes.guess_type(original_filename)[0],
                'created_at': doc_info.created_at.isoformat(),
                'updated_at': datetime.now().isoformat(),
                'processing_metadata': doc_info.metadata,
                'azure_processed': True
            }
            
            # 存儲到記錄中
            documents_store[doc_info.id] = doc_record
            
            logger.info(f"File {original_filename} processed successfully. Document ID: {doc_info.id}")
            
            return jsonify({
                "success": True,
                "file_id": doc_info.id,
                "filename": original_filename,
                "file_size": doc_info.file_size,
                "pages": doc_info.pages,
                "file_type": doc_info.file_type,
                "blob_url": doc_info.blob_url,
                "content_length": len(doc_info.content),
                "azure_processed": True,
                "message": "文件上傳並處理成功"
            })
            
        except Exception as azure_error:
            logger.warning(f"Azure processing failed: {str(azure_error)}, falling back to local processing")
            
            # Azure 處理失敗時，回退到本地處理
            return upload_file_local_fallback(file_content, original_filename, metadata)
        
    except Exception as e:
        logger.error(f"File upload failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def upload_file_local_fallback(file_content, original_filename, metadata=None):
    """本地文件處理回退方案"""
    try:
        # 生成唯一文件名
        file_id = str(uuid.uuid4())
        file_extension = original_filename.rsplit('.', 1)[1].lower()
        stored_filename = f"{file_id}.{file_extension}"
        file_path = os.path.join(UPLOAD_FOLDER, stored_filename)
        
        # 保存文件
        file_content.seek(0)
        with open(file_path, 'wb') as f:
            f.write(file_content.read())
        
        # 簡單的內容提取
        content = extract_content_local(file_path, original_filename)
        
        # 獲取文件大小
        file_size = os.path.getsize(file_path)
        
        # 創建文件記錄
        doc_record = {
            'id': file_id,
            'filename': original_filename,
            'title': original_filename.rsplit('.', 1)[0],
            'content': content,
            'file_type': f'.{file_extension}',
            'file_size': file_size,
            'pages': 1,
            'blob_url': None,
            'local_file_path': file_path,
            'local_file_id': file_id,
            'mime_type': mimetypes.guess_type(original_filename)[0],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'processing_metadata': metadata or {},
            'azure_processed': False
        }
        
        # 存儲到記錄中
        documents_store[file_id] = doc_record
        
        logger.info(f"File {original_filename} processed locally. Document ID: {file_id}")
        
        return jsonify({
            "success": True,
            "file_id": file_id,
            "filename": original_filename,
            "file_size": file_size,
            "pages": 1,
            "file_type": f'.{file_extension}',
            "blob_url": None,
            "content_length": len(content),
            "azure_processed": False,
            "message": "文件上傳成功（本地處理）"
        })
        
    except Exception as e:
        logger.error(f"Local file processing failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"文件處理失敗: {str(e)}"
        }), 500


def extract_content_local(file_path, filename):
    """本地內容提取"""
    try:
        file_ext = filename.rsplit('.', 1)[1].lower()
        
        if file_ext in ['txt', 'md', 'markdown']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_ext in ['html', 'htm']:
            with open(file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                # 簡單的 HTML 標籤移除
                import re
                return re.sub(r'<[^>]+>', '', html_content)
        elif file_ext == 'pdf':
            # 嘗試使用 PyMuPDF
            try:
                import PyMuPDF as fitz
                pdf_document = fitz.open(file_path)
                content = ""
                for page_num in range(pdf_document.page_count):
                    content += pdf_document[page_num].get_text()
                pdf_document.close()
                return content
            except ImportError:
                try:
                    import fitz
                    pdf_document = fitz.open(file_path)
                    content = ""
                    for page_num in range(pdf_document.page_count):
                        content += pdf_document[page_num].get_text()
                    pdf_document.close()
                    return content
                except ImportError:
                    return f"PDF文件: {filename} (需要安裝 PyMuPDF 來提取內容)"
        elif file_ext in ['doc', 'docx']:
            return f"Word文檔: {filename} (需要 Word 解析器來提取內容)"
        else:
            return f"不支援的文件格式: {filename}"
    except Exception as e:
        return f"讀取文件內容失敗: {str(e)}"

@file_bp.route('/documents', methods=['GET'])
def list_documents():
    """列出所有文件"""
    try:
        documents = []
        for doc_id, doc_data in documents_store.items():
            doc_info = {
                'id': doc_data['id'],
                'filename': doc_data['filename'],
                'title': doc_data['title'],
                'file_size': doc_data['file_size'],
                'file_type': doc_data.get('file_type', ''),
                'pages': doc_data.get('pages', 1),
                'mime_type': doc_data['mime_type'],
                'created_at': doc_data['created_at'],
                'updated_at': doc_data['updated_at'],
                'azure_processed': doc_data.get('azure_processed', False),
                'blob_url': doc_data.get('blob_url'),
                'content_length': len(doc_data.get('content', ''))
            }
            documents.append(doc_info)
        
        documents.sort(key=lambda x: x['created_at'], reverse=True)
        return jsonify({
            "success": True,
            "documents": documents,
            "total": len(documents)
        })
        
    except Exception as e:
        logger.error(f"List documents failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@file_bp.route('/documents/<doc_id>', methods=['GET'])
def get_document(doc_id):
    """獲取特定文件的詳細信息"""
    try:
        if doc_id not in documents_store:
            return jsonify({"error": "文件不存在"}), 404
        
        doc_data = documents_store[doc_id].copy()
        
        # 返回完整的文件資訊
        return jsonify({
            "success": True,
            "document": doc_data
        })
        
    except Exception as e:
        logger.error(f"Get document failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@file_bp.route('/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """刪除文件"""
    try:
        if doc_id not in documents_store:
            return jsonify({"error": "文件不存在"}), 404
        
        doc_data = documents_store[doc_id]
        
        # 刪除本地文件
        try:
            local_path = doc_data.get('local_file_path') or doc_data.get('file_path')
            if local_path and os.path.exists(local_path):
                os.remove(local_path)
                logger.info(f"Local file deleted: {local_path}")
        except Exception as e:
            logger.warning(f"刪除本地文件失敗: {e}")
        
        # TODO: 刪除 Azure Blob Storage 中的文件
        # if doc_data.get('blob_url'):
        #     try:
        #         # 刪除 Azure Blob
        #         pass
        #     except Exception as e:
        #         logger.warning(f"刪除 Azure Blob 失敗: {e}")
        
        # 從記錄中刪除
        del documents_store[doc_id]
        
        return jsonify({
            "success": True,
            "message": "文件已成功刪除"
        })
        
    except Exception as e:
        logger.error(f"Delete document failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@file_bp.route('/documents/<doc_id>/download', methods=['GET'])
def download_document(doc_id):
    """下載文件"""
    try:
        if doc_id not in documents_store:
            return jsonify({"error": "文件不存在"}), 404
        
        doc_data = documents_store[doc_id]
        
        # 優先使用本地文件
        local_path = doc_data.get('local_file_path') or doc_data.get('file_path')
        
        if local_path and os.path.exists(local_path):
            return send_file(
                local_path,
                as_attachment=True,
                download_name=doc_data['filename']
            )
        else:
            # TODO: 從 Azure Blob Storage 下載
            # if doc_data.get('blob_url'):
            #     # 從 Azure 下載並返回
            #     pass
            
            return jsonify({"error": "文件已不存在"}), 404
        
    except Exception as e:
        logger.error(f"Download document failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@file_bp.route('/search', methods=['POST'])
def search_documents():
    """
    搜索文件內容 - 增強版本
    支援基於內容的語義搜索
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400
        
        query = data.get('query', '')
        if not query:
            return jsonify({"error": "查詢內容不能為空"}), 400
        
        # 獲取搜索參數
        max_results = data.get('max_results', 10)
        include_content = data.get('include_content', False)
        
        # 文本搜索
        results = []
        for doc_id, doc_data in documents_store.items():
            content = doc_data.get('content', '').lower()
            title = doc_data.get('title', '').lower()
            filename = doc_data.get('filename', '').lower()
            
            query_lower = query.lower()
            
            # 檢查是否匹配
            if (query_lower in content or 
                query_lower in title or 
                query_lower in filename):
                
                # 計算相似度分數
                score = 0
                matches = []
                
                if query_lower in title:
                    score += 0.5
                    matches.append("title")
                if query_lower in filename:
                    score += 0.3
                    matches.append("filename")
                if query_lower in content:
                    score += 0.2
                    matches.append("content")
                
                # 生成摘要片段
                snippet = ""
                if query_lower in content:
                    # 找到包含查詢的句子
                    sentences = content.split('.')
                    for sentence in sentences:
                        if query_lower in sentence:
                            snippet = sentence.strip()[:200] + '...'
                            break
                
                if not snippet:
                    snippet = content[:200] + '...' if len(content) > 200 else content
                
                result = {
                    'id': doc_data['id'],
                    'title': doc_data['title'],
                    'filename': doc_data['filename'],
                    'file_type': doc_data.get('file_type', ''),
                    'file_size': doc_data['file_size'],
                    'pages': doc_data.get('pages', 1),
                    'azure_processed': doc_data.get('azure_processed', False),
                    'score': score,
                    'matches': matches,
                    'snippet': snippet,
                    'created_at': doc_data['created_at']
                }
                
                # 如果要求包含完整內容
                if include_content:
                    result['content'] = doc_data.get('content', '')
                
                results.append(result)
        
        # 按分數排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # 限制結果數量
        results = results[:max_results]
        
        return jsonify({
            "success": True,
            "query": query,
            "results": results,
            "total_found": len(results),
            "search_params": {
                "max_results": max_results,
                "include_content": include_content
            }
        })
        
    except Exception as e:
        logger.error(f"Search documents failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@file_bp.route('/documents/<doc_id>/analyze', methods=['POST'])
def analyze_document():
    """
    分析文件內容 - 新增功能
    提供文件的詳細分析資訊
    """
    try:
        doc_id = request.view_args['doc_id']
        
        if doc_id not in documents_store:
            return jsonify({"error": "文件不存在"}), 404
        
        doc_data = documents_store[doc_id]
        content = doc_data.get('content', '')
        
        # 基本分析
        analysis = {
            'word_count': len(content.split()),
            'character_count': len(content),
            'line_count': len(content.split('\n')),
            'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
            'file_info': {
                'filename': doc_data['filename'],
                'file_type': doc_data.get('file_type', ''),
                'file_size': doc_data['file_size'],
                'pages': doc_data.get('pages', 1),
                'azure_processed': doc_data.get('azure_processed', False)
            }
        }
        
        # 如果有 Azure 處理的元數據，添加更多分析
        processing_metadata = doc_data.get('processing_metadata', {})
        if processing_metadata:
            analysis['processing_info'] = processing_metadata
        
        return jsonify({
            "success": True,
            "document_id": doc_id,
            "analysis": analysis
        })
        
    except Exception as e:
        logger.error(f"Analyze document failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500