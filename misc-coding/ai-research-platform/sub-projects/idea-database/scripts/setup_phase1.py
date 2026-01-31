#!/usr/bin/env python3
"""
Phase 1 Setup Script for Idea Database
Applies database migrations and validates the enhanced attachment storage setup
"""

import asyncio
import os
import sys
from pathlib import Path
import asyncpg
import structlog

# Add services to path
sys.path.append(str(Path(__file__).parent.parent / "services" / "email_processor"))

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

async def check_database_connection():
    """Check if database is accessible"""
    postgres_url = os.getenv('POSTGRES_URL', 'postgresql://ai_user:ai_platform_dev@localhost:5432/ai_platform')
    
    try:
        conn = await asyncpg.connect(postgres_url)
        await conn.execute("SELECT 1")
        await conn.close()
        logger.info("Database connection successful")
        return True
    except Exception as e:
        logger.error("Database connection failed", error=str(e))
        return False

async def apply_migration():
    """Apply Phase 1 database migration"""
    postgres_url = os.getenv('POSTGRES_URL', 'postgresql://ai_user:ai_platform_dev@localhost:5432/ai_platform')
    
    migration_sql = """
    -- Phase 1 Migration: Enhanced Attachment Storage
    -- Adds Google Drive integration and markdown content storage capabilities
    
    -- Add Google Drive integration columns to attachments table
    ALTER TABLE idea_database.attachments 
    ADD COLUMN IF NOT EXISTS drive_file_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS drive_file_url TEXT,
    ADD COLUMN IF NOT EXISTS markdown_content TEXT,
    ADD COLUMN IF NOT EXISTS conversion_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS conversion_error TEXT,
    ADD COLUMN IF NOT EXISTS storage_type VARCHAR(20) DEFAULT 'local';
    
    -- Add Google Drive integration columns to URLs table
    ALTER TABLE idea_database.urls
    ADD COLUMN IF NOT EXISTS markdown_content TEXT,
    ADD COLUMN IF NOT EXISTS processing_status VARCHAR(20) DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS processing_error TEXT,
    ADD COLUMN IF NOT EXISTS content_length INTEGER,
    ADD COLUMN IF NOT EXISTS processed_date TIMESTAMP WITH TIME ZONE;
    
    -- Create new table for file conversion jobs
    CREATE TABLE IF NOT EXISTS idea_database.conversion_jobs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        attachment_id UUID REFERENCES idea_database.attachments(id) ON DELETE CASCADE,
        url_id UUID REFERENCES idea_database.urls(id) ON DELETE CASCADE,
        job_type VARCHAR(20) NOT NULL,
        status VARCHAR(20) DEFAULT 'pending',
        priority INTEGER DEFAULT 5,
        retry_count INTEGER DEFAULT 0,
        error_message TEXT,
        started_at TIMESTAMP WITH TIME ZONE,
        completed_at TIMESTAMP WITH TIME ZONE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        CONSTRAINT conversion_jobs_single_target CHECK (
            (attachment_id IS NOT NULL AND url_id IS NULL) OR
            (attachment_id IS NULL AND url_id IS NOT NULL)
        )
    );
    
    -- Create Google Drive service configuration table
    CREATE TABLE IF NOT EXISTS idea_database.drive_config (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        service_account_email VARCHAR(255) NOT NULL,
        drive_folder_id VARCHAR(255) NOT NULL,
        folder_name VARCHAR(255) NOT NULL,
        quota_bytes BIGINT DEFAULT 15000000000,
        used_bytes BIGINT DEFAULT 0,
        is_active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    
    -- Add indexes for performance
    CREATE INDEX IF NOT EXISTS idx_attachments_drive_file_id ON idea_database.attachments(drive_file_id);
    CREATE INDEX IF NOT EXISTS idx_attachments_conversion_status ON idea_database.attachments(conversion_status);
    CREATE INDEX IF NOT EXISTS idx_attachments_storage_type ON idea_database.attachments(storage_type);
    
    CREATE INDEX IF NOT EXISTS idx_urls_processing_status ON idea_database.urls(processing_status);
    CREATE INDEX IF NOT EXISTS idx_urls_processed_date ON idea_database.urls(processed_date);
    
    CREATE INDEX IF NOT EXISTS idx_conversion_jobs_status ON idea_database.conversion_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_conversion_jobs_type ON idea_database.conversion_jobs(job_type);
    CREATE INDEX IF NOT EXISTS idx_conversion_jobs_priority ON idea_database.conversion_jobs(priority);
    CREATE INDEX IF NOT EXISTS idx_conversion_jobs_created_at ON idea_database.conversion_jobs(created_at);
    
    -- Full-text search indexes for markdown content
    CREATE INDEX IF NOT EXISTS idx_attachments_markdown_search ON idea_database.attachments USING gin(to_tsvector('english', markdown_content));
    CREATE INDEX IF NOT EXISTS idx_urls_markdown_search ON idea_database.urls USING gin(to_tsvector('english', markdown_content));
    
    -- Update processing summary to track new metrics
    ALTER TABLE idea_database.processing_summary
    ADD COLUMN IF NOT EXISTS attachments_processed INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS attachments_converted INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS urls_processed INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS drive_storage_used_mb INTEGER DEFAULT 0;
    """
    
    try:
        conn = await asyncpg.connect(postgres_url)
        await conn.execute(migration_sql)
        await conn.close()
        logger.info("Phase 1 migration applied successfully")
        return True
    except Exception as e:
        logger.error("Migration failed", error=str(e))
        return False

async def verify_installation():
    """Verify Phase 1 installation"""
    postgres_url = os.getenv('POSTGRES_URL', 'postgresql://ai_user:ai_platform_dev@localhost:5432/ai_platform')
    
    verification_queries = [
        ("Attachments table enhanced", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'attachments' AND column_name = 'drive_file_id'"),
        ("URLs table enhanced", "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'urls' AND column_name = 'markdown_content'"),
        ("Conversion jobs table", "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'conversion_jobs'"),
        ("Drive config table", "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'drive_config'"),
    ]
    
    try:
        conn = await asyncpg.connect(postgres_url)
        
        for description, query in verification_queries:
            result = await conn.fetchval(query)
            status = "✅ PASS" if result > 0 else "❌ FAIL"
            logger.info(f"{status} {description}")
        
        await conn.close()
        logger.info("Phase 1 verification completed")
        return True
    except Exception as e:
        logger.error("Verification failed", error=str(e))
        return False

async def check_dependencies():
    """Check if required Python packages are installed"""
    required_packages = [
        'PyMuPDF',
        'python-docx', 
        'python-pptx',
        'markdownify',
        'beautifulsoup4',
        'Pillow',
        'pytesseract',
        'cv2',
        'google-api-python-client',
        'google-auth'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'cv2':
                import cv2
            elif package == 'PyMuPDF':
                import fitz
            else:
                __import__(package.replace('-', '_'))
            logger.info(f"✅ {package} installed")
        except ImportError:
            missing_packages.append(package)
            logger.warning(f"❌ {package} not installed")
    
    if missing_packages:
        logger.error("Missing required packages", packages=missing_packages)
        logger.info("Run: pip install " + " ".join(missing_packages))
        return False
    
    logger.info("All dependencies satisfied")
    return True

async def setup_credentials_directories():
    """Create necessary credential directories"""
    base_dir = Path(__file__).parent.parent
    
    directories = [
        base_dir / "gmail_credentials",
        base_dir / "config"
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
        logger.info(f"✅ Directory ready: {directory}")
    
    # Create credential file templates if they don't exist
    drive_creds_example = base_dir / "config" / "drive_service_account.example.json"
    drive_creds_actual = base_dir / "gmail_credentials" / "drive_service_account.json"
    
    if not drive_creds_actual.exists() and drive_creds_example.exists():
        logger.warning(f"📋 Copy and configure: {drive_creds_example} -> {drive_creds_actual}")
    
    logger.info("Credentials directories setup completed")
    return True

async def main():
    """Main setup function"""
    logger.info("Starting Phase 1 Setup")
    
    # Check database connection
    if not await check_database_connection():
        logger.error("Setup aborted: Database not accessible")
        return False
    
    # Apply migration
    if not await apply_migration():
        logger.error("Setup aborted: Migration failed")
        return False
    
    # Verify installation
    if not await verify_installation():
        logger.error("Setup aborted: Verification failed")
        return False
    
    # Check dependencies
    if not await check_dependencies():
        logger.warning("Setup completed with dependency warnings")
    
    # Setup credential directories
    await setup_credentials_directories()
    
    logger.info("🎉 Phase 1 Setup completed successfully!")
    logger.info("Next steps:")
    logger.info("1. Configure Google Drive service account credentials")
    logger.info("2. Set up Gmail OAuth credentials")
    logger.info("3. Update docker-compose environment variables")
    logger.info("4. Restart email processor service")
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1) 