import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useToast } from '@/contexts/ToastContext'
import { MessageSquare, FileText, Eye, Tag, Copy, CheckCircle, RefreshCw, Download } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface PromptFile {
  name: string
  path: string
  content: string
  category: string
}

interface PromptGroup {
  category: string
  files: PromptFile[]
}

function Prompts() {
  const [prompts, setPrompts] = useState<PromptGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedPrompt, setSelectedPrompt] = useState<PromptFile | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [isDark, setIsDark] = useState(false)
  const [copied, setCopied] = useState(false)
  const { showToast } = useToast()

  useEffect(() => {
    // Check if dark mode is enabled
    setIsDark(document.documentElement.classList.contains('dark'))
    fetchPrompts()
  }, [])

  const fetchPrompts = async () => {
    try {
      const response = await fetch('/api/prompts')
      if (!response.ok) {
        throw new Error('Failed to fetch prompts')
      }
      const data = await response.json()
      setPrompts(data)
      
      // Auto-expand all groups initially
      const allCategories = data.map((group: PromptGroup) => group.category)
      setExpandedGroups(new Set(allCategories))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const toggleGroup = (category: string) => {
    const newExpanded = new Set(expandedGroups)
    if (newExpanded.has(category)) {
      newExpanded.delete(category)
    } else {
      newExpanded.add(category)
    }
    setExpandedGroups(newExpanded)
  }

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'agents':
        return '🤖'
      case 'gemini':
        return '✨'
      case 'claude-code':
        return '💻'
      case 'components':
        return '🧩'
      case 'tasks':
        return '📝'
      case 'visual-generation':
        return '🎨'
      case 'history':
        return '📚'
      default:
        return '📄'
    }
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      showToast('success', 'Copied to clipboard')
    } catch (err) {
      console.error('Failed to copy:', err)
      showToast('error', 'Failed to copy')
    }
  }

  const downloadPrompt = (prompt: PromptFile) => {
    try {
      const dataBlob = new Blob([prompt.content], { type: 'text/yaml' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = prompt.name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      showToast('success', 'Prompt downloaded')
    } catch (err) {
      showToast('error', 'Failed to download prompt')
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <MessageSquare className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Prompts Library</h1>
        </div>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Spinner size="lg" className="mx-auto mb-4" />
            <p className="text-muted-foreground">Loading prompts...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <MessageSquare className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Prompts Library</h1>
        </div>
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  const totalPrompts = prompts.reduce((sum, group) => sum + group.files.length, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <MessageSquare className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Prompts Library</h1>
        </div>
        <Button onClick={fetchPrompts} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="text-sm text-muted-foreground">
        {totalPrompts} prompts across {prompts.length} categories
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        {/* Left column: Prompt groups */}
        <div className="space-y-4">
          {prompts.map((group) => (
            <Card key={group.category} className="overflow-hidden transition-all duration-200 hover:shadow-md">
              <CardHeader
                className="cursor-pointer hover:bg-accent transition-colors duration-150"
                onClick={() => toggleGroup(group.category)}
              >
                <CardTitle className="flex items-center space-x-2">
                  <span className="text-xl">{getCategoryIcon(group.category)}</span>
                  <span className="capitalize">{group.category.replace('-', ' ')}</span>
                  <span className="text-sm text-muted-foreground">
                    ({group.files.length})
                  </span>
                </CardTitle>
              </CardHeader>
              {expandedGroups.has(group.category) && (
                <CardContent className="pt-0">
                  <div className="space-y-2">
                    {group.files.map((prompt) => (
                      <div
                        key={prompt.path}
                        className={`flex items-center space-x-3 p-2 rounded cursor-pointer transition-all duration-150 focus-within:ring-2 focus-within:ring-ring ${
                          selectedPrompt?.path === prompt.path
                            ? 'bg-primary text-primary-foreground'
                            : 'hover:bg-accent hover:scale-102'
                        }`}
                        onClick={() => setSelectedPrompt(prompt)}
                        tabIndex={0}
                        role="button"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setSelectedPrompt(prompt)
                          }
                        }}
                      >
                        <FileText className="h-4 w-4" />
                        <span className="text-sm font-medium truncate">
                          {prompt.name}
                        </span>
                        <Eye className="h-3 w-3 ml-auto opacity-60" />
                      </div>
                    ))}
                  </div>
                </CardContent>
              )}
            </Card>
          ))}
        </div>

        {/* Right column: Prompt content */}
        <div className="lg:sticky lg:top-6">
          {selectedPrompt ? (
            <Card className="h-[600px] overflow-hidden">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center space-x-2">
                      <FileText className="h-5 w-5" />
                      <span>{selectedPrompt.name}</span>
                    </CardTitle>
                    <CardDescription className="flex items-center space-x-2">
                      <Tag className="h-4 w-4" />
                      <span className="capitalize font-medium">
                        {selectedPrompt.category.replace('-', ' ')} category
                      </span>
                    </CardDescription>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => downloadPrompt(selectedPrompt)}
                      title="Download prompt"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => copyToClipboard(selectedPrompt.content)}
                      title="Copy content"
                    >
                      {copied ? (
                        <>
                          <CheckCircle className="h-4 w-4 mr-2 text-green-500" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-2" />
                          Copy
                        </>
                      )}
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="h-[calc(100%-80px)] overflow-hidden">
                <div className="h-full code-viewer">
                  <SyntaxHighlighter
                    language="yaml"
                    style={isDark ? vscDarkPlus : oneLight}
                    className="h-full text-sm"
                    customStyle={{
                      margin: 0,
                      padding: '16px',
                      background: 'transparent',
                      fontSize: '14px'
                    }}
                  >
                    {selectedPrompt.content}
                  </SyntaxHighlighter>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="h-[600px]">
              <CardContent className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Select a prompt to view its content</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default Prompts