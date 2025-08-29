# AI資訊安全RAG Chat機器人 - 部署指南

## 🚀 快速部署

### 方法一：本地開發部署

```bash
# 1. 克隆專案
git clone <repository-url>
cd ai_security_rag_bot

# 2. 啟動虛擬環境
source venv/bin/activate

# 3. 安裝依賴
pip install -r requirements.txt

# 4. 配置環境變數
cp .env.example .env
# 編輯 .env 檔案

# 5. 啟動應用程式
python src/main.py
```

### 方法二：Docker部署

```bash
# 1. 建立Docker映像
docker build -t ai-security-rag-bot .

# 2. 運行容器
docker run -d \
  --name ai-security-rag-bot \
  -p 5000:5000 \
  -e OPENAI_API_KEY=your_api_key \
  -e OPENAI_API_BASE=your_api_base \
  ai-security-rag-bot
```

### 方法三：Docker Compose部署（推薦）

```yaml
# docker-compose.yml
version: '3.8'

services:
  ai-security-rag-bot:
    build: .
    ports:
      - "5000:5000"
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - OPENAI_API_BASE=${OPENAI_API_BASE}
      - FLASK_ENV=production
    volumes:
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
    restart: unless-stopped

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - ai-security-rag-bot
    restart: unless-stopped
```

```bash
# 啟動服務
docker-compose up -d
```

## 🏗️ 生產環境部署

### 1. 系統需求

**最低配置：**
- CPU: 2核心
- RAM: 4GB
- 儲存: 20GB SSD
- 網路: 100Mbps

**建議配置：**
- CPU: 4核心
- RAM: 8GB
- 儲存: 50GB SSD
- 網路: 1Gbps

### 2. 環境準備

```bash
# Ubuntu 22.04 LTS
sudo apt update && sudo apt upgrade -y

# 安裝必要套件
sudo apt install -y python3.11 python3.11-venv python3-pip nginx redis-server

# 安裝Docker（可選）
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### 3. 應用程式部署

```bash
# 建立應用程式目錄
sudo mkdir -p /opt/ai-security-rag-bot
sudo chown $USER:$USER /opt/ai-security-rag-bot

# 部署應用程式
cd /opt/ai-security-rag-bot
git clone <repository-url> .

# 建立虛擬環境
python3.11 -m venv venv
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
pip install gunicorn

# 配置環境變數
sudo cp .env.example .env
sudo nano .env
```

### 4. Systemd服務配置

```bash
# 建立服務檔案
sudo nano /etc/systemd/system/ai-security-rag-bot.service
```

```ini
[Unit]
Description=AI Security RAG Chat Bot
After=network.target

[Service]
Type=exec
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/ai-security-rag-bot
Environment=PATH=/opt/ai-security-rag-bot/venv/bin
ExecStart=/opt/ai-security-rag-bot/venv/bin/gunicorn -w 4 -b 127.0.0.1:5000 src.main:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# 啟動服務
sudo systemctl daemon-reload
sudo systemctl enable ai-security-rag-bot
sudo systemctl start ai-security-rag-bot
sudo systemctl status ai-security-rag-bot
```

### 5. Nginx反向代理配置

```bash
# 建立Nginx配置
sudo nano /etc/nginx/sites-available/ai-security-rag-bot
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL配置
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 安全標頭
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # 代理設定
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支援
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 靜態檔案快取
    location /static/ {
        alias /opt/ai-security-rag-bot/src/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # API限流
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# 限流配置
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
}
```

```bash
# 啟用站點
sudo ln -s /etc/nginx/sites-available/ai-security-rag-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔒 SSL憑證配置

### 使用Let's Encrypt

```bash
# 安裝Certbot
sudo apt install certbot python3-certbot-nginx

# 取得憑證
sudo certbot --nginx -d your-domain.com

# 自動續期
sudo crontab -e
# 添加：0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 監控與日誌

### 1. 應用程式監控

```bash
# 安裝監控工具
pip install prometheus-flask-exporter

# 查看系統狀態
sudo systemctl status ai-security-rag-bot
sudo journalctl -u ai-security-rag-bot -f
```

### 2. 日誌配置

```python
# 在main.py中添加日誌配置
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
```

### 3. 效能監控

```bash
# 安裝htop
sudo apt install htop

# 監控系統資源
htop

# 監控網路連接
sudo netstat -tulpn | grep :5000
```

## 🔧 維護與更新

### 1. 應用程式更新

```bash
# 停止服務
sudo systemctl stop ai-security-rag-bot

# 更新代碼
cd /opt/ai-security-rag-bot
git pull origin main

# 更新依賴
source venv/bin/activate
pip install -r requirements.txt

# 重啟服務
sudo systemctl start ai-security-rag-bot
```

### 2. 資料庫維護

```bash
# 備份向量資料庫
tar -czf chroma_db_backup_$(date +%Y%m%d).tar.gz chroma_db/

# 清理舊日誌
find logs/ -name "*.log" -mtime +30 -delete
```

### 3. 安全更新

```bash
# 系統更新
sudo apt update && sudo apt upgrade -y

# Python套件更新
pip list --outdated
pip install --upgrade package_name
```

## 🚨 故障排除

### 常見問題

1. **服務無法啟動**
```bash
# 檢查日誌
sudo journalctl -u ai-security-rag-bot -n 50

# 檢查端口佔用
sudo lsof -i :5000

# 檢查權限
ls -la /opt/ai-security-rag-bot/
```

2. **記憶體不足**
```bash
# 檢查記憶體使用
free -h

# 增加swap空間
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

3. **SSL憑證問題**
```bash
# 檢查憑證狀態
sudo certbot certificates

# 手動續期
sudo certbot renew
```

## 📈 擴展部署

### 1. 負載平衡

```nginx
upstream ai_security_backend {
    server 127.0.0.1:5000;
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
}

server {
    location / {
        proxy_pass http://ai_security_backend;
    }
}
```

### 2. 資料庫分離

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ai_security
      POSTGRES_USER: app_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### 3. 微服務架構

```yaml
services:
  api-gateway:
    image: nginx:alpine
    ports:
      - "80:80"

  auth-service:
    build: ./services/auth
    
  rag-service:
    build: ./services/rag
    
  agent-service:
    build: ./services/agent
```

## 🔐 安全最佳實踐

1. **防火牆配置**
```bash
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

2. **定期備份**
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf /backup/ai_security_backup_$DATE.tar.gz \
  /opt/ai-security-rag-bot \
  --exclude=/opt/ai-security-rag-bot/venv
```

3. **監控異常**
```bash
# 安裝fail2ban
sudo apt install fail2ban

# 配置nginx日誌監控
sudo nano /etc/fail2ban/jail.local
```

---

**注意**：請根據實際環境調整配置參數，確保系統安全性和效能最佳化。

