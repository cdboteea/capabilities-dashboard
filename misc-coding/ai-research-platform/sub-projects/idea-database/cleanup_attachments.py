#!/usr/bin/env python3
"""
Comprehensive Attachment Cleanup Utility for Idea Database

This utility provides multiple cleanup options:
1. Delete all attachments (Drive + Database)
2. Delete specific attachments by ID
3. Delete only Drive files (keep database records)
4. Delete only database records (keep Drive files)
5. Cleanup orphaned records (database records without Drive files)

Usage Examples:
    python3 cleanup_attachments.py --all                    # Delete everything
    python3 cleanup_attachments.py --database-only          # Clean database only
    python3 cleanup_attachments.py --drive-only             # Clean Drive only
    python3 cleanup_attachments.py --orphaned               # Clean orphaned records
    python3 cleanup_attachments.py --ids id1,id2,id3        # Delete specific IDs
    python3 cleanup_attachments.py --dry-run --all          # Preview without deleting
"""

import asyncio
import sys
import os
import argparse
import asyncpg
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add the services source directory to Python path
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(script_dir, 'services/email_processor/src')
if not os.path.exists(src_dir):
    # Running inside container
    src_dir = '/app/src'
sys.path.append(src_dir)

from drive_client import DriveClient

class AttachmentCleanup:
    """Comprehensive attachment cleanup utility"""
    
    def __init__(self, postgres_url: str, dry_run: bool = False):
        self.postgres_url = postgres_url
        self.dry_run = dry_run
        self.drive_client = None
        self._init_drive_client()
    
    def _init_drive_client(self):
        """Initialize Google Drive client"""
        try:
            config = {
                'drive': {
                    'service_account_path': '/app/config/drive_service_account.json',
                    'folder_name': 'idea-database-attachments'
                },
                'email': {
                    'intake_email': os.getenv('INTAKE_EMAIL', 'ideaseea@gmail.com')
                }
            }
            self.drive_client = DriveClient(config)
            if not self.drive_client.has_credentials():
                print("⚠️  Google Drive credentials not available")
                self.drive_client = None
            else:
                print("✅ Google Drive client initialized")
        except Exception as e:
            print(f"❌ Failed to initialize Drive client: {e}")
            self.drive_client = None
    
    async def get_all_attachments(self) -> List[Dict[str, Any]]:
        """Get all attachment records from database"""
        try:
            conn = await asyncpg.connect(self.postgres_url)
            records = await conn.fetch("""
                SELECT id, filename, drive_file_id, storage_type, file_size, created_at
                FROM idea_database.attachments
                ORDER BY created_at DESC
            """)
            await conn.close()
            return [dict(record) for record in records]
        except Exception as e:
            print(f"❌ Failed to fetch attachment records: {e}")
            return []
    
    async def get_attachments_by_ids(self, attachment_ids: List[str]) -> List[Dict[str, Any]]:
        """Get specific attachment records by IDs"""
        try:
            conn = await asyncpg.connect(self.postgres_url)
            # Create placeholder string for parameterized query
            placeholders = ','.join(f'${i+1}' for i in range(len(attachment_ids)))
            query = f"""
                SELECT id, filename, drive_file_id, storage_type, file_size, created_at
                FROM idea_database.attachments
                WHERE id IN ({placeholders})
                ORDER BY created_at DESC
            """
            records = await conn.fetch(query, *attachment_ids)
            await conn.close()
            return [dict(record) for record in records]
        except Exception as e:
            print(f"❌ Failed to fetch specific attachment records: {e}")
            return []
    
    async def get_orphaned_attachments(self) -> List[Dict[str, Any]]:
        """Get database records that don't have corresponding Drive files"""
        attachments = await self.get_all_attachments()
        orphaned = []
        
        if not self.drive_client:
            print("⚠️  Cannot check for orphaned records without Drive client")
            return orphaned
        
        print("🔍 Checking for orphaned records...")
        for attachment in attachments:
            drive_file_id = attachment.get('drive_file_id')
            if drive_file_id:
                # Check if file exists in Drive
                metadata = await self.drive_client.get_file_metadata(drive_file_id)
                if not metadata:
                    orphaned.append(attachment)
                    print(f"   🔍 Found orphaned: {attachment['filename']}")
        
        return orphaned
    
    async def delete_drive_files(self, attachments: List[Dict[str, Any]]) -> int:
        """Delete files from Google Drive"""
        if not self.drive_client:
            print("⚠️  Cannot delete Drive files - no Drive client")
            return 0
        
        deleted_count = 0
        drive_files = [a for a in attachments if a.get('drive_file_id')]
        
        if not drive_files:
            print("ℹ️  No Drive files to delete")
            return 0
        
        print(f"🔄 {'[DRY RUN] ' if self.dry_run else ''}Deleting {len(drive_files)} files from Google Drive...")
        
        for attachment in drive_files:
            drive_file_id = attachment['drive_file_id']
            filename = attachment['filename']
            
            if self.dry_run:
                print(f"   🔄 [DRY RUN] Would delete: {filename} (ID: {drive_file_id})")
                deleted_count += 1
            else:
                try:
                    success = await self.drive_client.delete_file(drive_file_id)
                    if success:
                        deleted_count += 1
                        print(f"   ✅ Deleted: {filename} (ID: {drive_file_id})")
                    else:
                        print(f"   ❌ Failed to delete: {filename} (ID: {drive_file_id})")
                except Exception as e:
                    print(f"   ❌ Error deleting {filename}: {e}")
        
        return deleted_count
    
    async def delete_database_records(self, attachments: List[Dict[str, Any]]) -> int:
        """Delete attachment records from database"""
        if not attachments:
            print("ℹ️  No database records to delete")
            return 0
        
        try:
            conn = await asyncpg.connect(self.postgres_url)
            
            attachment_ids = [a['id'] for a in attachments]
            
            print(f"🔄 {'[DRY RUN] ' if self.dry_run else ''}Deleting {len(attachment_ids)} database records...")
            
            if self.dry_run:
                for attachment in attachments:
                    print(f"   🔄 [DRY RUN] Would delete: {attachment['filename']} (ID: {attachment['id']})")
                await conn.close()
                return len(attachment_ids)
            
            # Delete conversion jobs first (foreign key constraint)
            placeholders = ','.join(f'${i+1}' for i in range(len(attachment_ids)))
            jobs_query = f"DELETE FROM idea_database.conversion_jobs WHERE attachment_id IN ({placeholders})"
            jobs_result = await conn.execute(jobs_query, *attachment_ids)
            print(f"🗑️  Deleted conversion jobs: {jobs_result}")
            
            # Delete attachment records
            attachment_query = f"DELETE FROM idea_database.attachments WHERE id IN ({placeholders})"
            attachment_result = await conn.execute(attachment_query, *attachment_ids)
            print(f"🗑️  Deleted attachment records: {attachment_result}")
            
            await conn.close()
            return len(attachment_ids)
            
        except Exception as e:
            print(f"❌ Database deletion failed: {e}")
            return 0
    
    async def cleanup_all(self):
        """Delete all attachments (Drive + Database)"""
        print("🧹 Cleaning up ALL attachments...")
        attachments = await self.get_all_attachments()
        
        if not attachments:
            print("✅ No attachments found")
            return
        
        self._print_summary(attachments)
        
        if not self.dry_run and not self._confirm_deletion(len(attachments)):
            print("❌ Cleanup cancelled")
            return
        
        # Delete from Drive
        drive_deleted = await self.delete_drive_files(attachments)
        
        # Delete from Database
        db_deleted = await self.delete_database_records(attachments)
        
        self._print_results("ALL ATTACHMENTS", drive_deleted, db_deleted)
    
    async def cleanup_drive_only(self):
        """Delete only Drive files (keep database records)"""
        print("🧹 Cleaning up Drive files only...")
        attachments = await self.get_all_attachments()
        drive_files = [a for a in attachments if a.get('drive_file_id')]
        
        if not drive_files:
            print("✅ No Drive files found")
            return
        
        self._print_summary(drive_files, "Drive files")
        
        if not self.dry_run and not self._confirm_deletion(len(drive_files)):
            print("❌ Cleanup cancelled")
            return
        
        drive_deleted = await self.delete_drive_files(drive_files)
        self._print_results("DRIVE FILES", drive_deleted, 0)
    
    async def cleanup_database_only(self):
        """Delete only database records (keep Drive files)"""
        print("🧹 Cleaning up database records only...")
        attachments = await self.get_all_attachments()
        
        if not attachments:
            print("✅ No database records found")
            return
        
        self._print_summary(attachments, "database records")
        
        if not self.dry_run and not self._confirm_deletion(len(attachments)):
            print("❌ Cleanup cancelled")
            return
        
        db_deleted = await self.delete_database_records(attachments)
        self._print_results("DATABASE RECORDS", 0, db_deleted)
    
    async def cleanup_orphaned(self):
        """Delete orphaned database records (no corresponding Drive file)"""
        print("🧹 Cleaning up orphaned database records...")
        orphaned = await self.get_orphaned_attachments()
        
        if not orphaned:
            print("✅ No orphaned records found")
            return
        
        self._print_summary(orphaned, "orphaned records")
        
        if not self.dry_run and not self._confirm_deletion(len(orphaned)):
            print("❌ Cleanup cancelled")
            return
        
        db_deleted = await self.delete_database_records(orphaned)
        self._print_results("ORPHANED RECORDS", 0, db_deleted)
    
    async def cleanup_specific(self, attachment_ids: List[str]):
        """Delete specific attachments by ID"""
        print(f"🧹 Cleaning up specific attachments: {', '.join(attachment_ids)}")
        attachments = await self.get_attachments_by_ids(attachment_ids)
        
        if not attachments:
            print("❌ No attachments found with the specified IDs")
            return
        
        found_ids = [a['id'] for a in attachments]
        missing_ids = set(attachment_ids) - set(found_ids)
        if missing_ids:
            print(f"⚠️  IDs not found: {', '.join(missing_ids)}")
        
        self._print_summary(attachments, f"specific attachments")
        
        if not self.dry_run and not self._confirm_deletion(len(attachments)):
            print("❌ Cleanup cancelled")
            return
        
        drive_deleted = await self.delete_drive_files(attachments)
        db_deleted = await self.delete_database_records(attachments)
        self._print_results("SPECIFIC ATTACHMENTS", drive_deleted, db_deleted)
    
    def _print_summary(self, attachments: List[Dict[str, Any]], description: str = "attachments"):
        """Print cleanup summary"""
        drive_files = [a for a in attachments if a.get('drive_file_id')]
        local_files = [a for a in attachments if not a.get('drive_file_id')]
        
        print(f"\n📊 Cleanup Summary ({description}):")
        print(f"   • Total records: {len(attachments)}")
        print(f"   • Files in Google Drive: {len(drive_files)}")
        print(f"   • Local/database only: {len(local_files)}")
        
        if len(attachments) <= 10:
            print(f"\n📋 Files to be {'processed' if self.dry_run else 'deleted'}:")
            for attachment in attachments:
                storage_type = "Drive" if attachment.get('drive_file_id') else "Local"
                print(f"   • {attachment['filename']} ({storage_type}) - ID: {attachment['id']}")
    
    def _confirm_deletion(self, count: int) -> bool:
        """Ask for user confirmation"""
        response = input(f"\n⚠️  This will DELETE {count} attachment(s). Continue? (y/N): ")
        return response.lower() == 'y'
    
    def _print_results(self, operation: str, drive_deleted: int, db_deleted: int):
        """Print final results"""
        print(f"\n{'='*60}")
        print(f"🎉 {operation} Cleanup Complete!")
        print(f"   • Google Drive files deleted: {drive_deleted}")
        print(f"   • Database records deleted: {db_deleted}")
        print(f"{'='*60}")

async def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Attachment Cleanup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                    Delete all attachments (Drive + Database)
  %(prog)s --database-only          Delete only database records
  %(prog)s --drive-only             Delete only Drive files
  %(prog)s --orphaned               Delete orphaned database records
  %(prog)s --ids id1,id2,id3        Delete specific attachments by ID
  %(prog)s --dry-run --all          Preview deletion without actually deleting
        """
    )
    
    # Operation modes (mutually exclusive)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument('--all', action='store_true',
                          help='Delete all attachments (Drive + Database)')
    operations.add_argument('--database-only', action='store_true',
                          help='Delete only database records (keep Drive files)')
    operations.add_argument('--drive-only', action='store_true',
                          help='Delete only Drive files (keep database records)')
    operations.add_argument('--orphaned', action='store_true',
                          help='Delete orphaned database records (no Drive file)')
    operations.add_argument('--ids', type=str,
                          help='Delete specific attachments by ID (comma-separated)')
    
    # Options
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview operations without actually deleting anything')
    
    args = parser.parse_args()
    
    # Get database URL
    postgres_url = os.getenv('POSTGRES_URL')
    if not postgres_url:
        print("❌ POSTGRES_URL environment variable not found")
        sys.exit(1)
    
    # Initialize cleanup utility
    cleanup = AttachmentCleanup(postgres_url, dry_run=args.dry_run)
    
    print("🧹 Attachment Cleanup Utility")
    print("="*60)
    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual deletions will be performed")
        print("="*60)
    
    # Execute requested operation
    try:
        if args.all:
            await cleanup.cleanup_all()
        elif args.database_only:
            await cleanup.cleanup_database_only()
        elif args.drive_only:
            await cleanup.cleanup_drive_only()
        elif args.orphaned:
            await cleanup.cleanup_orphaned()
        elif args.ids:
            attachment_ids = [id.strip() for id in args.ids.split(',') if id.strip()]
            if not attachment_ids:
                print("❌ No valid attachment IDs provided")
                sys.exit(1)
            await cleanup.cleanup_specific(attachment_ids)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 