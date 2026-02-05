# 🦞 Capabilities Dashboard

A modern web dashboard to explore and manage OpenClaw AI assistant capabilities.

![Dashboard Preview](docs/preview.png)

## Features

### 📚 Browse & Search
- **Skills Library** - View all installed skills with metadata
- **Scripts** - Browse and run scripts from ~/clawd/scripts/
- **Workflows** - View YAML workflow definitions with syntax highlighting
- **Prompts** - Browse prompt database by category

### 📊 Live Monitoring
- **API Integrations** - Status of Gemini, Claude Code, WhatsApp, Google Workspace
- **Agents** - View agent configurations and models
- **Cron Jobs** - Scheduled tasks with next run times
- **System Status** - Context usage, uptime, recent activity

### 🧠 Memory & Media
- **Memory Browser** - View daily notes and session archives
- **Media Gallery** - Browse recordings, screenshots, transcripts

### ⚡ Power Features
- **Global Search** - Cmd/Ctrl+K to search everything
- **Keyboard Shortcuts** - 1-9 for navigation, Cmd+/ for help
- **Dark/Light Mode** - Toggle with system preference detection
- **Export** - Download skills, workflows, prompts as JSON/YAML
- **Quick Actions** - Run scripts, copy content, refresh data

## Quick Start

```bash
cd ~/projects/capabilities-dashboard

# Install dependencies
npm install

# Start development server (frontend + backend)
npm run dev

# Open in browser
open http://localhost:5173
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 19 + TypeScript + Vite |
| Styling | Tailwind CSS + shadcn/ui patterns |
| Backend | Express 5 + TypeScript |
| Icons | Lucide React |
| Syntax Highlighting | react-syntax-highlighter |

## Project Structure

```
capabilities-dashboard/
├── src/
│   ├── pages/           # 10 page components
│   ├── components/      # Shared UI components
│   │   └── ui/          # Button, Card, Dialog, etc.
│   ├── hooks/           # Custom React hooks
│   ├── contexts/        # React contexts (Toast)
│   └── lib/             # Utilities
├── server/
│   └── index.ts         # Express API server
├── SPEC.md              # Original specification
├── QUALITY_REVIEW.md    # Quality assessment
└── README.md            # This file
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| GET /api/skills | List all skills |
| GET /api/scripts | List all scripts |
| POST /api/scripts/run | Run a script |
| GET /api/workflows | List workflows by app |
| GET /api/prompts | List prompts by category |
| GET /api/memory | List memory files |
| GET /api/memory/:file | Get file content |
| GET /api/media | List media files |
| GET /api/integrations | API status |
| GET /api/agents | Agent configs |
| GET /api/cron | Cron jobs |
| GET /api/status | System status |
| GET /api/search | Global search |

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Cmd/Ctrl+K | Focus search |
| Cmd/Ctrl+/ | Show shortcuts help |
| 1-9 | Navigate to sidebar item |
| Escape | Close modal/search |

## Development

```bash
# Run frontend only
npm run client

# Run backend only
npm run server

# Build for production
npm run build

# Preview production build
npm run preview
```

## Configuration

The dashboard reads from these directories:
- `~/clawd/skills/` - Skills library
- `~/clawd/scripts/` - Scripts
- `~/clawd/workflows/` - Workflow definitions
- `~/clawd/prompts/` - Prompt database
- `~/clawd/memory/` - Memory files
- `~/clawd/media/` - Media files
- `~/.openclaw/openclaw.json` - Agent configuration

## License

Private - OpenClaw Internal Tool

---

Built in 22 minutes with Claude Code 🤖
