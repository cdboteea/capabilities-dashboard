import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { PlaySquare, Image, Music, Video, FileText, File, RefreshCw, FolderOpen, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { useToast } from '@/contexts/ToastContext'

interface MediaFile {
  name: string
  path: string
  relativePath: string
  subfolder: string
  type: 'image' | 'video' | 'audio' | 'text' | 'pdf' | 'unknown'
  size: string
  date: string
  dateTime: string
}

function Media() {
  const [mediaFiles, setMediaFiles] = useState<MediaFile[]>([])
  const [selectedFile, setSelectedFile] = useState<MediaFile | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [selectedSubfolder, setSelectedSubfolder] = useState<string>('all')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { showToast } = useToast()

  const subfolders = ['all', 'recordings', 'screenshots', 'transcripts', 'operator', 'research']

  useEffect(() => {
    fetchMediaFiles()
  }, [])

  const fetchMediaFiles = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/media')
      if (!response.ok) {
        throw new Error('Failed to fetch media files')
      }
      const data = await response.json()
      setMediaFiles(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const fetchFileContent = async (file: MediaFile) => {
    if (file.type === 'text') {
      try {
        const response = await fetch(`/api/media/${file.subfolder}/${encodeURIComponent(file.name)}`)
        if (!response.ok) {
          throw new Error('Failed to fetch file content')
        }
        const data = await response.json()
        setFileContent(data.content)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
        setFileContent('')
      }
    }
    setSelectedFile(file)
  }

  const deleteFile = async (file: MediaFile) => {
    if (!confirm(`Delete "${file.name}"? This will move it to trash.`)) return

    try {
      const response = await fetch(
        `/api/media/${file.subfolder}/${encodeURIComponent(file.name)}`,
        { method: 'DELETE' }
      )
      if (!response.ok) throw new Error('Delete failed')

      showToast('success', 'File moved to trash')
      setSelectedFile(null)
      fetchMediaFiles()
    } catch (err) {
      showToast('error', 'Failed to delete file')
    }
  }

  const getFileIcon = (type: string) => {
    switch (type) {
      case 'image':
        return <Image className="h-4 w-4" />
      case 'video':
        return <Video className="h-4 w-4" />
      case 'audio':
        return <Music className="h-4 w-4" />
      case 'text':
        return <FileText className="h-4 w-4" />
      default:
        return <File className="h-4 w-4" />
    }
  }

  const filteredFiles = selectedSubfolder === 'all'
    ? mediaFiles
    : mediaFiles.filter(f => f.subfolder === selectedSubfolder)

  const renderFilePreview = (file: MediaFile) => {
    const fileUrl = `/api/media/${file.subfolder}/${encodeURIComponent(file.name)}`

    switch (file.type) {
      case 'image':
        return (
          <div className="space-y-4">
            <img
              src={fileUrl}
              alt={file.name}
              className="max-w-full h-auto rounded-lg border border-border"
            />
            <div className="text-sm text-muted-foreground">
              <p><strong>Name:</strong> {file.name}</p>
              <p><strong>Size:</strong> {file.size}</p>
              <p><strong>Date:</strong> {file.date}</p>
              <p><strong>Location:</strong> {file.subfolder}</p>
            </div>
          </div>
        )

      case 'video':
        return (
          <div className="space-y-4">
            <video
              controls
              className="max-w-full h-auto rounded-lg border border-border"
              src={fileUrl}
            >
              Your browser does not support the video tag.
            </video>
            <div className="text-sm text-muted-foreground">
              <p><strong>Name:</strong> {file.name}</p>
              <p><strong>Size:</strong> {file.size}</p>
              <p><strong>Date:</strong> {file.date}</p>
              <p><strong>Location:</strong> {file.subfolder}</p>
            </div>
          </div>
        )

      case 'audio':
        return (
          <div className="space-y-4">
            <audio
              controls
              className="w-full"
              src={fileUrl}
            >
              Your browser does not support the audio tag.
            </audio>
            <div className="text-sm text-muted-foreground">
              <p><strong>Name:</strong> {file.name}</p>
              <p><strong>Size:</strong> {file.size}</p>
              <p><strong>Date:</strong> {file.date}</p>
              <p><strong>Location:</strong> {file.subfolder}</p>
            </div>
          </div>
        )

      case 'text':
        return (
          <div className="space-y-4">
            <div className="prose prose-sm dark:prose-invert max-w-none">
              {file.name.endsWith('.md') ? (
                <ReactMarkdown>{fileContent}</ReactMarkdown>
              ) : (
                <pre className="whitespace-pre-wrap bg-muted p-4 rounded-md text-sm">
                  {fileContent}
                </pre>
              )}
            </div>
            <div className="text-sm text-muted-foreground">
              <p><strong>Name:</strong> {file.name}</p>
              <p><strong>Size:</strong> {file.size}</p>
              <p><strong>Date:</strong> {file.date}</p>
              <p><strong>Location:</strong> {file.subfolder}</p>
            </div>
          </div>
        )

      case 'pdf':
        return (
          <div className="space-y-4">
            <div className="bg-muted p-8 rounded-lg text-center">
              <File className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium mb-2">{file.name}</p>
              <Button asChild>
                <a href={fileUrl} target="_blank" rel="noopener noreferrer">
                  Open PDF in new tab
                </a>
              </Button>
            </div>
            <div className="text-sm text-muted-foreground">
              <p><strong>Name:</strong> {file.name}</p>
              <p><strong>Size:</strong> {file.size}</p>
              <p><strong>Date:</strong> {file.date}</p>
              <p><strong>Location:</strong> {file.subfolder}</p>
            </div>
          </div>
        )

      default:
        return (
          <div className="space-y-4">
            <div className="bg-muted p-8 rounded-lg text-center">
              <File className="h-16 w-16 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium mb-2">{file.name}</p>
              <p className="text-sm text-muted-foreground mb-4">Preview not available</p>
              <Button asChild>
                <a href={fileUrl} download>
                  Download File
                </a>
              </Button>
            </div>
            <div className="text-sm text-muted-foreground">
              <p><strong>Name:</strong> {file.name}</p>
              <p><strong>Size:</strong> {file.size}</p>
              <p><strong>Date:</strong> {file.date}</p>
              <p><strong>Location:</strong> {file.subfolder}</p>
            </div>
          </div>
        )
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <PlaySquare className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Media Gallery</h1>
        </div>
        <Button onClick={fetchMediaFiles} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {error && (
        <div className="text-red-500 p-4 bg-red-50 dark:bg-red-900/10 rounded-md">
          Error: {error}
        </div>
      )}

      {/* Subfolder Filter */}
      <div className="flex items-center space-x-2 overflow-x-auto pb-2">
        {subfolders.map((subfolder) => (
          <Button
            key={subfolder}
            variant={selectedSubfolder === subfolder ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedSubfolder(subfolder)}
            className="capitalize"
          >
            <FolderOpen className="h-4 w-4 mr-2" />
            {subfolder}
            {subfolder !== 'all' && (
              <span className="ml-2 text-xs">
                ({mediaFiles.filter(f => f.subfolder === subfolder).length})
              </span>
            )}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* File Grid */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Files</CardTitle>
              <CardDescription>
                {loading ? 'Loading...' : `${filteredFiles.length} files`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-sm text-muted-foreground">Loading files...</div>
              ) : filteredFiles.length === 0 ? (
                <div className="text-sm text-muted-foreground">No files found</div>
              ) : (
                <div className="grid grid-cols-1 gap-2 max-h-[600px] overflow-y-auto">
                  {filteredFiles.map((file) => (
                    <button
                      key={file.path}
                      onClick={() => fetchFileContent(file)}
                      className={`w-full text-left p-3 rounded-md border transition-colors ${
                        selectedFile?.path === file.path
                          ? 'bg-primary text-primary-foreground border-primary'
                          : 'bg-card hover:bg-accent border-border'
                      }`}
                    >
                      <div className="flex items-start space-x-2">
                        {getFileIcon(file.type)}
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium truncate">{file.name}</div>
                          <div className="flex items-center justify-between mt-1">
                            <span className="text-xs text-muted-foreground capitalize">
                              {file.subfolder}
                            </span>
                            <span className="text-xs text-muted-foreground">{file.size}</span>
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">{file.date}</div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* File Preview */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle>
                    {selectedFile ? selectedFile.name : 'Select a file to preview'}
                  </CardTitle>
                  {selectedFile && (
                    <CardDescription>
                      {selectedFile.type} • {selectedFile.size} • {selectedFile.date}
                    </CardDescription>
                  )}
                </div>
                {selectedFile && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => deleteFile(selectedFile)}
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    title="Delete file"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {selectedFile ? (
                renderFilePreview(selectedFile)
              ) : (
                <div className="text-muted-foreground text-center py-12">
                  Select a media file to view its preview
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}

export default Media
