import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plug, CheckCircle, XCircle, Clock, AlertCircle, RefreshCw } from 'lucide-react'

interface Integration {
  name: string
  status: 'connected' | 'disconnected' | 'unknown'
  lastUsed?: string
  quota?: {
    used: number
    limit: number
    unit: string
  }
  message?: string
}

function Integrations() {
  const [integrations, setIntegrations] = useState<Integration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchIntegrations()
  }, [])

  const fetchIntegrations = async () => {
    try {
      const response = await fetch('/api/integrations')
      if (!response.ok) {
        throw new Error('Failed to fetch integrations')
      }
      const data = await response.json()
      setIntegrations(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'disconnected':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    switch (status) {
      case 'connected':
        return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`
      case 'disconnected':
        return `${baseClasses} bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200`
      default:
        return `${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200`
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Plug className="h-6 w-6" />
          <h1 className="text-2xl font-bold">API Integrations</h1>
        </div>
        <div>Loading integrations...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Plug className="h-6 w-6" />
          <h1 className="text-2xl font-bold">API Integrations</h1>
        </div>
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Plug className="h-6 w-6" />
          <h1 className="text-2xl font-bold">API Integrations</h1>
        </div>
        <Button onClick={fetchIntegrations} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="text-sm text-muted-foreground">
        {integrations.length} integrations configured
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {integrations.map((integration) => (
          <Card key={integration.name} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Plug className="h-5 w-5" />
                  <span>{integration.name}</span>
                </div>
                {getStatusIcon(integration.status)}
              </CardTitle>
              <CardDescription>
                <span className={getStatusBadge(integration.status)}>
                  {integration.status}
                </span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {integration.lastUsed && (
                  <div className="flex items-center space-x-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Last used:</span>
                    <span>{integration.lastUsed}</span>
                  </div>
                )}

                {integration.quota && (
                  <div className="space-y-1">
                    <div className="text-sm text-muted-foreground">
                      Quota: {integration.quota.used} / {integration.quota.limit} {integration.quota.unit}
                    </div>
                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                      <div
                        className="bg-blue-600 h-2 rounded-full transition-all"
                        style={{
                          width: `${Math.min((integration.quota.used / integration.quota.limit) * 100, 100)}%`
                        }}
                      />
                    </div>
                  </div>
                )}

                {integration.message && (
                  <div className="text-sm text-muted-foreground italic">
                    {integration.message}
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

export default Integrations
