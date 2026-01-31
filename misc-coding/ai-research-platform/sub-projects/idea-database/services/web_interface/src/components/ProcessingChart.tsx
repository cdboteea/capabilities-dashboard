import { useQuery } from 'react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'
import { apiService } from '../services/api'

const ProcessingChart: React.FC = () => {
  const { data: timeSeriesData, isLoading } = useQuery(
    'processing-timeseries',
    () => apiService.getTimeSeriesData('ideas', 'day', 7),
    {
      refetchInterval: 60000, // Refresh every minute
    }
  )

  if (isLoading) {
    return (
      <div className="h-64 flex items-center justify-center">
        <div className="animate-pulse">
          <div className="h-4 bg-secondary-200 rounded w-48 mb-2"></div>
          <div className="h-4 bg-secondary-200 rounded w-32"></div>
        </div>
      </div>
    )
  }

  if (!timeSeriesData || timeSeriesData.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-secondary-500">
        <div className="text-center">
          <p className="text-sm">No processing data available</p>
          <p className="text-xs mt-1">Processing activity will appear here over time</p>
        </div>
      </div>
    )
  }

  const chartData = timeSeriesData.map(item => ({
    ...item,
    date: format(new Date(item.date), 'MMM dd'),
  }))

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-secondary-200 rounded-lg shadow-medium">
          <p className="text-sm font-medium text-secondary-900">{label}</p>
          <p className="text-sm text-primary-600">
            {payload[0].value} idea{payload[0].value !== 1 ? 's' : ''} processed
          </p>
        </div>
      )
    }
    return null
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={chartData}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
          <XAxis
            dataKey="date"
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#64748B' }}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fontSize: 12, fill: '#64748B' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="#3B82F6"
            strokeWidth={2}
            dot={{ fill: '#3B82F6', strokeWidth: 0, r: 4 }}
            activeDot={{ r: 6, stroke: '#3B82F6', strokeWidth: 2, fill: '#FFFFFF' }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default ProcessingChart 