# 文件上傳和分析功能擴展
# 這些功能將添加到 rag_api.py 中

from datetime import datetime
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'csv', 'json', 'xml', 'html'}
UPLOAD_FOLDER = 'uploads'
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# 確保上傳目錄存在
import os
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    """檢查檔案類型是否允許"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 新增：報告類型偵測與分析（簡化版）
def detect_report_type(content: str, filename: str) -> str:
    name_lower = filename.lower()
    if 'nessus' in name_lower or 'nessus' in content.lower():
        return 'nessus'
    if 'qualys' in name_lower or 'qualys' in content.lower():
        return 'qualys'
    if 'openvas' in name_lower or 'openvas' in content.lower():
        return 'openvas'
    if 'cve-' in content.lower():
        return 'cve_list'
    return 'generic'


def analyze_vulnerability_report(content: str, report_type: str) -> dict:
    # 簡化版：回傳摘要與假設的風險條目
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    sample = lines[:20]
    high_risk_keywords = ['sql injection', 'xss', 'rce', 'remote code', 'privilege escalation', 'critical']
    risk_hits = [l for l in lines if any(k in l.lower() for k in high_risk_keywords)][:10]
    return {
        'summary': f'{report_type} 報告，行數: {len(lines)}，截取 {len(sample)} 行樣本。',
        'potential_high_risks': risk_hits,
        'sample': sample,
        'parsed_at': datetime.now().isoformat()
    }

# 以下是需要添加到 rag_api.py 的路由函數：

"""
@rag_bp.route('/upload/vulnerability-report', methods=['POST'])
def upload_vulnerability_report():
    \"\"\"上傳並分析弱掃報告\"\"\"
    try:
        initialize_services()
        initialize_azure_openai()
        
        # 檢查是否有文件
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File type not allowed"}), 400
        
        # 檢查文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({"error": "File too large"}), 400
        
        # 讀取文件內容
        filename = secure_filename(file.filename)
        file_content = file.read().decode('utf-8', errors='ignore')
        
        # 分析報告類型
        report_type = detect_report_type(file_content, filename)
        
        # 使用 Azure OpenAI 分析弱掃報告
        analysis_result = analyze_vulnerability_report(file_content, report_type)
        
        # 將分析結果加入知識庫
        metadata = {
            'filename': filename,
            'report_type': report_type,
            'upload_date': datetime.now().isoformat(),
            'analysis_summary': analysis_result.get('summary', '')
        }
        
        document_id = vectorization_service.add_document(
            collection_name='vulnerability_reports',
            content=f"檔案名稱: {filename}\\n報告類型: {report_type}\\n\\n{file_content}",
            metadata=metadata
        )
        
        return jsonify({
            "success": True,
            "filename": filename,
            "report_type": report_type,
            "analysis": analysis_result,
            "document_id": document_id,
            "message": "弱掃報告上傳並分析完成"
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
"""
