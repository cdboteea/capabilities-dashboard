import { useQuery } from 'react-query'
import {
  Mail,
  Brain,
  Link as LinkIcon,
  FileText,
  Clock,
  TrendingUp,
  AlertCircle,
  CheckCircle,
} from 'lucide-react'
import { apiService } from '../services/api'
import { format } from 'date-fns'
import StatsCard from '../components/StatsCard'
import ActivityFeed from '../components/ActivityFeed'
import CategoryChart from '../components/CategoryChart'
import ProcessingChart from '../components/ProcessingChart'

const Dashboard = () => {
  const { data: stats, isLoading: statsLoading, error: statsError } = useQuery(
    'dashboard-stats',
    () => apiService.getDashboardStats(),
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  )

  const { data: recentActivity, isLoading: activityLoading } = useQuery(
    'recent-activity',
    () => apiService.getRecentActivity(10),
    {
      refetchInterval: 15000, // Refresh every 15 seconds
    }
  )

  const { data: processingStatus } = useQuery(
    'processing-status',
    () => apiService.getProcessingStatus(),
    {
      refetchInterval: 5000, // Check every 5 seconds
    }
  )

  if (statsLoading) {
    return (
      <div className="animate-pulse">
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="card">
              <div className="card-body">
                <div className="h-4 bg-secondary-200 rounded mb-2"></div>
                <div className="h-8 bg-secondary-200 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (statsError) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="mx-auto h-12 w-12 text-error-400" />
        <h3 className="mt-2 text-sm font-medium text-secondary-900">Unable to load dashboard</h3>
        <p className="mt-1 text-sm text-secondary-500">
          There was an error loading the dashboard data. Please try again.
        </p>
      </div>
    )
  }

  const statsCards = [
    {
      title: 'Total Ideas',
      value: stats?.total_ideas || 0,
      icon: Mail,
      color: 'primary',
    },
    {
      title: 'Processed Today',
      value: stats?.processed_today || 0,
      icon: CheckCircle,
      color: 'success',
      change: stats?.processed_today ? `${stats.processed_today} new` : 'No new items',
      changeType: 'neutral' as const,
    },
    {
      title: 'Total Entities',
      value: stats?.total_entities || 0,
      icon: Brain,
      color: 'accent',
    },
    {
      title: 'Pending Processing',
      value: stats?.pending_processing ?? 0,
      icon: Clock,
      color: (stats?.pending_processing ?? 0) > 0 ? 'warning' : 'secondary',
      change: (stats?.pending_processing ?? 0) > 0 ? 'Needs attention' : undefined,
      changeType: (stats?.pending_processing ?? 0) > 0 ? ('decrease' as const) : ('neutral' as const),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Dashboard</h1>
        <p className="mt-1 text-sm text-secondary-600">
          Overview of your email intelligence and knowledge management system
        </p>
      </div>

      {/* Processing Status Banner */}
      {processingStatus && processingStatus.status === 'processing' && (
        <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-primary-800">
                Processing in progress
              </h3>
              <div className="mt-1 text-sm text-primary-600">
                {processingStatus.current_task && (
                  <p>Current task: {processingStatus.current_task}</p>
                )}
                {processingStatus.progress && (
                  <div className="mt-2">
                    <div className="bg-primary-200 rounded-full h-2">
                      <div
                        className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                        style={{ width: `${processingStatus.progress}%` }}
                      ></div>
                    </div>
                    <p className="mt-1 text-xs">
                      {processingStatus.progress}% complete
                      {processingStatus.estimated_completion && (
                        <span className="ml-2">
                          (ETA: {format(new Date(processingStatus.estimated_completion), 'HH:mm')})
                        </span>
                      )}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statsCards.map((card, index) => (
          <StatsCard
            key={index}
            title={card.title}
            value={card.value}
            icon={card.icon}
            color={card.color}
            change={card.change}
            changeType={card.changeType}
          />
        ))}
      </div>

      {/* Secondary Stats */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-3">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <LinkIcon className="h-8 w-8 text-primary-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-secondary-600">URLs Extracted</p>
                <p className="text-2xl font-bold text-secondary-900">
                  {stats?.total_urls || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <FileText className="h-8 w-8 text-accent-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-secondary-600">Attachments</p>
                <p className="text-2xl font-bold text-secondary-900">
                  {stats?.total_attachments || 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <div className="flex items-center">
              <Clock className="h-8 w-8 text-accent-500" />
              <div className="ml-4">
                <p className="text-sm font-medium text-secondary-600">Last Processing</p>
                <p className="text-2xl font-bold text-secondary-900">
                  {stats?.avg_processing_time ? (
                    stats.avg_processing_time < 60 
                      ? `${Math.round(stats.avg_processing_time)}s ago`
                      : stats.avg_processing_time < 3600 
                        ? `${Math.round(stats.avg_processing_time / 60)}m ago`
                        : `${Math.round(stats.avg_processing_time / 3600)}h ago`
                  ) : '—'}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Charts and Activity */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Category Breakdown */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-secondary-900">Category Breakdown</h3>
            <p className="text-sm text-secondary-600">
              Distribution of ideas by category
            </p>
          </div>
          <div className="card-body">
            <CategoryChart data={stats?.categories_breakdown} />
          </div>
        </div>

        {/* Processing Timeline */}
        <div className="card">
          <div className="card-header">
            <h3 className="text-lg font-medium text-secondary-900">Processing Activity</h3>
            <p className="text-sm text-secondary-600">
              Recent processing activity over time
            </p>
          </div>
          <div className="card-body">
            <ProcessingChart />
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-secondary-900">Recent Activity</h3>
          <p className="text-sm text-secondary-600">
            Latest email processing and system events
          </p>
        </div>
        <div className="card-body">
          <ActivityFeed
            activities={recentActivity || []}
            loading={activityLoading}
          />
        </div>
      </div>
    </div>
  )
}

export default Dashboard 