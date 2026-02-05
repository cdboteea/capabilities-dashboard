import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Brain, FileText, Folder, RefreshCw } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface MemoryFile {
  name: string
  path: string
  date: string
  size: string
  isSession: boolean
}

function Memory() {
  const [memoryFiles, setMemoryFiles] = useState<MemoryFile[]>([])
  const [selectedFile, setSelectedFile] = useState<MemoryFile | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [contentLoading, setContentLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchMemoryFiles()
  }, [])

  const fetchMemoryFiles = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/memory')
      if (!response.ok) {
        throw new Error('Failed to fetch memory files')
      }
      const data = await response.json()
      setMemoryFiles(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchFileContent = async (file: MemoryFile) => {
    try {
      setContentLoading(true)
      setSelectedFile(file)
      const response = await fetch(`/api/memory/${encodeURIComponent(file.name)}?isSession=${file.isSession}`)
      if (!response.ok) {
        throw new Error('Failed to fetch file content')
      }
      const data = await response.json()
      setFileContent(data.content)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
      setFileContent('')
    } finally {
      setContentLoading(false)
    }
  }

  const memoryFilesList = memoryFiles.filter(f => !f.isSession)
  const sessionFilesList = memoryFiles.filter(f => f.isSession)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Brain className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Memory Browser</h1>
        </div>
        <Button onClick={fetchMemoryFiles} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="text-red-500 p-4 bg-red-50 dark:bg-red-900/10 rounded-md">
          Error: {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* File List */}
        <div className="lg:col-span-1 space-y-4">
          {/* Memory Files */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-base">
                <FileText className="h-4 w-4" />
                <span>Memory Files</span>
              </CardTitle>
              <CardDescription>Daily memory logs</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-sm text-muted-foreground">Loading...</div>
              ) : memoryFilesList.length === 0 ? (
                <div className="text-sm text-muted-foreground">No memory files found</div>
              ) : (
                <div className="space-y-2">
                  {memoryFilesList.map((file) => (
                    <button
                      key={file.path}
                      onClick={() => fetchFileContent(file)}
                      className={`w-full text-left p-3 rounded-md border transition-colors ${
                        selectedFile?.path === file.path
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-card hover:bg-accent border-border'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{file.name}</span>
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-muted-foreground">{file.date}</span>
                        <span className="text-xs text-muted-foreground">{file.size}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Session Archives */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2 text-base">
                <Folder className="h-4 w-4" />
                <span>Session Archives</span>
              </CardTitle>
              <CardDescription>Historical sessions</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-sm text-muted-foreground">Loading...</div>
              ) : sessionFilesList.length === 0 ? (
                <div className="text-sm text-muted-foreground">No session archives found</div>
              ) : (
                <div className="space-y-2">
                  {sessionFilesList.map((file) => (
                    <button
                      key={file.path}
                      onClick={() => fetchFileContent(file)}
                      className={`w-full text-left p-3 rounded-md border transition-colors ${
                        selectedFile?.path === file.path
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-card hover:bg-accent border-border'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{file.name}</span>
                      </div>
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-xs text-muted-foreground">{file.date}</span>
                        <span className="text-xs text-muted-foreground">{file.size}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Content Viewer */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader>
              <CardTitle>
                {selectedFile ? selectedFile.name : 'Select a file to view'}
              </CardTitle>
              {selectedFile && (
                <CardDescription>
                  {selectedFile.date} • {selectedFile.size}
                </CardDescription>
              )}
            </CardHeader>
            <CardContent>
              {contentLoading ? (
                <div className="text-muted-foreground">Loading content...</div>
              ) : selectedFile && fileContent ? (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  <ReactMarkdown>{fileContent}</ReactMarkdown>
                </div>
              ) : (
                <div className="text-muted-foreground text-center py-12">
                  Select a memory file or session archive to view its contents
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default Memory
