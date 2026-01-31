#!/usr/bin/env python3
"""
Gmail Client for Idea Database
Handles Gmail API integration with graceful placeholder handling
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
import structlog

logger = structlog.get_logger()

class GmailClient:
    """Gmail API client with placeholder support"""
    
    def __init__(self, config: dict):
        self.config = config
        self.email_address = config['email']['intake_email']
        self.credentials_path = "/app/credentials/gmail_credentials.json"
        self.token_path = "/app/credentials/gmail_token.json"
        
        # Initialize service (will be None if no credentials)
        self.service = None
        self._initialize_service()
        
        # Initialize Drive client
        from .drive_client import DriveClient
        self.drive_client = DriveClient(config)
    
    def _initialize_service(self):
        """Initialize Gmail service if credentials are available"""
        try:
            if self.has_credentials():
                # Import Google APIs only if we have credentials
                from google.auth.transport.requests import Request
                from google.oauth2.credentials import Credentials
                from googleapiclient.discovery import build
                
                creds = None
                
                # Load existing token
                if os.path.exists(self.token_path):
                    creds = Credentials.from_authorized_user_file(self.token_path)
                
                # If there are no valid credentials, return without service
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        logger.info("Gmail credentials need setup", 
                                  email=self.email_address)
                        return
                
                self.service = build('gmail', 'v1', credentials=creds)
                logger.info("Gmail service initialized", email=self.email_address)
            else:
                logger.info("No Gmail credentials found - using placeholder mode",
                          email=self.email_address)
                
        except ImportError:
            logger.info("Google API libraries not available - placeholder mode active")
        except Exception as e:
            logger.warning("Gmail service initialization failed", 
                         error=str(e), email=self.email_address)
    
    def has_credentials(self) -> bool:
        """Check if Gmail credentials are available"""
        return (os.path.exists(self.credentials_path) and 
                os.path.exists(self.token_path))
    
    async def fetch_recent_emails(self, max_emails: int = 50, 
                                force_reprocess: bool = False) -> Dict[str, Any]:
        """Fetch recent emails from Gmail"""
        
        if not self.service:
            # Return placeholder response
            return {
                "status": "placeholder",
                "total_count": 0,
                "emails": [],
                "message": f"Credentials needed for: {self.email_address}"
            }
        
        try:
            # Search for emails in the inbox
            query = "in:inbox"
            if not force_reprocess:
                query += " is:unread"
            
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_emails
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for msg in messages:
                email_data = await self._get_email_details(msg['id'])
                if email_data:
                    emails.append(email_data)
            
            logger.info("Fetched emails from Gmail", 
                       count=len(emails), email=self.email_address)
            
            return {
                "status": "success",
                "total_count": len(emails),
                "emails": emails
            }
            
        except Exception as e:
            logger.error("Failed to fetch emails", error=str(e))
            raise
    
    async def _get_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed email information"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract key headers
            subject = ""
            sender = ""
            date = ""
            
            for header in headers:
                name = header['name'].lower()
                if name == 'subject':
                    subject = header['value']
                elif name == 'from':
                    sender = header['value']
                elif name == 'date':
                    date = header['value']

            # Debug: log every fetched subject for troubleshooting
            logger.info("Fetched email subject", message_id=message_id, subject=subject)
            
            # Extract body and HTML content
            body = self._extract_email_body(message['payload'])
            html_body = self._extract_html_body(message['payload'])
            
            # File debug logging for body and html_body
            try:
                with open('/app/email_debug.log', 'a') as f:
                    f.write(f"GmailClient: message_id={message_id} subject={subject} body_preview={body[:120] if body else 'EMPTY'} html_body_preview={html_body[:120] if html_body else 'EMPTY'}\n")
            except Exception as e:
                pass
            logger.info("GmailClient extracted email content", 
                        message_id=message_id, 
                        subject=subject,
                        body_preview=body[:120] if body else "EMPTY",
                        html_body_preview=html_body[:120] if html_body else "EMPTY")
            
            # Extract attachments metadata (do not download file here)
            try:
                attachments = self._extract_attachments(message['payload'], message_id)
            except Exception as e:
                logger.error("Failed to extract attachments, skipping", message_id=message_id, error=str(e))
                attachments = []
            
            return {
                "id": message_id,
                "subject": subject,
                "sender": sender,
                "date": date,
                "body": body,
                "html_body": html_body,
                "attachments": attachments,
                "thread_id": message.get('threadId'),
                "labels": message.get('labelIds', [])
            }
            
        except Exception as e:
            logger.error("Failed to get email details", 
                        message_id=message_id, error=str(e))
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """Extract email body from payload, handling both text/plain and text/html"""
        body = ""
        html_body = ""
        
        if 'parts' in payload:
            # Multipart message - check all parts
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        import base64
                        body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break  # Prefer plain text if available
                elif part['mimeType'] == 'text/html' and not body:
                    data = part['body'].get('data')
                    if data:
                        import base64
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                        
                # Also check nested parts (multipart/alternative, multipart/related)
                if part.get('parts'):
                    nested_body = self._extract_email_body(part)
                    if nested_body and not body:
                        body = nested_body
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data')
                if data:
                    import base64
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
            elif payload['mimeType'] == 'text/html':
                data = payload['body'].get('data')
                if data:
                    import base64
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        # If we only have HTML, convert it to plain text
        if not body and html_body:
            body = self._html_to_text(html_body)
        
        return body
    
    def _extract_html_body(self, payload: Dict[str, Any]) -> str:
        """Extract HTML body from payload without converting to text"""
        html_body = ""
        
        if 'parts' in payload:
            # Multipart message - find HTML part
            for part in payload['parts']:
                if part['mimeType'] == 'text/html':
                    data = part['body'].get('data')
                    if data:
                        import base64
                        html_body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
                        
                # Also check nested parts
                if part.get('parts'):
                    nested_html = self._extract_html_body(part)
                    if nested_html and not html_body:
                        html_body = nested_html
        else:
            # Single part message
            if payload['mimeType'] == 'text/html':
                data = payload['body'].get('data')
                if data:
                    import base64
                    html_body = base64.urlsafe_b64decode(data).decode('utf-8')
        
        return html_body
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        try:
            from bs4 import BeautifulSoup
            import re
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            logger.warning("Failed to convert HTML to text", error=str(e))
            # Fallback: strip HTML tags with regex
            import re
            text = re.sub(r'<[^>]+>', '', html_content)
            return text.strip()
    
    def _extract_attachments(self, payload: Dict[str, Any], message_id: str):
        """Traverse MIME parts and return a list of attachment metadata dictionaries"""
        import hashlib  # Ensure hashlib is available
        attachments = []

        seen_attach_ids: set[str] = set()

        def walk_parts(parts):
            for part in parts:
                filename = part.get('filename')
                body = part.get('body', {})
                attachment_id = body.get('attachmentId')

                if filename and attachment_id and attachment_id in seen_attach_ids:
                    # Duplicate attachment reference – skip
                    continue
                if filename:
                    if attachment_id:
                        seen_attach_ids.add(attachment_id)
                    # Determine deterministic content hash (<=64 chars)
                    # Use message_id + filename for stable hashing across reprocessing
                    stable_key = f"{message_id}_{filename}"
                    chash = hashlib.sha256(stable_key.encode()).hexdigest()[:64]

                    attachments.append({
                        'filename': filename,
                        'original_filename': filename,
                        'mime_type': part.get('mimeType'),
                        'size': body.get('size'),
                        # Include Gmail identifiers so the backend can fetch on demand
                        'gmail_message_id': message_id,
                        'gmail_attachment_id': attachment_id,
                        # file_path placeholder
                        'file_path': '',
                        'content_hash': chash,
                    })
                if part.get('parts'):
                    walk_parts(part['parts'])

        if 'parts' in payload:
            walk_parts(payload['parts'])

        if attachments:
            logger.info("Found attachments in email", message_id=message_id, count=len(attachments))

        return attachments

    async def download_gmail_attachment(self, message_id: str, attachment_id: str):
        """Download attachment bytes from Gmail using message & attachment IDs"""
        if not self.service:
            return None

        import base64
        import asyncio
        import hashlib

        try:
            loop = asyncio.get_event_loop()

            def _fetch():
                return (
                    self.service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=message_id, id=attachment_id)
                    .execute()
                )

            attachment_data = await loop.run_in_executor(None, _fetch)

            if not attachment_data or "data" not in attachment_data:
                return None

            return base64.urlsafe_b64decode(attachment_data["data"])
        except Exception as e:
            logger.error(
                "Failed to download Gmail attachment",
                message_id=message_id,
                attachment_id=attachment_id,
                error=str(e),
            )
            return None
    
    async def mark_as_processed(self, message_id: str):
        """Mark email as processed by adding a label"""
        if not self.service:
            return
        
        try:
            # Add a custom label to mark as processed
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['PROCESSED']}
            ).execute()
            
        except Exception as e:
            logger.warning("Failed to mark email as processed", 
                         message_id=message_id, error=str(e)) 
