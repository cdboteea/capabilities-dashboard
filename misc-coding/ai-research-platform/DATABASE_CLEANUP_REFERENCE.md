# Database Cleanup Reference

This document contains the canonical command for cleaning up (truncating) all tables in the `idea_database` schema for a full reset and reprocessing.

## ⚠️ CRITICAL WARNING: PROTECT TAXONOMY TABLES ⚠️

### 🚨 DO NOT DELETE THESE TABLES UNDER ANY CIRCUMSTANCES:
- **`taxonomy_node_types`** - Contains all node type definitions (idea, evidence, method, etc.)
- **`taxonomy_edge_types`** - Contains all relationship definitions (supports, contradicts, etc.)

### 🔥 CONSEQUENCES OF DELETING TAXONOMY TABLES:
- **COMPLETE SYSTEM FAILURE** - AI processor will crash
- **NO EMAIL CATEGORIZATION** - LLM-based categorization will fail
- **BROKEN KNOWLEDGE GRAPH** - No visualization or entity extraction
- **SETTINGS UI BROKEN** - Taxonomy management tab will fail
- **REQUIRES FULL SYSTEM RESET** - Manual restoration from YAML files needed

### ✅ WHAT THESE TABLES CONTAIN:
- **Dynamic taxonomy definitions** - User-editable via Settings > Taxonomy tab
- **9 modern node types** - idea, evidence, method, metric, person, organization, concept, technology, event
- **10 semantic edge types** - supports, contradicts, leads-to, part-of, is-a, etc.
- **Color schemes and metadata** - For knowledge graph visualization
- **System configuration** - Essential for all AI processing services

## When to Use
- When you need to fully reset the knowledge graph and all related data.
- Before reprocessing all emails from scratch.
- For troubleshooting or development resets.

## Safe Database Cleanup Command

**Run from your host terminal (NOT inside a container):**

```bash
docker exec -i ai_platform_postgres psql -U ai_user -d ai_platform -c "TRUNCATE idea_database.links, idea_database.entities, idea_database.urls, idea_database.ideas, idea_database.attachments, idea_database.categories, idea_database.senders RESTART IDENTITY CASCADE;"
```

### ✅ What This Command DOES Clean:
- **`ideas`** - All processed emails and content
- **`entities`** - Extracted entities from emails
- **`links`** - Knowledge graph connections between entities
- **`urls`** - Extracted URLs from emails
- **`attachments`** - File attachment metadata
- **`categories`** - Legacy category data (safe to delete)
- **`senders`** - Email sender information

### 🛡️ What This Command PROTECTS:
- **`taxonomy_node_types`** - ✅ PRESERVED (essential for system function)
- **`taxonomy_edge_types`** - ✅ PRESERVED (essential for system function)

## Alternative Cleanup Methods

### Python Cleanup Script (Recommended)
For more controlled cleanup with preview mode:

```bash
# Preview what will be deleted (safe)
docker exec -it idea_db_email_processor python3 /app/cleanup_database.py --dry-run --all

# Execute cleanup (after reviewing preview)
docker exec -it idea_db_email_processor python3 /app/cleanup_database.py --all
```

The Python script automatically protects taxonomy tables and provides detailed summaries.

## After Cleanup: Reprocess Emails

After cleaning the database, reprocess all emails:

```bash
curl -X POST http://localhost:3003/process-emails \
  -H "Content-Type: application/json" \
  -d '{"force_reprocess": true, "max_emails": 50}'
```

## Emergency Taxonomy Recovery

If taxonomy tables are accidentally deleted, restore them immediately:

```bash
# Navigate to idea-database directory
cd sub-projects/idea-database

# Run the taxonomy restoration script
python3 -c "
import subprocess
subprocess.run(['python3', 'migrations/008_update_modern_taxonomy.sql'], check=True)
print('✅ Taxonomy tables restored from default configuration')
"
```

## See Also
- This document is referenced in:
  - `README.md` (see "Database Maintenance" section)
  - `API_ENDPOINTS_REFERENCE.md` (see "Reset & Reprocessing" section)
  - `.cursor-memory/memory.json` (project context log)
- **`sub-projects/idea-database/CLEANUP_UTILITY_GUIDE.md`** - Attachment cleanup guide
- **`sub-projects/idea-database/cleanup_database.py`** - Advanced cleanup script

---
**💡 Tip:** If you ever need to clean up the database, search for "database clean up reference" or "DATABASE_CLEANUP_REFERENCE.md" in your project root. 

**🚨 Remember:** When in doubt about taxonomy tables, DON'T DELETE THEM. The system depends on them for all AI functionality. 