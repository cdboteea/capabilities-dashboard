import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts'

interface CategoryChartProps {
  data?: Record<string, number>
}

const CategoryChart: React.FC<CategoryChartProps> = ({ data }) => {
  if (!data || Object.keys(data).length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-secondary-500">
        <div className="text-center">
          <p className="text-sm">No category data available</p>
          <p className="text-xs mt-1">Categories will appear as ideas are processed</p>
        </div>
      </div>
    )
  }

  const chartData = Object.entries(data).map(([category, count]) => ({
    name: category,
    value: count,
  }))

  const COLORS = [
    '#3B82F6', // primary-500
    '#E149F0', // accent-500
    '#22C55E', // success-500
    '#F59E0B', // warning-500
    '#EF4444', // error-500
    '#64748B', // secondary-500
    '#8B5CF6', // purple-500
    '#06B6D4', // cyan-500
    '#84CC16', // lime-500
    '#F97316', // orange-500
  ]

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0]
      return (
        <div className="bg-white p-3 border border-secondary-200 rounded-lg shadow-medium">
          <p className="text-sm font-medium text-secondary-900">{data.name}</p>
          <p className="text-sm text-secondary-600">
            {data.value} idea{data.value !== 1 ? 's' : ''}
          </p>
        </div>
      )
    }
    return null
  }

  const CustomLegend = ({ payload }: any) => {
    return (
      <div className="flex flex-wrap gap-2 justify-center mt-4">
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center space-x-2">
            <div
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-xs text-secondary-600">{entry.value}</span>
          </div>
        ))}
      </div>
    )
  }

  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            labelLine={false}
            outerRadius={80}
            fill="#8884d8"
            dataKey="value"
            label={({ name, percent }) => 
              percent > 0.05 ? `${(percent * 100).toFixed(0)}%` : ''
            }
          >
            {chartData.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend content={<CustomLegend />} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

export default CategoryChart 