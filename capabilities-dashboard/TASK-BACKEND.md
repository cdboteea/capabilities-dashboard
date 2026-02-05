# Backend Fixes Task

## Priority: HIGH | Deadline: ASAP

Fix the backend APIs so they return real data instead of "unknown" or empty arrays.

---

## 1. Fix Cron API (`server/index.ts`)

**Problem:** Currently tries to fetch from `http://localhost:8080/api/cron` which doesn't exist.

**Solution:** Use shell command to get cron data:
```typescript
app.get('/api/cron', async (req, res) => {
  try {
    // OpenClaw CLI returns JSON with --json flag (if available)
    // Otherwise parse the gateway config file
    const configPath = path.join(process.env.HOME || '', '.openclaw', 'openclaw.json')
    const configContent = await fs.readFile(configPath, 'utf-8')
    const config = JSON.parse(configContent)
    
    // Cron jobs are stored in config.cron.jobs or similar
    // Check the actual structure and extract jobs
    const jobs = config.cron?.jobs || config.cronJobs || []
    
    const formattedJobs = jobs.map((job: any) => ({
      id: job.id,
      name: job.name || 'Unnamed Job',
      schedule: formatSchedule(job.schedule),
      nextRun: job.state?.nextRunAtMs ? new Date(job.state.nextRunAtMs).toLocaleString() : 'Unknown',
      lastRun: job.state?.lastRunAtMs ? new Date(job.state.lastRunAtMs).toLocaleString() : null,
      lastStatus: job.state?.lastStatus || 'pending',
      description: job.payload?.text?.substring(0, 150) || job.description || '',
      enabled: job.enabled !== false
    }))
    
    res.json(formattedJobs)
  } catch (error) {
    console.error('Error fetching cron:', error)
    res.json([])
  }
})

// Helper to format schedule object
function formatSchedule(schedule: any): string {
  if (!schedule) return 'Unknown'
  if (schedule.kind === 'cron') return schedule.expr
  if (schedule.kind === 'every') return `Every ${Math.round(schedule.everyMs / 60000)} min`
  if (schedule.kind === 'at') return `At ${new Date(schedule.atMs).toLocaleString()}`
  return JSON.stringify(schedule)
}
```

---

## 2. Fix Status API (`server/index.ts`)

**Problem:** Returns "unknown" for all fields. Not reading real data.

**Solution:** Use shell commands to get real metrics:
```typescript
app.get('/api/status', async (req, res) => {
  try {
    const status: any = {
      openclaw: { version: 'unknown', uptime: 'unknown' },
      session: { contextUsage: 'unknown', model: 'unknown', contextPercent: 0 },
      activity: { summary: 'No recent activity', recent: [] },
      timestamp: new Date().toISOString()
    }

    // Get OpenClaw version
    try {
      const { stdout } = await execAsync('openclaw --version 2>/dev/null || echo "unknown"')
      status.openclaw.version = stdout.trim() || 'unknown'
    } catch {}

    // Get context usage via check-context.sh
    try {
      const { stdout } = await execAsync('~/clawd/scripts/check-context.sh 2>/dev/null | head -1')
      // Parse: "📊 Context: 26745/200K tokens (13%)"
      const match = stdout.match(/(\d+)\/(\d+)K tokens \((\d+)%\)/)
      if (match) {
        status.session.contextUsage = `${match[1]}/${match[2]}K tokens`
        status.session.contextPercent = parseInt(match[3])
      }
    } catch {}

    // Get uptime from gateway process
    try {
      const { stdout } = await execAsync('ps -o etime= -p $(pgrep -f "openclaw" | head -1) 2>/dev/null')
      status.openclaw.uptime = stdout.trim() || 'unknown'
    } catch {}

    // Get model from environment or config
    status.session.model = process.env.OPENCLAW_MODEL || 'claude-opus-4-5'

    // Keep existing activity logic (reading from memory files)
    // ... (existing code for activity)

    res.json(status)
  } catch (error) {
    console.error('Error fetching status:', error)
    res.status(500).json({ error: 'Failed to fetch status' })
  }
})
```

---

## 3. Add Media Delete API (`server/index.ts`)

**Problem:** No way to delete media files from the UI.

**Solution:** Add DELETE endpoint:
```typescript
app.delete('/api/media/:subfolder/:filename', async (req, res) => {
  try {
    const { subfolder, filename } = req.params
    const mediaPath = path.join(process.env.HOME || '', 'clawd', 'media', subfolder, filename)

    // Security check
    const resolvedPath = path.resolve(mediaPath)
    const resolvedMediaBase = path.resolve(path.join(process.env.HOME || '', 'clawd', 'media'))
    if (!resolvedPath.startsWith(resolvedMediaBase)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    // Check if file exists
    await fs.access(mediaPath)

    // Use trash command for safety (recoverable delete)
    try {
      await execAsync(`trash "${mediaPath}"`)
    } catch {
      // Fallback to unlink if trash not available
      await fs.unlink(mediaPath)
    }

    res.json({ success: true, message: 'File moved to trash' })
  } catch (error: any) {
    console.error('Error deleting media file:', error)
    if (error.code === 'ENOENT') {
      return res.status(404).json({ error: 'File not found' })
    }
    res.status(500).json({ error: 'Failed to delete file' })
  }
})
```

---

## 4. Add Skill Detail API (`server/index.ts`)

**Problem:** No endpoint to get full SKILL.md content.

**Solution:**
```typescript
app.get('/api/skills/:name', async (req, res) => {
  try {
    const { name } = req.params
    const skillPath = path.join(process.env.HOME || '', 'clawd', 'skills', name)
    
    // Security check
    const resolvedPath = path.resolve(skillPath)
    const resolvedSkillsBase = path.resolve(path.join(process.env.HOME || '', 'clawd', 'skills'))
    if (!resolvedPath.startsWith(resolvedSkillsBase)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    const skillMdPath = path.join(skillPath, 'SKILL.md')
    const content = await fs.readFile(skillMdPath, 'utf-8')
    
    // Get list of files in skill directory
    const entries = await fs.readdir(skillPath, { withFileTypes: true })
    const files = entries.filter(e => e.isFile()).map(e => e.name)
    const scripts = files.filter(f => f.endsWith('.sh') || f.endsWith('.py') || f.endsWith('.js'))
    
    res.json({
      name,
      content,
      files,
      scripts,
      path: skillPath
    })
  } catch (error: any) {
    console.error('Error fetching skill:', error)
    if (error.code === 'ENOENT') {
      return res.status(404).json({ error: 'Skill not found' })
    }
    res.status(500).json({ error: 'Failed to fetch skill' })
  }
})
```

---

## Testing

After implementation, verify:
1. `curl http://localhost:3001/api/cron` returns actual cron jobs (should be 7+)
2. `curl http://localhost:3001/api/status` returns real version, uptime, context %
3. `curl -X DELETE http://localhost:3001/api/media/screenshots/test.png` works
4. `curl http://localhost:3001/api/skills/gemini` returns SKILL.md content

---

## Files to Modify
- `server/index.ts` - All API changes go here
