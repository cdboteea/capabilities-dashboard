import { useState, useEffect } from 'react'
import { X, RotateCcw, ChevronDown } from 'lucide-react'
import { SearchFilters } from '../types'
import { apiService } from '../services/api'

interface EmailFiltersProps {
  filters: SearchFilters
  onFiltersChange: (filters: SearchFilters) => void
}

const EmailFilters: React.FC<EmailFiltersProps> = ({ filters, onFiltersChange }) => {
  const [availableSenders, setAvailableSenders] = useState<string[]>([])
  const [loadingSenders, setLoadingSenders] = useState(false)

  // Load available senders for the filter dropdown
  useEffect(() => {
    const loadSenders = async () => {
      setLoadingSenders(true)
      try {
        // Get recent emails to extract unique senders
        const response = await apiService.getIdeas(1, 100)
        const senders = [...new Set(response.items.map(email => email.sender_email))]
          .filter(Boolean)
          .sort()
        setAvailableSenders(senders)
      } catch (error) {
        console.error('Failed to load senders:', error)
      } finally {
        setLoadingSenders(false)
      }
    }
    loadSenders()
  }, [])

  const hasActiveFilters = () => {
    return (
      (filters.entity_types && filters.entity_types.length > 0) ||
      (filters.senders && filters.senders.length > 0) ||
      (filters.processing_status && filters.processing_status.length > 0) ||
      (filters.date_range && (filters.date_range.start || filters.date_range.end))
    )
  }

  const resetFilters = () => {
    onFiltersChange({})
  }

  const removeFilter = (type: string, value?: string) => {
    const newFilters = { ...filters }
    
    switch (type) {
      case 'entity_types':
        if (value) {
          newFilters.entity_types = filters.entity_types?.filter(e => e !== value)
        } else {
          delete newFilters.entity_types
        }
        break
      case 'senders':
        if (value) {
          newFilters.senders = filters.senders?.filter(s => s !== value)
        } else {
          delete newFilters.senders
        }
        break
      case 'processing_status':
        if (value) {
          newFilters.processing_status = filters.processing_status?.filter(s => s !== value)
        } else {
          delete newFilters.processing_status
        }
        break
      case 'date_range':
        delete newFilters.date_range
        break
    }
    
    onFiltersChange(newFilters)
  }

  const toggleArrayFilter = (type: 'categories' | 'senders' | 'processing_status' | 'entity_types', value: string) => {
    const currentValues = filters[type] || []
    const newValues = currentValues.includes(value)
      ? currentValues.filter(v => v !== value)
      : [...currentValues, value]
    
    onFiltersChange({
      ...filters,
      [type]: newValues.length > 0 ? newValues : undefined
    })
  }

  return (
    <div className="space-y-4">
      {/* Filter Controls Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <span className="text-sm font-medium text-secondary-700">Active Filters:</span>
          {hasActiveFilters() ? (
            <button
              onClick={resetFilters}
              className="flex items-center text-xs text-primary-600 hover:text-primary-700"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Reset All
            </button>
          ) : (
            <span className="text-xs text-secondary-500">None</span>
          )}
        </div>
      </div>

      {/* Active Filter Tags */}
      {hasActiveFilters() && (
        <div className="flex flex-wrap gap-2">
          {filters.entity_types?.map(entityType => (
            <span
              key={entityType}
              className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-blue-100 text-blue-800"
            >
              Entity: {entityType}
              <button
                onClick={() => removeFilter('entity_types', entityType)}
                className="ml-1 text-blue-600 hover:text-blue-800"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          
          {filters.senders?.map(sender => (
            <span
              key={sender}
              className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-green-100 text-green-800"
            >
              Sender: {sender.split('<')[0].trim() || sender}
              <button
                onClick={() => removeFilter('senders', sender)}
                className="ml-1 text-green-600 hover:text-green-800"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          
          {filters.processing_status?.map(status => (
            <span
              key={status}
              className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-purple-100 text-purple-800"
            >
              Status: {status}
              <button
                onClick={() => removeFilter('processing_status', status)}
                className="ml-1 text-purple-600 hover:text-purple-800"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
          
          {filters.date_range && (filters.date_range.start || filters.date_range.end) && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-orange-100 text-orange-800">
              Date: {filters.date_range.start || '...'} to {filters.date_range.end || '...'}
              <button
                onClick={() => removeFilter('date_range')}
                className="ml-1 text-orange-600 hover:text-orange-800"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          )}
        </div>
      )}

      {/* Filter Options */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Entity Types Filter */}
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-2">
            Entity Types
          </label>
          <div className="space-y-1">
            {['concept', 'organization', 'technology'].map(entityType => (
              <label key={entityType} className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                  checked={filters.entity_types?.includes(entityType) || false}
                  onChange={() => toggleArrayFilter('entity_types', entityType)}
                />
                <span className="ml-2 text-sm text-secondary-700 capitalize">{entityType}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Senders Filter */}
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-2">
            Senders {loadingSenders && <span className="text-xs text-secondary-500">(Loading...)</span>}
          </label>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {availableSenders.map(sender => (
              <label key={sender} className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                  checked={filters.senders?.includes(sender) || false}
                  onChange={() => toggleArrayFilter('senders', sender)}
                />
                <span className="ml-2 text-sm text-secondary-700 truncate">
                  {sender.split('<')[0].trim() || sender}
                </span>
              </label>
            ))}
            {availableSenders.length === 0 && !loadingSenders && (
              <p className="text-xs text-secondary-500">No senders found</p>
            )}
          </div>
        </div>

        {/* Status Filter */}
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-2">
            Processing Status
          </label>
          <div className="space-y-1">
            {['completed', 'processing', 'pending', 'failed'].map(status => (
              <label key={status} className="flex items-center">
                <input
                  type="checkbox"
                  className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                  checked={filters.processing_status?.includes(status) || false}
                  onChange={() => toggleArrayFilter('processing_status', status)}
                />
                <span className="ml-2 text-sm text-secondary-700 capitalize">{status}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Date Range Filter */}
        <div>
          <label className="block text-sm font-medium text-secondary-700 mb-2">
            Date Range
          </label>
          <div className="space-y-2">
            <input
              type="date"
              className="input w-full"
              placeholder="Start date"
              value={filters.date_range?.start || ''}
              onChange={(e) => {
                onFiltersChange({
                  ...filters,
                  date_range: {
                    ...filters.date_range,
                    start: e.target.value,
                    end: filters.date_range?.end || '',
                  },
                })
              }}
            />
            <input
              type="date"
              className="input w-full"
              placeholder="End date"
              value={filters.date_range?.end || ''}
              onChange={(e) => {
                onFiltersChange({
                  ...filters,
                  date_range: {
                    start: filters.date_range?.start || '',
                    end: e.target.value,
                  },
                })
              }}
            />
          </div>
        </div>
      </div>

      {/* Search Help */}
      <div className="mt-4 p-3 bg-blue-50 rounded-lg">
        <h4 className="text-sm font-medium text-blue-900 mb-1">Search Tips:</h4>
        <ul className="text-xs text-blue-700 space-y-1">
          <li>• Search works across <strong>email subject</strong>, <strong>content</strong>, and <strong>sender</strong> fields</li>
          <li>• Try searching for: sender names, email subjects, keywords from content</li>
          <li>• Use filters below to narrow down results by category, sender, status, or date</li>
          <li>• Click the filter tags above to remove individual filters, or "Reset All" to clear everything</li>
        </ul>
      </div>
    </div>
  )
}

export default EmailFilters 