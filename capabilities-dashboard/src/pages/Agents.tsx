import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Bot, Cpu, FolderOpen, Activity, CheckCircle, XCircle, RefreshCw } from 'lucide-react'

interface Agent {
  id: string
  model: string
  workspace: string
  status: 'active' | 'inactive'
  recentRuns?: string[]
}

function Agents() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    try {
      const response = await fetch('/api/agents')
      if (!response.ok) {
        throw new Error('Failed to fetch agents')
      }
      const data = await response.json()
      setAgents(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    return status === 'active'
      ? <CheckCircle className="h-5 w-5 text-green-500" />
      : <XCircle className="h-5 w-5 text-gray-400" />
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    return status === 'active'
      ? `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`
      : `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200`
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Bot className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Agents</h1>
        </div>
        <div>Loading agents...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Bot className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Agents</h1>
        </div>
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  if (agents.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Bot className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Agents</h1>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-muted-foreground">
              No agents configured. Check ~/.openclaw/openclaw.json to configure agents.
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Bot className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Agents</h1>
        </div>
        <Button onClick={fetchAgents} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="text-sm text-muted-foreground">
        {agents.length} agent{agents.length !== 1 ? 's' : ''} configured
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {agents.map((agent) => (
          <Card key={agent.id} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Bot className="h-5 w-5" />
                  <span className="truncate">{agent.id}</span>
                </div>
                {getStatusIcon(agent.status)}
              </CardTitle>
              <CardDescription>
                <span className={getStatusBadge(agent.status)}>
                  {agent.status}
                </span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-start space-x-2 text-sm">
                  <Cpu className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-muted-foreground">Model:</span>{' '}
                    <span className="font-mono text-xs">{agent.model}</span>
                  </div>
                </div>

                <div className="flex items-start space-x-2 text-sm">
                  <FolderOpen className="h-4 w-4 text-muted-foreground mt-0.5 flex-shrink-0" />
                  <div className="min-w-0 flex-1">
                    <span className="text-muted-foreground">Workspace:</span>{' '}
                    <span className="font-mono text-xs break-all">{agent.workspace}</span>
                  </div>
                </div>

                {agent.recentRuns && agent.recentRuns.length > 0 && (
                  <div className="pt-2 border-t border-border">
                    <div className="flex items-center space-x-2 text-sm text-muted-foreground mb-2">
                      <Activity className="h-4 w-4" />
                      <span>Recent Runs</span>
                    </div>
                    <div className="space-y-1">
                      {agent.recentRuns.slice(0, 3).map((run, index) => (
                        <div key={index} className="text-xs text-muted-foreground font-mono">
                          {run}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default Agents
