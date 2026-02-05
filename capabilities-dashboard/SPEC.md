# Capabilities Dashboard - Specification

## Overview
A web app to consolidate and visualize all AI assistant capabilities, integrations, automations, and tools developed over time. A living documentation hub that grows with the system.

## Goals
- **Single source of truth** for all capabilities
- **Easy discovery** of what's available
- **Clear documentation** with examples and syntax
- **Real-time view** of system state (cron jobs, active sessions)
- **Grows automatically** as new features are added

## Design Principles
- **Modern but simple** — clean, uncluttered
- **Soft edges** — rounded corners, gentle shadows
- **Ease of use** — intuitive navigation, search-first
- **Readable** — good typography, proper spacing
- **Dark mode friendly** — works in both themes

## Core Sections

### 1. Skills Library
- List all installed skills (`~/clawd/skills/`, system skills)
- View SKILL.md content rendered as markdown
- Syntax highlighting for code blocks
- Search/filter by name, description, category
- Show skill metadata (version, author, dependencies)

### 2. Workflows & Automations
- Desktop workflows (`~/clawd/workflows/`)
- YAML viewer with syntax highlighting
- Visual step-by-step breakdown
- Test workflow button (future)
- Group by app (ChatGPT, Gemini, Spotify, etc.)

### 3. Prompt Database
- Browse all prompts (`~/clawd/prompts/`)
- View/edit YAML definitions
- Variable substitution preview
- Prompt versioning history (if tracked)
- Categories: Gemini, Claude Code, Research, etc.

### 4. API Integrations
- Status dashboard for each integration:
  - Gemini API ✅/❌
  - Claude Code ✅/❌
  - WhatsApp ✅/❌
  - Google Workspace ✅/❌
- Auth status, last used, quota info
- Quick test buttons

### 5. Agents & Sub-agents
- List configured agents (`~/.openclaw/openclaw.json`)
- Model assignments
- Workspace locations
- Spawn history (recent sub-agent runs)
- Active sessions view

### 6. Cron Jobs & Schedules
- List all cron jobs (OpenClaw cron)
- Next run time, last run status
- Enable/disable toggle
- Job history/logs

### 7. Scripts & Tools
- Browse `~/clawd/scripts/`
- Syntax-highlighted code view
- Usage documentation (from comments)
- Run button (with confirmation)

### 8. Memory & Context
- View memory files (`~/clawd/memory/`)
- Session archives
- MEMORY.md viewer
- Context usage graph over time

### 9. Media & Recordings
- Browse `~/clawd/media/`
- Audio/video playback
- Transcription viewer
- Screenshot gallery

### 10. System Status
- OpenClaw version, uptime
- Current session context %
- Model being used
- Recent activity log

## Technical Stack

### Frontend
- **Framework**: React + TypeScript
- **Styling**: Tailwind CSS (easy customization)
- **Components**: shadcn/ui (modern, accessible)
- **Icons**: Lucide React
- **Markdown**: react-markdown with syntax highlighting
- **State**: React Query for data fetching

### Backend
- **Runtime**: Node.js / Bun
- **Framework**: Hono or Express (lightweight)
- **File access**: Direct filesystem reads
- **OpenClaw integration**: Gateway API calls
- **Real-time**: WebSocket for live updates (optional)

### Data Sources
```
~/clawd/
├── skills/           → Skills Library
├── workflows/        → Workflows & Automations
├── prompts/          → Prompt Database
├── scripts/          → Scripts & Tools
├── memory/           → Memory & Context
├── media/            → Media & Recordings
├── docs/             → Documentation
└── tasks.md          → Task tracking

~/.openclaw/
├── openclaw.json     → Agents config
└── agents/           → Agent workspaces

OpenClaw Gateway API:
├── sessions.list     → Active sessions
├── cron.list         → Cron jobs
└── status            → System status
```

## UI Wireframe

```
┌─────────────────────────────────────────────────────────────┐
│  🦞 Capabilities Dashboard              🔍 Search...    ⚙️  │
├─────────────┬───────────────────────────────────────────────┤
│             │                                               │
│  📚 Skills  │  Skills Library                              │
│  🔄 Workflows│  ─────────────────────────────────────────── │
│  💬 Prompts │                                               │
│  🔌 APIs    │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  🤖 Agents  │  │ gemini  │ │ github  │ │ weather │        │
│  ⏰ Cron    │  │ API,TTS │ │ PRs,CI  │ │ forecast│        │
│  📜 Scripts │  └─────────┘ └─────────┘ └─────────┘        │
│  🧠 Memory  │                                               │
│  🎬 Media   │  ┌─────────┐ ┌─────────┐ ┌─────────┐        │
│  📊 Status  │  │ imsg    │ │ oracle  │ │ peekaboo│        │
│             │  │ iMessage│ │ LLM CLI │ │ macOS UI│        │
│             │  └─────────┘ └─────────┘ └─────────┘        │
│             │                                               │
└─────────────┴───────────────────────────────────────────────┘
```

## File Structure

```
~/projects/capabilities-dashboard/
├── package.json
├── tsconfig.json
├── tailwind.config.js
├── vite.config.ts
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── SearchBar.tsx
│   │   ├── SkillCard.tsx
│   │   ├── WorkflowViewer.tsx
│   │   ├── PromptEditor.tsx
│   │   ├── CodeBlock.tsx
│   │   └── StatusBadge.tsx
│   ├── pages/
│   │   ├── Skills.tsx
│   │   ├── Workflows.tsx
│   │   ├── Prompts.tsx
│   │   ├── Integrations.tsx
│   │   ├── Agents.tsx
│   │   ├── Cron.tsx
│   │   ├── Scripts.tsx
│   │   ├── Memory.tsx
│   │   ├── Media.tsx
│   │   └── Status.tsx
│   ├── api/
│   │   ├── client.ts
│   │   └── endpoints.ts
│   └── styles/
│       └── globals.css
├── server/
│   ├── index.ts
│   ├── routes/
│   │   ├── skills.ts
│   │   ├── workflows.ts
│   │   ├── prompts.ts
│   │   └── ...
│   └── utils/
│       ├── fileReader.ts
│       └── openclawClient.ts
└── SPEC.md (this file)
```

## Implementation Phases

### Phase 1: Foundation (MVP)
- [ ] Project setup (Vite + React + Tailwind)
- [ ] Basic layout with sidebar navigation
- [ ] Skills page (read SKILL.md files)
- [ ] Scripts page (list and view)
- [ ] Simple backend for file reading

### Phase 2: Core Features
- [ ] Workflows viewer with YAML rendering
- [ ] Prompts browser
- [ ] Search functionality
- [ ] Dark/light mode toggle

### Phase 3: Live Data
- [ ] API integrations status
- [ ] Agents configuration viewer
- [ ] Cron jobs list (via OpenClaw API)
- [ ] System status dashboard

### Phase 4: Enhanced Features
- [ ] Memory browser
- [ ] Media gallery
- [ ] Real-time updates (WebSocket)
- [ ] Quick actions (run script, test workflow)

### Phase 5: Polish
- [ ] Mobile responsive
- [ ] Keyboard shortcuts
- [ ] Export/share capabilities
- [ ] Usage analytics

## Design Tokens

```css
/* Colors - Soft, modern palette */
--background: #fafafa (light) / #0a0a0a (dark)
--foreground: #171717 (light) / #fafafa (dark)
--card: #ffffff (light) / #171717 (dark)
--primary: #2563eb (blue-600)
--secondary: #64748b (slate-500)
--accent: #8b5cf6 (violet-500)
--success: #22c55e (green-500)
--warning: #f59e0b (amber-500)
--error: #ef4444 (red-500)

/* Borders - Soft edges */
--radius-sm: 0.375rem (6px)
--radius-md: 0.5rem (8px)
--radius-lg: 0.75rem (12px)
--radius-xl: 1rem (16px)

/* Shadows - Subtle */
--shadow-sm: 0 1px 2px rgba(0,0,0,0.05)
--shadow-md: 0 4px 6px rgba(0,0,0,0.07)
--shadow-lg: 0 10px 15px rgba(0,0,0,0.1)

/* Typography */
--font-sans: 'Inter', system-ui, sans-serif
--font-mono: 'JetBrains Mono', monospace
```

## API Endpoints (Backend)

```
GET  /api/skills              - List all skills
GET  /api/skills/:id          - Get skill details + SKILL.md
GET  /api/workflows           - List all workflows
GET  /api/workflows/:app/:id  - Get workflow YAML
GET  /api/prompts             - List all prompts
GET  /api/prompts/:category/:id - Get prompt YAML
GET  /api/scripts             - List all scripts
GET  /api/scripts/:id         - Get script content
GET  /api/memory              - List memory files
GET  /api/memory/:file        - Get memory file content
GET  /api/media               - List media files
GET  /api/cron                - List cron jobs (via OpenClaw)
GET  /api/agents              - Get agents config
GET  /api/status              - System status
POST /api/scripts/:id/run     - Run a script (protected)
```

## Notes

- Start simple, iterate
- Everything should be read-only initially (safer)
- Add write/execute capabilities carefully with confirmations
- Consider auth if exposed beyond localhost
- Keep bundle size small for fast loads

---

*Created: 2026-02-04*
*Status: Planning*
