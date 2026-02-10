# PowerLit API Deployment Guide

## 🚀 Quick Start (Docker - Recommended)

### Prerequisites
- Docker 20.10+
- Docker Compose 1.29+

### Deploy in 3 steps:

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd powerlit_fastapi

# 2. Run deployment script
./deploy.sh
# Choose option 1 for Docker

# 3. Or manually with docker-compose
docker-compose up --build -d
```

**API will be available at:** http://localhost:8000

**Documentation:** http://localhost:8000/docs

---

## 🐳 Docker Deployment

### Local Development
```bash
# Build and run
docker-compose up --build

# Run in background
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Production with Docker

```bash
# Build production image
docker build -t powerlit-api:latest .

# Run with environment variables
docker run -d \
  -p 8000:8000 \
  -e GOOGLE_API_KEY=your_key \
  -v $(pwd)/data:/app/data \
  -v powerlit_chroma:/app/chromadb_store \
  --name powerlit-api \
  --restart unless-stopped \
  powerlit-api:latest

# Or use docker-compose for production
docker-compose -f docker-compose.yml up -d
```

---

## ☁️ Cloud Deployment Options

### 1. Railway (Recommended for ease)

**Prerequisites:**
- Railway CLI: `npm install -g @railway/cli`

**Deploy:**
```bash
# Login
railway login

# Initialize project
railway init

# Deploy
railway up

# Get domain
railway domain
```

**Settings:**
- Build command: (uses Dockerfile automatically)
- Start command: (uses CMD from Dockerfile)
- Environment variables: Add GOOGLE_API_KEY in dashboard

### 2. Render

**Steps:**
1. Push code to GitHub/GitLab
2. Go to https://render.com
3. New → Web Service
4. Connect repository
5. Settings:
   - **Name:** powerlit-api
   - **Runtime:** Docker
   - **Instance Type:** Standard ($7/month) or higher
   - **Environment Variables:**
     - `GOOGLE_API_KEY`: your_api_key (optional)
6. Create Web Service

**Free tier limitations:**
- Sleeps after 15 min inactivity
- Limited to 512MB RAM (may be slow for large PDFs)

### 3. AWS (EC2 or ECS)

**EC2 Deployment:**
```bash
# Launch Ubuntu 22.04 instance (t3.medium or larger)
# SSH into instance
sudo apt-get update
sudo apt-get install -y docker.io docker-compose git

# Clone and deploy
git clone <your-repo>
cd powerlit_fastapi
docker-compose up -d

# Setup nginx reverse proxy (optional)
sudo apt-get install -y nginx
```

**ECS/Fargate:** Use AWS Copilot or Terraform for production-grade deployment.

### 4. Google Cloud Run

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/powerlit-api

# Deploy to Cloud Run
gcloud run deploy powerlit-api \
  --image gcr.io/PROJECT-ID/powerlit-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --concurrency 80
```

**Note:** Cloud Run has request timeout limits (300s default) - adjust for large PDF processing.

### 5. DigitalOcean App Platform

```bash
# Install doctl
# Deploy
doctl apps create --spec .do/app.yaml
```

---

## 🖥️ Manual Deployment (VPS/Bare Metal)

### Requirements
- Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- Python 3.11+
- 2GB+ RAM (4GB recommended)

### Installation

```bash
# 1. System dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip \
    tesseract-ocr poppler-utils

# 2. Clone repository
git clone <your-repo>
cd powerlit_fastapi

# 3. Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run with uvicorn (development)
uvicorn main:app --host 0.0.0.0 --port 8000

# Or with gunicorn (production)
pip install gunicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 5
```

### Production Setup with Systemd

Create `/etc/systemd/system/powerlit.service`:
```ini
[Unit]
Description=PowerLit API
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/powerlit_fastapi
Environment="PATH=/home/ubuntu/powerlit_fastapi/venv/bin"
Environment="GOOGLE_API_KEY=your_api_key"
ExecStart=/home/ubuntu/powerlit_fastapi/venv/bin/gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable powerlit
sudo systemctl start powerlit
sudo systemctl status powerlit
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for large file uploads
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

---

## 📊 Scaling Considerations

### Resource Requirements

| Component | CPU | RAM | Notes |
|-----------|-----|-----|-------|
| API Server | 0.5-1 | 512MB | Basic operations |
| PDF Processing | 1-2 | 1GB | Large PDFs need more |
| Vector DB | 0.2 | 256MB | ChromaDB in-memory |
| **Total** | **2** | **2GB** | **Recommended minimum** |

### Performance Tips

1. **For large PDFs:**
   - Use 4GB+ RAM
   - Set longer timeouts (120s+)
   - Consider async processing queue (Redis + Celery)

2. **For high throughput:**
   - Deploy multiple instances behind load balancer
   - Use Redis for session storage
   - Enable CDN for static files

3. **Database optimization:**
   - Persist ChromaDB to disk (not memory)
   - Regular backups of knowledge_base/

---

## 🔐 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | No | "" | Google Gemini API key (optional) |
| `DEBUG` | No | false | Enable debug mode |
| `CHROMA_DB_PATH` | No | ./chromadb_store | Vector DB storage path |
| `COLLECTION_NAME` | No | gs1009_standards | Standards collection name |
| `MAX_FILE_SIZE` | No | 52428800 (50MB) | Max upload size in bytes |

---

## ✅ Post-Deployment Checklist

- [ ] API accessible at `/health`
- [ ] Documentation accessible at `/docs`
- [ ] Can upload PDF via `/api/v1/analysis/analyze`
- [ ] File size limits configured
- [ ] Environment variables set
- [ ] Persistent volumes for data/
- [ ] SSL/HTTPS configured (for production)
- [ ] Monitoring/logging setup (optional)
- [ ] Backup strategy for knowledge_base/

---

## 🆘 Troubleshooting

### "tesseract not found"
Install Tesseract OCR:
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr

# macOS
brew install tesseract
```

### "poppler not found"
Install poppler-utils:
```bash
# Ubuntu/Debian
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

### Container crashes on large PDFs
Increase memory limits:
```yaml
# docker-compose.yml
services:
  api:
    deploy:
      resources:
        limits:
          memory: 4G
```

### Permission denied on data/
```bash
sudo chown -R 1000:1000 data/ chromadb_store/
```

---

## 📞 Support

For deployment issues:
1. Check logs: `docker-compose logs -f`
2. Run tests: `pytest tests/`
3. Check GitHub Issues

## 🎉 Success!

Your PowerLit API is now deployed and ready to analyze electrical blueprints!
