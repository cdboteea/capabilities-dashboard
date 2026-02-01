#!/bin/bash
# version-prompt.sh — Track prompt version changes with git
#
# Usage: ./version-prompt.sh [message]
# Commits all prompt changes with a descriptive message and updates changelog

set -euo pipefail

PROMPTS_DIR="$HOME/clawd/prompts"
CHANGELOG="$PROMPTS_DIR/history/changelog.yaml"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

cd "$HOME/clawd"

# Check for changes in prompts/
CHANGES=$(git diff --name-only -- prompts/ 2>/dev/null || true)
STAGED=$(git diff --cached --name-only -- prompts/ 2>/dev/null || true)
UNTRACKED=$(git ls-files --others --exclude-standard -- prompts/ 2>/dev/null || true)

ALL_CHANGES=$(echo -e "$CHANGES\n$STAGED\n$UNTRACKED" | sort -u | grep -v '^$' || true)

if [ -z "$ALL_CHANGES" ]; then
    echo "No prompt changes to version."
    exit 0
fi

echo -e "${GREEN}Changed prompts:${NC}"
echo "$ALL_CHANGES" | sed 's/^/  /'

# Generate commit message
MSG="${1:-"Update prompts: $(echo "$ALL_CHANGES" | wc -l | tr -d ' ') files"}"

# Append to changelog
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "" >> "$CHANGELOG"
echo "- date: \"$TIMESTAMP\"" >> "$CHANGELOG"
echo "  message: \"$MSG\"" >> "$CHANGELOG"
echo "  files:" >> "$CHANGELOG"
echo "$ALL_CHANGES" | while read -r f; do
    echo "    - \"$f\"" >> "$CHANGELOG"
done

# Stage and commit
git add prompts/
git commit -m "prompts: $MSG" --quiet 2>/dev/null || {
    echo -e "${YELLOW}Nothing to commit (already staged?)${NC}"
    exit 0
}

echo -e "${GREEN}✅ Versioned: $MSG${NC}"
echo "  Files: $(echo "$ALL_CHANGES" | wc -l | tr -d ' ')"
echo "  Commit: $(git rev-parse --short HEAD)"
