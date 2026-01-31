import { LucideIcon } from 'lucide-react'
import { clsx } from 'clsx'

interface StatsCardProps {
  title: string
  value: number | string
  icon: LucideIcon
  color: 'primary' | 'secondary' | 'accent' | 'success' | 'warning' | 'error'
  change?: string
  changeType?: 'increase' | 'decrease' | 'neutral'
  loading?: boolean
}

const StatsCard: React.FC<StatsCardProps> = ({
  title,
  value,
  icon: Icon,
  color,
  change,
  changeType = 'neutral',
  loading = false,
}) => {
  const colorClasses = {
    primary: 'text-primary-600 bg-primary-100',
    secondary: 'text-secondary-600 bg-secondary-100',
    accent: 'text-accent-600 bg-accent-100',
    success: 'text-success-600 bg-success-100',
    warning: 'text-warning-600 bg-warning-100',
    error: 'text-error-600 bg-error-100',
  }

  const changeColorClasses = {
    increase: 'text-success-600',
    decrease: 'text-error-600',
    neutral: 'text-secondary-500',
  }

  if (loading) {
    return (
      <div className="card animate-pulse">
        <div className="card-body">
          <div className="flex items-center">
            <div className="flex-shrink-0">
              <div className="h-12 w-12 bg-secondary-200 rounded-lg"></div>
            </div>
            <div className="ml-4 flex-1">
              <div className="h-4 bg-secondary-200 rounded mb-2"></div>
              <div className="h-8 bg-secondary-200 rounded mb-1"></div>
              <div className="h-3 bg-secondary-200 rounded w-20"></div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <div className={clsx('flex h-12 w-12 items-center justify-center rounded-lg', colorClasses[color])}>
              <Icon className="h-6 w-6" />
            </div>
          </div>
          <div className="ml-4 flex-1">
            <p className="text-sm font-medium text-secondary-600">{title}</p>
            <p className="text-2xl font-bold text-secondary-900">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
            {change && (
              <p className={clsx('text-sm', changeColorClasses[changeType])}>
                {change}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default StatsCard 