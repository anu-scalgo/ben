# Deployment Guide - Linux Server

This guide covers deploying the Dumacle Backend API to a Linux server (Ubuntu/Debian).

## Prerequisites

- Linux server (Ubuntu 20.04+ or Debian 11+)
- Root or sudo access
- Domain name (optional, but recommended)
- SSL certificate (Let's Encrypt recommended)

## 1. Server Setup

### Update System
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Required System Packages
```bash
sudo apt install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    git \
    curl \
    ffmpeg \
    supervisor
```

### Install Poetry (Python Package Manager)
```bash
curl -sSL https://install.python-poetry.org | python3 -
export PATH="/root/.local/bin:$PATH"
echo 'export PATH="/root/.local/bin:$PATH"' >> ~/.bashrc
```

## 2. PostgreSQL Setup

### Create Database and User
```bash
sudo -u postgres psql
```

In PostgreSQL shell:
```sql
CREATE DATABASE dumacle;
CREATE USER dumacle_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE dumacle TO dumacle_user;
\q
```

### Configure PostgreSQL for Remote Access (if needed)
Edit `/etc/postgresql/*/main/postgresql.conf`:
```
listen_addresses = 'localhost'
```

Edit `/etc/postgresql/*/main/pg_hba.conf`:
```
local   dumacle    dumacle_user                     md5
```

Restart PostgreSQL:
```bash
sudo systemctl restart postgresql
```

## 3. Redis Setup

### Start and Enable Redis
```bash
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

### Verify Redis is Running
```bash
redis-cli ping
# Should return: PONG
```

## 4. Application Deployment

### Create Application User
```bash
sudo useradd -m -s /bin/bash dumacle
sudo su - dumacle
```

### Clone Repository
```bash
cd /home/dumacle
git clone https://github.com/your-org/dumacle-backend.git
cd dumacle-backend
```

### Install Dependencies
```bash
poetry install --no-dev
```

### Configure Environment Variables
```bash
cp env.example .env
nano .env
```

Update the following critical values:
```bash
# Database
DATABASE_URL=postgresql+asyncpg://dumacle_user:your_secure_password@localhost:5432/dumacle

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT (IMPORTANT: Generate a secure key!)
JWT_SECRET_KEY=$(openssl rand -hex 32)
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Storage (configure your provider)
STORAGE_PROVIDER=s3
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
S3_BUCKET_NAME=your-bucket-name

# Stripe (if using subscriptions)
STRIPE_SECRET_KEY=sk_live_your_stripe_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret

# Application
DEBUG=False
ENVIRONMENT=production
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# File Upload
MAX_FILE_SIZE_MB=2048
```

### Run Database Migrations
```bash
poetry run alembic upgrade head
```

### Seed Default Super Admin
```bash
poetry run python scripts/seed.py
```

**Default credentials:**
- Email: `admin@example.com`
- Password: `admin123456`
- **⚠️ IMPORTANT:** Change this password immediately after first login!

### Run Deployment Checks
```bash
poetry run python scripts/deploy.py
```

## 5. Process Management with Systemd

### Create Systemd Service for FastAPI
Create `/etc/systemd/system/dumacle-api.service`:
```ini
[Unit]
Description=Dumacle FastAPI Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=dumacle
Group=dumacle
WorkingDirectory=/home/dumacle/dumacle-backend
Environment="PATH=/home/dumacle/dumacle-backend/.venv/bin"
ExecStart=/home/dumacle/dumacle-backend/.venv/bin/gunicorn src.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --access-logfile /var/log/dumacle/access.log \
    --error-logfile /var/log/dumacle/error.log \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Create Systemd Service for Celery Worker
Create `/etc/systemd/system/dumacle-celery.service`:
```ini
[Unit]
Description=Dumacle Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=dumacle
Group=dumacle
WorkingDirectory=/home/dumacle/dumacle-backend
Environment="PATH=/home/dumacle/dumacle-backend/.venv/bin"
ExecStart=/home/dumacle/dumacle-backend/.venv/bin/celery -A src.tasks.celery_app worker \
    --loglevel=info \
    --logfile=/var/log/dumacle/celery.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Create Systemd Service for Celery Beat (Scheduled Tasks)
Create `/etc/systemd/system/dumacle-celery-beat.service`:
```ini
[Unit]
Description=Dumacle Celery Beat Scheduler
After=network.target redis.service

[Service]
Type=simple
User=dumacle
Group=dumacle
WorkingDirectory=/home/dumacle/dumacle-backend
Environment="PATH=/home/dumacle/dumacle-backend/.venv/bin"
ExecStart=/home/dumacle/dumacle-backend/.venv/bin/celery -A src.tasks.celery_app beat \
    --loglevel=info \
    --logfile=/var/log/dumacle/celery-beat.log

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Create Log Directory
```bash
sudo mkdir -p /var/log/dumacle
sudo chown dumacle:dumacle /var/log/dumacle
```

### Enable and Start Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable dumacle-api dumacle-celery dumacle-celery-beat
sudo systemctl start dumacle-api dumacle-celery dumacle-celery-beat
```

### Check Service Status
```bash
sudo systemctl status dumacle-api
sudo systemctl status dumacle-celery
sudo systemctl status dumacle-celery-beat
```

## 6. Nginx Configuration

### Create Nginx Configuration
Create `/etc/nginx/sites-available/dumacle`:
```nginx
upstream dumacle_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Client Max Body Size (for file uploads)
    client_max_body_size 2048M;

    # Timeouts for large uploads
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    send_timeout 600s;

    location / {
        proxy_pass http://dumacle_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Static files (if any)
    location /static {
        alias /home/dumacle/dumacle-backend/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Access and Error Logs
    access_log /var/log/nginx/dumacle_access.log;
    error_log /var/log/nginx/dumacle_error.log;
}
```

### Enable Site and Test Configuration
```bash
sudo ln -s /etc/nginx/sites-available/dumacle /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 7. SSL Certificate (Let's Encrypt)

### Install Certbot
```bash
sudo apt install certbot python3-certbot-nginx -y
```

### Obtain SSL Certificate
```bash
sudo certbot --nginx -d api.yourdomain.com
```

### Auto-Renewal
Certbot automatically sets up renewal. Verify:
```bash
sudo certbot renew --dry-run
```

## 8. Firewall Configuration

### Configure UFW
```bash
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 9. Monitoring and Logs

### View Application Logs
```bash
# API logs
sudo journalctl -u dumacle-api -f

# Celery worker logs
sudo journalctl -u dumacle-celery -f

# Celery beat logs
sudo journalctl -u dumacle-celery-beat -f

# Nginx logs
sudo tail -f /var/log/nginx/dumacle_access.log
sudo tail -f /var/log/nginx/dumacle_error.log
```

### Check Service Status
```bash
sudo systemctl status dumacle-api dumacle-celery dumacle-celery-beat nginx postgresql redis
```

## 10. Updating the Application

### Pull Latest Changes
```bash
sudo su - dumacle
cd /home/dumacle/dumacle-backend
git pull origin main
```

### Install New Dependencies (if any)
```bash
poetry install --no-dev
```

### Run Migrations
```bash
poetry run alembic upgrade head
```

### Restart Services
```bash
sudo systemctl restart dumacle-api dumacle-celery dumacle-celery-beat
```

## 11. Backup Strategy

### Database Backup Script
Create `/home/dumacle/backup-db.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/home/dumacle/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

pg_dump -U dumacle_user dumacle > $BACKUP_DIR/dumacle_$DATE.sql
gzip $BACKUP_DIR/dumacle_$DATE.sql

# Keep only last 7 days of backups
find $BACKUP_DIR -name "dumacle_*.sql.gz" -mtime +7 -delete
```

### Setup Cron Job
```bash
chmod +x /home/dumacle/backup-db.sh
crontab -e
```

Add:
```
0 2 * * * /home/dumacle/backup-db.sh
```

## 12. Security Best Practices

1. **Change Default Credentials**
   - Change the default super admin password immediately
   - Use strong, unique passwords for all services

2. **Environment Variables**
   - Never commit `.env` to version control
   - Use strong random values for `JWT_SECRET_KEY`

3. **Database Security**
   - Use strong PostgreSQL passwords
   - Restrict database access to localhost only

4. **File Permissions**
   ```bash
   chmod 600 /home/dumacle/dumacle-backend/.env
   chown dumacle:dumacle /home/dumacle/dumacle-backend/.env
   ```

5. **Regular Updates**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

6. **Monitoring**
   - Set up monitoring (e.g., Prometheus, Grafana)
   - Configure alerts for service failures

## 13. Troubleshooting

### Service Won't Start
```bash
# Check logs
sudo journalctl -u dumacle-api -n 50

# Check configuration
poetry run python scripts/deploy.py
```

### Database Connection Issues
```bash
# Test connection
psql -U dumacle_user -d dumacle -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

### Redis Connection Issues
```bash
# Test Redis
redis-cli ping

# Check Redis status
sudo systemctl status redis-server
```

### High Memory Usage
```bash
# Reduce Gunicorn workers in systemd service
# Edit /etc/systemd/system/dumacle-api.service
# Change --workers 4 to --workers 2
sudo systemctl daemon-reload
sudo systemctl restart dumacle-api
```

## 14. Performance Optimization

### Enable Gzip Compression in Nginx
Add to nginx config:
```nginx
gzip on;
gzip_vary on;
gzip_min_length 1024;
gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
```

### Database Connection Pooling
Already configured in SQLAlchemy settings.

### Redis Caching
Configure Redis maxmemory policy in `/etc/redis/redis.conf`:
```
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## Support

For issues or questions:
- Check logs: `sudo journalctl -u dumacle-api -f`
- Review configuration: `poetry run python scripts/deploy.py`
- Consult README.md and INSTALLATION.md

---

**Deployment Checklist:**
- [ ] Server updated and packages installed
- [ ] PostgreSQL database created
- [ ] Redis running
- [ ] Application cloned and dependencies installed
- [ ] `.env` configured with production values
- [ ] Database migrations run
- [ ] Default super admin seeded and password changed
- [ ] Systemd services created and running
- [ ] Nginx configured and running
- [ ] SSL certificate obtained
- [ ] Firewall configured
- [ ] Backup strategy implemented
- [ ] Monitoring configured
