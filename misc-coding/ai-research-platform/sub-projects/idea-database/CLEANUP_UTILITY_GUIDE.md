# Attachment Cleanup Utility Guide

## Overview

The Idea Database includes a comprehensive attachment cleanup utility (`cleanup_attachments.py`) for managing files stored in Google Drive and database attachment records. This utility provides flexible options for cleaning up attachments based on various criteria.

## Features

- ✅ **Multiple cleanup modes**: all, database-only, drive-only, orphaned, specific IDs
- ✅ **Dry-run mode**: Preview operations without actual deletion
- ✅ **Safe deletion**: Proper handling of foreign key constraints
- ✅ **Orphan detection**: Find database records without corresponding Drive files
- ✅ **Flexible targeting**: Delete specific attachments by ID
- ✅ **Comprehensive reporting**: Detailed summaries and results

## Installation & Setup

### Prerequisites

The cleanup utility runs inside the email processor Docker container where all dependencies are available:

- Docker container: `idea_db_email_processor`
- Required environment variables: `POSTGRES_URL`
- Google Drive service account (for Drive operations)

### Quick Start

1. **Copy the script to the container:**
   ```bash
   docker cp cleanup_attachments.py idea_db_email_processor:/app/cleanup_attachments.py
   ```

2. **Run with dry-run mode first (recommended):**
   ```bash
   docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --dry-run --all
   ```

3. **Execute actual cleanup:**
   ```bash
   docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --all
   ```

## Usage Examples

### 1. Preview All Operations (Dry Run)

**Recommended first step** - see what would be deleted without actually deleting anything:

```bash
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --dry-run --all
```

**Output:**
```
🧹 Attachment Cleanup Utility
============================================================
🔍 DRY RUN MODE - No actual deletions will be performed
============================================================
✅ Google Drive client initialized
🧹 Cleaning up ALL attachments...

📊 Cleanup Summary (attachments):
   • Total records: 5
   • Files in Google Drive: 3
   • Local/database only: 2

📋 Files to be processed:
   • document1.pdf (Drive) - ID: abc-123
   • document2.xlsx (Local) - ID: def-456
   • image.png (Drive) - ID: ghi-789
```

### 2. Delete All Attachments

**Most common use case** - clean up everything for fresh testing:

```bash
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --all
```

This will:
- Delete all files from Google Drive
- Delete all attachment records from database
- Delete related conversion jobs

### 3. Database Only Cleanup

Clean up database records but keep files in Google Drive:

```bash
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --database-only
```

**Use case**: When you want to reprocess emails but keep the Drive files for reference.

### 4. Drive Only Cleanup

Delete files from Google Drive but keep database records:

```bash
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --drive-only
```

**Use case**: Free up Drive storage space while maintaining attachment metadata.

### 5. Orphaned Records Cleanup

Find and delete database records that don't have corresponding Drive files:

```bash
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --orphaned
```

**Use case**: Clean up after Drive files were manually deleted or lost.

### 6. Specific Attachments by ID

Delete specific attachments using their database IDs:

```bash
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --ids "abc-123,def-456,ghi-789"
```

**Finding attachment IDs:**
```bash
# Get attachment IDs from API
curl -X GET http://localhost:3003/ideas/IDEA_ID | jq '.attachments[].id'

# Or from database directly
docker exec idea_db_email_processor psql $POSTGRES_URL -c "SELECT id, filename FROM idea_database.attachments;"
```

## Command Line Options

| Option | Description | Required |
|--------|-------------|----------|
| `--all` | Delete all attachments (Drive + Database) | One of these |
| `--database-only` | Delete only database records | is required |
| `--drive-only` | Delete only Drive files | |
| `--orphaned` | Delete orphaned database records | |
| `--ids ID1,ID2,...` | Delete specific attachments by ID | |
| `--dry-run` | Preview without actual deletion | Optional |

## Safety Features

### 1. Confirmation Prompts

The utility asks for confirmation before performing deletions:

```
⚠️  This will DELETE 5 attachment(s). Continue? (y/N):
```

**Note**: Dry-run mode skips confirmation prompts.

### 2. Foreign Key Handling

The utility properly handles database foreign key constraints by deleting conversion jobs before attachment records.

### 3. Error Handling

- Graceful handling of missing Drive files
- Database connection error recovery
- Detailed error reporting

### 4. Dry Run Mode

Always test with `--dry-run` first to preview operations:

```bash
# Preview what would happen
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --dry-run --all

# Then execute if satisfied
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --all
```

## Output Interpretation

### Summary Format

```
📊 Cleanup Summary (attachments):
   • Total records: 5          # Database attachment records
   • Files in Google Drive: 3   # Records with drive_file_id
   • Local/database only: 2     # Records without drive_file_id
```

### Results Format

```
🎉 ALL ATTACHMENTS Cleanup Complete!
   • Google Drive files deleted: 3
   • Database records deleted: 5
```

## Integration with Testing Workflow

### Recommended Testing Sequence

1. **Clean everything:**
   ```bash
   docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --all
   ```

2. **Process emails fresh:**
   ```bash
   curl -X POST http://localhost:3003/process-emails -H "Content-Type: application/json" -d '{"force_reprocess": true, "max_emails": 10}'
   ```

3. **Verify results:**
   ```bash
   curl -X GET http://localhost:3003/conversion/stats
   ```

4. **Test reprocessing (no duplicates):**
   ```bash
   curl -X POST http://localhost:3003/process-emails -H "Content-Type: application/json" -d '{"force_reprocess": true, "max_emails": 10}'
   ```

### Cleanup Before Each Test

For consistent testing, always start with a clean state:

```bash
# Quick cleanup script for testing
echo "y" | docker exec -i idea_db_email_processor python3 /app/cleanup_attachments.py --all
```

## Troubleshooting

### Common Issues

1. **"POSTGRES_URL environment variable not found"**
   - Ensure you're running inside the Docker container
   - Check container is running: `docker compose ps`

2. **"Google Drive credentials not available"**
   - Drive operations will be skipped
   - Only database cleanup will work
   - Check service account file: `/app/config/drive_service_account.json`

3. **"Failed to delete file from Drive: File not found"**
   - File was already deleted or moved
   - This is normal and non-fatal
   - Database record will still be cleaned up

4. **Permission errors**
   - Ensure Docker container has proper permissions
   - Check service account has Drive API access

### Debug Mode

For troubleshooting, run with verbose output:

```bash
# Enable debug logging in container
docker exec -it idea_db_email_processor bash -c "
export LOG_LEVEL=DEBUG
python3 /app/cleanup_attachments.py --dry-run --all
"
```

## Best Practices

### 1. Always Start with Dry Run

```bash
# GOOD: Preview first
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --dry-run --all
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --all

# AVOID: Direct deletion without preview
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --all
```

### 2. Backup Before Major Cleanup

For production environments:

```bash
# Backup database
docker exec ai_platform_postgres pg_dump -U ai_user ai_platform > backup.sql

# Then cleanup
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --all
```

### 3. Use Specific Cleanup When Possible

Instead of cleaning everything, target specific issues:

```bash
# Clean only orphaned records
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --orphaned

# Clean specific problematic attachments
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --ids "problem-id-1,problem-id-2"
```

### 4. Monitor Storage Usage

After cleanup, verify storage stats:

```bash
curl -X GET http://localhost:3003/conversion/stats
curl -X GET http://localhost:3003/drive/sharing-status
```

## API Integration

The cleanup utility can be integrated into automated workflows:

```bash
#!/bin/bash
# Automated test cleanup script

echo "🧹 Starting automated cleanup..."

# Preview cleanup
docker exec -it idea_db_email_processor python3 /app/cleanup_attachments.py --dry-run --all

# Confirm and execute
echo "y" | docker exec -i idea_db_email_processor python3 /app/cleanup_attachments.py --all

echo "✅ Cleanup completed"
```

## Version History

- **v1.0**: Initial release with basic cleanup functionality
- **v1.1**: Added dry-run mode and orphan detection
- **v1.2**: Added specific ID targeting and improved error handling 