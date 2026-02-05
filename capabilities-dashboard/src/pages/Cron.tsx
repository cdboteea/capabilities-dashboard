import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Clock, Calendar, CheckCircle, XCircle, AlertCircle, PlayCircle, RefreshCw } from 'lucide-react'

interface CronJob {
  name: string
  schedule: string
  nextRun?: string
  lastStatus?: 'success' | 'failure' | 'running' | 'pending'
  lastRun?: string
  description?: string
}

function Cron() {
  const [cronJobs, setCronJobs] = useState<CronJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCronJobs()
  }, [])

  const fetchCronJobs = async () => {
    try {
      const response = await fetch('/api/cron')
      if (!response.ok) {
        throw new Error('Failed to fetch cron jobs')
      }
      const data = await response.json()
      setCronJobs(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'failure':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'running':
        return <PlayCircle className="h-5 w-5 text-blue-500" />
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />
      default:
        return <AlertCircle className="h-5 w-5 text-gray-400" />
    }
  }

  const getStatusBadge = (status?: string) => {
    const baseClasses = "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium"
    switch (status) {
      case 'success':
        return `${baseClasses} bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200`
      case 'failure':
        return `${baseClasses} bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200`
      case 'running':
        return `${baseClasses} bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200`
      case 'pending':
        return `${baseClasses} bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200`
      default:
        return `${baseClasses} bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200`
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Clock className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Cron Jobs</h1>
        </div>
        <div>Loading cron jobs...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Clock className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Cron Jobs</h1>
        </div>
        <div className="text-red-500">Error: {error}</div>
      </div>
    )
  }

  if (cronJobs.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Clock className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Cron Jobs</h1>
        </div>
        <Card>
          <CardContent className="pt-6">
            <div className="text-center text-muted-foreground">
              No cron jobs scheduled. Configure jobs through the OpenClaw gateway API.
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
          <Clock className="h-6 w-6" />
          <h1 className="text-2xl font-bold">Cron Jobs</h1>
        </div>
        <Button onClick={fetchCronJobs} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="text-sm text-muted-foreground">
        {cronJobs.length} scheduled job{cronJobs.length !== 1 ? 's' : ''}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {cronJobs.map((job, index) => (
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Clock className="h-5 w-5" />
                  <span>{job.name}</span>
                </div>
                {getStatusIcon(job.lastStatus)}
              </CardTitle>
              <CardDescription>
                {job.lastStatus && (
                  <span className={getStatusBadge(job.lastStatus)}>
                    {job.lastStatus}
                  </span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {job.description && (
                  <div className="text-sm text-muted-foreground">
                    {job.description}
                  </div>
                )}

                <div className="flex items-center space-x-2 text-sm">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Schedule:</span>
                  <span className="font-mono text-xs">{job.schedule}</span>
                </div>

                {job.nextRun && (
                  <div className="flex items-center space-x-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">Next run:</span>
                    <span>{job.nextRun}</span>
                  </div>
                )}

                {job.lastRun && (
                  <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                    <span>Last run: {job.lastRun}</span>
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

export default Cron
