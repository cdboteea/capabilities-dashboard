# Capabilities Dashboard v2.0 - Improvement Plan

**Created:** 2026-02-04  
**Status:** Planning  
**GitHub Backup:** https://github.com/cdboteea/capabilities-dashboard (v1.0 committed)

---

## 🎨 1. Color Palette Overhaul (Priority: HIGH)

### Current Problem
- Using default grayscale palette (HSL 0 0% everywhere)
- Looks generic and plain
- No visual personality or brand identity

### Solution: Modern Soothing Palette
Inspired by nature-based design systems (forest/ocean tones):

```css
/* Light Mode - Soft sage/forest tones */
:root {
  --background: 150 20% 98%;          /* Off-white with green tint */
  --foreground: 150 25% 10%;          /* Deep forest green-black */
  --card: 150 15% 99%;                /* Slightly warmer white */
  --primary: 160 45% 40%;             /* Sage green */
  --primary-foreground: 0 0% 100%;
  --secondary: 150 15% 94%;           /* Light sage */
  --muted: 150 10% 93%;               /* Soft gray-green */
  --muted-foreground: 150 10% 40%;
  --accent: 175 40% 45%;              /* Teal accent */
  --accent-foreground: 0 0% 100%;
  --border: 150 15% 88%;
  --ring: 160 45% 40%;
  --destructive: 0 65% 55%;           /* Soft red */
}

/* Dark Mode - Deep forest tones */
.dark {
  --background: 160 20% 8%;           /* Deep forest */
  --foreground: 150 15% 95%;          /* Soft white */
  --card: 160 18% 11%;                /* Slightly lighter */
  --primary: 160 50% 50%;             /* Brighter sage */
  --secondary: 160 15% 15%;
  --muted: 160 15% 18%;
  --muted-foreground: 150 10% 60%;
  --accent: 175 45% 50%;              /* Teal accent */
  --border: 160 15% 18%;
}
```

### Visual Enhancements
- Increase `--radius` to 0.75rem for softer edges
- Add subtle gradient backgrounds on header/sidebar
- Add glass morphism effect on cards in dark mode
- Smooth transitions on hover/focus states

---

## 📚 2. Skills Tab - Click-to-View Feature (Priority: HIGH)

### Current Problem
- Skills display as static cards
- No way to see skill details or SKILL.md content
- No understanding of how skill works

### Solution: Skill Detail Modal
```tsx
// New component: SkillDetailModal.tsx
- Full SKILL.md content rendered as markdown
- "How it works" section explaining workflow:
  - Dependencies/requirements
  - Key commands/scripts
  - Integration points with OpenClaw
- Example usage snippets
- Quick actions: Open in editor, Copy command
```

### API Addition
```typescript
// New endpoint: GET /api/skills/:name
// Returns:
{
  name: string,
  skillMdContent: string,
  scripts: string[],        // List of scripts in skill folder
  dependencies: string[],   // From package.json or requirements
  examples: string[],       // Usage examples extracted
  relatedSkills: string[]   // Skills that often work together
}
```

---

## 📜 3. Workflows Tab - Horizontal Scrolling Fix (Priority: HIGH)

### Current Problem
- YAML content gets cut off on long lines
- Only vertical scroll works

### Solution
```css
/* Add to SyntaxHighlighter container */
.workflow-viewer pre {
  overflow-x: auto;
  white-space: pre;
  word-wrap: normal;
  max-width: 100%;
}

/* Or use Tailwind */
<div className="overflow-x-auto">
  <SyntaxHighlighter ... />
</div>
```

Also fix the `customStyle` removing the height constraints that might be causing issues.

---

## ⏰ 4. Cron Tab - OpenClaw Integration (Priority: HIGH)

### Current Problem
- API tries to call `http://localhost:8080/api/cron` which doesn't exist
- OpenClaw doesn't expose a REST API for cron
- Dashboard shows empty list despite 7 active cron jobs

### Solution: Shell-based API
```typescript
// server/index.ts - Updated cron endpoint
app.get('/api/cron', async (req, res) => {
  try {
    // Use OpenClaw CLI to get cron jobs
    const { stdout } = await execAsync('openclaw cron list --json')
    const jobs = JSON.parse(stdout)
    
    // Transform to dashboard format
    const formattedJobs = jobs.map(job => ({
      name: job.name,
      schedule: formatSchedule(job.schedule),
      nextRun: new Date(job.state.nextRunAtMs).toLocaleString(),
      lastRun: job.state.lastRunAtMs ? new Date(job.state.lastRunAtMs).toLocaleString() : null,
      lastStatus: job.state.lastStatus || 'pending',
      description: job.payload?.text?.substring(0, 100) + '...',
      enabled: job.enabled
    }))
    
    res.json(formattedJobs)
  } catch (error) {
    // Fallback to reading from config file
    // ...
  }
})
```

### UI Enhancements
- Show enabled/disabled toggle
- Run Now button (calls `openclaw cron run --id <id>`)
- View full payload details in modal
- Color-coded status badges

---

## 🗑️ 5. Media Tab - Delete Capability (Priority: MEDIUM)

### Current Problem
- Can view media files but cannot delete them
- No cleanup workflow for old screenshots/recordings

### Solution
```typescript
// New endpoint: DELETE /api/media/:subfolder/:filename
app.delete('/api/media/:subfolder/:filename', async (req, res) => {
  // Security checks (already have path validation)
  // Use trash instead of rm for safety
  const { stdout } = await execAsync(`trash "${filePath}"`)
  res.json({ success: true })
})
```

### UI Addition
- Delete button on file preview
- Confirmation modal: "Move to Trash?"
- Bulk select mode for multi-delete
- "Clear old files" quick action (files > 7 days in screenshots/operator)

---

## 📊 6. Status Tab - Real Data (Priority: HIGH)

### Current Problem
- All fields show "unknown"
- Not reading from actual OpenClaw gateway

### Solution
```typescript
// Use check-context.sh or gateway API
app.get('/api/status', async (req, res) => {
  try {
    // Get context info via script
    const { stdout: contextOut } = await execAsync('~/clawd/scripts/check-context.sh 2>/dev/null')
    // Parse: "📊 Context: 26745/200K tokens (13%)"
    
    // Get OpenClaw version
    const { stdout: versionOut } = await execAsync('openclaw --version')
    
    // Get session info via gateway API (if available)
    // Or read from gateway's internal state files
    
    // Calculate uptime from process start
    const { stdout: uptimeOut } = await execAsync('ps -o etime= -p $(pgrep -f "openclaw gateway")')
    
    res.json({
      openclaw: { version: versionOut.trim(), uptime: uptimeOut.trim() },
      session: { contextUsage: contextOut, model: 'claude-opus-4-5', contextPercent: 13 },
      // ...
    })
  } catch (error) { ... }
})
```

---

## 🔍 7. Additional UI Issues Discovered

### 7.1 Navigation Active State
- Current nav item needs clearer visual indicator
- Add left border accent or background highlight

### 7.2 Mobile Responsiveness 
- Sidebar should collapse to hamburger on mobile
- Cards should stack properly
- File viewer needs mobile-friendly layout

### 7.3 Loading States
- Add skeleton loaders instead of "Loading..."
- Consistent loading patterns across all pages

### 7.4 Empty States
- Better empty state designs with illustrations
- Helpful CTAs (e.g., "No cron jobs? Learn how to create one")

### 7.5 Toast Positioning
- Move toasts to top-right (less intrusive)
- Add auto-dismiss with progress indicator

### 7.6 Search Enhancement
- Add keyboard shortcut (Cmd+K) for quick search
- Search should include cron jobs, memory files
- Show recent searches

### 7.7 Dark Mode Toggle
- Add explicit toggle in header (not just system preference)
- Store preference in localStorage

---

## 📋 Implementation Phases

### Phase 1: Critical Fixes (1-2 hours)
1. ✅ Fix horizontal scrolling in Workflows
2. ✅ Connect Cron tab to OpenClaw
3. ✅ Fix Status tab data sources
4. ✅ Add delete to Media tab

### Phase 2: Design Overhaul (2-3 hours)
1. ✅ Implement new color palette
2. ✅ Update border radius and shadows
3. ✅ Add glass morphism effects
4. ✅ Improve transitions and animations

### Phase 3: Feature Additions (2-3 hours)
1. ✅ Skills detail modal with SKILL.md viewer
2. ✅ Workflow explanation generator
3. ✅ Cron job actions (run, toggle)
4. ✅ Bulk media operations

### Phase 4: Polish (1-2 hours)
1. ✅ Skeleton loaders
2. ✅ Empty state designs
3. ✅ Mobile responsive fixes
4. ✅ Dark mode toggle

---

## 🚀 Quick Wins (Can be done immediately)

1. **Workflows horizontal scroll** - 5 min fix
2. **Delete button in Media** - 15 min
3. **Color palette CSS** - 20 min
4. **Nav active state** - 10 min

---

## 📝 Notes

- All changes should maintain backward compatibility
- Test in both light and dark modes
- Ensure mobile responsiveness
- Keep bundle size reasonable (lazy load modals)
