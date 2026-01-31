"""Alert management service for processing and routing alerts."""

import asyncio
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Set
import structlog
from jinja2 import Template, Environment, DictLoader
import redis.asyncio as redis

from ..models.alert_models import (
    AlertEvent, AlertRule, AlertCondition, NotificationDelivery,
    AlertBatch, UserPreferences, NotificationTemplate,
    AlertType, AlertPriority, AlertStatus, NotificationChannel, DeliveryStatus
)
from ..utils.database import DatabaseManager
from .email_service import EmailService
from .sms_service import SMSService
from .push_service import PushService
from .webhook_service import WebhookService
from ..config import config

logger = structlog.get_logger(__name__)


class AlertManager:
    """Main alert management service."""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.email_service = EmailService()
        self.sms_service = SMSService()
        self.push_service = PushService()
        self.webhook_service = WebhookService()
        
        self.redis_client = None
        self.template_env = Environment(loader=DictLoader({}))
        
        # Alert processing queues
        self.alert_queue = asyncio.Queue()
        self.delivery_queue = asyncio.Queue()
        self.batch_queue = asyncio.Queue()
        
        # Active rules cache
        self.active_rules: Dict[str, AlertRule] = {}
        self.user_preferences: Dict[str, UserPreferences] = {}
        self.templates: Dict[str, NotificationTemplate] = {}
        
        # Processing state
        self.processing_active = False
        self.batch_processing_active = False
    
    async def initialize(self):
        """Initialize alert manager."""
        try:
            # Initialize Redis connection
            self.redis_client = redis.from_url(config.redis.url)
            await self.redis_client.ping()
            
            # Initialize notification services
            await self.email_service.initialize()
            await self.sms_service.initialize()
            await self.push_service.initialize()
            await self.webhook_service.initialize()
            
            # Load active rules and preferences
            await self._load_active_rules()
            await self._load_user_preferences()
            await self._load_templates()
            
            # Start processing tasks
            await self._start_processing_tasks()
            
            logger.info("Alert manager initialized successfully")
            
        except Exception as e:
            logger.error("Alert manager initialization failed", error=str(e))
            raise
    
    async def process_alert(self, alert: AlertEvent) -> List[NotificationDelivery]:
        """Process a new alert event."""
        try:
            logger.info(
                "Processing alert",
                alert_id=alert.event_id,
                alert_type=alert.alert_type.value,
                priority=alert.priority.value
            )
            
            # Validate alert
            if not self._validate_alert(alert):
                logger.warning("Alert validation failed", alert_id=alert.event_id)
                return []
            
            # Check if alert should be processed
            if not await self._should_process_alert(alert):
                logger.info("Alert filtered out", alert_id=alert.event_id)
                return []
            
            # Find matching rules
            matching_rules = await self._find_matching_rules(alert)
            
            if not matching_rules:
                logger.info("No matching rules found", alert_id=alert.event_id)
                return []
            
            # Generate notifications
            deliveries = []
            for rule in matching_rules:
                rule_deliveries = await self._generate_notifications(alert, rule)
                deliveries.extend(rule_deliveries)
            
            # Save alert to database
            await self._save_alert(alert)
            
            # Queue deliveries
            for delivery in deliveries:
                await self.delivery_queue.put(delivery)
            
            # Update alert status
            alert.status = AlertStatus.SENT
            alert.processed_at = datetime.utcnow()
            
            logger.info(
                "Alert processed successfully",
                alert_id=alert.event_id,
                deliveries_count=len(deliveries)
            )
            
            return deliveries
            
        except Exception as e:
            logger.error(
                "Alert processing failed",
                alert_id=alert.event_id,
                error=str(e)
            )
            
            # Update alert status to failed
            alert.status = AlertStatus.FAILED
            await self._save_alert(alert)
            
            return []
    
    async def create_alert_rule(self, rule: AlertRule) -> bool:
        """Create a new alert rule."""
        try:
            # Validate rule
            if not self._validate_rule(rule):
                return False
            
            # Save to database
            await self._save_rule(rule)
            
            # Add to active rules cache
            self.active_rules[rule.rule_id] = rule
            
            logger.info("Alert rule created", rule_id=rule.rule_id, name=rule.name)
            return True
            
        except Exception as e:
            logger.error("Failed to create alert rule", rule_id=rule.rule_id, error=str(e))
            return False
    
    async def update_user_preferences(self, preferences: UserPreferences) -> bool:
        """Update user notification preferences."""
        try:
            # Save to database
            await self._save_user_preferences(preferences)
            
            # Update cache
            self.user_preferences[preferences.user_id] = preferences
            
            logger.info("User preferences updated", user_id=preferences.user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to update user preferences", user_id=preferences.user_id, error=str(e))
            return False
    
    async def get_alert_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get alert statistics for the specified period."""
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Query database for statistics
            stats = await self.db_manager.get_alert_statistics(start_date)
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get alert statistics", error=str(e))
            return {}
    
    async def _validate_alert(self, alert: AlertEvent) -> bool:
        """Validate alert event."""
        if not alert.title or not alert.message:
            return False
        
        if alert.priority not in AlertPriority:
            return False
        
        if alert.alert_type not in AlertType:
            return False
        
        return True
    
    async def _should_process_alert(self, alert: AlertEvent) -> bool:
        """Check if alert should be processed."""
        # Check for duplicate alerts (within cooldown period)
        cache_key = f"alert_cooldown:{alert.alert_type.value}:{alert.symbol or 'global'}"
        
        if self.redis_client:
            existing = await self.redis_client.get(cache_key)
            if existing:
                logger.info("Alert in cooldown period", alert_id=alert.event_id)
                return False
            
            # Set cooldown
            await self.redis_client.setex(cache_key, 300, alert.event_id)  # 5 min cooldown
        
        # Check if alert has expired
        if alert.expiry_timestamp and alert.expiry_timestamp < datetime.utcnow():
            logger.info("Alert expired", alert_id=alert.event_id)
            return False
        
        return True
    
    async def _find_matching_rules(self, alert: AlertEvent) -> List[AlertRule]:
        """Find alert rules that match the event."""
        matching_rules = []
        
        for rule in self.active_rules.values():
            if not rule.is_active:
                continue
            
            # Check alert type match
            if rule.alert_type != alert.alert_type:
                continue
            
            # Check portfolio/symbol targeting
            if rule.portfolio_ids and alert.portfolio_id not in rule.portfolio_ids:
                continue
            
            if rule.symbols and alert.symbol not in rule.symbols:
                continue
            
            # Check conditions
            if await self._evaluate_conditions(alert, rule.conditions, rule.condition_logic):
                matching_rules.append(rule)
        
        return matching_rules
    
    async def _evaluate_conditions(
        self,
        alert: AlertEvent,
        conditions: List[AlertCondition],
        logic: str
    ) -> bool:
        """Evaluate alert conditions."""
        if not conditions:
            return True
        
        results = []
        
        for condition in conditions:
            result = await self._evaluate_single_condition(alert, condition)
            results.append(result)
        
        # Apply logic
        if logic.upper() == "AND":
            return all(results)
        elif logic.upper() == "OR":
            return any(results)
        else:
            return all(results)  # Default to AND
    
    async def _evaluate_single_condition(self, alert: AlertEvent, condition: AlertCondition) -> bool:
        """Evaluate a single condition."""
        try:
            # Get field value from alert
            field_value = self._get_alert_field_value(alert, condition.field)
            
            if field_value is None:
                return False
            
            # Apply operator
            if condition.operator == ">":
                return float(field_value) > float(condition.value)
            elif condition.operator == "<":
                return float(field_value) < float(condition.value)
            elif condition.operator == ">=":
                return float(field_value) >= float(condition.value)
            elif condition.operator == "<=":
                return float(field_value) <= float(condition.value)
            elif condition.operator == "==":
                return str(field_value) == str(condition.value)
            elif condition.operator == "!=":
                return str(field_value) != str(condition.value)
            elif condition.operator == "contains":
                return str(condition.value).lower() in str(field_value).lower()
            elif condition.operator == "in":
                return str(field_value) in condition.value
            elif condition.operator == "not_in":
                return str(field_value) not in condition.value
            
            return False
            
        except Exception as e:
            logger.warning("Condition evaluation failed", condition=condition.dict(), error=str(e))
            return False
    
    def _get_alert_field_value(self, alert: AlertEvent, field: str) -> Any:
        """Get field value from alert event."""
        if hasattr(alert, field):
            return getattr(alert, field)
        elif field in alert.data:
            return alert.data[field]
        else:
            return None
    
    async def _generate_notifications(
        self,
        alert: AlertEvent,
        rule: AlertRule
    ) -> List[NotificationDelivery]:
        """Generate notification deliveries for an alert."""
        deliveries = []
        
        for recipient in rule.recipients:
            # Get user preferences
            user_prefs = self.user_preferences.get(recipient)
            
            # Determine channels to use
            channels = await self._determine_channels(rule.channels, user_prefs, alert.priority)
            
            for channel in channels:
                # Check if user wants this type of alert
                if user_prefs and not self._user_wants_alert(user_prefs, alert):
                    continue
                
                # Check quiet hours
                if user_prefs and self._is_quiet_hours(user_prefs):
                    continue
                
                # Generate delivery
                delivery = await self._create_delivery(alert, rule, recipient, channel)
                if delivery:
                    deliveries.append(delivery)
        
        return deliveries
    
    async def _determine_channels(
        self,
        rule_channels: List[NotificationChannel],
        user_prefs: Optional[UserPreferences],
        priority: AlertPriority
    ) -> List[NotificationChannel]:
        """Determine which channels to use for notification."""
        if not user_prefs:
            return rule_channels
        
        available_channels = []
        
        for channel in rule_channels:
            if channel == NotificationChannel.EMAIL and user_prefs.email_enabled:
                available_channels.append(channel)
            elif channel == NotificationChannel.SMS and user_prefs.sms_enabled:
                available_channels.append(channel)
            elif channel == NotificationChannel.PUSH and user_prefs.push_enabled:
                available_channels.append(channel)
            elif channel == NotificationChannel.WEBHOOK and user_prefs.webhook_enabled:
                available_channels.append(channel)
            else:
                # Always allow other channels
                available_channels.append(channel)
        
        # For high priority alerts, ensure at least one channel
        if priority in [AlertPriority.HIGH, AlertPriority.CRITICAL, AlertPriority.URGENT]:
            if not available_channels and user_prefs.email_enabled:
                available_channels.append(NotificationChannel.EMAIL)
        
        return available_channels
    
    def _user_wants_alert(self, user_prefs: UserPreferences, alert: AlertEvent) -> bool:
        """Check if user wants this type of alert."""
        # Check priority threshold
        priority_levels = {
            AlertPriority.LOW: 1,
            AlertPriority.MEDIUM: 2,
            AlertPriority.HIGH: 3,
            AlertPriority.CRITICAL: 4,
            AlertPriority.URGENT: 5
        }
        
        if priority_levels.get(alert.priority, 0) < priority_levels.get(user_prefs.priority_threshold, 0):
            return False
        
        # Check alert type preferences
        if alert.alert_type in user_prefs.alert_type_preferences:
            return user_prefs.alert_type_preferences[alert.alert_type]
        
        return True
    
    def _is_quiet_hours(self, user_prefs: UserPreferences) -> bool:
        """Check if current time is within user's quiet hours."""
        if not user_prefs.quiet_hours_start or not user_prefs.quiet_hours_end:
            return False
        
        # Simplified quiet hours check (would need proper timezone handling)
        current_time = datetime.utcnow().time()
        
        try:
            start_time = datetime.strptime(user_prefs.quiet_hours_start, "%H:%M").time()
            end_time = datetime.strptime(user_prefs.quiet_hours_end, "%H:%M").time()
            
            if start_time <= end_time:
                return start_time <= current_time <= end_time
            else:
                # Quiet hours span midnight
                return current_time >= start_time or current_time <= end_time
        except:
            return False
    
    async def _create_delivery(
        self,
        alert: AlertEvent,
        rule: AlertRule,
        recipient: str,
        channel: NotificationChannel
    ) -> Optional[NotificationDelivery]:
        """Create a notification delivery."""
        try:
            # Get template
            template = await self._get_template(alert.alert_type, channel)
            
            # Render content
            subject, content = await self._render_notification(alert, template)
            
            delivery = NotificationDelivery(
                alert_id=alert.event_id,
                channel=channel,
                recipient=recipient,
                subject=subject,
                content=content,
                status=DeliveryStatus.QUEUED
            )
            
            return delivery
            
        except Exception as e:
            logger.error(
                "Failed to create delivery",
                alert_id=alert.event_id,
                recipient=recipient,
                channel=channel.value,
                error=str(e)
            )
            return None
    
    async def _get_template(
        self,
        alert_type: AlertType,
        channel: NotificationChannel
    ) -> Optional[NotificationTemplate]:
        """Get notification template for alert type and channel."""
        template_key = f"{alert_type.value}_{channel.value}"
        return self.templates.get(template_key)
    
    async def _render_notification(
        self,
        alert: AlertEvent,
        template: Optional[NotificationTemplate]
    ) -> tuple[str, str]:
        """Render notification content using template."""
        if not template:
            # Use default templates
            subject = f"Alert: {alert.title}"
            content = alert.message
        else:
            # Prepare template variables
            variables = {
                'title': alert.title,
                'message': alert.message,
                'symbol': alert.symbol or '',
                'portfolio_id': alert.portfolio_id or '',
                'priority': alert.priority.value,
                'timestamp': alert.event_timestamp.isoformat(),
                'data': alert.data
            }
            
            # Render templates
            subject_template = Template(template.subject_template)
            body_template = Template(template.body_template)
            
            subject = subject_template.render(**variables)
            content = body_template.render(**variables)
        
        return subject, content
    
    async def _start_processing_tasks(self):
        """Start background processing tasks."""
        self.processing_active = True
        self.batch_processing_active = True
        
        # Start delivery processing
        asyncio.create_task(self._process_delivery_queue())
        
        # Start batch processing
        asyncio.create_task(self._process_batch_queue())
        
        logger.info("Alert processing tasks started")
    
    async def _process_delivery_queue(self):
        """Process delivery queue."""
        while self.processing_active:
            try:
                # Get delivery from queue
                delivery = await asyncio.wait_for(
                    self.delivery_queue.get(),
                    timeout=1.0
                )
                
                # Process delivery
                await self._deliver_notification(delivery)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error("Delivery queue processing error", error=str(e))
                await asyncio.sleep(1)
    
    async def _deliver_notification(self, delivery: NotificationDelivery):
        """Deliver a notification."""
        try:
            delivery.status = DeliveryStatus.SENDING
            delivery.sent_at = datetime.utcnow()
            delivery.attempts += 1
            
            # Route to appropriate service
            success = False
            
            if delivery.channel == NotificationChannel.EMAIL:
                success = await self.email_service.send_email(
                    delivery.recipient,
                    delivery.subject,
                    delivery.content
                )
            elif delivery.channel == NotificationChannel.SMS:
                success = await self.sms_service.send_sms(
                    delivery.recipient,
                    delivery.content
                )
            elif delivery.channel == NotificationChannel.PUSH:
                success = await self.push_service.send_push(
                    delivery.recipient,
                    delivery.subject,
                    delivery.content
                )
            elif delivery.channel == NotificationChannel.WEBHOOK:
                success = await self.webhook_service.send_webhook(
                    delivery.recipient,
                    {
                        'subject': delivery.subject,
                        'content': delivery.content,
                        'alert_id': delivery.alert_id
                    }
                )
            
            # Update delivery status
            if success:
                delivery.status = DeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.utcnow()
            else:
                delivery.status = DeliveryStatus.FAILED
                
                # Schedule retry if attempts remaining
                if delivery.attempts < delivery.max_attempts:
                    delivery.status = DeliveryStatus.RETRY
                    delivery.retry_at = datetime.utcnow() + timedelta(minutes=5 * delivery.attempts)
                    await self.delivery_queue.put(delivery)
            
            # Save delivery record
            await self._save_delivery(delivery)
            
            logger.info(
                "Notification delivered",
                delivery_id=delivery.delivery_id,
                channel=delivery.channel.value,
                status=delivery.status.value
            )
            
        except Exception as e:
            logger.error(
                "Notification delivery failed",
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = str(e)
            await self._save_delivery(delivery)
    
    async def _process_batch_queue(self):
        """Process batch notification queue."""
        while self.batch_processing_active:
            try:
                # Check for batches to process
                await self._process_pending_batches()
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error("Batch processing error", error=str(e))
                await asyncio.sleep(60)
    
    async def _process_pending_batches(self):
        """Process pending batch notifications."""
        # Implementation would check for users with batch preferences
        # and create batch notifications for accumulated alerts
        pass
    
    # Database operations
    
    async def _save_alert(self, alert: AlertEvent):
        """Save alert to database."""
        await self.db_manager.save_alert(alert)
    
    async def _save_rule(self, rule: AlertRule):
        """Save alert rule to database."""
        await self.db_manager.save_alert_rule(rule)
    
    async def _save_user_preferences(self, preferences: UserPreferences):
        """Save user preferences to database."""
        await self.db_manager.save_user_preferences(preferences)
    
    async def _save_delivery(self, delivery: NotificationDelivery):
        """Save delivery record to database."""
        await self.db_manager.save_delivery(delivery)
    
    async def _load_active_rules(self):
        """Load active alert rules from database."""
        rules = await self.db_manager.get_active_rules()
        self.active_rules = {rule.rule_id: rule for rule in rules}
        logger.info("Loaded active rules", count=len(self.active_rules))
    
    async def _load_user_preferences(self):
        """Load user preferences from database."""
        preferences = await self.db_manager.get_user_preferences()
        self.user_preferences = {pref.user_id: pref for pref in preferences}
        logger.info("Loaded user preferences", count=len(self.user_preferences))
    
    async def _load_templates(self):
        """Load notification templates from database."""
        templates = await self.db_manager.get_templates()
        self.templates = {f"{t.alert_type.value}_{t.channel.value}": t for t in templates}
        logger.info("Loaded notification templates", count=len(self.templates))
    
    async def cleanup(self):
        """Cleanup alert manager resources."""
        try:
            self.processing_active = False
            self.batch_processing_active = False
            
            if self.redis_client:
                await self.redis_client.close()
            
            await self.email_service.cleanup()
            await self.sms_service.cleanup()
            await self.push_service.cleanup()
            await self.webhook_service.cleanup()
            
            logger.info("Alert manager cleanup completed")
            
        except Exception as e:
            logger.error("Alert manager cleanup failed", error=str(e)) 