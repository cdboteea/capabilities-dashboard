#!/bin/bash
# deploy.sh — Deploy skills and scripts from development to production
# Usage: ./deploy.sh [skill|script|all] [item-name]

set -euo pipefail

DEV_ROOT="$HOME/projects"
PROD_ROOT="$HOME/clawd"
TIMESTAMP=$(date '+%Y%m%d-%H%M%S')

log() {
    echo "$(date '+%H:%M:%S') [DEPLOY] $*"
}

backup_production() {
    local type="$1"
    local name="$2"
    
    if [ -e "$PROD_ROOT/${type}s/$name" ]; then
        local backup_dir="$PROD_ROOT/backups/$TIMESTAMP"
        mkdir -p "$backup_dir"
        cp -r "$PROD_ROOT/${type}s/$name" "$backup_dir/"
        log "📦 Backed up existing $name to $backup_dir/"
    fi
}

deploy_skill() {
    local skill_name="$1"
    local source_path
    
    # Check if it exists in stable first, then development
    if [ -d "$DEV_ROOT/skills/stable/$skill_name" ]; then
        source_path="$DEV_ROOT/skills/stable/$skill_name"
        log "📋 Deploying STABLE skill: $skill_name"
    elif [ -d "$DEV_ROOT/skills/development/$skill_name" ]; then
        source_path="$DEV_ROOT/skills/development/$skill_name"
        log "⚠️  Deploying DEVELOPMENT skill: $skill_name (consider moving to stable first)"
    else
        log "❌ Skill '$skill_name' not found in development or stable"
        return 1
    fi
    
    backup_production "skill" "$skill_name"
    cp -r "$source_path" "$PROD_ROOT/skills/"
    log "✅ Deployed skill: $skill_name"
}

deploy_script() {
    local script_name="$1"
    local source_path
    
    # Check production folder first, then development
    if [ -f "$DEV_ROOT/scripts/production/$script_name" ]; then
        source_path="$DEV_ROOT/scripts/production/$script_name"
        log "📋 Deploying PRODUCTION script: $script_name"
    elif [ -f "$DEV_ROOT/scripts/development/$script_name" ]; then
        source_path="$DEV_ROOT/scripts/development/$script_name"
        log "⚠️  Deploying DEVELOPMENT script: $script_name (consider moving to production first)"
    else
        log "❌ Script '$script_name' not found in development or production"
        return 1
    fi
    
    backup_production "script" "${script_name%.*}"
    cp "$source_path" "$PROD_ROOT/scripts/"
    chmod +x "$PROD_ROOT/scripts/$script_name"
    log "✅ Deployed script: $script_name"
}

show_usage() {
    echo "Usage: $0 [command] [item]"
    echo ""
    echo "Commands:"
    echo "  skill <name>     Deploy specific skill"
    echo "  script <name>    Deploy specific script"
    echo "  list             List available items"
    echo "  status           Show deployment status"
    echo ""
    echo "Examples:"
    echo "  $0 skill chatgpt-app"
    echo "  $0 script auto-session-manager.sh"
    echo "  $0 list"
}

main() {
    case "${1:-}" in
        "skill")
            if [ -z "${2:-}" ]; then
                log "❌ Skill name required"
                show_usage
                exit 1
            fi
            deploy_skill "$2"
            ;;
        "script")
            if [ -z "${2:-}" ]; then
                log "❌ Script name required"
                show_usage
                exit 1
            fi
            deploy_script "$2"
            ;;
        "list")
            echo "📂 Available for deployment:"
            echo "SKILLS:" && ls -1 "$DEV_ROOT/skills/stable" 2>/dev/null | sed 's/^/  ✅ /' || echo "  (none)"
            echo "SCRIPTS:" && ls -1 "$DEV_ROOT/scripts/production" 2>/dev/null | sed 's/^/  ✅ /' || echo "  (none)"
            ;;
        "status")
            echo "📊 Production: $(ls -1 "$PROD_ROOT/skills" | wc -l | tr -d ' ') skills, $(ls -1 "$PROD_ROOT/scripts" | wc -l | tr -d ' ') scripts"
            echo "📊 Development: $(ls -1 "$DEV_ROOT/skills/stable" 2>/dev/null | wc -l | tr -d ' ') stable skills"
            ;;
        *)
            show_usage
            ;;
    esac
}

main "$@"