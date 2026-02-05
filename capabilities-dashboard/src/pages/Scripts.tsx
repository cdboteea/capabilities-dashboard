import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Code, Play, FileText, Clock, Copy, CheckCircle, RefreshCw, AlertTriangle } from 'lucide-react'

interface Script {
  name: string
  path: string
  description?: string
  language?: string
  executable?: boolean
  size?: string
  lastModified?: string
}

function Scripts() {
  const [scripts, setScripts] = useState<Script[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [confirmRunDialog, setConfirmRunDialog] = useState<Script | null>(null)
  const [runningScript, setRunningScript] = useState<string | null>(null)
  const [runOutput, setRunOutput] = useState<string>('')
  const [copiedPath, setCopiedPath] = useState<string | null>(null)

  useEffect(() => {
    fetchScripts()
  }, [])

  const fetchScripts = async () => {
    try {
      const response = await fetch('/api/scripts')
      if (!response.ok) {
        throw new Error('Failed to fetch scripts')
      }
      const data = await response.json()
      setScripts(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const getLanguageFromExtension = (filename: string): string => {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
      case 'sh':
        return 'Shell'
      case 'py':
        return 'Python'
      case 'js':
        return 'JavaScript'
      case 'ts':
        return 'TypeScript'
      case 'yaml':
      case 'yml':
        return 'YAML'
      default:
        return 'Unknown'
    }
  }

  const handleRunScript = (script: Script) => {
    setConfirmRunDialog(script)
  }

  const executeScript = async () => {
    if (!confirmRunDialog) return

    setRunningScript(confirmRunDialog.path)
    setRunOutput('')
    setConfirmRunDialog(null)

    try {
      const response = await fetch('/api/scripts/run', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path: confirmRunDialog.path }),
      })

      const data = await response.json()

      if (!response.ok) {
        setRunOutput(`Error: ${data.error || 'Failed to run script'}`)
      } else {
        setRunOutput(data.output || 'Script executed successfully')
      }
    } catch (err) {
      setRunOutput(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`)
    } finally {
      setRunningScript(null)
    }
  }

  const copyToClipboard = async (text: string, scriptName: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedPath(scriptName)
      setTimeout(() => setCopiedPath(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Code className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Scripts & Tools</h1>
        </div>
        <div>Loading scripts...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Code className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Scripts & Tools</h1>
        </div>
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Code className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Scripts & Tools</h1>
        </div>
        <Button onClick={fetchScripts} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="text-sm text-muted-foreground">
        {scripts.length} scripts available
      </div>

      {runOutput && (
        <Card className="border-blue-500">
          <CardHeader>
            <CardTitle className="text-base">Script Output</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-sm bg-muted p-4 rounded-md overflow-x-auto whitespace-pre-wrap">
              {runOutput}
            </pre>
            <Button
              onClick={() => setRunOutput('')}
              variant="outline"
              size="sm"
              className="mt-4"
            >
              Clear Output
            </Button>
          </CardContent>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {scripts.map((script) => (
          <Card key={script.name} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Code className="h-5 w-5" />
                <span className="truncate">{script.name}</span>
              </CardTitle>
              {script.description && (
                <CardDescription>{script.description}</CardDescription>
              )}
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">
                    {getLanguageFromExtension(script.name)}
                  </span>
                  <div className="flex items-center space-x-2">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => copyToClipboard(script.path, script.name)}
                      title="Copy path"
                    >
                      {copiedPath === script.name ? (
                        <CheckCircle className="h-3 w-3 text-green-500" />
                      ) : (
                        <Copy className="h-3 w-3" />
                      )}
                    </Button>
                    {script.executable && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRunScript(script)}
                        disabled={runningScript === script.path}
                      >
                        <Play className="h-3 w-3 mr-1" />
                        {runningScript === script.path ? 'Running...' : 'Run'}
                      </Button>
                    )}
                  </div>
                </div>

                <div className="space-y-1">
                  {script.size && (
                    <div className="flex items-center space-x-2 text-sm">
                      <FileText className="h-4 w-4" />
                      <span>{script.size}</span>
                    </div>
                  )}
                  {script.lastModified && (
                    <div className="flex items-center space-x-2 text-sm">
                      <Clock className="h-4 w-4" />
                      <span>{script.lastModified}</span>
                    </div>
                  )}
                </div>

                <div className="text-xs text-muted-foreground truncate">
                  {script.path}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Confirmation Dialog */}
      <Dialog open={!!confirmRunDialog} onOpenChange={() => setConfirmRunDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              <span>Confirm Script Execution</span>
            </DialogTitle>
            <DialogDescription>
              Are you sure you want to run this script?
            </DialogDescription>
          </DialogHeader>

          {confirmRunDialog && (
            <div className="py-4">
              <div className="bg-muted p-3 rounded-md">
                <p className="text-sm font-medium">{confirmRunDialog.name}</p>
                <p className="text-xs text-muted-foreground mt-1">{confirmRunDialog.path}</p>
              </div>
              {confirmRunDialog.description && (
                <p className="text-sm text-muted-foreground mt-3">
                  {confirmRunDialog.description}
                </p>
              )}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmRunDialog(null)}>
              Cancel
            </Button>
            <Button onClick={executeScript}>
              <Play className="h-4 w-4 mr-2" />
              Run Script
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Scripts