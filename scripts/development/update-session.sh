#!/bin/bash
# update-session.sh — Update research session in database
# Usage: ./update-session.sh session_id field_name new_value

set -euo pipefail

SESSION_ID="$1"
FIELD_NAME="$2"
NEW_VALUE="$3"

DB_FILE="$HOME/clawd/comparative-research/database/sessions.yaml"

if [ ! -f "$DB_FILE" ]; then
    echo "❌ Sessions database not found: $DB_FILE"
    exit 1
fi

echo "📊 Updating session: $SESSION_ID"
echo "Field: $FIELD_NAME"
echo "New Value: $NEW_VALUE"

# Create backup
cp "$DB_FILE" "$DB_FILE.backup"

# Update using Python for reliable YAML handling
python3 - << EOF
import yaml
import sys

try:
    with open('$DB_FILE', 'r') as f:
        data = yaml.safe_load(f)
    
    sessions = data.get('sessions', [])
    session_found = False
    
    for session in sessions:
        if session.get('id') == '$SESSION_ID':
            session_found = True
            
            # Handle different field types
            field_name = '$FIELD_NAME'
            new_value = '$NEW_VALUE'
            
            if field_name in ['total_duration_minutes']:
                session[field_name] = int(new_value)
            elif field_name in ['platforms_attempted', 'platforms_successful']:
                # Handle arrays - expect JSON-like format
                import json
                session[field_name] = json.loads(new_value)
            else:
                session[field_name] = new_value
            
            print(f"✅ Updated {field_name} for session {session['id']}")
            break
    
    if not session_found:
        print(f"❌ Session not found: $SESSION_ID")
        sys.exit(1)
    
    # Write back to file
    with open('$DB_FILE', 'w') as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
    print(f"💾 Database updated: $DB_FILE")
    
except Exception as e:
    print(f"❌ Error updating session: {e}")
    sys.exit(1)
EOF