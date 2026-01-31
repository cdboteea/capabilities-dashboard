import React, { useState } from 'react'
import { useQuery, useQueryClient, useMutation } from 'react-query'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Mail,
  Network,
  Search,
  BarChart3,
  Settings,
  Menu,
  X,
  HardDrive,
  Link as LinkIcon,
  RefreshCw,
  Bell,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
} from 'lucide-react'
import { apiService } from '../services/api'

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const location = useLocation()

  const { data: healthStatus, isLoading: healthLoading } = useQuery(
    'health',
    () => apiService.healthCheck(),
    {
      refetchInterval: 30000, // Check every 30 seconds
      retry: false,
    }
  )

  const navigation = [
    {
      name: 'Dashboard',
      href: '/',
      icon: LayoutDashboard,
      current: location.pathname === '/',
    },
    {
      name: 'Emails',
      href: '/emails',
      icon: Mail,
      current: location.pathname === '/emails',
    },
    {
      name: 'Knowledge Graph',
      href: '/knowledge-graph',
      icon: Network,
      current: location.pathname === '/knowledge-graph',
    },
    {
      name: 'Search',
      href: '/search',
      icon: Search,
      current: location.pathname === '/search',
    },
    {
      name: 'Analytics',
      href: '/analytics',
      icon: BarChart3,
      current: location.pathname === '/analytics',
    },
    {
      name: 'Files',
      href: '/files',
      icon: HardDrive,
      current: location.pathname === '/files',
    },
    {
      name: 'URLs',
      href: '/urls',
      icon: LinkIcon,
      current: location.pathname === '/urls',
    },
    {
      name: 'Settings',
      href: '/settings',
      icon: Settings,
      current: location.pathname === '/settings',
    },
  ]

  const getHealthStatusColor = () => {
    if (healthLoading) return 'bg-yellow-500'
    if (!healthStatus) return 'bg-red-500'
    
    switch (healthStatus.status) {
      case 'healthy':
        return 'bg-green-500'
      case 'degraded':
        return 'bg-yellow-500'
      case 'unhealthy':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Mobile sidebar */}
      <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
        <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
        <div className="fixed inset-y-0 left-0 flex w-64 flex-col bg-gray-50">
          <div className="flex h-16 items-center justify-between px-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-gradient-to-r from-primary-600 to-accent-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">ID</span>
                </div>
              </div>
              <div className="ml-3">
                <h1 className="text-lg font-semibold text-gray-800">Ideas DB</h1>
              </div>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              <X className="h-6 w-6" />
            </button>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`group flex items-center px-2 py-2 text-sm font-medium rounded-lg ${
                    item.current
                      ? 'bg-primary-100 text-primary-900'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
                  }`}
                >
                  <Icon
                    className={`mr-3 h-5 w-5 flex-shrink-0 ${
                      item.current ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'
                    }`}
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>
        </div>
      </div>

      {/* Desktop sidebar */}
      <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
        <div className="flex flex-col flex-grow bg-gray-50 border-r border-gray-200">
          <div className="flex items-center h-16 px-4 border-b border-gray-200">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="h-8 w-8 bg-gradient-to-r from-primary-600 to-accent-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">ID</span>
                </div>
              </div>
              <div className="ml-3">
                <h1 className="text-lg font-semibold text-gray-800">Ideas Database</h1>
              </div>
            </div>
          </div>
          <nav className="flex-1 space-y-1 px-2 py-4">
            {navigation.map((item) => {
              const Icon = item.icon
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`group flex items-center px-2 py-2 text-sm font-medium rounded-lg ${
                    item.current
                      ? 'bg-primary-100 text-primary-900'
                      : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
                  }`}
                >
                  <Icon
                    className={`mr-3 h-5 w-5 flex-shrink-0 ${
                      item.current ? 'text-primary-500' : 'text-gray-400 group-hover:text-gray-500'
                    }`}
                  />
                  {item.name}
                </Link>
              )
            })}
          </nav>
          
          {/* Health status */}
          <div className="p-4 border-t border-gray-200">
            <div className="flex items-center text-sm text-gray-600">
              <div className={`w-2 h-2 rounded-full mr-2 ${getHealthStatusColor()}`} />
              <span>
                {healthLoading ? 'Checking...' : healthStatus?.status || 'Unknown'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <div className="sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-gray-50 px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8">
          <button
            type="button"
            className="-m-2.5 p-2.5 text-gray-600 lg:hidden"
            onClick={() => setSidebarOpen(true)}
          >
            <span className="sr-only">Open sidebar</span>
            <Menu className="h-6 w-6" />
          </button>

          {/* Separator */}
          <div className="h-6 w-px bg-gray-200 lg:hidden" />

          <div className="flex flex-1 gap-x-4 self-stretch lg:gap-x-6">
            <div className="relative flex flex-1 items-center">
              <h2 className="text-lg font-semibold text-gray-800">
                {navigation.find(item => item.current)?.name || 'Dashboard'}
              </h2>
            </div>
            <div className="flex items-center gap-x-4 lg:gap-x-6">
              {/* Auto-sync & manual trigger */}
              <AutoSyncControl />
            </div>
          </div>
        </div>

        {/* Page content */}
        <main className="py-6">
          <div className="px-4 sm:px-6 lg:px-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout

// ---- Internal helper component ----

const AUTO_SYNC_INTERVAL_SEC = 30 // match refetchInterval used in Dashboard

const AutoSyncControl: React.FC = () => {
  const queryClient = useQueryClient()

  const invalidateAll = () => {
    queryClient.invalidateQueries('dashboard-stats')
    queryClient.invalidateQueries('recent-activity')
    queryClient.invalidateQueries('processing-timeseries')
  }

  // Normal sync – only new/unread emails
  const {
    mutate: syncNow,
    isLoading: isSyncing,
  } = useMutation(() => apiService.triggerProcessing(), {
    onSuccess: invalidateAll,
  })

  // Force reprocess – re-ingest everything (rare)
  const {
    mutate: forceReprocess,
    isLoading: isForcing,
  } = useMutation(() => apiService.triggerProcessing({ force_reprocess: true }), {
    onSuccess: invalidateAll,
  })

  return (
    <div className="flex items-center gap-x-2">
      <RefreshCw
        className={`h-4 w-4 text-gray-400 ${isSyncing ? 'animate-spin' : ''}`}
      />
      <span className="text-sm text-gray-600">
        Auto-sync every {AUTO_SYNC_INTERVAL_SEC}s
      </span>
      <button
        onClick={() => syncNow()}
        disabled={isSyncing}
        className="ml-2 px-2 py-1 text-xs font-medium rounded-md bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
      >
        {isSyncing ? 'Syncing…' : 'Sync now'}
      </button>

      <button
        onClick={() => {
          if (isForcing) return
          if (window.confirm('Force reprocess will re-ingest all historical emails and may take significant time. Continue?')) {
            forceReprocess()
          }
        }}
        disabled={isForcing}
        className="ml-2 px-2 py-1 text-xs font-medium rounded-md border border-primary-600 text-primary-600 hover:bg-primary-50 disabled:opacity-50"
      >
        {isForcing ? 'Reprocessing…' : 'Force reprocess'}
      </button>
    </div>
  )
} 