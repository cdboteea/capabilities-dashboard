# Alert Engine Service

Multi-channel alert and notification system for the Real-Time Intel platform, providing intelligent alert routing, delivery management, and user preference handling.

## Overview

The Alert Engine service is the final component in the Real-Time Intel data pipeline, responsible for delivering actionable intelligence to users through multiple notification channels.

## Features

### Core Alert Processing
- **Multi-Channel Delivery**: Email, SMS, push notifications, webhooks, Slack, Discord, Telegram
- **Intelligent Routing**: Rule-based alert routing with complex condition evaluation
- **Priority Management**: 5-tier priority system (Low, Medium, High, Critical, Urgent)
- **Batch Processing**: Configurable alert batching to prevent notification fatigue
- **Delivery Tracking**: Comprehensive delivery status tracking and retry mechanisms

### Alert Rule Engine
- **Flexible Conditions**: Support for complex alert conditions with AND/OR logic
- **Portfolio Targeting**: Portfolio-specific and symbol-specific alert rules
- **Cooldown Management**: Configurable cooldown periods to prevent spam
- **Time-Based Rules**: Active hours and quiet time support
- **Dynamic Updates**: Real-time rule updates without service restart

### User Experience
- **Preference Management**: Granular user notification preferences
- **Quiet Hours**: Customizable quiet time periods
- **Channel Selection**: Per-user channel enable/disable
- **Priority Thresholds**: User-defined minimum priority levels
- **Template Customization**: Personalized notification templates

### Delivery Management
- **Retry Logic**: Automatic retry with exponential backoff
- **Failure Handling**: Comprehensive error handling and logging
- **Status Tracking**: Real-time delivery status updates
- **Performance Metrics**: Delivery success rates and timing analytics

## Architecture

### Service Components
```
Alert Engine (8307)
├── Alert Manager - Core orchestration
├── Notification Services
│   ├── Email Service - SMTP/API email delivery
│   ├── SMS Service - Twilio/Vonage integration
│   ├── Push Service - FCM/APNS push notifications
│   └── Webhook Service - HTTP webhook delivery
├── Rule Engine - Condition evaluation
├── Template Engine - Content rendering
└── Delivery Queue - Async processing
```

### Data Flow
```
External Event → Alert Manager → Rule Evaluation → Notification Generation
                     ↓              ↓                    ↓
                 User Prefs → Channel Selection → Template Rendering
                     ↓              ↓                    ↓
                 Delivery Queue → Service Routing → Status Tracking
```

## API Endpoints

### Core Alert Operations
- `POST /alerts/send` - Send immediate alert
- `POST /alerts/batch` - Send multiple alerts
- `GET /alerts` - List alerts with filtering
- `GET /alerts/{alert_id}` - Get specific alert
- `POST /alerts/{alert_id}/acknowledge` - Acknowledge alert

### Rule Management
- `POST /rules` - Create alert rule
- `GET /rules` - List all rules
- `GET /rules/{rule_id}` - Get specific rule
- `PUT /rules/{rule_id}` - Update rule
- `DELETE /rules/{rule_id}` - Delete rule

### User Preferences
- `POST /preferences` - Update user preferences
- `GET /preferences/{user_id}` - Get user preferences

### Statistics & Analytics
- `GET /stats` - Alert statistics
- `GET /stats/deliveries` - Delivery statistics

### Testing & Administration
- `POST /test/alert` - Send test alert
- `GET /test/channels` - Test channel connectivity
- `POST /admin/reload-rules` - Reload rules
- `DELETE /admin/cache` - Clear cache

## Configuration

### Environment Variables
```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ai_research_platform
DB_USER=postgres
DB_PASSWORD=your_password

# Redis Cache
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password

# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Push Notifications
FCM_SERVER_KEY=your_fcm_server_key
APNS_KEY_ID=your_apns_key_id
APNS_TEAM_ID=your_apns_team_id
```

### Configuration File
See `config/config.yml` for detailed configuration options including:
- Alert processing settings
- Notification service configurations
- Template settings
- Retry and timeout configurations

## Alert Types

### Supported Alert Types
- **PRICE_CHANGE**: Asset price movements
- **NEWS_EVENT**: Breaking news alerts
- **SENTIMENT_SHIFT**: Sentiment analysis changes
- **PORTFOLIO_RISK**: Risk threshold breaches
- **MARKET_VOLATILITY**: Market volatility alerts
- **EARNINGS_RELEASE**: Earnings announcements
- **ANALYST_UPGRADE/DOWNGRADE**: Analyst rating changes
- **VOLUME_SPIKE**: Unusual trading volume
- **TECHNICAL_SIGNAL**: Technical analysis signals
- **MACRO_EVENT**: Macroeconomic events
- **CUSTOM**: User-defined alerts

### Priority Levels
- **LOW**: Informational alerts
- **MEDIUM**: Standard notifications
- **HIGH**: Important alerts requiring attention
- **CRITICAL**: Urgent alerts requiring immediate action
- **URGENT**: Emergency alerts with immediate delivery

## Notification Channels

### Email Notifications
- **SMTP Support**: Standard SMTP server integration
- **HTML Templates**: Rich HTML email templates
- **Attachment Support**: File attachments for reports
- **Bounce Handling**: Automatic bounce detection and handling

### SMS Notifications
- **Twilio Integration**: Primary SMS provider
- **Vonage Support**: Secondary SMS provider
- **International Support**: Global SMS delivery
- **Character Optimization**: Automatic message truncation

### Push Notifications
- **FCM (Android)**: Firebase Cloud Messaging
- **APNS (iOS)**: Apple Push Notification Service
- **Web Push**: Browser push notifications
- **Rich Notifications**: Images and action buttons

### Webhook Notifications
- **HTTP/HTTPS**: Secure webhook delivery
- **Custom Headers**: Configurable request headers
- **Retry Logic**: Automatic retry on failure
- **Signature Verification**: Webhook signature validation

## Alert Rules

### Condition Types
```yaml
# Price-based conditions
- field: "current_price"
  operator: ">"
  value: 100.0
  timeframe: "5m"

# Percentage change conditions
- field: "price_change_percent"
  operator: ">="
  value: 5.0
  timeframe: "1d"

# Volume conditions
- field: "volume"
  operator: ">"
  value: 1000000
  timeframe: "1h"

# Sentiment conditions
- field: "sentiment_score"
  operator: "<"
  value: -0.5
  timeframe: "15m"
```

### Rule Logic
- **AND Logic**: All conditions must be met
- **OR Logic**: Any condition triggers alert
- **Complex Logic**: Nested condition groups
- **Time Windows**: Condition evaluation timeframes

## Templates

### Template Variables
Available variables for notification templates:
- `{{title}}` - Alert title
- `{{message}}` - Alert message
- `{{symbol}}` - Asset symbol
- `{{portfolio_id}}` - Portfolio identifier
- `{{priority}}` - Alert priority
- `{{timestamp}}` - Alert timestamp
- `{{data.*}}` - Custom data fields

### Template Examples
```jinja2
# Email Subject Template
Alert: {{title}} - {{symbol}} ({{priority|upper}})

# Email Body Template
Dear {{user_name}},

{{message}}

Symbol: {{symbol}}
Portfolio: {{portfolio_id}}
Time: {{timestamp}}
Priority: {{priority|upper}}

{% if data.price_change %}
Price Change: {{data.price_change}}%
{% endif %}

Best regards,
Real-Time Intel Platform
```

## Database Schema

### Core Tables
- `alerts`: Alert event records
- `alert_rules`: Alert rule configurations
- `alert_deliveries`: Delivery tracking records
- `user_preferences`: User notification preferences
- `notification_templates`: Template definitions

### Indexes
- Alert timestamp indexes for time-based queries
- Rule condition indexes for fast evaluation
- Delivery status indexes for monitoring

## Deployment

### Docker
```bash
# Build image
docker build -t alert-engine:latest .

# Run container
docker run -d \
  --name alert-engine \
  -p 8307:8307 \
  -e DB_HOST=postgres \
  -e REDIS_HOST=redis \
  -e SMTP_HOST=smtp.gmail.com \
  alert-engine:latest
```

### Docker Compose
```yaml
services:
  alert-engine:
    build: .
    ports:
      - "8307:8307"
    environment:
      - DB_HOST=postgres
      - REDIS_HOST=redis
      - SMTP_HOST=smtp.gmail.com
    depends_on:
      - postgres
      - redis
```

## Monitoring

### Health Checks
- Database connectivity
- Redis cache availability
- Notification service status
- Queue processing status

### Metrics (Prometheus)
- Alert processing rates
- Delivery success rates
- Channel-specific metrics
- Error rates and types
- Processing latency

### Logging
- Structured JSON logging
- Alert processing traces
- Delivery status updates
- Error tracking with context

## Integration

### Real-Time Intel Pipeline
The Alert Engine integrates with other Real-Time Intel services:

1. **Event Processor** → Sends processed events for alerting
2. **Sentiment Analyzer** → Triggers sentiment-based alerts
3. **Holdings Router** → Provides portfolio context
4. **Price Fetcher** → Triggers price-based alerts
5. **Portfolio Analytics** → Sends risk-based alerts

### External Integrations
- **Email Providers**: SMTP servers, SendGrid, Mailgun
- **SMS Providers**: Twilio, Vonage, AWS SNS
- **Push Services**: FCM, APNS, OneSignal
- **Chat Platforms**: Slack, Discord, Telegram
- **Webhook Endpoints**: Custom HTTP endpoints

## Development

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/config.example.yml config/config.yml
# Edit config.yml with your settings

# Run tests
pytest tests/

# Start development server
uvicorn src.main:app --reload --port 8307
```

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Test specific functionality
pytest tests/test_alert_manager.py -v
```

## Performance

### Optimization Features
- **Async Processing**: Full async/await implementation
- **Queue Management**: Separate queues for different priority levels
- **Batch Processing**: Configurable batch sizes and frequencies
- **Connection Pooling**: Database and HTTP connection pooling
- **Caching**: Redis caching for rules and preferences

### Scaling Considerations
- **Horizontal Scaling**: Stateless service design
- **Queue Partitioning**: Separate queues by priority/channel
- **Rate Limiting**: Per-channel rate limiting
- **Circuit Breakers**: Automatic failure handling

## Security

### Authentication & Authorization
- Service-to-service authentication
- API key validation for webhooks
- User permission validation

### Data Protection
- Sensitive data encryption
- PII handling compliance
- Audit logging for all operations

### Network Security
- TLS encryption for all communications
- Webhook signature verification
- Rate limiting and DDoS protection

## Troubleshooting

### Common Issues
1. **Email Delivery Failures**: Check SMTP configuration and credentials
2. **SMS Delivery Failures**: Verify Twilio/Vonage credentials and phone numbers
3. **Push Notification Failures**: Validate FCM/APNS certificates
4. **High Latency**: Check database and Redis connectivity

### Debug Tools
- Health check endpoints for all services
- Test alert functionality
- Channel connectivity testing
- Comprehensive logging and metrics

---

**Service**: Alert Engine  
**Port**: 8307  
**Version**: 1.0.0  
**Status**: Production Ready ✅