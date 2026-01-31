"""Email notification service."""

import asyncio
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
from jinja2 import Environment, FileSystemLoader, Template
from premailer import transform
import structlog

from ..config import config
from ..models.alert_models import AlertData, AlertDelivery, AlertChannel, AlertStatus

logger = structlog.get_logger(__name__)


class EmailService:
    """Service for sending email notifications."""
    
    def __init__(self):
        self.smtp_config = config.email
        self.template_env = Environment(
            loader=FileSystemLoader(config.templates_email_dir),
            autoescape=True
        )
        self._connection_pool = {}
        
    async def send_alert_email(
        self,
        alert: AlertData,
        delivery: AlertDelivery,
        template_name: Optional[str] = None
    ) -> bool:
        """Send alert via email."""
        try:
            # Prepare email content
            subject, html_content, text_content = await self._prepare_email_content(
                alert, delivery, template_name
            )
            
            # Send email
            success = await self._send_email(
                to_email=delivery.recipient,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if success:
                logger.info(
                    "Email sent successfully",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    recipient=delivery.recipient
                )
                return True
            else:
                logger.error(
                    "Failed to send email",
                    alert_id=alert.alert_id,
                    delivery_id=delivery.delivery_id,
                    recipient=delivery.recipient
                )
                return False
                
        except Exception as e:
            logger.error(
                "Email sending error",
                alert_id=alert.alert_id,
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def send_batch_email(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery,
        template_name: Optional[str] = None
    ) -> bool:
        """Send batch of alerts via email."""
        try:
            # Prepare batch email content
            subject, html_content, text_content = await self._prepare_batch_email_content(
                alerts, delivery, template_name
            )
            
            # Send email
            success = await self._send_email(
                to_email=delivery.recipient,
                subject=subject,
                html_content=html_content,
                text_content=text_content
            )
            
            if success:
                logger.info(
                    "Batch email sent successfully",
                    delivery_id=delivery.delivery_id,
                    recipient=delivery.recipient,
                    alert_count=len(alerts)
                )
                return True
            else:
                logger.error(
                    "Failed to send batch email",
                    delivery_id=delivery.delivery_id,
                    recipient=delivery.recipient,
                    alert_count=len(alerts)
                )
                return False
                
        except Exception as e:
            logger.error(
                "Batch email sending error",
                delivery_id=delivery.delivery_id,
                error=str(e)
            )
            return False
    
    async def _prepare_email_content(
        self,
        alert: AlertData,
        delivery: AlertDelivery,
        template_name: Optional[str] = None
    ) -> tuple[str, str, str]:
        """Prepare email content from template."""
        # Default template based on alert type
        if not template_name:
            template_name = f"{alert.alert_type.value}.html"
        
        # Template context
        context = {
            'alert': alert,
            'delivery': delivery,
            'title': alert.title,
            'message': alert.message,
            'summary': alert.summary,
            'asset_symbol': alert.asset_symbol,
            'priority': alert.priority.value,
            'created_at': alert.created_at,
            'data': alert.data
        }
        
        try:
            # Load and render HTML template
            template = self.template_env.get_template(template_name)
            html_content = template.render(**context)
            
            # Convert to inline CSS
            html_content = transform(html_content)
            
            # Generate text version
            text_content = self._html_to_text(html_content)
            
            # Subject
            subject = f"[{alert.priority.value.upper()}] {alert.title}"
            
            return subject, html_content, text_content
            
        except Exception as e:
            logger.warning(
                "Template rendering failed, using fallback",
                template_name=template_name,
                error=str(e)
            )
            
            # Fallback content
            subject = f"[{alert.priority.value.upper()}] {alert.title}"
            html_content = self._create_fallback_html(alert)
            text_content = self._create_fallback_text(alert)
            
            return subject, html_content, text_content
    
    async def _prepare_batch_email_content(
        self,
        alerts: List[AlertData],
        delivery: AlertDelivery,
        template_name: Optional[str] = None
    ) -> tuple[str, str, str]:
        """Prepare batch email content."""
        if not template_name:
            template_name = "batch_alerts.html"
        
        # Group alerts by priority and type
        alert_groups = self._group_alerts(alerts)
        
        context = {
            'alerts': alerts,
            'alert_groups': alert_groups,
            'delivery': delivery,
            'total_count': len(alerts),
            'high_priority_count': len([a for a in alerts if a.priority.value in ['high', 'critical']]),
            'created_at': delivery.created_at
        }
        
        try:
            # Load and render template
            template = self.template_env.get_template(template_name)
            html_content = template.render(**context)
            html_content = transform(html_content)
            text_content = self._html_to_text(html_content)
            
            # Subject
            subject = f"Alert Summary - {len(alerts)} new alerts"
            
            return subject, html_content, text_content
            
        except Exception as e:
            logger.warning(
                "Batch template rendering failed, using fallback",
                template_name=template_name,
                error=str(e)
            )
            
            # Fallback batch content
            subject = f"Alert Summary - {len(alerts)} new alerts"
            html_content = self._create_fallback_batch_html(alerts)
            text_content = self._create_fallback_batch_text(alerts)
            
            return subject, html_content, text_content
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: str,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send email via SMTP."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.smtp_config.from_name} <{self.smtp_config.from_email}>"
            msg['To'] = to_email
            
            # Add text and HTML parts
            text_part = MIMEText(text_content, 'plain', 'utf-8')
            html_part = MIMEText(html_content, 'html', 'utf-8')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    await self._add_attachment(msg, attachment)
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_config.smtp_host,
                port=self.smtp_config.smtp_port,
                username=self.smtp_config.smtp_user,
                password=self.smtp_config.smtp_password,
                use_tls=self.smtp_config.use_tls
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "SMTP sending failed",
                to_email=to_email,
                subject=subject,
                error=str(e)
            )
            return False
    
    async def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message."""
        try:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(attachment['content'])
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment["filename"]}'
            )
            msg.attach(part)
        except Exception as e:
            logger.warning(
                "Failed to add attachment",
                filename=attachment.get('filename'),
                error=str(e)
            )
    
    def _group_alerts(self, alerts: List[AlertData]) -> Dict[str, List[AlertData]]:
        """Group alerts by priority and type."""
        groups = {}
        
        for alert in alerts:
            key = f"{alert.priority.value}_{alert.alert_type.value}"
            if key not in groups:
                groups[key] = []
            groups[key].append(alert)
        
        return groups
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text."""
        # Simple HTML to text conversion
        # In production, consider using html2text or similar library
        import re
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html_content)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def _create_fallback_html(self, alert: AlertData) -> str:
        """Create fallback HTML content."""
        return f"""
        <html>
        <body>
            <h2>{alert.title}</h2>
            <p><strong>Priority:</strong> {alert.priority.value.upper()}</p>
            <p><strong>Type:</strong> {alert.alert_type.value}</p>
            {f'<p><strong>Asset:</strong> {alert.asset_symbol}</p>' if alert.asset_symbol else ''}
            <p>{alert.message}</p>
            {f'<p><em>{alert.summary}</em></p>' if alert.summary else ''}
            <p><small>Created: {alert.created_at}</small></p>
        </body>
        </html>
        """
    
    def _create_fallback_text(self, alert: AlertData) -> str:
        """Create fallback text content."""
        lines = [
            alert.title,
            f"Priority: {alert.priority.value.upper()}",
            f"Type: {alert.alert_type.value}",
        ]
        
        if alert.asset_symbol:
            lines.append(f"Asset: {alert.asset_symbol}")
        
        lines.extend([
            "",
            alert.message
        ])
        
        if alert.summary:
            lines.extend(["", alert.summary])
        
        lines.extend(["", f"Created: {alert.created_at}"])
        
        return "\n".join(lines)
    
    def _create_fallback_batch_html(self, alerts: List[AlertData]) -> str:
        """Create fallback batch HTML content."""
        html_parts = [
            "<html><body>",
            f"<h2>Alert Summary - {len(alerts)} New Alerts</h2>"
        ]
        
        for alert in alerts:
            html_parts.extend([
                "<hr>",
                f"<h3>{alert.title}</h3>",
                f"<p><strong>Priority:</strong> {alert.priority.value.upper()}</p>",
                f"<p>{alert.message}</p>"
            ])
        
        html_parts.append("</body></html>")
        return "\n".join(html_parts)
    
    def _create_fallback_batch_text(self, alerts: List[AlertData]) -> str:
        """Create fallback batch text content."""
        lines = [f"Alert Summary - {len(alerts)} New Alerts", "=" * 40]
        
        for i, alert in enumerate(alerts, 1):
            lines.extend([
                "",
                f"{i}. {alert.title}",
                f"   Priority: {alert.priority.value.upper()}",
                f"   {alert.message}"
            ])
        
        return "\n".join(lines)
    
    async def test_connection(self) -> bool:
        """Test SMTP connection."""
        try:
            # Test connection
            await aiosmtplib.connect(
                hostname=self.smtp_config.smtp_host,
                port=self.smtp_config.smtp_port,
                username=self.smtp_config.smtp_user,
                password=self.smtp_config.smtp_password,
                use_tls=self.smtp_config.use_tls,
                timeout=10
            )
            
            logger.info("SMTP connection test successful")
            return True
            
        except Exception as e:
            logger.error("SMTP connection test failed", error=str(e))
            return False 