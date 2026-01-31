import React from 'react'
import { useQuery } from 'react-query'
import { apiService } from '../services/api'
import { RefreshCw } from 'lucide-react'

const getColor = (pct: number) => {
  if (pct >= 1) return 'bg-red-600'
  if (pct >= 0.8) return 'bg-yellow-500'
  return 'bg-green-500'
}

const XAPIQuotaCard: React.FC = () => {
  const { data, isLoading, error } = useQuery('xApiUsage', () => apiService.getXApiUsage(), {
    refetchInterval: 30000,
  })

  if (isLoading) {
    return (
      <div className="card flex items-center justify-center h-24">
        <RefreshCw className="animate-spin" />
      </div>
    )
  }
  if (error || !data) {
    return (
      <div className="card p-4 text-red-600">X API quota info unavailable</div>
    )
  }

  const pct = data.calls_used / data.calls_limit
  const percentStr = Math.min(100, Math.round(pct * 100)) + '%'

  return (
    <div className="card p-4 space-y-2">
      <h3 className="font-semibold">X API Quota</h3>
      <div className="w-full bg-gray-200 rounded h-3 overflow-hidden">
        <div
          className={`${getColor(pct)} h-3 transition-all duration-300`}
          style={{ width: percentStr }}
        />
      </div>
      <p className="text-sm text-secondary-600">
        {data.calls_used} / {data.calls_limit} calls used this month
      </p>
    </div>
  )
}

export default XAPIQuotaCard 