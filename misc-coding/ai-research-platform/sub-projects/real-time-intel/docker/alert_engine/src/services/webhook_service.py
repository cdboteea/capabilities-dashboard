"""Webhook notification service for HTTP callbacks."""

import asyncio
import hashlib
import hmac
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
import httpx
from urllib.parse import urlparse
import structlog

from ..config import config
from ..models.alert_models import AlertData, AlertDelivery, AlertChannel, AlertStatus

logger = structlog.get_logger(__name__)


class WebhookService:
    """Service for sending webhook notifications."""
    
    def __init__(self):
        self.webhook_config = config.webhook
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.webhook_config.timeout),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
    
    async def send_alert_webhook(
        self,
        alert: AlertData,
        delivery: AlertDelivery,
        webhook_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send alert via webhook."""
        try:
            # Parse webhook URL and configuration
            webhook_url, headers, secret = self._parse_webhook_config(
                delivery.recipient, webhook_config
            )
            
            if not webhook_url:
                logger.error(
                    "Invalid webhook URL",
                    delivery_id=delivery.delivery_id,
                    url=delivery.recipient
                )
                return False
            
            # Prepare webhook payload
            payload = self._prepare_webhook_payload(alert, delivery)
            
            # Add signature if secret provided
            if secret:
                signature = self._generate_signature(payload, secret)
                headers['X-Signature'] = signature
                headers['X-Signature-256'] = f"sha256={signature}"
            
            # Send webhook with retries
            success = await self._send_webhook_with_retries(
                url=webhook_url,
                payload=payload,
                headers=headers,
                delivery_id=delivery.delivery_id
            )
            
            if success:
                logger.info(
                    "Webhook sent successfully",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    url=webhook_url
                )
                return True
            else:
                logger.error(
                    "Failed to send webhook",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    url=webhook_url
                )
                return False
                
        except Exception as e:
            logger.error(
                "Webhook sending error",
                alert_id=alert.alert_id,
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def send_batch_webhook(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery,
        webhook_config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send batch of alerts via webhook."""
        try:
            # Parse webhook configuration
            webhook_url, headers, secret = self._parse_webhook_config(
                delivery.recipient, webhook_config
            )
            
            if not webhook_url:
                logger.error(
                    "Invalid webhook URL for batch",
                    delivery_id=delivery.delivery_id
                )
                return False
            
            # Prepare batch webhook payload
            payload = self._prepare_batch_webhook_payload(alerts, delivery)
            
            # Add signature if secret provided
            if secret:
                signature = self._generate_signature(payload, secret)
                headers['X-Signature'] = signature
                headers['X-Signature-256'] = f"sha256={signature}"
            
            # Send webhook
            success = await self._send_webhook_with_retries(
                url=webhook_url,
                payload=payload,
                headers=headers,
                delivery_id=delivery.delivery_id
            )
            
            if success:
                logger.info(
                    "Batch webhook sent successfully",
                    delivery_id=delivery.delivery_id,
                    alert_count=len(alerts),
                    url=webhook_url
                )
                return True
            else:
                logger.error(
                    "Failed to send batch webhook",
                    delivery_id=delivery.delivery_id,
                    alert_count=len(alerts),
                    url=webhook_url
                )
                return False
                
        except Exception as e:
            logger.error(
                "Batch webhook sending error",
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    def _parse_webhook_config(
        self,
        recipient: str,
        webhook_config: Optional[Dict[str, Any]] = None
    ) -> tuple[Optional[str], Dict[str, str], Optional[str]]:
        """Parse webhook configuration from recipient and config."""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'AI-Research-Platform-AlertEngine/1.0',
            'X-Alert-Source': 'ai-research-platform'
        }
        
        webhook_url = None
        secret = None
        
        # If recipient is a JSON config
        if recipient.startswith('{'):
            try:
                config_data = json.loads(recipient)
                webhook_url = config_data.get('url')
                secret = config_data.get('secret')
                
                # Add custom headers
                if 'headers' in config_data:
                    headers.update(config_data['headers'])
                    
            except json.JSONDecodeError:
                logger.warning("Invalid JSON webhook config", recipient=recipient[:100])
                return None, headers, None
        else:
            # Simple URL
            webhook_url = recipient
        
        # Additional config from webhook_config parameter
        if webhook_config:
            secret = webhook_config.get('secret', secret)
            if 'headers' in webhook_config:
                headers.update(webhook_config['headers'])
        
        # Validate URL
        if webhook_url and self._validate_webhook_url(webhook_url):
            return webhook_url, headers, secret
        else:
            return None, headers, None
    
    def _validate_webhook_url(self, url: str) -> bool:
        """Validate webhook URL."""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Must be HTTP or HTTPS
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Should be HTTPS in production
            if parsed.scheme == 'http' and not config.debug:
                logger.warning("HTTP webhook URL in production", url=url)
            
            return True
            
        except Exception:
            return False
    
    def _prepare_webhook_payload(
        self,
        alert: AlertData,
        delivery: AlertDelivery
    ) -> Dict[str, Any]:
        """Prepare webhook payload for single alert."""
        return {
            'event': 'alert.created',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'delivery_id': delivery.delivery_id,
            'alert': {
                'id': alert.alert_id,
                'type': alert.alert_type.value,
                'priority': alert.priority.value,
                'title': alert.title,
                'message': alert.message,
                'summary': alert.summary,
                'asset_symbol': alert.asset_symbol,
                'portfolio_id': alert.portfolio_id,
                'source_service': alert.source_service,
                'source_event_id': alert.source_event_id,
                'data': alert.data,
                'created_at': alert.created_at.isoformat() + 'Z',
                'expires_at': alert.expires_at.isoformat() + 'Z' if alert.expires_at else None
            },
            'metadata': {
                'platform': 'ai-research-platform',
                'version': '1.0',
                'environment': 'production' if not config.debug else 'development'
            }
        }
    
    def _prepare_batch_webhook_payload(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery
    ) -> Dict[str, Any]:
        """Prepare webhook payload for batch of alerts."""
        # Group alerts by priority and type
        alert_summary = self._summarize_alerts(alerts)
        
        return {
            'event': 'alerts.batch',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'delivery_id': delivery.delivery_id,
            'batch': {
                'count': len(alerts),
                'summary': alert_summary,
                'alerts': [
                    {
                        'id': alert.alert_id,
                        'type': alert.alert_type.value,
                        'priority': alert.priority.value,
                        'title': alert.title,
                        'message': alert.message,
                        'asset_symbol': alert.asset_symbol,
                        'created_at': alert.created_at.isoformat() + 'Z'
                    }
                    for alert in alerts
                ]
            },
            'metadata': {
                'platform': 'ai-research-platform',
                'version': '1.0',
                'environment': 'production' if not config.debug else 'development'
            }
        }
    
    def _summarize_alerts(self, alerts: List[AlertData]) -> Dict[str, Any]:
        """Create summary of alerts for batch payload."""
        summary = {
            'by_priority': {},
            'by_type': {},
            'assets': set(),
            'time_range': {
                'earliest': None,
                'latest': None
            }
        }
        
        for alert in alerts:
            # Count by priority
            priority = alert.priority.value
            summary['by_priority'][priority] = summary['by_priority'].get(priority, 0) + 1
            
            # Count by type
            alert_type = alert.alert_type.value
            summary['by_type'][alert_type] = summary['by_type'].get(alert_type, 0) + 1
            
            # Collect assets
            if alert.asset_symbol:
                summary['assets'].add(alert.asset_symbol)
            
            # Track time range
            if not summary['time_range']['earliest'] or alert.created_at < summary['time_range']['earliest']:
                summary['time_range']['earliest'] = alert.created_at
            if not summary['time_range']['latest'] or alert.created_at > summary['time_range']['latest']:
                summary['time_range']['latest'] = alert.created_at
        
        # Convert sets to lists for JSON serialization
        summary['assets'] = list(summary['assets'])
        
        # Convert datetime to ISO strings
        if summary['time_range']['earliest']:
            summary['time_range']['earliest'] = summary['time_range']['earliest'].isoformat() + 'Z'
        if summary['time_range']['latest']:
            summary['time_range']['latest'] = summary['time_range']['latest'].isoformat() + 'Z'
        
        return summary
    
    def _generate_signature(self, payload: Dict[str, Any], secret: str) -> str:
        """Generate HMAC signature for webhook payload."""
        payload_json = json.dumps(payload, sort_keys=True, separators=(',', ':'))
        signature = hmac.new(
            secret.encode('utf-8'),
            payload_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    async def _send_webhook_with_retries(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
        delivery_id: str
    ) -> bool:
        """Send webhook with retry logic."""
        last_error = None
        
        for attempt in range(self.webhook_config.retry_attempts):
            try:
                # Add attempt number to headers
                headers['X-Attempt'] = str(attempt + 1)
                
                # Send request
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                # Check response
                if 200 <= response.status_code < 300:
                    logger.debug(
                        "Webhook sent successfully",
                        delivery_id=delivery_id,
                        url=url,
                        status_code=response.status_code,
                        attempt=attempt + 1
                    )
                    return True
                elif response.status_code == 410:
                    # Gone - don't retry
                    logger.warning(
                        "Webhook endpoint gone (410)",
                        delivery_id=delivery_id,
                        url=url
                    )
                    return False
                elif response.status_code >= 500:
                    # Server error - retry
                    last_error = f"Server error: {response.status_code}"
                    logger.warning(
                        "Webhook server error, will retry",
                        delivery_id=delivery_id,
                        url=url,
                        status_code=response.status_code,
                        attempt=attempt + 1
                    )
                else:
                    # Client error - don't retry
                    logger.error(
                        "Webhook client error",
                        delivery_id=delivery_id,
                        url=url,
                        status_code=response.status_code,
                        response=response.text[:500]
                    )
                    return False
                    
            except httpx.TimeoutException:
                last_error = "Request timeout"
                logger.warning(
                    "Webhook timeout, will retry",
                    delivery_id=delivery_id,
                    url=url,
                    attempt=attempt + 1
                )
            except httpx.ConnectError:
                last_error = "Connection error"
                logger.warning(
                    "Webhook connection error, will retry",
                    delivery_id=delivery_id,
                    url=url,
                    attempt=attempt + 1
                )
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "Webhook error, will retry",
                    delivery_id=delivery_id,
                    url=url,
                    error=str(e),
                    attempt=attempt + 1
                )
            
            # Wait before retry (except last attempt)
            if attempt < self.webhook_config.retry_attempts - 1:
                await asyncio.sleep(self.webhook_config.retry_delay * (attempt + 1))
        
        logger.error(
            "Webhook failed after all retries",
            delivery_id=delivery_id,
            url=url,
            attempts=self.webhook_config.retry_attempts,
            last_error=last_error
        )
        return False
    
    async def test_webhook_url(self, url: str, secret: Optional[str] = None) -> bool:
        """Test webhook URL with a test payload."""
        try:
            # Validate URL first
            if not self._validate_webhook_url(url):
                logger.error("Invalid webhook URL for testing", url=url)
                return False
            
            # Prepare test payload
            test_payload = {
                'event': 'webhook.test',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'test': True,
                'message': 'This is a test webhook from AI Research Platform',
                'metadata': {
                    'platform': 'ai-research-platform',
                    'version': '1.0'
                }
            }
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'AI-Research-Platform-AlertEngine/1.0',
                'X-Alert-Source': 'ai-research-platform',
                'X-Test': 'true'
            }
            
            # Add signature if secret provided
            if secret:
                signature = self._generate_signature(test_payload, secret)
                headers['X-Signature'] = signature
                headers['X-Signature-256'] = f"sha256={signature}"
            
            # Send test webhook
            response = await self.client.post(
                url,
                json=test_payload,
                headers=headers
            )
            
            if 200 <= response.status_code < 300:
                logger.info(
                    "Webhook test successful",
                    url=url,
                    status_code=response.status_code
                )
                return True
            else:
                logger.error(
                    "Webhook test failed",
                    url=url,
                    status_code=response.status_code,
                    response=response.text[:500]
                )
                return False
                
        except Exception as e:
            logger.error("Webhook test error", url=url, error=str(e))
            return False
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
    
    def __del__(self):
        """Cleanup on deletion."""
        try:
            asyncio.create_task(self.close())
        except:
            pass 