"""
UI 測試：測試登入狀態修復頁面和跨設備兼容性
對應測試計畫中的「使用者介面（UI）測試」測試用例
"""
import pytest
from unittest.mock import Mock, patch

selenium = pytest.importorskip("selenium")
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import os
from src.main import app


@pytest.mark.ui
class TestLoginFixPage:
    """登入狀態修復頁面測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_fix_login_page_loads(self, client):
        """測試修復登入頁面能正常載入"""
        response = client.get('/static/fix-login.html')
        
        assert response.status_code == 200
        html_content = response.get_data(as_text=True)
        
        # 檢查頁面基本元素
        assert '修復右上角登入顯示' in html_content
        assert 'aaron-ren2021' in html_content
        assert 'aaron_l@cloudinfo.com.tw' in html_content
        assert 'GitHub' in html_content
    
    def test_fix_login_page_buttons_present(self, client):
        """測試修復登入頁面按鈕存在"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查關鍵按鈕
        assert '修復登入狀態' in html_content
        assert '檢查認證狀態' in html_content
        assert '前往主頁' in html_content
        assert 'onclick="fixLogin()"' in html_content
        assert 'onclick="checkStatus()"' in html_content
        assert 'onclick="goToMain()"' in html_content
    
    def test_fix_login_page_css_styling(self, client):
        """測試修復登入頁面CSS樣式"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查CSS樣式定義
        assert 'background: linear-gradient' in html_content
        assert '.container' in html_content
        assert '.btn' in html_content
        assert '.success' in html_content
        
        # 檢查響應式設計
        assert 'viewport' in html_content
        assert 'width=device-width' in html_content
    
    def test_fix_login_javascript_functions(self, client):
        """測試修復登入頁面JavaScript功能"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查JavaScript函數定義
        assert 'function fixLogin()' in html_content
        assert 'function checkStatus()' in html_content
        assert 'function goToMain()' in html_content
        
        # 檢查Session Cookie設定
        assert 'document.cookie' in html_content
        assert 'session_id=' in html_content
        assert 'path=/' in html_content
        assert 'SameSite=Lax' in html_content
    
    def test_auth_status_endpoint_integration(self, client):
        """測試認證狀態端點整合"""
        # 檢查fix-login.html中使用的認證端點
        response = client.get('/auth/status')
        
        assert response.status_code == 200
        data = response.get_json()
        
        # 應該有基本的認證狀態回應
        assert 'authenticated' in data
        assert isinstance(data['authenticated'], bool)


@pytest.mark.ui
@pytest.mark.slow
class TestCrossDeviceCompatibility:
    """跨設備兼容性測試"""
    
    @pytest.fixture(scope="class")
    def web_server(self):
        """測試Web伺服器 fixture"""
        import threading
        import time
        from werkzeug.serving import make_server
        
        app.config['TESTING'] = True
        server = make_server('127.0.0.1', 5555, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        
        # 等待伺服器啟動
        time.sleep(1)
        
        yield 'http://127.0.0.1:5555'
        
        server.shutdown()
    
    @pytest.fixture
    def desktop_driver(self):
        """桌面瀏覽器驅動 fixture"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 無頭模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--window-size=1920,1080')
            
            driver = webdriver.Chrome(options=chrome_options)
            yield driver
            driver.quit()
        except Exception:
            pytest.skip("Chrome WebDriver not available")
    
    @pytest.fixture
    def mobile_driver(self):
        """行動設備模擬器驅動 fixture"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            
            # 模擬行動設備
            mobile_emulation = {
                "deviceName": "iPhone 12"
            }
            chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
            
            driver = webdriver.Chrome(options=chrome_options)
            yield driver
            driver.quit()
        except Exception:
            pytest.skip("Chrome WebDriver not available")
    
    def test_desktop_ui_elements(self, web_server, desktop_driver):
        """測試桌面設備UI元素顯示"""
        desktop_driver.get(f"{web_server}/static/fix-login.html")
        
        # 等待頁面載入
        wait = WebDriverWait(desktop_driver, 10)
        
        # 檢查主要容器
        container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "container"))
        )
        assert container.is_displayed()
        
        # 檢查按鈕
        buttons = desktop_driver.find_elements(By.CLASS_NAME, "btn")
        assert len(buttons) >= 3  # 至少3個按鈕
        
        for button in buttons:
            assert button.is_displayed()
            assert button.is_enabled()
        
        # 檢查資訊區塊
        info_block = desktop_driver.find_element(By.CLASS_NAME, "info")
        assert info_block.is_displayed()
        
        # 檢查用戶資訊
        assert "aaron-ren2021" in desktop_driver.page_source
        assert "aaron_l@cloudinfo.com.tw" in desktop_driver.page_source
    
    def test_mobile_ui_elements(self, web_server, mobile_driver):
        """測試行動設備UI元素顯示"""
        mobile_driver.get(f"{web_server}/static/fix-login.html")
        
        # 等待頁面載入
        wait = WebDriverWait(mobile_driver, 10)
        
        # 檢查主要容器在行動設備上的顯示
        container = wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "container"))
        )
        assert container.is_displayed()
        
        # 檢查容器寬度適應行動設備
        container_width = container.size['width']
        viewport_width = mobile_driver.execute_script("return window.innerWidth")
        
        # 容器寬度應該適應視窗寬度（考慮padding和margins）
        assert container_width <= viewport_width
        
        # 檢查按鈕在行動設備上可點擊
        buttons = mobile_driver.find_elements(By.CLASS_NAME, "btn")
        for button in buttons:
            assert button.is_displayed()
            assert button.is_enabled()
            
            # 按鈕應該有足夠的觸控區域（至少44px高度，iOS建議）
            button_height = button.size['height']
            assert button_height >= 40  # 稍微放寬要求
    
    def test_responsive_design_breakpoints(self, web_server, desktop_driver):
        """測試響應式設計斷點"""
        test_resolutions = [
            (1920, 1080),  # 桌面
            (1024, 768),   # 平板橫向
            (768, 1024),   # 平板直向
            (375, 667),    # 手機
        ]
        
        for width, height in test_resolutions:
            desktop_driver.set_window_size(width, height)
            desktop_driver.get(f"{web_server}/static/fix-login.html")
            
            # 等待頁面載入
            time.sleep(1)
            
            # 檢查容器顯示
            container = desktop_driver.find_element(By.CLASS_NAME, "container")
            assert container.is_displayed()
            
            # 檢查按鈕佈局
            buttons = desktop_driver.find_elements(By.CLASS_NAME, "btn")
            for button in buttons:
                assert button.is_displayed()
    
    def test_button_functionality(self, web_server, desktop_driver):
        """測試按鈕功能"""
        desktop_driver.get(f"{web_server}/static/fix-login.html")
        
        # 等待頁面載入
        wait = WebDriverWait(desktop_driver, 10)
        
        # 測試修復登入按鈕
        fix_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), '修復登入狀態')]"))
        )
        
        # 點擊修復按鈕
        fix_button.click()
        
        # 檢查是否有成功訊息顯示
        time.sleep(1)  # 等待JavaScript執行
        result_div = desktop_driver.find_element(By.ID, "result")
        
        # 應該顯示某種回饋訊息
        assert result_div.text != ""
    
    def test_css_media_queries(self, web_server, desktop_driver):
        """測試CSS媒體查詢效果"""
        desktop_driver.get(f"{web_server}/static/fix-login.html")
        
        # 檢查不同螢幕尺寸下的樣式
        desktop_driver.set_window_size(1200, 800)
        container = desktop_driver.find_element(By.CLASS_NAME, "container")
        desktop_width = container.size['width']
        
        desktop_driver.set_window_size(400, 600)
        time.sleep(0.5)  # 等待重新渲染
        mobile_width = container.size['width']
        
        # 在較小螢幕上，容器寬度應該調整
        assert mobile_width < desktop_width


@pytest.mark.ui
class TestUIErrorHandling:
    """UI 錯誤處理測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_missing_static_file_handling(self, client):
        """測試靜態檔案缺失處理"""
        response = client.get('/static/nonexistent.html')
        assert response.status_code == 404
    
    def test_javascript_error_resilience(self, client):
        """測試JavaScript錯誤容錯性"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查是否有try-catch錯誤處理
        assert 'try' in html_content or 'catch' in html_content or \
               'async' in html_content, "應該有某種錯誤處理機制"
    
    def test_network_failure_handling(self, client):
        """測試網路失敗處理"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查fetch調用是否有錯誤處理
        if 'fetch(' in html_content:
            assert '.catch(' in html_content or 'try' in html_content, \
                   "fetch調用應該有錯誤處理"


@pytest.mark.ui
class TestAccessibility:
    """UI 可訪問性測試"""
    
    @pytest.fixture
    def client(self):
        """測試客戶端 fixture"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    def test_semantic_html_structure(self, client):
        """測試語義化HTML結構"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查基本HTML語義
        assert '<h1>' in html_content or '<h2>' in html_content, "應該有標題元素"
        assert '<button' in html_content, "按鈕應該使用button元素"
        assert 'lang=' in html_content, "應該設定頁面語言"
    
    def test_contrast_and_readability(self, client):
        """測試對比度和可讀性"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查是否有適當的顏色設計
        assert 'color:' in html_content, "應該有顏色定義"
        assert 'background:' in html_content or 'background-color:' in html_content, \
               "應該有背景顏色定義"
    
    def test_keyboard_navigation_support(self, client):
        """測試鍵盤導航支援"""
        response = client.get('/static/fix-login.html')
        html_content = response.get_data(as_text=True)
        
        # 檢查是否有鍵盤導航支援的跡象
        # 這主要通過button元素自動支援
        assert '<button' in html_content, "button元素支援鍵盤導航"
