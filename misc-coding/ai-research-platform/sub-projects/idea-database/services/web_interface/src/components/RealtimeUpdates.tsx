import React, { useState, useEffect, useContext, createContext, useCallback } from 'react'
import { 
  Bell, 
  Wifi, 
  WifiOff, 
  Check, 
  X, 
  Info, 
  AlertTriangle,
  Zap,
  RefreshCw,
  Clock
} from 'lucide-react'

// Real-time context and types
interface RealtimeUpdate {
  id: string
  type: 'email_processed' | 'entity_extracted' | 'url_fetched' | 'processing_complete' | 'error'
  message: string
  data?: any
  timestamp: string
  read: boolean
}

interface ProcessingStatus {
  is_processing: boolean
  current_batch: number
  total_batches: number
  eta_minutes: number
  current_operation: string
}

interface RealtimeContextType {
  isConnected: boolean
  updates: RealtimeUpdate[]
  processingStatus: ProcessingStatus | null
  markAsRead: (id: string) => void
  clearAllUpdates: () => void
  unreadCount: number
}

const RealtimeContext = createContext<RealtimeContextType | null>(null)

// Real-time Provider Component
export const RealtimeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [isConnected, setIsConnected] = useState(false)
  const [updates, setUpdates] = useState<RealtimeUpdate[]>([])
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null)
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  const [lastPingTime, setLastPingTime] = useState<Date>(new Date())

  const maxReconnectAttempts = 5
  const reconnectDelay = 1000

  const connectWebSocket = useCallback(() => {
    try {
      const websocket = new WebSocket('ws://localhost:3002/ws')
      
      websocket.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        setReconnectAttempts(0)
        setLastPingTime(new Date())
      }

      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          handleRealtimeUpdate(data)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }

      websocket.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        
        // Attempt to reconnect
        if (reconnectAttempts < maxReconnectAttempts) {
          setTimeout(() => {
            setReconnectAttempts(prev => prev + 1)
            connectWebSocket()
          }, reconnectDelay * Math.pow(2, reconnectAttempts))
        }
      }

      websocket.onerror = (error) => {
        console.error('WebSocket error:', error)
        setIsConnected(false)
      }

      setWs(websocket)
    } catch (error) {
      console.error('Failed to connect WebSocket:', error)
      setIsConnected(false)
    }
  }, [reconnectAttempts])

  const handleRealtimeUpdate = (data: any) => {
    setLastPingTime(new Date())

    switch (data.type) {
      case 'processing_status':
        setProcessingStatus(data.status)
        break
      
      case 'notification':
        const newUpdate: RealtimeUpdate = {
          id: data.id || generateId(),
          type: data.notification_type,
          message: data.message,
          data: data.data,
          timestamp: data.timestamp || new Date().toISOString(),
          read: false
        }
        setUpdates(prev => [newUpdate, ...prev.slice(0, 49)]) // Keep last 50 updates
        break
      
      case 'bulk_update':
        if (data.updates && Array.isArray(data.updates)) {
          const newUpdates = data.updates.map((update: any) => ({
            id: update.id || generateId(),
            type: update.type,
            message: update.message,
            data: update.data,
            timestamp: update.timestamp || new Date().toISOString(),
            read: false
          }))
          setUpdates(prev => [...newUpdates, ...prev].slice(0, 50))
        }
        break
      
      case 'ping':
        // Keep connection alive
        if (ws && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'pong', timestamp: new Date().toISOString() }))
        }
        break
    }
  }

  const generateId = () => Math.random().toString(36).substr(2, 9)

  const markAsRead = (id: string) => {
    setUpdates(prev => prev.map(update => 
      update.id === id ? { ...update, read: true } : update
    ))
  }

  const clearAllUpdates = () => {
    setUpdates([])
  }

  const unreadCount = updates.filter(update => !update.read).length

  // Initialize WebSocket connection
  useEffect(() => {
    connectWebSocket()
    
    return () => {
      if (ws) {
        ws.close()
      }
    }
  }, [])

  // Heartbeat to detect connection issues
  useEffect(() => {
    const heartbeatInterval = setInterval(() => {
      if (isConnected && ws && ws.readyState === WebSocket.OPEN) {
        const now = new Date()
        const timeSinceLastPing = now.getTime() - lastPingTime.getTime()
        
        if (timeSinceLastPing > 30000) { // 30 seconds without ping
          console.warn('WebSocket connection seems stale, attempting reconnect')
          ws.close()
        }
      }
    }, 10000) // Check every 10 seconds

    return () => clearInterval(heartbeatInterval)
  }, [isConnected, ws, lastPingTime])

  const contextValue: RealtimeContextType = {
    isConnected,
    updates,
    processingStatus,
    markAsRead,
    clearAllUpdates,
    unreadCount
  }

  return (
    <RealtimeContext.Provider value={contextValue}>
      {children}
    </RealtimeContext.Provider>
  )
}

// Hook to use realtime context
export const useRealtime = () => {
  const context = useContext(RealtimeContext)
  if (!context) {
    throw new Error('useRealtime must be used within a RealtimeProvider')
  }
  return context
}

// Connection Status Indicator Component
export const ConnectionStatus: React.FC = () => {
  const { isConnected } = useRealtime()

  return (
    <div className={`flex items-center px-2 py-1 rounded-full text-xs ${
      isConnected 
        ? 'bg-green-100 text-green-800' 
        : 'bg-red-100 text-red-800'
    }`}>
      {isConnected ? (
        <>
          <Wifi className="w-3 h-3 mr-1" />
          Connected
        </>
      ) : (
        <>
          <WifiOff className="w-3 h-3 mr-1" />
          Disconnected
        </>
      )}
    </div>
  )
}

// Processing Status Component
export const ProcessingStatusIndicator: React.FC = () => {
  const { processingStatus } = useRealtime()

  if (!processingStatus || !processingStatus.is_processing) {
    return null
  }

  const progress = processingStatus.total_batches > 0 
    ? (processingStatus.current_batch / processingStatus.total_batches) * 100 
    : 0

  return (
    <div className="bg-primary-50 border border-primary-200 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center">
          <RefreshCw className="w-4 h-4 text-primary-600 animate-spin mr-2" />
          <span className="text-sm font-medium text-primary-900">Processing in Progress</span>
        </div>
        <span className="text-xs text-primary-600">
          {processingStatus.current_batch}/{processingStatus.total_batches}
        </span>
      </div>
      
      <div className="w-full bg-primary-200 rounded-full h-2 mb-2">
        <div 
          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
      
      <div className="flex items-center justify-between text-xs text-primary-700">
        <span>{processingStatus.current_operation}</span>
        {processingStatus.eta_minutes > 0 && (
          <span className="flex items-center">
            <Clock className="w-3 h-3 mr-1" />
            ETA: {processingStatus.eta_minutes}m
          </span>
        )}
      </div>
    </div>
  )
}

// Notifications Panel Component
export const NotificationsPanel: React.FC<{
  isOpen: boolean
  onClose: () => void
}> = ({ isOpen, onClose }) => {
  const { updates, markAsRead, clearAllUpdates, unreadCount } = useRealtime()

  if (!isOpen) return null

  const getUpdateIcon = (type: RealtimeUpdate['type']) => {
    switch (type) {
      case 'email_processed':
        return <Check className="w-4 h-4 text-green-600" />
      case 'entity_extracted':
        return <Zap className="w-4 h-4 text-blue-600" />
      case 'url_fetched':
        return <RefreshCw className="w-4 h-4 text-purple-600" />
      case 'processing_complete':
        return <Check className="w-4 h-4 text-green-600" />
      case 'error':
        return <AlertTriangle className="w-4 h-4 text-red-600" />
      default:
        return <Info className="w-4 h-4 text-gray-600" />
    }
  }

  const getUpdateColor = (type: RealtimeUpdate['type']) => {
    switch (type) {
      case 'email_processed':
      case 'processing_complete':
        return 'border-l-green-500'
      case 'entity_extracted':
        return 'border-l-blue-500'
      case 'url_fetched':
        return 'border-l-purple-500'
      case 'error':
        return 'border-l-red-500'
      default:
        return 'border-l-gray-500'
    }
  }

  return (
    <div className="absolute right-0 top-full mt-2 w-96 bg-white rounded-lg shadow-xl border border-secondary-200 z-50">
      <div className="p-4 border-b border-secondary-200">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium text-secondary-900">
            Notifications
            {unreadCount > 0 && (
              <span className="ml-2 px-2 py-1 bg-primary-500 text-white text-xs rounded-full">
                {unreadCount}
              </span>
            )}
          </h3>
          <div className="flex items-center space-x-2">
            {updates.length > 0 && (
              <button
                onClick={clearAllUpdates}
                className="text-sm text-secondary-500 hover:text-secondary-700"
              >
                Clear All
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 hover:bg-secondary-100 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      <div className="max-h-96 overflow-y-auto">
        {updates.length === 0 ? (
          <div className="p-8 text-center">
            <Bell className="w-8 h-8 text-secondary-400 mx-auto mb-2" />
            <p className="text-secondary-600">No notifications yet</p>
          </div>
        ) : (
          <div className="space-y-2 p-2">
            {updates.map((update) => (
              <div
                key={update.id}
                onClick={() => markAsRead(update.id)}
                className={`p-3 rounded-lg border-l-4 cursor-pointer transition-all ${
                  getUpdateColor(update.type)
                } ${
                  update.read 
                    ? 'bg-secondary-50 opacity-60' 
                    : 'bg-white hover:bg-secondary-50'
                }`}
              >
                <div className="flex items-start">
                  <div className="mr-3 mt-0.5">
                    {getUpdateIcon(update.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm ${
                      update.read ? 'text-secondary-600' : 'text-secondary-900 font-medium'
                    }`}>
                      {update.message}
                    </p>
                    <p className="text-xs text-secondary-500 mt-1">
                      {new Date(update.timestamp).toLocaleString()}
                    </p>
                    {update.data && (
                      <div className="mt-2 p-2 bg-secondary-100 rounded text-xs">
                        <pre className="whitespace-pre-wrap">
                          {JSON.stringify(update.data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                  {!update.read && (
                    <div className="w-2 h-2 bg-primary-500 rounded-full ml-2 mt-2" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Live Activity Feed Component (for dashboard)
export const LiveActivityFeed: React.FC<{ maxItems?: number }> = ({ maxItems = 5 }) => {
  const { updates } = useRealtime()

  const recentUpdates = updates.slice(0, maxItems)

  return (
    <div className="space-y-3">
      {recentUpdates.map((update) => (
        <div key={update.id} className="flex items-start space-x-3">
          <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
            {update.type === 'email_processed' && <Check className="w-4 h-4 text-green-600" />}
            {update.type === 'entity_extracted' && <Zap className="w-4 h-4 text-blue-600" />}
            {update.type === 'url_fetched' && <RefreshCw className="w-4 h-4 text-purple-600" />}
            {update.type === 'error' && <AlertTriangle className="w-4 h-4 text-red-600" />}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-secondary-900">{update.message}</p>
            <p className="text-xs text-secondary-500">
              {new Date(update.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      ))}
      {recentUpdates.length === 0 && (
        <div className="text-center py-4 text-secondary-500">
          <Bell className="w-6 h-6 mx-auto mb-2 opacity-50" />
          <p className="text-sm">No recent activity</p>
        </div>
      )}
    </div>
  )
}

// Notification Button Component (for header)
export const NotificationButton: React.FC = () => {
  const { unreadCount } = useRealtime()
  const [isOpen, setIsOpen] = useState(false)

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-secondary-600 hover:text-secondary-900 hover:bg-secondary-100 rounded-lg"
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>
      
      <NotificationsPanel 
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </div>
  )
} 