import pytest
import json
from src.main import app

def test_download_error_debug():
    """調試下載功能錯誤"""
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # 創建測試文件
        test_content = "Test file content for download"
        
        # 上傳文件
        from io import BytesIO
        data = {
            'file': (BytesIO(test_content.encode('utf-8')), 'test_download.txt')
        }
        upload_response = client.post('/api/files/upload', data=data)
        print(f"Upload response: {upload_response.get_json()}")
        
        if upload_response.status_code == 200:
            file_id = upload_response.get_json()['file_id']
            
            # 嘗試下載
            download_response = client.get(f'/api/files/documents/{file_id}/download')
            print(f"Download status: {download_response.status_code}")
            print(f"Download data: {download_response.get_data(as_text=True)}")

if __name__ == "__main__":
    test_download_error_debug()