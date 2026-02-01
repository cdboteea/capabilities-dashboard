# Overnight Automation Monitoring Guide

## 🌅 Morning Review Commands

### Check Overnight Progress
```bash
# See all background sessions from overnight work
sessions_list kinds=isolated

# Check specific overnight skill sessions
sessions_list | grep overnight

# Review work done by specific skill agent
sessions_history sessionKey=agent:main:subagent:<session-id>
```

### Assess Improvement Results
```bash
# Re-assess all development skills to see improvements
for skill in $(ls ~/projects/skills/development/ 2>/dev/null); do
  echo "=== $skill ==="
  ~/projects/scripts/assess-skill.sh $skill | grep -E "(Score:|Status:)"
done

# Quick summary of promotion readiness
~/projects/scripts/spawn-skill-improvers.sh
```

### Promote Ready Skills
```bash
# For skills now scoring 80%+, promote to stable
mv ~/projects/skills/development/claude-app ~/projects/skills/stable/  # if ready
mv ~/projects/skills/development/gemini-web ~/projects/skills/stable/  # if ready
mv ~/projects/skills/development/gog ~/projects/skills/stable/        # if ready

# Deploy to production
~/projects/scripts/deploy.sh skill claude-app
~/projects/scripts/deploy.sh skill gemini-web  
~/projects/scripts/deploy.sh skill gog

# Check final production status
~/projects/scripts/deploy.sh status
```

## 📊 Monitoring Overnight Jobs

### Cron Job Status
```bash
# Check all scheduled jobs
cron action=list

# See when overnight job last ran and next run
# Look for: "Overnight Skill Development"
```

### Background Session Management
```bash
# List all active sub-agents
sessions_list maxConcurrent=15

# Check if overnight agents are still running
sessions_list | grep "overnight-"

# Review completed overnight work
ls ~/clawd/logs/overnight-*
```

## 🔄 Troubleshooting

### If Overnight Jobs Don't Run
```bash
# Check cron job is enabled
cron action=list | grep "Overnight Skill Development"

# Manual trigger for testing
~/projects/scripts/spawn-skill-improvers.sh

# Check logs for issues
ls -la ~/clawd/logs/
```

### If Skills Don't Improve
```bash
# Check what the overnight agent actually worked on
sessions_history sessionKey=<overnight-session-key>

# Re-assess to see what's still failing
~/projects/scripts/assess-skill.sh <skill-name>

# Manual improvement (if needed)
# Edit ~/projects/skills/development/<skill>/SKILL.md
# Add missing examples, dependencies, error handling
```

### If Sub-Agents Time Out
```bash
# Overnight agents have 2-hour timeout
# Check if they completed or hit time limit
sessions_list kinds=isolated | grep timeout

# Continue work manually if needed
cd ~/projects/skills/development/<skill>/
# Review and complete remaining improvements
```

## 📈 Expected Daily Results

### Week 1 Pattern
- **Day 1**: 3 skills improved (claude-app, gemini-web, gog)
- **Day 2**: All development work caught up, new experimental skills added
- **Day 3**: New skills from day 2 improved and promoted
- **Steady state**: Always wake up to production-ready skills

### Success Indicators
- **Morning assessment**: All development skills score 80%+
- **Promotion pipeline**: 3-6 new skills ready for stable/production daily  
- **Development queue**: Never accumulates more than 2-3 skills
- **Production growth**: Steady expansion of available skills

### Quality Metrics
- **Assessment scores**: Consistent improvement (+10-15% per skill per night)
- **Documentation quality**: Enhanced examples, dependencies, troubleshooting
- **Code quality**: Better error handling, input validation, structure
- **Security compliance**: No hardcoded secrets, proper boundaries

## 🎯 Long-term Benefits

### Productivity Gains
- **Zero development backlog** - work never accumulates
- **Continuous skill improvement** - steady progress every night
- **Quality assurance** - systematic enhancement following standards
- **Resource optimization** - sub-agents work during off-hours

### Development Velocity
- **Faster time-to-production** - skills ready next morning vs. days/weeks
- **Higher quality standards** - automated improvement to 80%+ criteria
- **Reduced manual work** - automation handles tedious improvement tasks  
- **Focus on innovation** - spend time creating, not fixing

This system transforms skill development from **manual day work** into **automated overnight completion** - you wake up every morning to improved, production-ready skills! 🌅✨