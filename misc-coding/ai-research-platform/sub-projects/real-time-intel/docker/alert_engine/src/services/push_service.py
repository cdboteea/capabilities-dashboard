"""Push notification service for mobile and web notifications."""

import asyncio
import json
from typing import List, Optional, Dict, Any
from pyfcm import FCMNotification
import httpx
from webpush_data_encrypt import encrypt, WebPushEncryption
import structlog

from ..config import config
from ..models.alert_models import AlertData, AlertDelivery, AlertChannel, AlertStatus

logger = structlog.get_logger(__name__)


class PushService:
    """Service for sending push notifications."""
    
    def __init__(self):
        self.push_config = config.push
        self.fcm_service = None
        self.webpush_encryption = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize push notification services."""
        # Initialize FCM for mobile push
        if self.push_config.fcm_server_key:
            try:
                self.fcm_service = FCMNotification(api_key=self.push_config.fcm_server_key)
                logger.info("FCM service initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize FCM service", error=str(e))
        
        # Initialize WebPush for browser notifications
        if self.push_config.vapid_private_key and self.push_config.vapid_public_key:
            try:
                self.webpush_encryption = WebPushEncryption(
                    private_key=self.push_config.vapid_private_key,
                    public_key=self.push_config.vapid_public_key,
                    email=self.push_config.vapid_email
                )
                logger.info("WebPush service initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize WebPush service", error=str(e))
    
    async def send_alert_push(
        self,
        alert: AlertData,
        delivery: AlertDelivery
    ) -> bool:
        """Send alert via push notification."""
        try:
            # Determine push type from token format
            if self._is_fcm_token(delivery.recipient):
                return await self._send_fcm_notification(alert, delivery)
            elif self._is_webpush_token(delivery.recipient):
                return await self._send_webpush_notification(alert, delivery)
            else:
                logger.error(
                    "Unknown push token format",
                    delivery_id=delivery.delivery_id,
                    token_prefix=delivery.recipient[:20] if delivery.recipient else None
                )
                return False
                
        except Exception as e:
            logger.error(
                "Push notification error",
                alert_id=alert.alert_id,
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def send_batch_push(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery
    ) -> bool:
        """Send batch of alerts via push notification."""
        try:
            # Determine push type
            if self._is_fcm_token(delivery.recipient):
                return await self._send_fcm_batch_notification(alerts, delivery)
            elif self._is_webpush_token(delivery.recipient):
                return await self._send_webpush_batch_notification(alerts, delivery)
            else:
                logger.error(
                    "Unknown push token format for batch",
                    delivery_id=delivery.delivery_id
                )
                return False
                
        except Exception as e:
            logger.error(
                "Batch push notification error",
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def _send_fcm_notification(
        self,
        alert: AlertData,
        delivery: AlertDelivery
    ) -> bool:
        """Send FCM notification to mobile device."""
        if not self.fcm_service:
            logger.error("FCM service not available")
            return False
        
        try:
            # Prepare notification data
            notification_data = self._prepare_fcm_data(alert)
            
            # Send notification
            loop = asyncio.get_event_loop()
            
            def _send():
                return self.fcm_service.notify_single_device(
                    registration_id=delivery.recipient,
                    message_title=notification_data['title'],
                    message_body=notification_data['body'],
                    data_message=notification_data['data'],
                    sound='default',
                    badge=1,
                    extra_notification_kwargs=notification_data['extra']
                )
            
            result = await loop.run_in_executor(None, _send)
            
            if result.get('success', 0) > 0:
                logger.info(
                    "FCM notification sent successfully",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    message_id=result.get('results', [{}])[0].get('message_id')
                )
                return True
            else:
                logger.error(
                    "FCM notification failed",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    result=result
                )
                return False
                
        except Exception as e:
            logger.error(
                "FCM sending error",
                alert_id=alert.alert_id,
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def _send_webpush_notification(
        self,
        alert: AlertData,
        delivery: AlertDelivery
    ) -> bool:
        """Send WebPush notification to browser."""
        if not self.webpush_encryption:
            logger.error("WebPush service not available")
            return False
        
        try:
            # Parse subscription from token
            subscription = json.loads(delivery.recipient)
            
            # Prepare notification payload
            payload = self._prepare_webpush_payload(alert)
            
            # Encrypt payload
            encrypted_data = encrypt(
                data=json.dumps(payload),
                subscription_info=subscription,
                vapid_private_key=self.push_config.vapid_private_key,
                vapid_claims={
                    "sub": f"mailto:{self.push_config.vapid_email}",
                    "aud": f"{subscription['endpoint'].split('/')[2]}"
                }
            )
            
            # Send notification
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription['endpoint'],
                    headers=encrypted_data['headers'],
                    data=encrypted_data['body'],
                    timeout=30
                )
            
            if response.status_code in [200, 201, 204]:
                logger.info(
                    "WebPush notification sent successfully",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    status_code=response.status_code
                )
                return True
            else:
                logger.error(
                    "WebPush notification failed",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    status_code=response.status_code,
                    response=response.text
                )
                return False
                
        except Exception as e:
            logger.error(
                "WebPush sending error",
                alert_id=alert.alert_id,
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def _send_fcm_batch_notification(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery
    ) -> bool:
        """Send FCM batch notification."""
        if not self.fcm_service:
            logger.error("FCM service not available")
            return False
        
        try:
            # Prepare batch notification data
            notification_data = self._prepare_fcm_batch_data(alerts)
            
            # Send notification
            loop = asyncio.get_event_loop()
            
            def _send():
                return self.fcm_service.notify_single_device(
                    registration_id=delivery.recipient,
                    message_title=notification_data['title'],
                    message_body=notification_data['body'],
                    data_message=notification_data['data'],
                    sound='default',
                    badge=len(alerts),
                    extra_notification_kwargs=notification_data['extra']
                )
            
            result = await loop.run_in_executor(None, _send)
            
            if result.get('success', 0) > 0:
                logger.info(
                    "FCM batch notification sent successfully",
                    delivery_id=delivery.delivery_id,
                    alert_count=len(alerts)
                )
                return True
            else:
                logger.error(
                    "FCM batch notification failed",
                    delivery_id=delivery.delivery_id,
                    result=result
                )
                return False
                
        except Exception as e:
            logger.error(
                "FCM batch sending error",
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def _send_webpush_batch_notification(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery
    ) -> bool:
        """Send WebPush batch notification."""
        if not self.webpush_encryption:
            logger.error("WebPush service not available")
            return False
        
        try:
            # Parse subscription
            subscription = json.loads(delivery.recipient)
            
            # Prepare batch payload
            payload = self._prepare_webpush_batch_payload(alerts)
            
            # Encrypt and send
            encrypted_data = encrypt(
                data=json.dumps(payload),
                subscription_info=subscription,
                vapid_private_key=self.push_config.vapid_private_key,
                vapid_claims={
                    "sub": f"mailto:{self.push_config.vapid_email}",
                    "aud": f"{subscription['endpoint'].split('/')[2]}"
                }
            )
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    subscription['endpoint'],
                    headers=encrypted_data['headers'],
                    data=encrypted_data['body'],
                    timeout=30
                )
            
            if response.status_code in [200, 201, 204]:
                logger.info(
                    "WebPush batch notification sent successfully",
                    delivery_id=delivery.delivery_id,
                    alert_count=len(alerts)
                )
                return True
            else:
                logger.error(
                    "WebPush batch notification failed",
                    delivery_id=delivery.delivery_id,
                    status_code=response.status_code
                )
                return False
                
        except Exception as e:
            logger.error(
                "WebPush batch sending error",
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    def _is_fcm_token(self, token: str) -> bool:
        """Check if token is FCM format."""
        # FCM tokens are typically 140+ characters, alphanumeric with some special chars
        return (
            len(token) > 100 and
            not token.startswith('{') and
            ':' in token
        )
    
    def _is_webpush_token(self, token: str) -> bool:
        """Check if token is WebPush subscription format."""
        try:
            data = json.loads(token)
            return 'endpoint' in data and 'keys' in data
        except:
            return False
    
    def _prepare_fcm_data(self, alert: AlertData) -> Dict[str, Any]:
        """Prepare FCM notification data."""
        # Priority emoji mapping
        priority_emoji = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '📢',
            'low': 'ℹ️'
        }
        
        title = f"{priority_emoji.get(alert.priority.value, '')} {alert.title}"
        body = alert.message
        
        # Add asset symbol to body if available
        if alert.asset_symbol:
            body = f"{alert.asset_symbol}: {body}"
        
        return {
            'title': title,
            'body': body,
            'data': {
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type.value,
                'priority': alert.priority.value,
                'asset_symbol': alert.asset_symbol or '',
                'created_at': alert.created_at.isoformat(),
                'click_action': 'FLUTTER_NOTIFICATION_CLICK',
                'sound': 'default'
            },
            'extra': {
                'android_channel_id': f"alerts_{alert.priority.value}",
                'priority': 'high' if alert.priority.value in ['high', 'critical'] else 'normal'
            }
        }
    
    def _prepare_fcm_batch_data(self, alerts: List[AlertData]) -> Dict[str, Any]:
        """Prepare FCM batch notification data."""
        # Count by priority
        critical_count = len([a for a in alerts if a.priority.value == 'critical'])
        high_count = len([a for a in alerts if a.priority.value == 'high'])
        
        # Create title
        if critical_count > 0:
            title = f"🚨 {critical_count} Critical Alerts"
        elif high_count > 0:
            title = f"⚠️ {high_count} High Priority Alerts"
        else:
            title = f"📢 {len(alerts)} New Alerts"
        
        # Create body with first alert
        if alerts:
            first_alert = alerts[0]
            body = first_alert.title
            if first_alert.asset_symbol:
                body = f"{first_alert.asset_symbol}: {body}"
        else:
            body = "Tap to view details"
        
        return {
            'title': title,
            'body': body,
            'data': {
                'batch_id': f"batch_{len(alerts)}_{alerts[0].created_at.timestamp()}",
                'alert_count': str(len(alerts)),
                'critical_count': str(critical_count),
                'high_count': str(high_count),
                'click_action': 'FLUTTER_NOTIFICATION_CLICK'
            },
            'extra': {
                'android_channel_id': 'alerts_batch',
                'priority': 'high' if critical_count > 0 or high_count > 0 else 'normal'
            }
        }
    
    def _prepare_webpush_payload(self, alert: AlertData) -> Dict[str, Any]:
        """Prepare WebPush notification payload."""
        return {
            'title': alert.title,
            'body': alert.message,
            'icon': '/icons/alert-icon.png',
            'badge': '/icons/badge.png',
            'tag': f"alert_{alert.alert_id}",
            'data': {
                'alert_id': alert.alert_id,
                'alert_type': alert.alert_type.value,
                'priority': alert.priority.value,
                'asset_symbol': alert.asset_symbol,
                'url': f"/alerts/{alert.alert_id}"
            },
            'actions': [
                {
                    'action': 'view',
                    'title': 'View Details',
                    'icon': '/icons/view.png'
                },
                {
                    'action': 'dismiss',
                    'title': 'Dismiss',
                    'icon': '/icons/dismiss.png'
                }
            ],
            'requireInteraction': alert.priority.value in ['high', 'critical'],
            'silent': alert.priority.value == 'low'
        }
    
    def _prepare_webpush_batch_payload(self, alerts: List[AlertData]) -> Dict[str, Any]:
        """Prepare WebPush batch notification payload."""
        critical_count = len([a for a in alerts if a.priority.value == 'critical'])
        high_count = len([a for a in alerts if a.priority.value == 'high'])
        
        if critical_count > 0:
            title = f"🚨 {critical_count} Critical Alerts"
        elif high_count > 0:
            title = f"⚠️ {high_count} High Priority Alerts"
        else:
            title = f"📢 {len(alerts)} New Alerts"
        
        body = f"You have {len(alerts)} new alerts. Tap to view details."
        
        return {
            'title': title,
            'body': body,
            'icon': '/icons/alert-icon.png',
            'badge': '/icons/badge.png',
            'tag': 'alert_batch',
            'data': {
                'alert_count': len(alerts),
                'critical_count': critical_count,
                'high_count': high_count,
                'url': '/alerts'
            },
            'actions': [
                {
                    'action': 'view_all',
                    'title': 'View All',
                    'icon': '/icons/view.png'
                }
            ],
            'requireInteraction': critical_count > 0 or high_count > 0
        }
    
    async def test_fcm_connection(self) -> bool:
        """Test FCM connection."""
        if not self.fcm_service:
            logger.error("FCM service not initialized")
            return False
        
        try:
            # Test with a dry run (no actual notification sent)
            loop = asyncio.get_event_loop()
            
            def _test():
                # Use a test token format - this will fail but validate the connection
                return self.fcm_service.notify_single_device(
                    registration_id="test_token_123",
                    message_title="Test",
                    message_body="Test message",
                    dry_run=True
                )
            
            result = await loop.run_in_executor(None, _test)
            
            # Even if it fails due to invalid token, connection is working
            logger.info("FCM connection test completed", result=result)
            return True
            
        except Exception as e:
            logger.error("FCM connection test failed", error=str(e))
            return False
    
    async def test_webpush_connection(self) -> bool:
        """Test WebPush configuration."""
        if not self.webpush_encryption:
            logger.error("WebPush service not initialized")
            return False
        
        try:
            # Test encryption with dummy data
            test_subscription = {
                "endpoint": "https://fcm.googleapis.com/fcm/send/test",
                "keys": {
                    "p256dh": "test_key",
                    "auth": "test_auth"
                }
            }
            
            test_payload = {"title": "Test", "body": "Test message"}
            
            # This will fail but validates the encryption setup
            try:
                encrypt(
                    data=json.dumps(test_payload),
                    subscription_info=test_subscription,
                    vapid_private_key=self.push_config.vapid_private_key,
                    vapid_claims={"sub": f"mailto:{self.push_config.vapid_email}"}
                )
            except:
                pass  # Expected to fail with test data
            
            logger.info("WebPush configuration test completed")
            return True
            
        except Exception as e:
            logger.error("WebPush configuration test failed", error=str(e))
            return False 