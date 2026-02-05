import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useToast } from '@/contexts/ToastContext'
import { Workflow, FileText, FolderOpen, Eye, Copy, CheckCircle, RefreshCw, Download } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface WorkflowFile {
  name: string
  path: string
  content: string
  app: string
}

interface WorkflowGroup {
  app: string
  files: WorkflowFile[]
}

function Workflows() {
  const [workflows, setWorkflows] = useState<WorkflowGroup[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowFile | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set())
  const [isDark, setIsDark] = useState(false)
  const [copied, setCopied] = useState(false)
  const { showToast } = useToast()

  useEffect(() => {
    // Check if dark mode is enabled
    setIsDark(document.documentElement.classList.contains('dark'))
    fetchWorkflows()
  }, [])

  const fetchWorkflows = async () => {
    try {
      const response = await fetch('/api/workflows')
      if (!response.ok) {
        throw new Error('Failed to fetch workflows')
      }
      const data = await response.json()
      setWorkflows(data)
      
      // Auto-expand all groups initially
      const allApps = data.map((group: WorkflowGroup) => group.app)
      setExpandedGroups(new Set(allApps))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const toggleGroup = (app: string) => {
    const newExpanded = new Set(expandedGroups)
    if (newExpanded.has(app)) {
      newExpanded.delete(app)
    } else {
      newExpanded.add(app)
    }
    setExpandedGroups(newExpanded)
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

  const downloadWorkflow = (workflow: WorkflowFile) => {
    try {
      const dataBlob = new Blob([workflow.content], { type: 'text/yaml' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = workflow.name
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      showToast('success', 'Workflow downloaded')
    } catch (err) {
      showToast('error', 'Failed to download workflow')
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Workflow className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Workflows</h1>
        </div>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Spinner size="lg" className="mx-auto mb-4" />
            <p className="text-muted-foreground">Loading workflows...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Workflow className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Workflows</h1>
        </div>
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  const totalWorkflows = workflows.reduce((sum, group) => sum + group.files.length, 0)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Workflow className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Workflows</h1>
        </div>
        <Button onClick={fetchWorkflows} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="text-sm text-muted-foreground">
        {totalWorkflows} workflows across {workflows.length} apps
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-6">
        {/* Left column: Workflow groups */}
        <div className="space-y-4">
          {workflows.map((group) => (
            <Card key={group.app} className="overflow-hidden transition-all duration-200 hover:shadow-md">
              <CardHeader
                className="cursor-pointer hover:bg-accent transition-colors duration-150"
                onClick={() => toggleGroup(group.app)}
              >
                <CardTitle className="flex items-center space-x-2">
                  <FolderOpen className="h-5 w-5" />
                  <span>{group.app}</span>
                  <span className="text-sm text-muted-foreground">
                    ({group.files.length})
                  </span>
                </CardTitle>
              </CardHeader>
              {expandedGroups.has(group.app) && (
                <CardContent className="pt-0">
                  <div className="space-y-2">
                    {group.files.map((workflow) => (
                      <div
                        key={workflow.path}
                        className={`flex items-center space-x-3 p-2 rounded cursor-pointer transition-all duration-150 focus-within:ring-2 focus-within:ring-ring ${
                          selectedWorkflow?.path === workflow.path
                            ? 'bg-primary text-primary-foreground'
                            : 'hover:bg-accent hover:scale-102'
                        }`}
                        onClick={() => setSelectedWorkflow(workflow)}
                        tabIndex={0}
                        role="button"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            setSelectedWorkflow(workflow)
                          }
                        }}
                      >
                        <FileText className="h-4 w-4" />
                        <span className="text-sm font-medium truncate">
                          {workflow.name}
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

        {/* Right column: Workflow content */}
        <div className="lg:sticky lg:top-6">
          {selectedWorkflow ? (
            <Card className="h-[600px] overflow-hidden">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center space-x-2">
                      <FileText className="h-5 w-5" />
                      <span>{selectedWorkflow.name}</span>
                    </CardTitle>
                    <CardDescription>
                      <span className="font-medium">{selectedWorkflow.app}</span> workflow
                    </CardDescription>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => downloadWorkflow(selectedWorkflow)}
                      title="Download workflow"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => copyToClipboard(selectedWorkflow.content)}
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
                    customStyle={{
                      margin: 0,
                      padding: '16px',
                      background: 'transparent',
                      fontSize: '14px',
                      overflow: 'visible',
                      minWidth: 'max-content'
                    }}
                    wrapLines={false}
                    wrapLongLines={false}
                  >
                    {selectedWorkflow.content}
                  </SyntaxHighlighter>
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card className="h-[600px]">
              <CardContent className="h-full flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Workflow className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>Select a workflow to view its content</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

export default Workflows