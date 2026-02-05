import express from 'express'
import cors from 'cors'
import path from 'path'
import fs from 'fs/promises'
import { fileURLToPath } from 'url'
import { exec } from 'child_process'
import { promisify } from 'util'

const execAsync = promisify(exec)

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const app = express()
const PORT = process.env.PORT || 3001

app.use(cors())
app.use(express.json())

// Skills API endpoint
app.get('/api/skills', async (req, res) => {
  try {
    const skillsPath = path.join(process.env.HOME || '', 'clawd', 'skills')
    const entries = await fs.readdir(skillsPath, { withFileTypes: true })

    const skills = []

    for (const entry of entries) {
      if (entry.isDirectory()) {
        const skillPath = path.join(skillsPath, entry.name)
        const skill = {
          name: entry.name,
          path: skillPath,
          description: '',
          category: '',
          author: '',
          version: ''
        }

        // Try to read SKILL.md file for metadata
        try {
          const skillMdPath = path.join(skillPath, 'SKILL.md')
          const content = await fs.readFile(skillMdPath, 'utf-8')

          // Parse basic metadata from SKILL.md content
          const lines = content.split('\n')
          for (const line of lines) {
            if (line.startsWith('# ')) {
              skill.description = line.substring(2).trim()
            }
            if (line.includes('Category:')) {
              skill.category = line.split(':')[1]?.trim() || ''
            }
            if (line.includes('Author:')) {
              skill.author = line.split(':')[1]?.trim() || ''
            }
            if (line.includes('Version:')) {
              skill.version = line.split(':')[1]?.trim() || ''
            }
          }
        } catch {
          // SKILL.md doesn't exist or can't be read
          skill.description = `${entry.name.replace(/-/g, ' ')} skill`
        }

        skills.push(skill)
      }
    }

    res.json(skills)
  } catch (error) {
    console.error('Error fetching skills:', error)
    res.status(500).json({ error: 'Failed to fetch skills' })
  }
})

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

// Run script endpoint
app.post('/api/scripts/run', async (req, res) => {
  try {
    const { path: scriptPath } = req.body

    if (!scriptPath) {
      return res.status(400).json({ error: 'Script path is required' })
    }

    // Security check: ensure the path is within the scripts directory
    const scriptsDir = path.join(process.env.HOME || '', 'clawd', 'scripts')
    const resolvedPath = path.resolve(scriptPath)
    const resolvedScriptsDir = path.resolve(scriptsDir)

    if (!resolvedPath.startsWith(resolvedScriptsDir)) {
      return res.status(403).json({ error: 'Access denied: script must be in scripts directory' })
    }

    // Check if file exists and is executable
    try {
      await fs.access(scriptPath, fs.constants.X_OK)
    } catch {
      return res.status(403).json({ error: 'Script is not executable' })
    }

    // Execute the script with a timeout
    const { stdout, stderr } = await execAsync(scriptPath, {
      timeout: 30000, // 30 second timeout
      maxBuffer: 1024 * 1024 // 1MB max output
    })

    res.json({
      success: true,
      output: stdout || stderr || 'Script executed successfully (no output)',
    })
  } catch (error: any) {
    console.error('Error running script:', error)
    res.status(500).json({
      error: error.message || 'Failed to execute script',
      output: error.stdout || error.stderr || ''
    })
  }
})

// Scripts API endpoint
app.get('/api/scripts', async (req, res) => {
  try {
    const scriptsPath = path.join(process.env.HOME || '', 'clawd', 'scripts')
    const entries = await fs.readdir(scriptsPath, { withFileTypes: true })
    
    const scripts = []
    
    for (const entry of entries) {
      if (entry.isFile()) {
        const scriptPath = path.join(scriptsPath, entry.name)
        const stats = await fs.stat(scriptPath)
        
        const script = {
          name: entry.name,
          path: scriptPath,
          description: '',
          executable: false,
          size: `${Math.round(stats.size / 1024)} KB`,
          lastModified: stats.mtime.toLocaleDateString()
        }

        // Check if file is executable
        try {
          await fs.access(scriptPath, fs.constants.X_OK)
          script.executable = true
        } catch {
          script.executable = false
        }

        // Try to extract description from file comments
        try {
          const content = await fs.readFile(scriptPath, 'utf-8')
          const lines = content.split('\n').slice(0, 10) // Only check first 10 lines
          
          for (const line of lines) {
            const trimmed = line.trim()
            // Look for comment lines that might contain descriptions
            if (trimmed.startsWith('#') && trimmed.length > 2) {
              const comment = trimmed.substring(1).trim()
              if (!comment.startsWith('!') && !comment.startsWith('/') && comment.length > 10) {
                script.description = comment
                break
              }
            }
          }
        } catch {
          // Can't read file
        }

        if (!script.description) {
          script.description = `${entry.name} script`
        }

        scripts.push(script)
      }
    }

    res.json(scripts)
  } catch (error) {
    console.error('Error fetching scripts:', error)
    res.status(500).json({ error: 'Failed to fetch scripts' })
  }
})

// Workflows API endpoint
app.get('/api/workflows', async (req, res) => {
  try {
    const workflowsPath = path.join(process.env.HOME || '', 'clawd', 'workflows')
    const entries = await fs.readdir(workflowsPath, { withFileTypes: true })
    
    const workflows = []
    
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const appPath = path.join(workflowsPath, entry.name)
        const files = await fs.readdir(appPath, { withFileTypes: true })
        
        const workflowFiles = []
        
        for (const file of files) {
          if (file.isFile() && (file.name.endsWith('.yaml') || file.name.endsWith('.yml'))) {
            const filePath = path.join(appPath, file.name)
            try {
              const content = await fs.readFile(filePath, 'utf-8')
              workflowFiles.push({
                name: file.name,
                path: filePath,
                content: content,
                app: entry.name
              })
            } catch (error) {
              console.error(`Error reading workflow file ${filePath}:`, error)
            }
          }
        }
        
        if (workflowFiles.length > 0) {
          workflows.push({
            app: entry.name,
            files: workflowFiles
          })
        }
      }
    }

    res.json(workflows)
  } catch (error) {
    console.error('Error fetching workflows:', error)
    res.status(500).json({ error: 'Failed to fetch workflows' })
  }
})

// Prompts API endpoint
app.get('/api/prompts', async (req, res) => {
  try {
    const promptsPath = path.join(process.env.HOME || '', 'clawd', 'prompts')
    const entries = await fs.readdir(promptsPath, { withFileTypes: true })
    
    const prompts = []
    
    for (const entry of entries) {
      if (entry.isDirectory()) {
        const categoryPath = path.join(promptsPath, entry.name)
        const files = await fs.readdir(categoryPath, { withFileTypes: true })
        
        const promptFiles = []
        
        for (const file of files) {
          if (file.isFile() && (file.name.endsWith('.yaml') || file.name.endsWith('.yml') || file.name.endsWith('.md'))) {
            const filePath = path.join(categoryPath, file.name)
            try {
              const content = await fs.readFile(filePath, 'utf-8')
              promptFiles.push({
                name: file.name,
                path: filePath,
                content: content,
                category: entry.name
              })
            } catch (error) {
              console.error(`Error reading prompt file ${filePath}:`, error)
            }
          }
        }
        
        if (promptFiles.length > 0) {
          prompts.push({
            category: entry.name,
            files: promptFiles
          })
        }
      } else if (entry.isFile() && (entry.name.endsWith('.yaml') || entry.name.endsWith('.yml') || entry.name.endsWith('.md'))) {
        // Handle files in the root prompts directory
        const filePath = path.join(promptsPath, entry.name)
        try {
          const content = await fs.readFile(filePath, 'utf-8')
          
          // Check if we already have a "root" category
          let rootCategory = prompts.find(p => p.category === 'root')
          if (!rootCategory) {
            rootCategory = { category: 'root', files: [] }
            prompts.push(rootCategory)
          }
          
          rootCategory.files.push({
            name: entry.name,
            path: filePath,
            content: content,
            category: 'root'
          })
        } catch (error) {
          console.error(`Error reading prompt file ${filePath}:`, error)
        }
      }
    }

    res.json(prompts)
  } catch (error) {
    console.error('Error fetching prompts:', error)
    res.status(500).json({ error: 'Failed to fetch prompts' })
  }
})

// Search API endpoint
app.get('/api/search', async (req, res) => {
  try {
    const query = req.query.q as string
    if (!query) {
      return res.status(400).json({ error: 'Query parameter "q" is required' })
    }

    const results = []
    const searchTerm = query.toLowerCase()

    // Search skills
    try {
      const skillsPath = path.join(process.env.HOME || '', 'clawd', 'skills')
      const skillEntries = await fs.readdir(skillsPath, { withFileTypes: true })
      
      for (const entry of skillEntries) {
        if (entry.isDirectory()) {
          const skillName = entry.name.toLowerCase()
          if (skillName.includes(searchTerm)) {
            results.push({
              type: 'skill',
              name: entry.name,
              path: path.join(skillsPath, entry.name),
              category: 'Skills'
            })
          }
        }
      }
    } catch (error) {
      console.error('Error searching skills:', error)
    }

    // Search scripts
    try {
      const scriptsPath = path.join(process.env.HOME || '', 'clawd', 'scripts')
      const scriptEntries = await fs.readdir(scriptsPath, { withFileTypes: true })
      
      for (const entry of scriptEntries) {
        if (entry.isFile()) {
          const scriptName = entry.name.toLowerCase()
          if (scriptName.includes(searchTerm)) {
            results.push({
              type: 'script',
              name: entry.name,
              path: path.join(scriptsPath, entry.name),
              category: 'Scripts'
            })
          }
        }
      }
    } catch (error) {
      console.error('Error searching scripts:', error)
    }

    // Search workflows
    try {
      const workflowsPath = path.join(process.env.HOME || '', 'clawd', 'workflows')
      const workflowEntries = await fs.readdir(workflowsPath, { withFileTypes: true })
      
      for (const entry of workflowEntries) {
        if (entry.isDirectory()) {
          const appPath = path.join(workflowsPath, entry.name)
          const files = await fs.readdir(appPath, { withFileTypes: true })
          
          for (const file of files) {
            if (file.isFile() && (file.name.endsWith('.yaml') || file.name.endsWith('.yml'))) {
              const fileName = file.name.toLowerCase()
              const appName = entry.name.toLowerCase()
              if (fileName.includes(searchTerm) || appName.includes(searchTerm)) {
                results.push({
                  type: 'workflow',
                  name: file.name,
                  path: path.join(appPath, file.name),
                  category: 'Workflows',
                  app: entry.name
                })
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error searching workflows:', error)
    }

    // Search prompts
    try {
      const promptsPath = path.join(process.env.HOME || '', 'clawd', 'prompts')
      const promptEntries = await fs.readdir(promptsPath, { withFileTypes: true })
      
      for (const entry of promptEntries) {
        if (entry.isDirectory()) {
          const categoryPath = path.join(promptsPath, entry.name)
          const files = await fs.readdir(categoryPath, { withFileTypes: true })
          
          for (const file of files) {
            if (file.isFile() && (file.name.endsWith('.yaml') || file.name.endsWith('.yml') || file.name.endsWith('.md'))) {
              const fileName = file.name.toLowerCase()
              const categoryName = entry.name.toLowerCase()
              if (fileName.includes(searchTerm) || categoryName.includes(searchTerm)) {
                results.push({
                  type: 'prompt',
                  name: file.name,
                  path: path.join(categoryPath, file.name),
                  category: 'Prompts',
                  promptCategory: entry.name
                })
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error searching prompts:', error)
    }

    res.json(results)
  } catch (error) {
    console.error('Error in search:', error)
    res.status(500).json({ error: 'Search failed' })
  }
})

// Integrations API endpoint
app.get('/api/integrations', async (req, res) => {
  try {
    const integrations = []

    // Check Gemini API
    const geminiApiKey = process.env.GEMINI_API_KEY
    integrations.push({
      name: 'Gemini API',
      status: geminiApiKey ? 'connected' : 'disconnected',
      lastUsed: geminiApiKey ? 'Recently' : undefined,
      message: geminiApiKey ? 'API key configured' : 'No API key found in environment'
    })

    // Check Claude Code
    const claudeConfigPath = path.join(process.env.HOME || '', '.claude', 'config.json')
    try {
      await fs.access(claudeConfigPath)
      const configContent = await fs.readFile(claudeConfigPath, 'utf-8')
      const config = JSON.parse(configContent)
      integrations.push({
        name: 'Claude Code',
        status: 'connected',
        lastUsed: 'Active',
        message: `Version: ${config.version || 'unknown'}`
      })
    } catch {
      integrations.push({
        name: 'Claude Code',
        status: 'unknown',
        message: 'Config file not accessible'
      })
    }

    // Check WhatsApp (placeholder - would need actual WhatsApp Business API check)
    const whatsappToken = process.env.WHATSAPP_TOKEN
    integrations.push({
      name: 'WhatsApp',
      status: whatsappToken ? 'connected' : 'disconnected',
      lastUsed: whatsappToken ? 'Recently' : undefined,
      message: whatsappToken ? 'Business API configured' : 'No token configured'
    })

    // Check Google Workspace
    const googleCredsPath = path.join(process.env.HOME || '', '.config', 'gcloud', 'application_default_credentials.json')
    try {
      await fs.access(googleCredsPath)
      integrations.push({
        name: 'Google Workspace',
        status: 'connected',
        lastUsed: 'Recently',
        message: 'Credentials found'
      })
    } catch {
      integrations.push({
        name: 'Google Workspace',
        status: 'disconnected',
        message: 'No credentials found'
      })
    }

    res.json(integrations)
  } catch (error) {
    console.error('Error fetching integrations:', error)
    res.status(500).json({ error: 'Failed to fetch integrations' })
  }
})

// Agents API endpoint
app.get('/api/agents', async (req, res) => {
  try {
    const openclawConfigPath = path.join(process.env.HOME || '', '.openclaw', 'openclaw.json')

    try {
      const configContent = await fs.readFile(openclawConfigPath, 'utf-8')
      const config = JSON.parse(configContent)

      const agents = []

      // Extract agent configurations
      if (config.agents && Array.isArray(config.agents)) {
        for (const agent of config.agents) {
          agents.push({
            id: agent.id || agent.name || 'unknown',
            model: agent.model || 'unknown',
            workspace: agent.workspace || agent.workspaceLocation || 'unknown',
            status: agent.enabled !== false ? 'active' : 'inactive',
            recentRuns: agent.recentRuns || []
          })
        }
      }

      res.json(agents)
    } catch (error) {
      // If config doesn't exist or can't be read, return empty array
      res.json([])
    }
  } catch (error) {
    console.error('Error fetching agents:', error)
    res.status(500).json({ error: 'Failed to fetch agents' })
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

// Cron Jobs API endpoint
app.get('/api/cron', async (req, res) => {
  try {
    // Read from OpenClaw cron jobs file
    const cronPath = path.join(process.env.HOME || '', '.openclaw', 'cron', 'jobs.json')
    const cronContent = await fs.readFile(cronPath, 'utf-8')
    const cronData = JSON.parse(cronContent)

    // Jobs are stored in cronData.jobs array
    const jobs = cronData.jobs || []

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

// System Status API endpoint
app.get('/api/status', async (req, res) => {
  try {
    const status: any = {
      openclaw: {
        version: 'unknown',
        uptime: 'unknown'
      },
      session: {
        contextUsage: 'unknown',
        model: 'unknown',
        contextPercent: 0
      },
      activity: {
        summary: 'No recent activity',
        recent: []
      },
      timestamp: new Date().toISOString()
    }

    // Get OpenClaw version
    try {
      const { stdout } = await execAsync('openclaw --version 2>/dev/null || echo "unknown"')
      status.openclaw.version = stdout.trim() || 'unknown'
    } catch {
      // Command failed, keep unknown
    }

    // Get context usage via check-context.sh
    try {
      const { stdout } = await execAsync('~/clawd/scripts/check-context.sh 2>/dev/null | head -1')
      // Parse: "📊 Context: 26745/200K tokens (13%)"
      const match = stdout.match(/(\d+)\/(\d+)K tokens \((\d+)%\)/)
      if (match) {
        status.session.contextUsage = `${match[1]}/${match[2]}K tokens`
        status.session.contextPercent = parseInt(match[3])
      }
    } catch {
      // Script failed, keep unknown
    }

    // Get uptime from gateway process
    try {
      const { stdout } = await execAsync('ps -o etime= -p $(pgrep -f "openclaw" | head -1) 2>/dev/null')
      status.openclaw.uptime = stdout.trim() || 'unknown'
    } catch {
      // Process not found, keep unknown
    }

    // Get model from environment or config
    status.session.model = process.env.OPENCLAW_MODEL || 'claude-opus-4-5'

    // Try to get recent activity from clawd memory
    const memoryPath = path.join(process.env.HOME || '', 'clawd', 'memory')
    try {
      // Look for today's memory file
      const today = new Date().toISOString().split('T')[0]
      const todayMemoryPath = path.join(memoryPath, `${today}.md`)

      try {
        const memoryContent = await fs.readFile(todayMemoryPath, 'utf-8')
        const lines = memoryContent.split('\n').filter(line => line.trim())

        // Extract recent entries (look for lines that start with timestamps or bullets)
        const recentEntries = lines
          .filter(line => line.match(/^[\-\*\#]|^\d{2}:\d{2}/))
          .slice(-10)
          .reverse()

        if (recentEntries.length > 0) {
          status.activity.summary = `${recentEntries.length} recent activities today`
          status.activity.recent = recentEntries
        }
      } catch {
        // Today's file doesn't exist yet
      }

      // If no activity found, check last modified file
      if (status.activity.recent.length === 0) {
        const files = await fs.readdir(memoryPath, { withFileTypes: true })
        const mdFiles = files
          .filter(f => f.isFile() && f.name.endsWith('.md'))
          .map(f => path.join(memoryPath, f.name))

        if (mdFiles.length > 0) {
          // Get the most recently modified file
          const fileStats = await Promise.all(
            mdFiles.map(async (file) => ({
              file,
              mtime: (await fs.stat(file)).mtime
            }))
          )

          fileStats.sort((a, b) => b.mtime.getTime() - a.mtime.getTime())

          if (fileStats.length > 0) {
            const recentFile = fileStats[0].file
            const content = await fs.readFile(recentFile, 'utf-8')
            const lines = content.split('\n').filter(line => line.trim())
            const recentEntries = lines
              .filter(line => line.match(/^[\-\*\#]|^\d{2}:\d{2}/))
              .slice(-5)
              .reverse()

            if (recentEntries.length > 0) {
              status.activity.recent = recentEntries
              status.activity.summary = `Recent activities from ${path.basename(recentFile)}`
            }
          }
        }
      }
    } catch (error) {
      console.error('Error reading activity from memory:', error)
    }

    // If still no activity, provide a default message
    if (status.activity.recent.length === 0) {
      status.activity.recent = ['No recent activity recorded']
    }

    res.json(status)
  } catch (error) {
    console.error('Error fetching status:', error)
    res.status(500).json({ error: 'Failed to fetch status' })
  }
})

// Memory API endpoints
app.get('/api/memory', async (req, res) => {
  try {
    const memoryPath = path.join(process.env.HOME || '', 'clawd', 'memory')
    const sessionPath = path.join(memoryPath, 'sessions')

    const files = []

    // Read main memory directory
    try {
      const entries = await fs.readdir(memoryPath, { withFileTypes: true })
      for (const entry of entries) {
        if (entry.isFile() && entry.name.endsWith('.md')) {
          const filePath = path.join(memoryPath, entry.name)
          const stats = await fs.stat(filePath)
          files.push({
            name: entry.name,
            path: filePath,
            date: stats.mtime.toLocaleDateString(),
            size: `${Math.round(stats.size / 1024)} KB`,
            isSession: false
          })
        }
      }
    } catch (error) {
      console.error('Error reading memory directory:', error)
    }

    // Read session archives
    try {
      const sessionEntries = await fs.readdir(sessionPath, { withFileTypes: true })
      for (const entry of sessionEntries) {
        if (entry.isFile() && entry.name.endsWith('.md')) {
          const filePath = path.join(sessionPath, entry.name)
          const stats = await fs.stat(filePath)
          files.push({
            name: entry.name,
            path: filePath,
            date: stats.mtime.toLocaleDateString(),
            size: `${Math.round(stats.size / 1024)} KB`,
            isSession: true
          })
        }
      }
    } catch (error) {
      console.error('Error reading sessions directory:', error)
    }

    // Sort by date (newest first)
    files.sort((a, b) => {
      const dateA = new Date(a.date).getTime()
      const dateB = new Date(b.date).getTime()
      return dateB - dateA
    })

    res.json(files)
  } catch (error) {
    console.error('Error fetching memory files:', error)
    res.status(500).json({ error: 'Failed to fetch memory files' })
  }
})

app.get('/api/memory/:filename', async (req, res) => {
  try {
    const { filename } = req.params
    const isSession = req.query.isSession === 'true'

    const memoryPath = path.join(process.env.HOME || '', 'clawd', 'memory')
    const filePath = isSession
      ? path.join(memoryPath, 'sessions', filename)
      : path.join(memoryPath, filename)

    // Security check: ensure the path is within the memory directory
    const resolvedPath = path.resolve(filePath)
    const resolvedMemoryPath = path.resolve(memoryPath)
    if (!resolvedPath.startsWith(resolvedMemoryPath)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    const content = await fs.readFile(filePath, 'utf-8')
    res.json({ content })
  } catch (error) {
    console.error('Error reading memory file:', error)
    res.status(500).json({ error: 'Failed to read file' })
  }
})

// Media API endpoints
app.get('/api/media', async (req, res) => {
  try {
    const mediaPath = path.join(process.env.HOME || '', 'clawd', 'media')
    const subfolders = ['recordings', 'screenshots', 'transcripts', 'operator', 'research']

    const mediaFiles = []

    for (const subfolder of subfolders) {
      const subfolderPath = path.join(mediaPath, subfolder)

      try {
        await fs.access(subfolderPath)
        const entries = await fs.readdir(subfolderPath, { withFileTypes: true })

        for (const entry of entries) {
          if (entry.isFile()) {
            const filePath = path.join(subfolderPath, entry.name)
            const stats = await fs.stat(filePath)

            // Determine file type
            const ext = path.extname(entry.name).toLowerCase()
            let type = 'unknown'
            if (['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'].includes(ext)) {
              type = 'image'
            } else if (['.mp4', '.webm', '.mov', '.avi'].includes(ext)) {
              type = 'video'
            } else if (['.mp3', '.wav', '.ogg', '.m4a'].includes(ext)) {
              type = 'audio'
            } else if (['.txt', '.md', '.json', '.log'].includes(ext)) {
              type = 'text'
            } else if (['.pdf'].includes(ext)) {
              type = 'pdf'
            }

            mediaFiles.push({
              name: entry.name,
              path: filePath,
              relativePath: `${subfolder}/${entry.name}`,
              subfolder,
              type,
              size: formatFileSize(stats.size),
              date: stats.mtime.toLocaleDateString(),
              dateTime: stats.mtime.toISOString()
            })
          }
        }
      } catch (error) {
        // Subfolder doesn't exist or can't be read
        console.error(`Error reading ${subfolder}:`, error)
      }
    }

    // Sort by date (newest first)
    mediaFiles.sort((a, b) => {
      return new Date(b.dateTime).getTime() - new Date(a.dateTime).getTime()
    })

    res.json(mediaFiles)
  } catch (error) {
    console.error('Error fetching media files:', error)
    res.status(500).json({ error: 'Failed to fetch media files' })
  }
})

app.get('/api/media/:subfolder/:filename', async (req, res) => {
  try {
    const { subfolder, filename } = req.params
    const mediaPath = path.join(process.env.HOME || '', 'clawd', 'media', subfolder, filename)

    // Security check: ensure the path is within the media directory
    const resolvedPath = path.resolve(mediaPath)
    const resolvedMediaBase = path.resolve(path.join(process.env.HOME || '', 'clawd', 'media'))
    if (!resolvedPath.startsWith(resolvedMediaBase)) {
      return res.status(403).json({ error: 'Access denied' })
    }

    // Check if file exists
    await fs.access(mediaPath)

    // For text files, return content as JSON
    const ext = path.extname(filename).toLowerCase()
    if (['.txt', '.md', '.json', '.log'].includes(ext)) {
      const content = await fs.readFile(mediaPath, 'utf-8')
      return res.json({ content })
    }

    // For other files, send the file directly
    res.sendFile(mediaPath)
  } catch (error) {
    console.error('Error serving media file:', error)
    res.status(404).json({ error: 'File not found' })
  }
})

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

// Helper function to format file sizes
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() })
})

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`)
})