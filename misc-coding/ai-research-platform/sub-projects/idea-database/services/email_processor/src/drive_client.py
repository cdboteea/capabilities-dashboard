#!/usr/bin/env python3
"""
Google Drive Client for Idea Database
Handles Google Drive API integration for attachment storage
"""

import os
import io
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional, BinaryIO
import structlog
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError

logger = structlog.get_logger()

class DriveClient:
    """Google Drive API client for file storage"""
    
    def __init__(self, config: dict):
        self.config = config
        
        # OAuth credentials paths
        self.oauth_credentials_path = os.getenv(
            "DRIVE_OAUTH_CREDENTIALS_PATH",
            "/app/credentials/drive_oauth_credentials.json"
        )
        self.oauth_token_path = os.getenv(
            "DRIVE_OAUTH_TOKEN_PATH", 
            "/app/credentials/drive_oauth_token.json"
        )
        
        # Fallback to service account for backward compatibility
        self.service_account_path = os.getenv(
            "DRIVE_SERVICE_ACCOUNT_PATH",
            config.get('drive', {}).get('service_account_path', "/app/config/drive_service_account.json")
        )

        # Folder ID can be stored in DB; start with env/config if provided
        self.drive_folder_id = os.getenv("DRIVE_FOLDER_ID", config.get('drive', {}).get('folder_id'))

        # Folder name used when creating / locating folder
        self.drive_folder_name = os.getenv(
            "DRIVE_FOLDER_NAME",
            config.get('drive', {}).get('folder_name', 'idea-database-attachments')
        )
        
        # User email for sharing (from email config)
        self.user_email = config.get('email', {}).get('intake_email')
        
        # OAuth scopes
        self.oauth_scopes = ['https://www.googleapis.com/auth/drive.file']
        
        # Initialize service
        self.service = None
        self.auth_method = None  # 'oauth' or 'service_account'
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive service with OAuth or service account"""
        try:
            # Try OAuth first (preferred for user Drive access)
            if self._try_oauth_initialization():
                return
                
            # Fallback to service account (will likely fail due to quota policy)
            if self._try_service_account_initialization():
                return
                
            logger.info("No Google Drive credentials found - storage disabled")
                
        except Exception as e:
            logger.error("Google Drive service initialization failed", error=str(e))
    
    def _try_oauth_initialization(self) -> bool:
        """Try to initialize with OAuth credentials"""
        try:
            creds = None
            
            logger.info("Attempting OAuth initialization", 
                       token_path=self.oauth_token_path, 
                       credentials_path=self.oauth_credentials_path)
            
            # Load existing token if available
            if os.path.exists(self.oauth_token_path):
                logger.info("Loading OAuth token from file")
                creds = Credentials.from_authorized_user_file(self.oauth_token_path, self.oauth_scopes)
                logger.info("OAuth token loaded", valid=creds.valid if creds else False, 
                           expired=creds.expired if creds else False)
            
            # If there are no (valid) credentials available, let the user log in
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logger.info("Attempting to refresh expired OAuth token")
                    try:
                        creds.refresh(Request())
                        logger.info("OAuth token refreshed successfully")
                    except Exception as refresh_error:
                        logger.error("Failed to refresh OAuth token", error=str(refresh_error))
                        return False
                elif os.path.exists(self.oauth_credentials_path):
                    # For Docker/server environment, we can't do interactive flow
                    # The credentials need to be generated externally and copied
                    logger.warning("OAuth credentials need refresh but no interactive flow available")
                    return False
                else:
                    logger.info("No OAuth credentials found")
                    return False
            
            # Save the credentials for the next run
            if creds and creds.valid:
                os.makedirs(os.path.dirname(self.oauth_token_path), exist_ok=True)
                with open(self.oauth_token_path, 'w') as token:
                    token.write(creds.to_json())
            
            self.service = build('drive', 'v3', credentials=creds)
            self.auth_method = 'oauth'
            logger.info("Google Drive service initialized with OAuth", user_email=self.user_email)
            
            # Ensure folder exists
            if not self.drive_folder_id:
                self.drive_folder_id = self._ensure_folder_exists()
                
            return True
            
        except Exception as e:
            logger.error("OAuth Drive initialization failed", error=str(e))
            return False
    
    def _try_service_account_initialization(self) -> bool:
        """Try to initialize with service account (fallback)"""
        try:
            if os.path.exists(self.service_account_path):
                credentials = service_account.Credentials.from_service_account_file(
                    self.service_account_path,
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
                self.service = build('drive', 'v3', credentials=credentials)
                self.auth_method = 'service_account'
                logger.info("Google Drive service initialized with service account")
                
                # Ensure folder exists
                if not self.drive_folder_id:
                    self.drive_folder_id = self._ensure_folder_exists()
                    
                return True
            return False
                
        except Exception as e:
            logger.error("Service account Drive initialization failed", error=str(e))
            return False
    
    def has_credentials(self) -> bool:
        """Check if Google Drive credentials are available"""
        return self.service is not None
    
    def get_auth_info(self) -> Dict[str, Any]:
        """Get authentication information"""
        return {
            "has_credentials": self.has_credentials(),
            "auth_method": self.auth_method,
            "oauth_available": os.path.exists(self.oauth_credentials_path) or os.path.exists(self.oauth_token_path),
            "service_account_available": os.path.exists(self.service_account_path),
            "user_email": self.user_email
        }
    
    def _ensure_folder_exists(self) -> Optional[str]:
        """Ensure the attachments folder exists in Google Drive"""
        if not self.service:
            return None
            
        try:
            # Search for existing folder
            query = f"name='{self.drive_folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.service.files().list(q=query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                folder_id = folders[0]['id']
                logger.info("Found existing Drive folder", folder_id=folder_id, name=self.drive_folder_name)
                
                # Share the folder with the user if not already shared
                if self.user_email:
                    self._share_folder_with_user_sync(folder_id)
                
                return folder_id
            
            # Create new folder
            folder_metadata = {
                'name': self.drive_folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            folder = self.service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder.get('id')
            
            logger.info("Created new Drive folder", folder_id=folder_id, name=self.drive_folder_name)
            
            # Share the new folder with the user
            if self.user_email:
                self._share_folder_with_user_sync(folder_id)
            
            return folder_id
            
        except HttpError as e:
            logger.error("Failed to ensure Drive folder exists", error=str(e))
            return None
    
    def _share_folder_with_user_sync(self, folder_id: str):
        """Share the attachments folder with the user email (synchronous version)"""
        if not self.service or not self.user_email:
            return
            
        try:
            # Check if already shared
            permissions = self.service.permissions().list(fileId=folder_id).execute()
            for permission in permissions.get('permissions', []):
                if permission.get('emailAddress') == self.user_email:
                    logger.info("Folder already shared with user", folder_id=folder_id, user_email=self.user_email)
                    return
            
            # Create permission to share with user
            permission_metadata = {
                'type': 'user',
                'role': 'reader',
                'emailAddress': self.user_email
            }
            
            self.service.permissions().create(
                fileId=folder_id,
                body=permission_metadata,
                sendNotificationEmail=False  # Don't spam user with notifications
            ).execute()
            
            logger.info("Shared folder with user", folder_id=folder_id, user_email=self.user_email)
            
        except HttpError as e:
            logger.error("Failed to share folder with user", folder_id=folder_id, user_email=self.user_email, error=str(e))
    
    async def _share_folder_with_user(self, folder_id: str):
        """Share the attachments folder with the user email"""
        if not self.service or not self.user_email:
            return
            
        try:
            # Check if already shared
            permissions = self.service.permissions().list(fileId=folder_id).execute()
            for permission in permissions.get('permissions', []):
                if permission.get('emailAddress') == self.user_email:
                    logger.info("Folder already shared with user", folder_id=folder_id, user_email=self.user_email)
                    return
            
            # Create permission to share with user
            permission_metadata = {
                'type': 'user',
                'role': 'reader',
                'emailAddress': self.user_email
            }
            
            self.service.permissions().create(
                fileId=folder_id,
                body=permission_metadata,
                sendNotificationEmail=False  # Don't spam user with notifications
            ).execute()
            
            logger.info("Shared folder with user", folder_id=folder_id, user_email=self.user_email)
            
        except HttpError as e:
            logger.error("Failed to share folder with user", folder_id=folder_id, user_email=self.user_email, error=str(e))
    
    async def upload_file(self, file_content: bytes, filename: str, 
                         mime_type: str = 'application/octet-stream') -> Optional[Dict[str, str]]:
        """Upload file to Google Drive"""
        if not self.service or not self.drive_folder_id:
            logger.warning("Google Drive not available for upload", filename=filename)
            return None
            
        try:
            # Generate unique filename to avoid conflicts
            content_hash = hashlib.sha256(file_content).hexdigest()[:16]
            unique_filename = f"{content_hash}_{filename}"
            
            # Check if file already exists (deduplication)
            existing_file = await self._find_file_by_hash(content_hash)
            if existing_file:
                logger.info("File already exists in Drive", filename=filename, file_id=existing_file['file_id'])
                return existing_file
            
            # Upload new file
            file_metadata = {
                'name': unique_filename,
                'parents': [self.drive_folder_id],
                # Store hash in Drive file properties for reliable future lookup
                'appProperties': {
                    'content_hash': content_hash,
                    'source': 'idea-database'
                }
            }
            
            media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype=mime_type)
            
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id,webViewLink,size'
            ).execute()
            
            result = {
                'file_id': file.get('id'),
                'file_url': file.get('webViewLink'),
                'size': file.get('size'),
                'filename': unique_filename,
                'content_hash': content_hash
            }
            
            logger.info("File uploaded to Drive", filename=filename, file_id=result['file_id'])
            return result
            
        except HttpError as e:
            logger.error("Failed to upload file to Drive", filename=filename, error=str(e))
            return None
    
    async def share_file_with_user(self, file_id: str) -> bool:
        """Share a specific file with the user email"""
        if not self.service or not self.user_email:
            logger.warning("Cannot share file - missing service or user email", file_id=file_id)
            return False
            
        try:
            # Check if already shared
            permissions = self.service.permissions().list(fileId=file_id).execute()
            for permission in permissions.get('permissions', []):
                if permission.get('emailAddress') == self.user_email:
                    logger.info("File already shared with user", file_id=file_id, user_email=self.user_email)
                    return True
            
            # Create permission to share with user
            permission_metadata = {
                'type': 'user',
                'role': 'reader',
                'emailAddress': self.user_email
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission_metadata,
                sendNotificationEmail=False  # Don't spam user with notifications
            ).execute()
            
            logger.info("Shared file with user", file_id=file_id, user_email=self.user_email)
            return True
            
        except HttpError as e:
            logger.error("Failed to share file with user", file_id=file_id, user_email=self.user_email, error=str(e))
            return False
    
    async def get_shared_folder_url(self) -> Optional[str]:
        """Get the URL to the shared attachments folder"""
        if not self.service or not self.drive_folder_id:
            return None
            
        try:
            folder = self.service.files().get(
                fileId=self.drive_folder_id,
                fields='webViewLink'
            ).execute()
            
            return folder.get('webViewLink')
            
        except HttpError as e:
            logger.error("Failed to get folder URL", folder_id=self.drive_folder_id, error=str(e))
            return None
    
    async def download_file(self, file_id: str) -> Optional[bytes]:
        """Download file from Google Drive"""
        if not self.service:
            return None
            
        try:
            request = self.service.files().get_media(fileId=file_id)
            file_io = io.BytesIO()
            downloader = MediaIoBaseDownload(file_io, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                
            file_content = file_io.getvalue()
            logger.info("File downloaded from Drive", file_id=file_id, size=len(file_content))
            return file_content
            
        except HttpError as e:
            logger.error("Failed to download file from Drive", file_id=file_id, error=str(e))
            return None
    
    async def get_file_metadata(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata from Google Drive"""
        if not self.service:
            return None
            
        try:
            file = self.service.files().get(
                fileId=file_id,
                fields='id,name,size,mimeType,createdTime,webViewLink,description'
            ).execute()
            
            return {
                'id': file.get('id'),
                'name': file.get('name'),
                'size': int(file.get('size', 0)),
                'mime_type': file.get('mimeType'),
                'created_time': file.get('createdTime'),
                'web_view_link': file.get('webViewLink'),
                'description': file.get('description', '')
            }
            
        except HttpError as e:
            logger.error("Failed to get file metadata from Drive", file_id=file_id, error=str(e))
            return None
    
    async def delete_file(self, file_id: str) -> bool:
        """Delete file from Google Drive"""
        if not self.service:
            return False
            
        try:
            self.service.files().delete(fileId=file_id).execute()
            logger.info("File deleted from Drive", file_id=file_id)
            return True
            
        except HttpError as e:
            logger.error("Failed to delete file from Drive", file_id=file_id, error=str(e))
            return False
    
    async def _find_file_by_hash(self, content_hash: str) -> Optional[Dict[str, str]]:
        """Find existing file by content hash"""
        if not self.service:
            return None
            
        try:
            # Search using appProperties set during upload
            query = (
                f"'{self.drive_folder_id}' in parents "
                f"and appProperties has {{ key='content_hash' and value='{content_hash}' }} "
                f"and trashed = false"
            )
            results = self.service.files().list(
                q=query,
                fields="files(id,name,webViewLink,size)"
            ).execute()
            
            files = results.get('files', [])
            if files:
                file = files[0]
                return {
                    'file_id': file['id'],
                    'file_url': file.get('webViewLink'),
                    'size': file.get('size'),
                    'filename': file['name'],
                    'content_hash': content_hash
                }
            
            return None
            
        except HttpError as e:
            logger.error("Failed to search for existing file", content_hash=content_hash, error=str(e))
            return None
    
    async def share_file_with_email(self, file_id: str, email: str, 
                                   permission: str = "reader", 
                                   send_notification: bool = True) -> bool:
        """Share a specific file with an email address"""
        if not self.service:
            logger.warning("Cannot share file - missing service", file_id=file_id)
            return False
            
        try:
            # Check if already shared with this email
            permissions = self.service.permissions().list(fileId=file_id).execute()
            for permission_obj in permissions.get('permissions', []):
                if permission_obj.get('emailAddress') == email:
                    logger.info("File already shared with email", 
                               file_id=file_id, email=email)
                    return True
            
            # Create permission to share with email
            permission_metadata = {
                'type': 'user',
                'role': permission,  # reader, commenter, writer
                'emailAddress': email
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission_metadata,
                sendNotificationEmail=send_notification
            ).execute()
            
            logger.info("Shared file with email", 
                       file_id=file_id, email=email, permission=permission)
            return True
            
        except HttpError as e:
            logger.error("Failed to share file with email", 
                        file_id=file_id, email=email, error=str(e))
            return False

    async def generate_shareable_link(self, file_id: str, 
                                     permission: str = "reader") -> Optional[Dict[str, str]]:
        """Generate a shareable link for a file"""
        if not self.service:
            logger.warning("Cannot generate link - missing service", file_id=file_id)
            return None
            
        try:
            # First, make the file shareable with link
            permission_metadata = {
                'type': 'anyone',
                'role': permission,  # reader, commenter, writer
            }
            
            # Check if anyone permission already exists
            permissions = self.service.permissions().list(fileId=file_id).execute()
            anyone_permission_exists = False
            for perm in permissions.get('permissions', []):
                if perm.get('type') == 'anyone':
                    anyone_permission_exists = True
                    break
            
            if not anyone_permission_exists:
                self.service.permissions().create(
                    fileId=file_id,
                    body=permission_metadata,
                    sendNotificationEmail=False
                ).execute()
            
            # Get the file metadata to get the shareable link
            file_metadata = self.service.files().get(
                fileId=file_id,
                fields='webViewLink,webContentLink'
            ).execute()
            
            result = {
                'link': file_metadata.get('webViewLink'),
                'download_link': file_metadata.get('webContentLink'),
                'permission': permission
            }
            
            logger.info("Generated shareable link", 
                       file_id=file_id, permission=permission)
            return result
            
        except HttpError as e:
            logger.error("Failed to generate shareable link", 
                        file_id=file_id, error=str(e))
            return None

    async def get_storage_quota(self) -> Dict[str, int]:
        """Get storage quota information"""
        if not self.service:
            return {'total': 0, 'used': 0, 'available': 0}
            
        try:
            about = self.service.about().get(fields='storageQuota').execute()
            quota = about.get('storageQuota', {})
            
            total = int(quota.get('limit', 0))
            used = int(quota.get('usage', 0))
            available = total - used
            
            return {
                'total': total,
                'used': used,
                'available': available
            }
            
        except HttpError as e:
            logger.error("Failed to get storage quota", error=str(e))
            return {'total': 0, 'used': 0, 'available': 0} 