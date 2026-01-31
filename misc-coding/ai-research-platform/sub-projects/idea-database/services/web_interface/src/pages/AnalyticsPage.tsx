import React, { useState, useEffect } from 'react'
import { 
  BarChart3, 
  TrendingUp, 
  TrendingDown, 
  Users, 
  Mail, 
  Tag, 
  Calendar,
  Clock,
  Target,
  Brain,
  Zap,
  Filter,
  Download,
  RefreshCw,
  AlertCircle
} from 'lucide-react'
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Area,
  AreaChart
} from 'recharts'
import { 
  getAnalytics, 
  getCategoryAnalytics, 
  getSenderAnalytics, 
  getEntityAnalytics,
  getTimeSeriesData
} from '../services/api'
import { 
  CategoryAnalytics, 
  SenderAnalytics, 
  EntityAnalytics, 
  TimeSeriesData 
} from '../types'

interface AnalyticsData {
  overview: {
    totalIdeas: number
    processed30d: number
    avgProcessingTime: number
    processingSuccessRate: number
    topCategory: string
    topSender: string
    sentimentAverage: number
    entityExtractionRate: number
  }
  trends: {
    dailyProcessing: TimeSeriesData[]
    weeklyStats: TimeSeriesData[]
    categoryTrends: TimeSeriesData[]
  }
}

const AnalyticsPage = () => {
  const [analyticsData, setAnalyticsData] = useState<AnalyticsData | null>(null)
  const [categoryData, setCategoryData] = useState<CategoryAnalytics[]>([])
  const [senderData, setSenderData] = useState<SenderAnalytics[]>([])
  const [entityData, setEntityData] = useState<EntityAnalytics[]>([])
  const [timeRange, setTimeRange] = useState('30d')
  const [selectedMetric, setSelectedMetric] = useState('processing')
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date())

  useEffect(() => {
    loadAnalyticsData()
  }, [timeRange])

  const loadAnalyticsData = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const [analytics, categories, senders, entities] = await Promise.all([
        getAnalytics(timeRange),
        getCategoryAnalytics(),
        getSenderAnalytics(),
        getEntityAnalytics()
      ])

      setAnalyticsData(analytics)
      setCategoryData(categories)
      setSenderData(senders)
      setEntityData(entities)
      setLastUpdated(new Date())
    } catch (error) {
      console.error('Failed to load analytics:', error)
      setError('Failed to load analytics data. Please check if the backend services are running.')
    } finally {
      setIsLoading(false)
    }
  }

  const exportData = () => {
    const dataToExport = {
      overview: analyticsData?.overview,
      categories: categoryData,
      senders: senderData,
      entities: entityData,
      exportedAt: new Date().toISOString()
    }

    const blob = new Blob([JSON.stringify(dataToExport, null, 2)], {
      type: 'application/json'
    })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `ideas-analytics-${timeRange}-${Date.now()}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Analytics</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Loading comprehensive insights about your email intelligence system...
          </p>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-center py-12">
              <BarChart3 className="mx-auto h-16 w-16 text-secondary-400 animate-pulse" />
              <h3 className="mt-4 text-lg font-medium text-secondary-900">
                Analyzing Data
              </h3>
              <p className="mt-2 text-sm text-secondary-500">
                Processing analytics across all your email data...
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Analytics</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Comprehensive insights and analytics about your email intelligence system
          </p>
        </div>
        <div className="card">
          <div className="card-body">
            <div className="text-center py-12">
              <AlertCircle className="mx-auto h-16 w-16 text-red-400" />
              <h3 className="mt-4 text-lg font-medium text-secondary-900">
                Failed to Load Analytics
              </h3>
              <p className="mt-2 text-sm text-secondary-500">
                {error}
              </p>
              <button
                onClick={loadAnalyticsData}
                className="mt-4 px-6 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#06B6D4', '#84CC16', '#F97316']

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Analytics Dashboard</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Comprehensive insights and analytics about your email intelligence system
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <select
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
            className="px-3 py-2 border border-secondary-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500"
          >
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
            <option value="1y">Last year</option>
          </select>
          <button
            onClick={loadAnalyticsData}
            className="p-2 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded-lg"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            onClick={exportData}
            className="p-2 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded-lg"
          >
            <Download className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard
          title="Total Ideas"
          value={analyticsData?.overview.totalIdeas || 0}
          icon={Brain}
          trend={15.2}
          trendUp={true}
        />
        <MetricCard
          title="Processed (30d)"
          value={analyticsData?.overview.processed30d || 0}
          icon={Zap}
          trend={8.4}
          trendUp={true}
        />
        <MetricCard
          title="Avg Processing Time"
          value={`${analyticsData?.overview.avgProcessingTime || 0}s`}
          icon={Clock}
          trend={12.1}
          trendUp={false}
        />
        <MetricCard
          title="Success Rate"
          value={`${(analyticsData?.overview.processingSuccessRate || 0)}%`}
          icon={Target}
          trend={2.3}
          trendUp={true}
        />
      </div>

      {/* Processing Trends */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <div className="card-body">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-secondary-900">Processing Trends</h3>
              <select
                value={selectedMetric}
                onChange={(e) => setSelectedMetric(e.target.value)}
                className="px-3 py-2 border border-secondary-300 rounded text-sm"
              >
                <option value="processing">Ideas Processed</option>
                <option value="entities">Entities Extracted</option>
                <option value="urls">URLs Processed</option>
              </select>
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={analyticsData?.trends.dailyProcessing || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date" 
                  tickFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <YAxis />
                <Tooltip 
                  labelFormatter={(value) => new Date(value).toLocaleDateString()}
                />
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#3B82F6" 
                  fill="#3B82F6" 
                  fillOpacity={0.3}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="card">
          <div className="card-body">
            <h3 className="text-lg font-medium text-secondary-900 mb-6">Category Distribution</h3>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="count"
                  label={({ category, percentage }) => `${category} (${percentage}%)`}
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Detailed Analytics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Category Performance */}
        <div className="card">
          <div className="card-body">
            <h3 className="text-lg font-medium text-secondary-900 mb-6">Category Performance</h3>
            <div className="space-y-4">
              {categoryData.slice(0, 6).map((category, index) => (
                <CategoryPerformanceItem
                  key={category.category}
                  category={category}
                  color={colors[index % colors.length]}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Top Senders */}
        <div className="card">
          <div className="card-body">
            <h3 className="text-lg font-medium text-secondary-900 mb-6">Top Senders</h3>
            <div className="space-y-4">
              {senderData.slice(0, 6).map((sender, index) => (
                <SenderAnalyticsItem
                  key={sender.sender_email}
                  sender={sender}
                  rank={index + 1}
                />
              ))}
            </div>
          </div>
        </div>

        {/* Entity Insights */}
        <div className="card">
          <div className="card-body">
            <h3 className="text-lg font-medium text-secondary-900 mb-6">Entity Insights</h3>
            <div className="space-y-4">
              {entityData.slice(0, 6).map((entity, index) => (
                <EntityAnalyticsItem
                  key={`${entity.entity_type}-${entity.entity_value}`}
                  entity={entity}
                  color={colors[index % colors.length]}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Comprehensive Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Weekly Comparison */}
        <div className="card">
          <div className="card-body">
            <h3 className="text-lg font-medium text-secondary-900 mb-6">Weekly Comparison</h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={analyticsData?.trends.weeklyStats || []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#10B981" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Sentiment Analysis */}
        <div className="card">
          <div className="card-body">
            <h3 className="text-lg font-medium text-secondary-900 mb-6">Sentiment Distribution</h3>
            <div className="space-y-4">
              <SentimentAnalytics 
                positive={65}
                neutral={25}
                negative={10}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Footer Info */}
      <div className="text-center text-sm text-secondary-500">
        Last updated: {lastUpdated.toLocaleString()} • 
        Analyzing {analyticsData?.overview.totalIdeas || 0} ideas across {timeRange}
      </div>
    </div>
  )
}

// Metric Card Component
const MetricCard: React.FC<{
  title: string
  value: string | number
  icon: React.ComponentType<any>
  trend?: number
  trendUp?: boolean
}> = ({ title, value, icon: Icon, trend, trendUp }) => (
  <div className="card">
    <div className="card-body">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-secondary-600">{title}</p>
          <p className="text-2xl font-bold text-secondary-900">{value}</p>
          {trend && (
            <div className={`flex items-center mt-2 text-sm ${
              trendUp ? 'text-green-600' : 'text-red-600'
            }`}>
              {trendUp ? <TrendingUp className="w-4 h-4 mr-1" /> : <TrendingDown className="w-4 h-4 mr-1" />}
              {trend}% vs last period
            </div>
          )}
        </div>
        <div className="p-3 bg-primary-100 rounded-lg">
          <Icon className="w-6 h-6 text-primary-600" />
        </div>
      </div>
    </div>
  </div>
)

// Category Performance Item
const CategoryPerformanceItem: React.FC<{
  category: CategoryAnalytics
  color: string
}> = ({ category, color }) => (
  <div className="flex items-center justify-between">
    <div className="flex items-center">
      <div 
        className="w-3 h-3 rounded-full mr-3" 
        style={{ backgroundColor: color }}
      />
      <div>
        <div className="font-medium text-secondary-900">{category.category}</div>
        <div className="text-sm text-secondary-600">{category.count} ideas</div>
      </div>
    </div>
    <div className="flex items-center space-x-2">
      <span className="text-sm text-secondary-600">{category.percentage}%</span>
      <div className={`flex items-center ${
        category.trend === 'up' ? 'text-green-600' : 
        category.trend === 'down' ? 'text-red-600' : 'text-secondary-500'
      }`}>
        {category.trend === 'up' && <TrendingUp className="w-4 h-4" />}
        {category.trend === 'down' && <TrendingDown className="w-4 h-4" />}
        <span className="text-xs ml-1">{category.change_percent}%</span>
      </div>
    </div>
  </div>
)

// Sender Analytics Item
const SenderAnalyticsItem: React.FC<{
  sender: SenderAnalytics
  rank: number
}> = ({ sender, rank }) => (
  <div className="flex items-center justify-between">
    <div className="flex items-center">
      <div className="w-8 h-8 rounded-full bg-secondary-100 flex items-center justify-center mr-3">
        <span className="text-sm font-medium text-secondary-600">#{rank}</span>
      </div>
      <div>
        <div className="font-medium text-secondary-900">
          {sender.sender_name || sender.sender_email.split('@')[0]}
        </div>
        <div className="text-sm text-secondary-600">{sender.total_emails} emails</div>
      </div>
    </div>
    <div className="text-right">
      <div className="text-sm text-secondary-900">
        Priority: {sender.avg_priority.toFixed(1)}
      </div>
      <div className={`text-xs ${
        sender.avg_sentiment > 0 ? 'text-green-600' : 
        sender.avg_sentiment < 0 ? 'text-red-600' : 'text-secondary-500'
      }`}>
        Sentiment: {sender.avg_sentiment > 0 ? '+' : ''}{sender.avg_sentiment.toFixed(1)}
      </div>
    </div>
  </div>
)

// Entity Analytics Item
const EntityAnalyticsItem: React.FC<{
  entity: EntityAnalytics
  color: string
}> = ({ entity, color }) => (
  <div className="flex items-center justify-between">
    <div className="flex items-center">
      <div 
        className="w-3 h-3 rounded-full mr-3" 
        style={{ backgroundColor: color }}
      />
      <div>
        <div className="font-medium text-secondary-900">{entity.entity_value}</div>
        <div className="text-sm text-secondary-600 capitalize">{entity.entity_type}</div>
      </div>
    </div>
    <div className="text-right">
      <div className="text-sm text-secondary-900">{entity.frequency}x</div>
      <div className="text-xs text-secondary-600">
        {(entity.avg_confidence * 100).toFixed(0)}% confidence
      </div>
    </div>
  </div>
)

// Sentiment Analytics Component
const SentimentAnalytics: React.FC<{
  positive: number
  neutral: number
  negative: number
}> = ({ positive, neutral, negative }) => {
  const total = positive + neutral + negative
  
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-secondary-600">Positive</span>
        <span className="text-sm font-medium text-green-600">{positive}%</span>
      </div>
      <div className="w-full bg-secondary-200 rounded-full h-2">
        <div 
          className="bg-green-500 h-2 rounded-full" 
          style={{ width: `${(positive / total) * 100}%` }}
        />
      </div>
      
      <div className="flex items-center justify-between">
        <span className="text-sm text-secondary-600">Neutral</span>
        <span className="text-sm font-medium text-secondary-600">{neutral}%</span>
      </div>
      <div className="w-full bg-secondary-200 rounded-full h-2">
        <div 
          className="bg-secondary-500 h-2 rounded-full" 
          style={{ width: `${(neutral / total) * 100}%` }}
        />
      </div>
      
      <div className="flex items-center justify-between">
        <span className="text-sm text-secondary-600">Negative</span>
        <span className="text-sm font-medium text-red-600">{negative}%</span>
      </div>
      <div className="w-full bg-secondary-200 rounded-full h-2">
        <div 
          className="bg-red-500 h-2 rounded-full" 
          style={{ width: `${(negative / total) * 100}%` }}
        />
      </div>
    </div>
  )
}

export default AnalyticsPage 