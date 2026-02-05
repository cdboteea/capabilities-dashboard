import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { useToast } from '@/contexts/ToastContext'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { BookOpen, Tag, User, RefreshCw, Download } from 'lucide-react'
import ReactMarkdown from 'react-markdown'

interface Skill {
  name: string
  path: string
  description?: string
  category?: string
  author?: string
  version?: string
}

function Skills() {
  const [skills, setSkills] = useState<Skill[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null)
  const [skillDetail, setSkillDetail] = useState<any>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)
  const { showToast } = useToast()

  useEffect(() => {
    fetchSkills()
  }, [])

  const fetchSkills = async () => {
    try {
      const response = await fetch('/api/skills')
      if (!response.ok) {
        throw new Error('Failed to fetch skills')
      }
      const data = await response.json()
      setSkills(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const exportSkills = () => {
    try {
      const dataStr = JSON.stringify(skills, null, 2)
      const dataBlob = new Blob([dataStr], { type: 'application/json' })
      const url = URL.createObjectURL(dataBlob)
      const link = document.createElement('a')
      link.href = url
      link.download = `skills-${new Date().toISOString().split('T')[0]}.json`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
      showToast('success', 'Skills exported successfully')
    } catch (err) {
      showToast('error', 'Failed to export skills')
    }
  }

  const fetchSkillDetail = async (name: string) => {
    setLoadingDetail(true)
    try {
      const response = await fetch(`/api/skills/${encodeURIComponent(name)}`)
      if (!response.ok) throw new Error('Failed to fetch')
      const data = await response.json()
      setSkillDetail(data)
      setSelectedSkill(name)
    } catch (err) {
      showToast('error', 'Failed to load skill details')
    } finally {
      setLoadingDetail(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <BookOpen className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Skills Library</h1>
        </div>
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <Spinner size="lg" className="mx-auto mb-4" />
            <p className="text-muted-foreground">Loading skills...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <BookOpen className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Skills Library</h1>
        </div>
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <BookOpen className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Skills Library</h1>
        </div>
        <div className="flex items-center space-x-2">
          <Button onClick={exportSkills} variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button onClick={fetchSkills} variant="outline" size="sm">
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      <div className="text-sm text-muted-foreground">
        {skills.length} skills available
      </div>

      {skills.length === 0 ? (
        <Card className="p-12">
          <div className="text-center">
            <BookOpen className="h-16 w-16 mx-auto mb-4 text-muted-foreground opacity-50" />
            <h3 className="text-lg font-semibold mb-2">No Skills Found</h3>
            <p className="text-muted-foreground mb-4">
              There are no skills available in your system yet.
            </p>
            <Button onClick={fetchSkills} variant="outline">
              <RefreshCw className="h-4 w-4 mr-2" />
              Refresh
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {skills.map((skill) => (
            <Card
              key={skill.name}
              className="hover:shadow-md transition-all duration-200 hover:scale-[1.02] cursor-pointer"
              onClick={() => fetchSkillDetail(skill.name)}
            >
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <BookOpen className="h-5 w-5" />
                  <span>{skill.name}</span>
                </CardTitle>
                {skill.description && (
                  <CardDescription>{skill.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {skill.category && (
                    <div className="flex items-center space-x-2 text-sm">
                      <Tag className="h-4 w-4" />
                      <span>{skill.category}</span>
                    </div>
                  )}
                  {skill.author && (
                    <div className="flex items-center space-x-2 text-sm">
                      <User className="h-4 w-4" />
                      <span>{skill.author}</span>
                    </div>
                  )}
                  {skill.version && (
                    <div className="text-sm text-muted-foreground">
                      v{skill.version}
                    </div>
                  )}
                  <div className="text-xs text-muted-foreground">
                    {skill.path}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Skill Detail Modal */}
      <Dialog open={!!selectedSkill} onOpenChange={() => setSelectedSkill(null)}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              {selectedSkill}
            </DialogTitle>
          </DialogHeader>
          {loadingDetail ? (
            <div className="flex justify-center py-8">
              <Spinner size="lg" />
            </div>
          ) : skillDetail ? (
            <div className="overflow-y-auto max-h-[60vh] pr-4">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown>{skillDetail.content}</ReactMarkdown>
              </div>
              {skillDetail.scripts?.length > 0 && (
                <div className="mt-6 pt-4 border-t">
                  <h4 className="font-medium mb-2">Scripts in this skill:</h4>
                  <ul className="text-sm text-muted-foreground space-y-1">
                    {skillDetail.scripts.map((s: string) => (
                      <li key={s} className="font-mono">{s}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default Skills