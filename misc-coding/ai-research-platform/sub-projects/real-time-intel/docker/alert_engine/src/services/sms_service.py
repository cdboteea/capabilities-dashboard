"""SMS notification service using Twilio."""

import asyncio
from typing import List, Optional
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
import phonenumbers
from phonenumbers import NumberParseException
import structlog

from ..config import config
from ..models.alert_models import AlertData, AlertDelivery, AlertChannel, AlertStatus

logger = structlog.get_logger(__name__)


class SMSService:
    """Service for sending SMS notifications via Twilio."""
    
    def __init__(self):
        self.sms_config = config.sms
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Twilio client."""
        if self.sms_config.twilio_account_sid and self.sms_config.twilio_auth_token:
            try:
                self.client = Client(
                    self.sms_config.twilio_account_sid,
                    self.sms_config.twilio_auth_token
                )
                logger.info("Twilio client initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize Twilio client", error=str(e))
                self.client = None
        else:
            logger.warning("Twilio credentials not configured")
    
    async def send_alert_sms(
        self,
        alert: AlertData,
        delivery: AlertDelivery
    ) -> bool:
        """Send alert via SMS."""
        if not self.client:
            logger.error("Twilio client not available")
            return False
        
        try:
            # Validate phone number
            phone_number = self._validate_phone_number(delivery.recipient)
            if not phone_number:
                logger.error(
                    "Invalid phone number",
                    delivery_id=delivery.delivery_id,
                    phone=delivery.recipient
                )
                return False
            
            # Prepare SMS content
            message_content = self._prepare_sms_content(alert)
            
            # Send SMS
            success = await self._send_sms(
                to_number=phone_number,
                message=message_content
            )
            
            if success:
                logger.info(
                    "SMS sent successfully",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    phone=phone_number
                )
                return True
            else:
                logger.error(
                    "Failed to send SMS",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    phone=phone_number
                )
                return False
                
        except Exception as e:
            logger.error(
                "SMS sending error",
                alert_id=alert.alert_id,
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def send_batch_sms(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery
    ) -> bool:
        """Send batch of alerts via SMS."""
        if not self.client:
            logger.error("Twilio client not available")
            return False
        
        try:
            # Validate phone number
            phone_number = self._validate_phone_number(delivery.recipient)
            if not phone_number:
                logger.error(
                    "Invalid phone number for batch SMS",
                    delivery_id=delivery.delivery_id,
                    phone=delivery.recipient
                )
                return False
            
            # Prepare batch SMS content
            message_content = self._prepare_batch_sms_content(alerts)
            
            # Send SMS
            success = await self._send_sms(
                to_number=phone_number,
                message=message_content
            )
            
            if success:
                logger.info(
                    "Batch SMS sent successfully",
                    delivery_id=delivery.delivery_id,
                    phone=phone_number,
                    alert_count=len(alerts)
                )
                return True
            else:
                logger.error(
                    "Failed to send batch SMS",
                    delivery_id=delivery.delivery_id,
                    phone=phone_number,
                    alert_count=len(alerts)
                )
                return False
                
        except Exception as e:
            logger.error(
                "Batch SMS sending error",
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    def _validate_phone_number(self, phone: str) -> Optional[str]:
        """Validate and format phone number."""
        try:
            # Parse phone number
            parsed = phonenumbers.parse(phone, None)
            
            # Validate
            if phonenumbers.is_valid_number(parsed):
                # Format in E164 format
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
            else:
                logger.warning("Invalid phone number", phone=phone)
                return None
                
        except NumberParseException as e:
            logger.warning("Phone number parsing error", phone=phone, error=str(e))
            return None
    
    def _prepare_sms_content(self, alert: AlertData) -> str:
        """Prepare SMS content from alert."""
        # SMS character limit considerations
        max_length = 160
        
        # Priority indicator
        priority_prefix = {
            'critical': '🚨',
            'high': '⚠️',
            'medium': '📢',
            'low': 'ℹ️'
        }.get(alert.priority.value, '')
        
        # Asset symbol if available
        asset_part = f" {alert.asset_symbol}" if alert.asset_symbol else ""
        
        # Base message
        base_message = f"{priority_prefix} {alert.title}{asset_part}: {alert.message}"
        
        # Truncate if too long
        if len(base_message) > max_length:
            # Try with shorter message
            short_message = f"{priority_prefix} {alert.title}{asset_part}"
            if len(short_message) < max_length - 3:
                remaining = max_length - len(short_message) - 3
                truncated_message = alert.message[:remaining]
                base_message = f"{short_message}: {truncated_message}..."
            else:
                # Just use title if still too long
                base_message = alert.title[:max_length]
        
        return base_message
    
    def _prepare_batch_sms_content(self, alerts: List[AlertData]) -> str:
        """Prepare batch SMS content."""
        max_length = 160
        
        # Count by priority
        critical_count = len([a for a in alerts if a.priority.value == 'critical'])
        high_count = len([a for a in alerts if a.priority.value == 'high'])
        
        # Create summary message
        if critical_count > 0:
            summary = f"🚨 {critical_count} critical"
            if high_count > 0:
                summary += f", ⚠️ {high_count} high"
            summary += f" alerts"
        elif high_count > 0:
            summary = f"⚠️ {high_count} high priority alerts"
        else:
            summary = f"📢 {len(alerts)} new alerts"
        
        # Add first alert details if space allows
        if alerts and len(summary) < max_length - 20:
            first_alert = alerts[0]
            asset_part = f" {first_alert.asset_symbol}" if first_alert.asset_symbol else ""
            alert_detail = f": {first_alert.title}{asset_part}"
            
            if len(summary + alert_detail) <= max_length:
                summary += alert_detail
        
        return summary[:max_length]
    
    async def _send_sms(self, to_number: str, message: str) -> bool:
        """Send SMS via Twilio."""
        try:
            # Run in thread pool since Twilio client is synchronous
            loop = asyncio.get_event_loop()
            
            def _send():
                return self.client.messages.create(
                    body=message,
                    from_=self.sms_config.from_number,
                    to=to_number
                )
            
            # Send SMS
            message_obj = await loop.run_in_executor(None, _send)
            
            # Check status
            if message_obj.status in ['queued', 'sent', 'delivered']:
                logger.debug(
                    "SMS queued successfully",
                    sid=message_obj.sid,
                    status=message_obj.status,
                    to=to_number
                )
                return True
            else:
                logger.error(
                    "SMS failed",
                    sid=message_obj.sid,
                    status=message_obj.status,
                    error_code=message_obj.error_code,
                    error_message=message_obj.error_message
                )
                return False
                
        except TwilioException as e:
            logger.error(
                "Twilio API error",
                to=to_number,
                error=str(e),
                error_code=getattr(e, 'code', None)
            )
            return False
        except Exception as e:
            logger.error(
                "SMS sending error",
                to=to_number,
                error=str(e)
            )
            return False
    
    async def test_connection(self) -> bool:
        """Test Twilio connection and configuration."""
        if not self.client:
            logger.error("Twilio client not initialized")
            return False
        
        try:
            # Test by fetching account info
            loop = asyncio.get_event_loop()
            
            def _test():
                return self.client.api.accounts(self.sms_config.twilio_account_sid).fetch()
            
            account = await loop.run_in_executor(None, _test)
            
            if account.status == 'active':
                logger.info("Twilio connection test successful", account_sid=account.sid)
                return True
            else:
                logger.error("Twilio account not active", status=account.status)
                return False
                
        except Exception as e:
            logger.error("Twilio connection test failed", error=str(e))
            return False
    
    def get_delivery_status(self, message_sid: str) -> Optional[str]:
        """Get delivery status of sent message."""
        if not self.client:
            return None
        
        try:
            message = self.client.messages(message_sid).fetch()
            return message.status
        except Exception as e:
            logger.error("Failed to get message status", sid=message_sid, error=str(e))
            return None
    
    def estimate_cost(self, message_count: int, country_code: str = "US") -> float:
        """Estimate SMS cost (approximate)."""
        # Approximate Twilio pricing (as of 2024)
        pricing = {
            "US": 0.0075,  # $0.0075 per SMS
            "CA": 0.0075,  # $0.0075 per SMS
            "GB": 0.040,   # $0.040 per SMS
            "AU": 0.052,   # $0.052 per SMS
            "DE": 0.075,   # $0.075 per SMS
        }
        
        rate = pricing.get(country_code, 0.10)  # Default rate
        return message_count * rate 