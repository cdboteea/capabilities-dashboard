#!/usr/bin/env python3
"""
Comprehensive Database Cleanup Utility for Idea Database

⚠️ CRITICAL WARNING: TAXONOMY TABLES PROTECTION ⚠️
This utility AUTOMATICALLY PROTECTS taxonomy tables and will NEVER delete:
- taxonomy_node_types (node definitions for AI processing)
- taxonomy_edge_types (relationship definitions for knowledge graph)

These tables are essential for system operation and are intentionally excluded.

This utility provides options to clean up various database tables:
1. Clean all data (complete reset)
2. Clean specific tables
3. Clean by date range
4. Preview operations (dry-run)

Usage Examples:
    python3 cleanup_database.py --all                        # Reset all data (protects taxonomy)
    python3 cleanup_database.py --tables ideas,urls          # Clean specific tables
    python3 cleanup_database.py --attachments-only           # Clean only attachments
    python3 cleanup_database.py --dry-run --all              # Preview operations
    
SAFE TO USE: Taxonomy tables are protected and system will remain functional.
"""

import asyncio
import sys
import os
import argparse
import asyncpg
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

class DatabaseCleanup:
    """Comprehensive database cleanup utility"""
    
    def __init__(self, postgres_url: str, dry_run: bool = False):
        self.postgres_url = postgres_url
        self.dry_run = dry_run
        
        # Define table cleanup order (respects foreign key constraints)
        # ⚠️ PROTECTED TABLES (NEVER CLEANED): taxonomy_node_types, taxonomy_edge_types
        self.table_order = [
            'conversion_jobs',      # References attachments, urls
            'attachments',          # References ideas
            'urls',                 # References ideas
            'search_queries',       # Independent search queries
            'entities',             # Entity storage
            'ideas',                # Main table
            'processing_summary',   # Processing statistics
            'drive_config'          # Drive configuration
            # taxonomy_node_types - ⚠️ PROTECTED - Essential for AI processing
            # taxonomy_edge_types - ⚠️ PROTECTED - Essential for knowledge graph
        ]
        
        # Table descriptions for user-friendly output
        self.table_descriptions = {
            'ideas': 'Email ideas and content',
            'urls': 'Extracted URLs from emails',
            'attachments': 'File attachments metadata',
            'conversion_jobs': 'Background processing jobs',
            'processing_summary': 'Processing statistics',
            'search_queries': 'Search query history',
            'entities': 'Entity storage',
            'drive_config': 'Google Drive configuration'
        }
    
    async def get_table_stats(self) -> Dict[str, int]:
        """Get record counts for all tables"""
        stats = {}
        try:
            conn = await asyncpg.connect(self.postgres_url)
            
            for table in self.table_order:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM idea_database.{table}")
                stats[table] = count
            
            await conn.close()
            return stats
            
        except Exception as e:
            print(f"❌ Failed to get table stats: {e}")
            return {}
    
    async def cleanup_all_tables(self):
        """Clean up all database tables"""
        print("🧹 Cleaning up ALL database tables...")
        
        stats = await self.get_table_stats()
        total_records = sum(stats.values())
        
        if total_records == 0:
            print("✅ Database is already clean")
            return
        
        self._print_table_summary(stats)
        
        if not self.dry_run and not self._confirm_deletion(total_records, "database records"):
            print("❌ Cleanup cancelled")
            return
        
        deleted_counts = {}
        
        try:
            conn = await asyncpg.connect(self.postgres_url)
            
            if not self.dry_run:
                await conn.execute("BEGIN")
            
            # Delete in proper order (foreign key constraints)
            for table in self.table_order:
                count = stats.get(table, 0)
                if count > 0:
                    deleted_count = await self._cleanup_table(conn, table, count)
                    deleted_counts[table] = deleted_count
                else:
                    deleted_counts[table] = 0
            
            if not self.dry_run:
                await conn.execute("COMMIT")
                print("✅ All changes committed")
            
            await conn.close()
            
        except Exception as e:
            if not self.dry_run:
                try:
                    await conn.execute("ROLLBACK")
                    print("⚠️  Changes rolled back due to error")
                except:
                    pass
            print(f"❌ Database cleanup failed: {e}")
            return
        
        self._print_cleanup_results("ALL TABLES", deleted_counts)
    
    async def cleanup_specific_tables(self, table_names: List[str]):
        """Clean up specific tables"""
        # Validate table names
        valid_tables = []
        invalid_tables = []
        
        for table in table_names:
            if table in self.table_order:
                valid_tables.append(table)
            else:
                invalid_tables.append(table)
        
        if invalid_tables:
            print(f"❌ Invalid table names: {', '.join(invalid_tables)}")
            print(f"   Valid tables: {', '.join(self.table_order)}")
            return
        
        # Sort tables by dependency order
        ordered_tables = [t for t in self.table_order if t in valid_tables]
        
        print(f"🧹 Cleaning up specific tables: {', '.join(ordered_tables)}")
        
        stats = await self.get_table_stats()
        relevant_stats = {table: stats.get(table, 0) for table in ordered_tables}
        total_records = sum(relevant_stats.values())
        
        if total_records == 0:
            print("✅ Selected tables are already clean")
            return
        
        self._print_table_summary(relevant_stats)
        
        if not self.dry_run and not self._confirm_deletion(total_records, "records from selected tables"):
            print("❌ Cleanup cancelled")
            return
        
        deleted_counts = {}
        
        try:
            conn = await asyncpg.connect(self.postgres_url)
            
            if not self.dry_run:
                await conn.execute("BEGIN")
            
            for table in ordered_tables:
                count = relevant_stats.get(table, 0)
                if count > 0:
                    deleted_count = await self._cleanup_table(conn, table, count)
                    deleted_counts[table] = deleted_count
                else:
                    deleted_counts[table] = 0
            
            if not self.dry_run:
                await conn.execute("COMMIT")
                print("✅ All changes committed")
            
            await conn.close()
            
        except Exception as e:
            if not self.dry_run:
                try:
                    await conn.execute("ROLLBACK")
                    print("⚠️  Changes rolled back due to error")
                except:
                    pass
            print(f"❌ Table cleanup failed: {e}")
            return
        
        self._print_cleanup_results("SELECTED TABLES", deleted_counts)
    
    async def cleanup_by_date(self, days_old: int):
        """Clean up records older than specified days"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        print(f"🧹 Cleaning up records older than {days_old} days (before {cutoff_date.strftime('%Y-%m-%d')})")
        
        # Count records to be deleted
        stats = {}
        try:
            conn = await asyncpg.connect(self.postgres_url)
            
            # Ideas and related records by created_at
            ideas_count = await conn.fetchval(
                "SELECT COUNT(*) FROM idea_database.ideas WHERE created_at < $1",
                cutoff_date
            )
            stats['ideas'] = ideas_count
            
            # Get affected URLs and attachments
            if ideas_count > 0:
                urls_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM idea_database.urls u
                    JOIN idea_database.ideas i ON u.idea_id = i.id
                    WHERE i.created_at < $1
                """, cutoff_date)
                stats['urls'] = urls_count
                
                attachments_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM idea_database.attachments a
                    JOIN idea_database.ideas i ON a.idea_id = i.id
                    WHERE i.created_at < $1
                """, cutoff_date)
                stats['attachments'] = attachments_count
                
                jobs_count = await conn.fetchval("""
                    SELECT COUNT(*) FROM idea_database.conversion_jobs j
                    LEFT JOIN idea_database.attachments a ON j.attachment_id = a.id
                    LEFT JOIN idea_database.urls u ON j.url_id = u.id
                    LEFT JOIN idea_database.ideas i ON (a.idea_id = i.id OR u.idea_id = i.id)
                    WHERE i.created_at < $1
                """, cutoff_date)
                stats['conversion_jobs'] = jobs_count
            else:
                stats['urls'] = 0
                stats['attachments'] = 0
                stats['conversion_jobs'] = 0
            
            # Processing summary by created_at
            summaries_count = await conn.fetchval(
                "SELECT COUNT(*) FROM idea_database.processing_summary WHERE created_at < $1",
                cutoff_date
            )
            stats['processing_summary'] = summaries_count
            
            await conn.close()
            
        except Exception as e:
            print(f"❌ Failed to count old records: {e}")
            return
        
        total_records = sum(stats.values())
        
        if total_records == 0:
            print(f"✅ No records older than {days_old} days found")
            return
        
        self._print_table_summary(stats)
        
        if not self.dry_run and not self._confirm_deletion(total_records, f"records older than {days_old} days"):
            print("❌ Cleanup cancelled")
            return
        
        # TODO: Implement date-based deletion logic
        print("🚧 Date-based cleanup not yet implemented")
        print("   Use --all or --tables options for now")
    
    async def _cleanup_table(self, conn, table_name: str, expected_count: int) -> int:
        """Clean up a specific table"""
        description = self.table_descriptions.get(table_name, table_name)
        
        if self.dry_run:
            print(f"   🔄 [DRY RUN] Would delete {expected_count} records from {table_name} ({description})")
            return expected_count
        
        try:
            result = await conn.execute(f"DELETE FROM idea_database.{table_name}")
            # Extract number from result like "DELETE 5"
            deleted_count = int(result.split()[-1]) if result.split()[-1].isdigit() else 0
            print(f"   🗑️  Deleted {deleted_count} records from {table_name} ({description})")
            return deleted_count
            
        except Exception as e:
            print(f"   ❌ Failed to delete from {table_name}: {e}")
            return 0
    
    def _print_table_summary(self, stats: Dict[str, int]):
        """Print table statistics summary"""
        print(f"\n📊 Database Summary:")
        total = sum(stats.values())
        
        for table in self.table_order:
            if table in stats:
                count = stats[table]
                description = self.table_descriptions.get(table, table)
                print(f"   • {table}: {count} records ({description})")
        
        print(f"   • Total: {total} records")
    
    def _confirm_deletion(self, count: int, description: str) -> bool:
        """Ask for user confirmation"""
        response = input(f"\n⚠️  This will DELETE {count} {description}. Continue? (y/N): ")
        return response.lower() == 'y'
    
    def _print_cleanup_results(self, operation: str, deleted_counts: Dict[str, int]):
        """Print final cleanup results"""
        total_deleted = sum(deleted_counts.values())
        
        print(f"\n{'='*60}")
        print(f"🎉 {operation} Cleanup Complete!")
        print(f"   • Total records deleted: {total_deleted}")
        
        for table in self.table_order:
            if table in deleted_counts and deleted_counts[table] > 0:
                description = self.table_descriptions.get(table, table)
                print(f"   • {table}: {deleted_counts[table]} ({description})")
        
        print(f"{'='*60}")

async def main():
    """Main function with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Comprehensive Database Cleanup Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --all                        Reset entire database
  %(prog)s --tables ideas,urls          Clean specific tables
  %(prog)s --attachments-only           Clean only attachment-related data
  %(prog)s --older-than 30              Clean records older than 30 days
  %(prog)s --dry-run --all              Preview all operations
        """
    )
    
    # Operation modes (mutually exclusive)
    operations = parser.add_mutually_exclusive_group(required=True)
    operations.add_argument('--all', action='store_true',
                          help='Clean all database tables (complete reset)')
    operations.add_argument('--tables', type=str,
                          help='Clean specific tables (comma-separated)')
    operations.add_argument('--attachments-only', action='store_true',
                          help='Clean only attachment-related tables')
    operations.add_argument('--older-than', type=int,
                          help='Clean records older than N days')
    
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
    cleanup = DatabaseCleanup(postgres_url, dry_run=args.dry_run)
    
    print("🧹 Database Cleanup Utility")
    print("="*60)
    if args.dry_run:
        print("🔍 DRY RUN MODE - No actual deletions will be performed")
        print("="*60)
    
    # Execute requested operation
    try:
        if args.all:
            await cleanup.cleanup_all_tables()
        elif args.tables:
            table_names = [t.strip() for t in args.tables.split(',') if t.strip()]
            if not table_names:
                print("❌ No valid table names provided")
                sys.exit(1)
            await cleanup.cleanup_specific_tables(table_names)
        elif args.attachments_only:
            # Clean attachment-related tables
            await cleanup.cleanup_specific_tables(['conversion_jobs', 'attachments'])
        elif args.older_than:
            if args.older_than < 1:
                print("❌ Days must be a positive number")
                sys.exit(1)
            await cleanup.cleanup_by_date(args.older_than)
    except KeyboardInterrupt:
        print("\n❌ Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 