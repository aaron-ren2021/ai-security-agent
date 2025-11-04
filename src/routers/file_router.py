from __future__ import annotations
"""FastAPI 版文件管理路由 (由原 Flask Blueprint `file_api.py` 遷移)

路徑前綴: /api/files

注意：
1. 為了與現有測試對齊，部分回傳格式（尤其 list_documents 與 get_document）
   與舊版 Flask 版略有差異：
   - GET /api/files/documents 直接回傳文件列(list)，而非 {success, documents, total}
   - GET /api/files/documents/{id} 直接回傳文件 dict，而非 {success, document: {...}}
2. 上傳、刪除、搜尋仍保留 success/message 結構。
3. 目前仍使用記憶體內部 store，後續可抽象為 repository / DB。
"""

import os
import uuid
import mimetypes
from datetime import datetime
from io import BytesIO
from typing import Dict, Any, List

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse, JSONResponse

from src.services.azure_document_service import DocumentProcessingService

router = APIRouter(prefix="/api/files", tags=["files"])

# 初始化 Azure 文件處理服務 (lazy)
document_service: DocumentProcessingService | None = None


def get_document_service() -> DocumentProcessingService:
    global document_service
    if document_service is None:
        document_service = DocumentProcessingService()
    return document_service


# 儲存路徑 (與原邏輯一致，使用專案根 uploads 目錄)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {
    'txt', 'md', 'markdown',
    'pdf',
    'doc', 'docx',
    'html', 'htm',
    'xlsx', 'xls',
    'pptx', 'ppt'
}


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# In-memory documents store (id -> record)
documents_store: Dict[str, Dict[str, Any]] = {}


@router.post('/upload')
async def upload_file(file: UploadFile = File(...)):
    """上傳文件並嘗試使用 Azure Document Intelligence 處理，失敗則回退本地解析。"""
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail='沒有選擇文件')
    if not allowed_file(file.filename):
        raise HTTPException(status_code=400, detail=f"不支援的文件類型。支援的格式: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    original_filename = file.filename
    raw_bytes = await file.read()
    file_content = BytesIO(raw_bytes)

    metadata = {
        'uploaded_by': 'fastapi-client',  # 可改為從 headers 解析
        'content_length': len(raw_bytes)
    }

    svc = get_document_service()
    try:
        doc_info = svc.process_file(
            file_content=file_content,
            filename=original_filename,
            metadata=metadata
        )
        processed = True
        file_id = doc_info.id
        file_type = doc_info.file_type
        file_size = doc_info.file_size
        pages = doc_info.pages
        content = doc_info.content
        blob_url = doc_info.blob_url
        processing_metadata = doc_info.metadata
    except Exception:
        # 回退本地
        processed = False
        file_id = str(uuid.uuid4())
        ext = original_filename.rsplit('.', 1)[1].lower()
        file_type = f'.{ext}'
        pages = 1
        content = extract_content_local_bytes(raw_bytes, original_filename)
        file_size = len(raw_bytes)
        blob_url = None
        processing_metadata = metadata

    # 本地備份
    ext = original_filename.rsplit('.', 1)[1].lower()
    local_filename = f"{file_id}.{ext}"
    local_path = os.path.join(UPLOAD_FOLDER, local_filename)
    with open(local_path, 'wb') as f:
        f.write(raw_bytes)

    record = {
        'id': file_id,
        'filename': original_filename,
        'title': original_filename.rsplit('.', 1)[0],
        'content': content,
        'file_type': file_type,
        'file_size': file_size,
        'pages': pages,
        'blob_url': blob_url,
        'local_file_path': local_path,
        'local_file_id': file_id,
        'mime_type': mimetypes.guess_type(original_filename)[0],
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat(),
        'processing_metadata': processing_metadata,
        'azure_processed': processed
    }
    documents_store[file_id] = record

    return {
        'success': True,
        'file_id': file_id,
        'filename': original_filename,
        'file_size': file_size,
        'pages': pages,
        'file_type': file_type,
        'blob_url': blob_url,
        'content_length': len(content),
        'azure_processed': processed,
        'message': '文件上傳並處理成功' if processed else '文件上傳成功（本地處理）'
    }


@router.get('/documents')
async def list_documents():
    # 回傳 list 以符合 tests 期望
    docs: List[Dict[str, Any]] = []
    for d in documents_store.values():
        docs.append({
            'id': d['id'],
            'filename': d['filename'],
            'title': d['title'],
            'file_size': d['file_size'],
            'file_type': d.get('file_type', ''),
            'pages': d.get('pages', 1),
            'mime_type': d.get('mime_type'),
            'created_at': d['created_at'],
            'updated_at': d['updated_at'],
            'azure_processed': d.get('azure_processed', False),
            'blob_url': d.get('blob_url'),
            'content_length': len(d.get('content', ''))
        })
    docs.sort(key=lambda x: x['created_at'], reverse=True)
    return docs


@router.get('/documents/{doc_id}')
async def get_document(doc_id: str):
    doc = documents_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail='文件不存在')
    # 直接回傳文件全部欄位（flatten）
    return doc


@router.delete('/documents/{doc_id}')
async def delete_document(doc_id: str):
    doc = documents_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail='文件不存在')
    local_path = doc.get('local_file_path')
    if local_path and os.path.exists(local_path):
        try:
            os.remove(local_path)
        except OSError:
            pass
    documents_store.pop(doc_id, None)
    return {'success': True, 'message': '文件已成功刪除'}


@router.get('/documents/{doc_id}/download')
async def download_document(doc_id: str):
    doc = documents_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail='文件不存在')
    local_path = doc.get('local_file_path')
    if local_path and os.path.isfile(local_path):
        return FileResponse(local_path, filename=doc['filename'], media_type=doc.get('mime_type') or 'application/octet-stream')
    raise HTTPException(status_code=404, detail='文件已不存在')


@router.post('/search')
async def search_documents(payload: Dict[str, Any]):
    query = (payload or {}).get('query', '')
    if not query:
        raise HTTPException(status_code=400, detail='查詢內容不能為空')
    max_results = (payload or {}).get('max_results', 10)
    include_content = (payload or {}).get('include_content', False)
    ql = query.lower()
    results = []
    for d in documents_store.values():
        content_l = d.get('content', '').lower()
        title_l = d.get('title', '').lower()
        filename_l = d.get('filename', '').lower()
        if ql in content_l or ql in title_l or ql in filename_l:
            score = 0
            matches = []
            if ql in title_l:
                score += 0.5; matches.append('title')
            if ql in filename_l:
                score += 0.3; matches.append('filename')
            if ql in content_l:
                score += 0.2; matches.append('content')
            snippet = ''
            if ql in content_l:
                sentences = content_l.split('.')
                for s in sentences:
                    if ql in s:
                        snippet = s.strip()[:200] + '...'
                        break
            if not snippet:
                snippet = content_l[:200] + ('...' if len(content_l) > 200 else '')
            item = {
                'id': d['id'],
                'title': d['title'],
                'filename': d['filename'],
                'file_type': d.get('file_type', ''),
                'file_size': d['file_size'],
                'pages': d.get('pages', 1),
                'azure_processed': d.get('azure_processed', False),
                'score': score,
                'matches': matches,
                'snippet': snippet,
                'created_at': d['created_at']
            }
            if include_content:
                item['content'] = d.get('content', '')
            results.append(item)
    results.sort(key=lambda x: x['score'], reverse=True)
    results = results[:max_results]
    return {
        'success': True,
        'query': query,
        'results': results,
        'total_found': len(results),
        'search_params': {'max_results': max_results, 'include_content': include_content}
    }


@router.post('/documents/{doc_id}/analyze')
async def analyze_document(doc_id: str):
    doc = documents_store.get(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail='文件不存在')
    content = doc.get('content', '')
    analysis = {
        'word_count': len(content.split()),
        'character_count': len(content),
        'line_count': len(content.split('\n')),
        'paragraph_count': len([p for p in content.split('\n\n') if p.strip()]),
        'file_info': {
            'filename': doc['filename'],
            'file_type': doc.get('file_type', ''),
            'file_size': doc['file_size'],
            'pages': doc.get('pages', 1),
            'azure_processed': doc.get('azure_processed', False)
        }
    }
    if doc.get('processing_metadata'):
        analysis['processing_info'] = doc['processing_metadata']
    return {'success': True, 'document_id': doc_id, 'analysis': analysis}


def extract_content_local_bytes(raw: bytes, filename: str) -> str:
    ext = filename.rsplit('.', 1)[1].lower()
    try:
        if ext in ['txt', 'md', 'markdown']:
            return raw.decode('utf-8', errors='replace')
        if ext in ['html', 'htm']:
            import re
            html = raw.decode('utf-8', errors='replace')
            return re.sub(r'<[^>]+>', '', html)
        if ext == 'pdf':
            try:
                import PyMuPDF as fitz  # type: ignore
            except Exception:
                try:
                    import fitz  # type: ignore
                except Exception:
                    return f"PDF文件: {filename} (需要安裝 PyMuPDF 來提取內容)"
            try:  # pragma: no cover (I/O heavy)
                tmp_path = os.path.join(UPLOAD_FOLDER, f"_tmp_{uuid.uuid4()}.pdf")
                with open(tmp_path, 'wb') as f:
                    f.write(raw)
                doc_pdf = fitz.open(tmp_path)
                text = ''.join(page.get_text() for page in doc_pdf)
                doc_pdf.close()
                os.remove(tmp_path)
                return text
            except Exception:
                return f"PDF文件: {filename} (解析失敗)"
        if ext in ['doc', 'docx']:
            return f"Word文檔: {filename} (需要解析器)"
        return f"不支援的文件格式: {filename}"
    except Exception as e:  # pragma: no cover
        return f"讀取文件內容失敗: {e}"
