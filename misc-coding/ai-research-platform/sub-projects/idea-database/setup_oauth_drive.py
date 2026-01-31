#!/usr/bin/env python3
"""
Google Drive OAuth Setup for Idea Database
Generates OAuth token for direct user Drive access (no service account needed)
"""

import os
import json
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required for Drive access
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    print("🚀 Google Drive OAuth Setup for Idea Database")
    print("=" * 50)
    
    # File paths
    base_dir = Path(__file__).parent
    credentials_dir = base_dir / "gmail_credentials"
    oauth_creds_file = credentials_dir / "drive_oauth_credentials.json"
    oauth_token_file = credentials_dir / "drive_oauth_token.json"
    
    # Ensure credentials directory exists
    credentials_dir.mkdir(exist_ok=True)
    
    # Check for OAuth credentials file
    if not oauth_creds_file.exists():
        print("❌ OAuth credentials file not found!")
        print(f"   Expected: {oauth_creds_file}")
        print()
        print("📝 To create OAuth credentials:")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Select your project (or create one)")
        print("3. Enable the Google Drive API")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'OAuth client ID'")
        print("5. Choose 'Desktop application'")
        print("6. Download the JSON file and save it as:")
        print(f"   {oauth_creds_file}")
        print()
        return False
    
    print(f"✅ Found OAuth credentials: {oauth_creds_file}")
    
    creds = None
    
    # Load existing token if available
    if oauth_token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(oauth_token_file), SCOPES)
            print(f"✅ Found existing token: {oauth_token_file}")
        except Exception as e:
            print(f"⚠️  Failed to load existing token: {e}")
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully")
            except Exception as e:
                print(f"❌ Failed to refresh token: {e}")
                creds = None
        
        if not creds:
            print("🔐 Starting OAuth flow...")
            print("   A browser window will open for authentication")
            print("   Please log in with the Google account: ideaseea@gmail.com")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                str(oauth_creds_file), SCOPES
            )
            creds = flow.run_local_server(port=0)
            print("✅ OAuth flow completed")
    
    # Save the credentials for the next run
    if creds and creds.valid:
        with open(oauth_token_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Token saved: {oauth_token_file}")
        
        # Test the credentials
        from googleapiclient.discovery import build
        try:
            service = build('drive', 'v3', credentials=creds)
            about = service.about().get(fields='user').execute()
            user_email = about.get('user', {}).get('emailAddress', 'Unknown')
            print(f"✅ Authentication successful for: {user_email}")
            
            # Check if we can access the folder
            folder_query = "name='idea-database-attachments' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = service.files().list(q=folder_query, fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if folders:
                folder = folders[0]
                print(f"✅ Found existing folder: {folder['name']} (ID: {folder['id']})")
            else:
                print("ℹ️  Folder 'idea-database-attachments' not found - will be created on first upload")
                
        except Exception as e:
            print(f"❌ Failed to test Drive API: {e}")
            return False
    else:
        print("❌ Failed to obtain valid credentials")
        return False
    
    print("\n📝 Next steps:")
    print("1. The OAuth token has been generated and saved")
    print("2. Copy the credentials to Docker:")
    print("   ```")
    print("   # The files should already be in the right place")
    print(f"   ls -la {credentials_dir}/")
    print("   ```")
    print()
    print("3. Restart the email processor:")
    print("   ```")
    print("   docker-compose restart email_processor")
    print("   ```")
    print()
    print("4. Test the Drive upload:")
    print("   ```")
    print("   curl -X POST -F \"file=@test.txt\" http://localhost:3003/drive/upload")
    print("   ```")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
        exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        exit(1) 