#!/bin/bash
# version-manager.sh — Professional version control for skill development
# Implements copy-on-promotion, version tracking, and rollback capabilities

set -euo pipefail

DEV_ROOT="$HOME/projects"
PROD_ROOT="$HOME/clawd"

# Utility functions
log() {
    echo "$(date '+%H:%M:%S') [VERSION] $*"
}

get_next_version() {
    local skill_dir="$1"
    local versions_file="$skill_dir/versions.json"
    
    if [ ! -f "$versions_file" ]; then
        echo "v1.0"
        return
    fi
    
    # Extract latest version number and increment
    local latest=$(jq -r '.currentVersion' "$versions_file" 2>/dev/null || echo "v1.0")
    local major=$(echo "$latest" | cut -d'v' -f2 | cut -d'.' -f1)
    local minor=$(echo "$latest" | cut -d'v' -f2 | cut -d'.' -f2)
    
    echo "v$major.$((minor + 1))"
}

assess_skill_score() {
    local skill_name="$1"
    
    if [ -x "$DEV_ROOT/scripts/assess-skill.sh" ]; then
        local assessment_output
        assessment_output=$("$DEV_ROOT/scripts/assess-skill.sh" "$skill_name" 2>/dev/null || echo "Assessment failed")
        local score_line=$(echo "$assessment_output" | grep "Score:" || echo "Score: 0/0 (0%)")
        echo "$score_line" | grep -o '[0-9]\+' | head -1 || echo "0"
    else
        echo "0"
    fi
}

convert_skill_to_versioned() {
    local skill_name="$1"
    local dev_skill_dir="$DEV_ROOT/skills/development/$skill_name"
    
    log "🔄 Converting $skill_name to versioned development..."
    
    if [ ! -d "$dev_skill_dir" ]; then
        log "❌ Skill not found: $skill_name"
        return 1
    fi
    
    # Check if already versioned
    if [ -d "$dev_skill_dir/v1.0" ]; then
        log "✅ $skill_name already versioned"
        return 0
    fi
    
    # Create v1.0 from current content
    local temp_dir=$(mktemp -d)
    cp -r "$dev_skill_dir"/* "$temp_dir/" 2>/dev/null || true
    
    # Clear original directory
    rm -rf "$dev_skill_dir"/*
    
    # Create v1.0 and current structure
    mkdir -p "$dev_skill_dir/v1.0"
    cp -r "$temp_dir"/* "$dev_skill_dir/v1.0/"
    
    # Create current symlink
    ln -sf v1.0 "$dev_skill_dir/current"
    
    # Initialize version metadata
    local assessment_score=$(assess_skill_score "$skill_name" || echo "0")
    cat > "$dev_skill_dir/versions.json" << EOF
{
  "skill": "$skill_name",
  "currentVersion": "v1.0",
  "productionVersion": null,
  "versions": {
    "v1.0": {
      "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
      "assessmentScore": $assessment_score,
      "status": "development",
      "changelog": "Converted to versioned development"
    }
  }
}
EOF
    
    rm -rf "$temp_dir"
    log "✅ $skill_name converted to versioned format"
}

promote_to_production() {
    local skill_name="$1"
    local dev_skill_dir="$DEV_ROOT/skills/development/$skill_name"
    local prod_skill_dir="$PROD_ROOT/skills/$skill_name"
    
    log "🚀 Promoting $skill_name to production..."
    
    # Ensure skill is versioned
    convert_skill_to_versioned "$skill_name"
    
    # Get current development version
    local current_version=$(jq -r '.currentVersion' "$dev_skill_dir/versions.json")
    local current_dir="$dev_skill_dir/$current_version"
    
    if [ ! -d "$current_dir" ]; then
        log "❌ Development version $current_version not found"
        return 1
    fi
    
    # Create production directory structure
    mkdir -p "$prod_skill_dir"
    
    # Deploy current development version to production
    cp -r "$current_dir" "$prod_skill_dir/$current_version"
    
    # Update production symlink
    ln -sf "$current_version" "$prod_skill_dir/current"
    
    # Update development metadata to reflect production deployment
    jq --arg ver "$current_version" \
       '.productionVersion = $ver | .versions[$ver].status = "production"' \
       "$dev_skill_dir/versions.json" > "${dev_skill_dir}/versions.json.tmp" && \
       mv "${dev_skill_dir}/versions.json.tmp" "$dev_skill_dir/versions.json"
    
    log "✅ $skill_name $current_version deployed to production"
}

show_usage() {
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  convert <skill-name>              Convert skill to versioned development"
    echo "  promote <skill-name>              Promote current development to production"
    echo "  compare <skill-name>              Compare development vs production"
    echo "  list [skill-name]                 List versions for skill(s)"
}

main() {
    case "${1:-}" in
        "convert")
            convert_skill_to_versioned "$2"
            ;;
        "promote") 
            promote_to_production "$2"
            ;;
        "compare")
            local skill_name="$2"
            local dev_skill_dir="$DEV_ROOT/skills/development/$skill_name"
            
            echo "📊 **Version Comparison: $skill_name**"
            echo ""
            
            if [ -f "$dev_skill_dir/versions.json" ]; then
                local dev_version=$(jq -r '.currentVersion' "$dev_skill_dir/versions.json")
                local dev_score=$(jq -r ".versions[\"$dev_version\"].assessmentScore" "$dev_skill_dir/versions.json")
                echo "🔬 **Development**: $dev_version (${dev_score}%)"
                
                local prod_version=$(jq -r '.productionVersion' "$dev_skill_dir/versions.json")
                if [ "$prod_version" != "null" ]; then
                    local prod_score=$(jq -r ".versions[\"$prod_version\"].assessmentScore" "$dev_skill_dir/versions.json")
                    echo "🏭 **Production**: $prod_version (${prod_score}%)"
                    
                    local improvement=$((dev_score - prod_score))
                    if [ "$improvement" -ge 5 ]; then
                        echo "🚀 **Ready for update**: +${improvement}% improvement"
                    else
                        echo "⏳ **Continue development**: +${improvement}% (need +5%)"
                    fi
                else
                    echo "🏭 **Production**: Not deployed"
                    if [ "$dev_score" -ge 80 ]; then
                        echo "🚀 **Ready for deployment**"
                    else
                        echo "🔧 **Needs development**"
                    fi
                fi
            else
                echo "❌ Not versioned"
            fi
            ;;
        "list")
            echo "📋 **Versioned Skills:**"
            for skill_dir in "$DEV_ROOT/skills/development"/*; do
                if [ -d "$skill_dir" ] && [ -f "$skill_dir/versions.json" ]; then
                    local skill_name=$(basename "$skill_dir")
                    local current_ver=$(jq -r '.currentVersion' "$skill_dir/versions.json")
                    local prod_ver=$(jq -r '.productionVersion' "$skill_dir/versions.json")
                    echo "  📦 $skill_name: dev=$current_ver, prod=${prod_ver:-none}"
                fi
            done
            ;;
        *)
            show_usage
            ;;
    esac
}

main "$@"