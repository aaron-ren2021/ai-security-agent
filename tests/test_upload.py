import requests

def test_file_upload():
    """測試文件上傳功能"""
    
    # 創建測試文件
    test_content = "這是一個測試安全報告文件\n包含一些關鍵字：SQL injection, XSS, CSRF"
    
    # 準備上傳
    files = {'file': ('test_security.txt', test_content, 'text/plain')}
    
    try:
        response = requests.post('http://127.0.0.1:5002/api/files/upload', files=files)
        print(f"上傳狀態碼: {response.status_code}")
        print(f"上傳回應: {response.text}")
        
        if response.status_code == 200:
            # 測試文件列表
            list_response = requests.get('http://127.0.0.1:5002/api/files/documents')
            print(f"文件列表狀態碼: {list_response.status_code}")
            print(f"文件列表: {list_response.text}")
            
    except Exception as e:
        print(f"測試失敗: {e}")

if __name__ == "__main__":
    test_file_upload()