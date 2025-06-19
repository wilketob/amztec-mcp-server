# VPS Deployment Guide

This guide covers deploying the Amazon SP API MCP Server on a VPS for production use with Django integration.

## Quick Deploy with Docker (Recommended)

### Prerequisites
- Docker and Docker Compose installed on your VPS
- Domain name pointed to your VPS (optional but recommended)
- Amazon SP API credentials

### Step 1: Copy Files to VPS
```bash
# From your local machine
scp -r . user@your-vps:/opt/amazon-mcp-server/
```

### Step 2: Configure Environment
```bash
# On your VPS
cd /opt/amazon-mcp-server
cp .env.example .env

# Edit .env with your Amazon SP API credentials
nano .env
```

### Step 3: Deploy with Docker Compose
```bash
# Build and start containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 4: Verify Deployment
```bash
# Test health endpoint
curl http://your-vps-ip/health

# Test MCP endpoint
curl -X POST http://your-vps-ip/sse \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list", "params": {}}'
```

## Manual VPS Setup

### Step 1: Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3.11 python3-pip python3.11-venv nginx git -y

# Install Docker (optional, for containerized deployment)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Step 2: Set Up Application
```bash
# Clone or copy your code
git clone https://github.com/wilketob/amztec-mcp-server.git
cd amztec-mcp-server

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your Amazon SP API credentials
```

### Step 3: Create Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/amazon-mcp.service
```

Add the following content:
```ini
[Unit]
Description=Amazon SP API MCP Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/amazon-mcp-server
Environment=PATH=/opt/amazon-mcp-server/venv/bin
ExecStart=/opt/amazon-mcp-server/venv/bin/python amazon_mcp_http_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable amazon-mcp
sudo systemctl start amazon-mcp
sudo systemctl status amazon-mcp
```

### Step 4: Configure Nginx Reverse Proxy
```bash
# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/amazon-mcp

# Enable the site
sudo ln -s /etc/nginx/sites-available/amazon-mcp /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## Django Integration

### Step 1: Install Client Dependencies
In your Django project:
```bash
pip install httpx asyncio
```

### Step 2: Copy Django Client
Copy `django_client.py` to your Django project or install it as a package.

### Step 3: Configure Django Settings
```python
# settings.py
AMAZON_MCP_BASE_URL = 'http://your-vps-domain.com'  # or IP address

# Add caching for better performance
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Step 4: Create Django Views
```python
# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from .django_client import DjangoAmazonMCPClient

# Initialize client
amazon_client = DjangoAmazonMCPClient()

@csrf_exempt
@require_http_methods(["GET"])
def get_product_info(request, sku):
    try:
        seller_id = request.GET.get('seller_id', 'default')
        product_info = amazon_client.get_product_info(sku, seller_id)
        return JsonResponse(product_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_product_pricing(request, sku):
    try:
        seller_id = request.GET.get('seller_id', 'default')
        pricing_info = amazon_client.get_product_pricing(sku, seller_id)
        return JsonResponse(pricing_info)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
```

### Step 5: Add URL Patterns
```python
# urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/amazon/product/<str:sku>/', views.get_product_info),
    path('api/amazon/pricing/<str:sku>/', views.get_product_pricing),
]
```

## Security Configuration

### Authentication
The server includes JWT and API key authentication. Configure in your `.env`:
```bash
MCP_SECRET_KEY=your-secret-key-here
MCP_API_KEYS=client1:secret1,client2:secret2
```

### SSL/TLS (Recommended for Production)
1. Obtain SSL certificate (Let's Encrypt recommended):
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

2. Update nginx configuration for HTTPS
3. Configure automatic certificate renewal

### Firewall
```bash
# Allow only necessary ports
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
```

## Monitoring and Maintenance

### Health Checks
Set up monitoring for the `/health` endpoint:
```bash
# Simple health check script
#!/bin/bash
if curl -f http://localhost/health > /dev/null 2>&1; then
    echo "MCP Server is healthy"
else
    echo "MCP Server is down"
    sudo systemctl restart amazon-mcp
fi
```

### Log Management
```bash
# View application logs
sudo journalctl -u amazon-mcp -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Updates
```bash
# Update code
cd /opt/amazon-mcp-server
git pull origin main

# Restart services
sudo systemctl restart amazon-mcp
sudo systemctl reload nginx
```

## Troubleshooting

### Common Issues

1. **Port already in use**: Check if another service is using port 8000
2. **Permission denied**: Ensure correct file permissions and user ownership
3. **Amazon API errors**: Verify credentials and API permissions
4. **Connection refused**: Check firewall settings and service status

### Debug Commands
```bash
# Check service status
sudo systemctl status amazon-mcp

# Test MCP server directly
curl -X POST http://localhost:8000/sse \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/list", "params": {}}'

# Check nginx configuration
sudo nginx -t

# Test SSL certificate
openssl s_client -connect your-domain.com:443
```

## Performance Optimization

### Caching
- Use Redis for Django caching
- Implement response caching in nginx
- Cache Amazon API responses appropriately

### Scaling
- Use multiple MCP server instances behind load balancer
- Implement connection pooling
- Monitor and adjust rate limits

### Resource Monitoring
```bash
# Monitor system resources
htop
df -h
free -h

# Monitor application performance
docker stats  # if using Docker
```