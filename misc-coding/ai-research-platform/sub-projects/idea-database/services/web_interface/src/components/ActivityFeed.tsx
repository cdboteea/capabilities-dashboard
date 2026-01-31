import { formatDistanceToNow } from 'date-fns'
import {
  Mail,
  Brain,
  Link as LinkIcon,
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
} from 'lucide-react'
import { ActivityItem } from '../types'

interface ActivityFeedProps {
  activities: ActivityItem[]
  loading?: boolean
}

const ActivityFeed: React.FC<ActivityFeedProps> = ({ activities, loading = false }) => {
  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'email_processed':
        return Mail
      case 'entity_extracted':
        return Brain
      case 'url_fetched':
        return LinkIcon
      case 'attachment_processed':
        return FileText
      case 'error':
        return AlertTriangle
      case 'processing_completed':
        return CheckCircle
      default:
        return Clock
    }
  }

  const getActivityColor = (type: string) => {
    switch (type) {
      case 'email_processed':
        return 'text-primary-600 bg-primary-100'
      case 'entity_extracted':
        return 'text-accent-600 bg-accent-100'
      case 'url_fetched':
        return 'text-secondary-600 bg-secondary-100'
      case 'attachment_processed':
        return 'text-secondary-600 bg-secondary-100'
      case 'error':
        return 'text-error-600 bg-error-100'
      case 'processing_completed':
        return 'text-success-600 bg-success-100'
      default:
        return 'text-secondary-600 bg-secondary-100'
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-start space-x-3 animate-pulse">
            <div className="flex-shrink-0">
              <div className="h-8 w-8 bg-secondary-200 rounded-full"></div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="h-4 bg-secondary-200 rounded mb-1"></div>
              <div className="h-3 bg-secondary-200 rounded w-24"></div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (!activities || activities.length === 0) {
    return (
      <div className="text-center py-8">
        <Clock className="mx-auto h-12 w-12 text-secondary-400" />
        <h3 className="mt-2 text-sm font-medium text-secondary-900">No recent activity</h3>
        <p className="mt-1 text-sm text-secondary-500">
          Activity will appear here as the system processes emails and extracts content.
        </p>
      </div>
    )
  }

  return (
    <div className="flow-root">
      <ul className="-mb-8">
        {activities.map((activity, activityIdx) => {
          const Icon = getActivityIcon(activity.type)
          const colorClasses = getActivityColor(activity.type)
          
          return (
            <li key={activity.id}>
              <div className="relative pb-8">
                {activityIdx !== activities.length - 1 ? (
                  <span
                    className="absolute left-4 top-4 -ml-px h-full w-0.5 bg-secondary-200"
                    aria-hidden="true"
                  />
                ) : null}
                <div className="relative flex items-start space-x-3">
                  <div>
                    <div className={`relative flex h-8 w-8 items-center justify-center rounded-full ${colorClasses}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div>
                      <p className="text-sm text-secondary-900">{activity.description}</p>
                      <div className="mt-1 flex items-center space-x-2 text-xs text-secondary-500">
                        <time dateTime={activity.timestamp}>
                          {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
                        </time>
                        {activity.metadata?.category && (
                          <>
                            <span>•</span>
                            <span className="badge badge-secondary">
                              {activity.metadata.category}
                            </span>
                          </>
                        )}
                        {activity.metadata?.sender && (
                          <>
                            <span>•</span>
                            <span className="text-secondary-600">
                              from {activity.metadata.sender}
                            </span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default ActivityFeed 