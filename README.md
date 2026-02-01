# OpenClaw Development Environment

## 🎯 Purpose
This folder serves as the **development environment** for OpenClaw skills, scripts, tools and experiments. It has Git/GitHub integration and Claude Code access for proper version control and collaboration.

## 📁 Structure

```
~/projects/                           # Git repo, Claude Code access
├── skills/
│   ├── stable/                       # Ready for production deployment
│   │   ├── ai-platforms/            # ✅ Stable
│   │   └── chatgpt-app/             # ✅ Stable
│   └── development/                  # Work in progress
│       ├── gkeep/                   # 🔬 Development
│       ├── google-workspace-mcp/    # 🔬 Development
│       └── ...
├── scripts/
│   ├── production/                   # Ready for deployment
│   │   ├── auto-session-manager.sh  # ✅ Production ready
│   │   └── archive-session.sh       # ✅ Production ready
│   ├── development/                  # Testing & iteration
│   │   ├── test-ai-platforms.sh     # 🔬 Development
│   │   └── ...
│   └── deploy.sh                     # 🚀 Deployment automation
├── tools/                            # Utility development
├── experiments/                      # Research & prototyping
└── README.md                         # This file
```

## 🚀 Development Workflow

### 1. Development Phase
```bash
# Work on new skills
cd ~/projects/skills/development/my-new-skill/
# Edit, test, iterate...

# Work on new scripts  
cd ~/projects/scripts/development/
# Create, test, debug...
```

### 2. Stabilization Phase
```bash
# Move to stable when ready for production
mv ~/projects/skills/development/my-new-skill/ ~/projects/skills/stable/

# Scripts go to production folder when ready
mv ~/projects/scripts/development/my-script.sh ~/projects/scripts/production/
```

### 3. Deployment Phase
```bash
# Deploy individual items
~/projects/scripts/deploy.sh skill my-new-skill
~/projects/scripts/deploy.sh script my-script.sh

# Or check what's available
~/projects/scripts/deploy.sh list
```

## 🔄 Production Environment
**~/clawd/** is the **production runtime** where OpenClaw actually runs. It only contains:
- **Deployed skills** that are tested and stable
- **Production scripts** that are essential for operation
- **No development/experimental code**

## 📊 Current Status

### Production Deployed
- **2 skills**: ai-platforms, chatgpt-app
- **3 scripts**: auto-session-manager.sh, archive-session.sh, check-context.sh

### Development Pipeline  
- **7 skills** in development (gkeep, google-workspace-mcp, etc.)
- **30+ scripts** in development for testing/iteration

## 🛠️ Common Commands

```bash
# Check deployment status
~/projects/scripts/deploy.sh status

# List available items
~/projects/scripts/deploy.sh list

# Deploy specific skill
~/projects/scripts/deploy.sh skill chatgpt-app

# Deploy specific script
~/projects/scripts/deploy.sh script auto-session-manager.sh

# Commit development changes
cd ~/projects
git add .
git commit -m "feat: new skill development"
git push
```

## 📝 Best Practices

- ✅ **All development work** happens in ~/projects
- ✅ **Version control** everything with Git
- ✅ **Test thoroughly** before moving to stable/production folders
- ✅ **Deploy selectively** - only stable, tested code goes to production
- ✅ **Use Claude Code** for development (has access to ~/projects)
- ✅ **Keep production minimal** - only essential, working code in ~/clawd

This setup gives you professional development workflow with proper separation between experimental work and production deployment!