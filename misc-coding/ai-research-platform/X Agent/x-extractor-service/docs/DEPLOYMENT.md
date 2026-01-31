# Deployment Guide

This guide provides detailed instructions for deploying the X Post Content Extraction Service in various environments.

## Prerequisites

- Docker 20.10+ and Docker Compose 2.0+
- Python 3.11+ (for local development)
- 512MB+ RAM recommended
- Network access to X/Twitter domains

## Quick Deployment

### Docker (Recommended)

```bash
# Clone/extract the service files
cd x-extractor-service

# Build and run
docker build -t x-extractor-service .
docker run -d -p 3000:3000 --name x-extractor x-extractor-service

# Verify deployment
curl http://localhost:3000/api/health
```

### Docker Compose

```bash
# Start the service
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f x-extractor-service

# Stop the service
docker-compose down
```

## Environment-Specific Deployments

### Development Environment

#### Local Python Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DEBUG=true
export LOG_LEVEL=DEBUG

# Run the service
python -m uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload

# Service available at http://localhost:3000
```

#### Docker Development

```bash
# Build development image
docker build -t x-extractor-service:dev .

# Run with development settings
docker run -d \
  -p 3000:3000 \
  -e DEBUG=true \
  -e LOG_LEVEL=DEBUG \
  --name x-extractor-dev \
  x-extractor-service:dev

# Access interactive docs at http://localhost:3000/docs
```

### Production Environment

#### Single Server Deployment

```bash
# Create production environment file
cat > .env << EOF
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
REQUEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=10
EOF

# Deploy with docker-compose
docker-compose -f docker-compose.yml up -d

# Set up log rotation
sudo logrotate -d /etc/logrotate.d/x-extractor
```

#### Multi-Instance Deployment

```bash
# Create multiple instances
for i in {1..3}; do
  docker run -d \
    --name x-extractor-$i \
    -p $((3000 + i)):3000 \
    -e LOG_LEVEL=INFO \
    x-extractor-service
done

# Set up load balancer (nginx example)
sudo tee /etc/nginx/sites-available/x-extractor << EOF
upstream x_extractor {
    server localhost:3001;
    server localhost:3002;
    server localhost:3003;
}

server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://x_extractor;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/x-extractor /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Cloud Deployments

#### AWS ECS

1. **Create Task Definition** (`task-definition.json`):

```json
{
  "family": "x-extractor-service",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "x-extractor",
      "image": "your-account.dkr.ecr.region.amazonaws.com/x-extractor-service:latest",
      "portMappings": [
        {
          "containerPort": 3000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "LOG_LEVEL", "value": "INFO"},
        {"name": "LOG_FORMAT", "value": "json"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/x-extractor-service",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:3000/api/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

2. **Deploy**:

```bash
# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster your-cluster \
  --service-name x-extractor-service \
  --task-definition x-extractor-service:1 \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

#### Google Cloud Run

```bash
# Build and push image
docker build -t gcr.io/PROJECT-ID/x-extractor-service .
docker push gcr.io/PROJECT-ID/x-extractor-service

# Deploy to Cloud Run
gcloud run deploy x-extractor-service \
  --image gcr.io/PROJECT-ID/x-extractor-service \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 3000 \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars LOG_LEVEL=INFO,LOG_FORMAT=json
```

#### Azure Container Instances

```bash
# Create resource group
az group create --name x-extractor-rg --location eastus

# Deploy container
az container create \
  --resource-group x-extractor-rg \
  --name x-extractor-service \
  --image your-registry.azurecr.io/x-extractor-service:latest \
  --cpu 1 \
  --memory 1 \
  --ports 3000 \
  --environment-variables LOG_LEVEL=INFO LOG_FORMAT=json \
  --restart-policy Always
```

### Kubernetes Deployment

#### Basic Deployment

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: x-extractor-service
  labels:
    app: x-extractor-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: x-extractor-service
  template:
    metadata:
      labels:
        app: x-extractor-service
    spec:
      containers:
      - name: x-extractor-service
        image: x-extractor-service:latest
        ports:
        - containerPort: 3000
        env:
        - name: LOG_LEVEL
          value: "INFO"
        - name: LOG_FORMAT
          value: "json"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: x-extractor-service
spec:
  selector:
    app: x-extractor-service
  ports:
  - port: 80
    targetPort: 3000
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: x-extractor-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  rules:
  - host: x-extractor.your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: x-extractor-service
            port:
              number: 80
```

#### Deploy to Kubernetes

```bash
# Apply deployment
kubectl apply -f deployment.yaml

# Check status
kubectl get pods -l app=x-extractor-service
kubectl get services x-extractor-service

# Scale deployment
kubectl scale deployment x-extractor-service --replicas=5

# Update deployment
kubectl set image deployment/x-extractor-service x-extractor-service=x-extractor-service:v2
```

#### Helm Chart

```yaml
# Chart.yaml
apiVersion: v2
name: x-extractor-service
description: X Post Content Extraction Service
version: 1.0.0
appVersion: 1.0.0

# values.yaml
replicaCount: 3

image:
  repository: x-extractor-service
  tag: latest
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 80
  targetPort: 3000

ingress:
  enabled: true
  annotations:
    kubernetes.io/ingress.class: nginx
  hosts:
    - host: x-extractor.your-domain.com
      paths:
        - path: /
          pathType: Prefix

resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"

env:
  LOG_LEVEL: INFO
  LOG_FORMAT: json
```

```bash
# Install with Helm
helm install x-extractor-service ./x-extractor-chart

# Upgrade
helm upgrade x-extractor-service ./x-extractor-chart
```

## Configuration Management

### Environment Variables

Create environment-specific configuration files:

#### Development (`.env.dev`)
```bash
DEBUG=true
LOG_LEVEL=DEBUG
LOG_FORMAT=console
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW=3600
```

#### Staging (`.env.staging`)
```bash
DEBUG=false
LOG_LEVEL=INFO
LOG_FORMAT=json
RATE_LIMIT_REQUESTS=500
RATE_LIMIT_WINDOW=3600
```

#### Production (`.env.prod`)
```bash
DEBUG=false
LOG_LEVEL=WARNING
LOG_FORMAT=json
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=3600
REQUEST_TIMEOUT=30
MAX_CONCURRENT_REQUESTS=10
```

### Secrets Management

#### Docker Secrets

```bash
# Create secrets
echo "redis://redis:6379/0" | docker secret create redis_url -

# Use in docker-compose
version: '3.8'
services:
  x-extractor-service:
    image: x-extractor-service
    secrets:
      - redis_url
    environment:
      - REDIS_URL_FILE=/run/secrets/redis_url

secrets:
  redis_url:
    external: true
```

#### Kubernetes Secrets

```bash
# Create secret
kubectl create secret generic x-extractor-secrets \
  --from-literal=redis-url=redis://redis:6379/0

# Use in deployment
env:
- name: REDIS_URL
  valueFrom:
    secretKeyRef:
      name: x-extractor-secrets
      key: redis-url
```

## Monitoring and Logging

### Health Monitoring

#### Basic Health Check Script

```bash
#!/bin/bash
# health-check.sh

ENDPOINT="http://localhost:3000/api/health"
TIMEOUT=10

response=$(curl -s -w "%{http_code}" --max-time $TIMEOUT "$ENDPOINT")
http_code="${response: -3}"

if [ "$http_code" = "200" ]; then
    echo "Service is healthy"
    exit 0
else
    echo "Service is unhealthy (HTTP $http_code)"
    exit 1
fi
```

#### Prometheus Monitoring

Add to `docker-compose.yml`:

```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### Log Management

#### Centralized Logging with ELK Stack

```yaml
# docker-compose.logging.yml
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:7.15.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:7.15.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf

  kibana:
    image: docker.elastic.co/kibana/kibana:7.15.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200

  x-extractor-service:
    image: x-extractor-service
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### Log Rotation

```bash
# /etc/logrotate.d/x-extractor
/var/log/x-extractor/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker kill -s USR1 x-extractor-service
    endscript
}
```

## Security Considerations

### Network Security

```bash
# Create custom network
docker network create x-extractor-network

# Run with custom network
docker run -d \
  --network x-extractor-network \
  --name x-extractor \
  -p 3000:3000 \
  x-extractor-service
```

### SSL/TLS Termination

#### Nginx SSL Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name x-extractor.your-domain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Container Security

```dockerfile
# Use non-root user
USER appuser

# Read-only filesystem
docker run --read-only --tmpfs /tmp x-extractor-service

# Security options
docker run --security-opt=no-new-privileges x-extractor-service
```

## Backup and Recovery

### Data Backup

```bash
# Backup configuration
tar -czf x-extractor-config-$(date +%Y%m%d).tar.gz \
  .env docker-compose.yml

# Backup logs
tar -czf x-extractor-logs-$(date +%Y%m%d).tar.gz logs/
```

### Disaster Recovery

```bash
# Recovery script
#!/bin/bash
set -e

echo "Starting disaster recovery..."

# Stop current service
docker-compose down

# Restore configuration
tar -xzf x-extractor-config-backup.tar.gz

# Restart service
docker-compose up -d

# Verify health
sleep 30
curl -f http://localhost:3000/api/health

echo "Recovery completed successfully"
```

## Performance Optimization

### Resource Limits

```yaml
# docker-compose.yml
services:
  x-extractor-service:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
```

### Caching

#### Redis Caching

```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  x-extractor-service:
    environment:
      - REDIS_URL=redis://redis:6379/0
```

### Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Load test
ab -n 1000 -c 10 -H "Content-Type: application/json" \
  -p test-payload.json \
  http://localhost:3000/api/extract
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker logs x-extractor-service

# Check port conflicts
netstat -tulpn | grep :3000

# Check resource usage
docker stats x-extractor-service
```

#### High Memory Usage

```bash
# Monitor memory
docker exec x-extractor-service ps aux

# Restart service
docker restart x-extractor-service
```

#### Rate Limiting Issues

```bash
# Check rate limit status
curl -v http://localhost:3000/api/extract \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://x.com/test/status/123"]}' \
  2>&1 | grep X-RateLimit
```

### Debug Mode

```bash
# Enable debug mode
docker run -e DEBUG=true -e LOG_LEVEL=DEBUG x-extractor-service

# Access debug endpoints
curl http://localhost:3000/docs
```

## Maintenance

### Updates

```bash
# Pull latest image
docker pull x-extractor-service:latest

# Rolling update
docker-compose up -d --no-deps x-extractor-service

# Verify update
curl http://localhost:3000/api/health
```

### Cleanup

```bash
# Remove old containers
docker container prune

# Remove old images
docker image prune

# Remove unused volumes
docker volume prune
```

This deployment guide covers various scenarios and environments. Choose the appropriate deployment method based on your infrastructure and requirements.

