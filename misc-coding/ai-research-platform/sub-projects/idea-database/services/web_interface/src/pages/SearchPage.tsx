import React, { useState, useEffect, useCallback } from 'react'
import { 
  Search, 
  Filter, 
  X, 
  Calendar, 
  User, 
  Tag, 
  FileText, 
  Bookmark,
  Clock,
  TrendingUp,
  Brain,
  Globe,
  Save,
  History,
  RefreshCw,
  AlertCircle
} from 'lucide-react'
import { useDebounce } from '../hooks/useDebounce'
import { SearchFilters, SearchResults, Idea, FilterOption, CategoryAnalytics, SenderAnalytics, EntityAnalytics } from '../types'
import { searchIdeas, getSearchSuggestions, getSavedSearches, saveSearch, apiService } from '../services/api'

const SearchPage = () => {
  const [query, setQuery] = useState('')
  const [searchType, setSearchType] = useState<'semantic' | 'keyword' | 'entity'>('semantic')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [results, setResults] = useState<SearchResults | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [savedSearches, setSavedSearches] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [selectedIdea, setSelectedIdea] = useState<Idea | null>(null)
  const [pageError, setPageError] = useState<string | null>(null)
  const [isInitialized, setIsInitialized] = useState(false)
  
  const debouncedQuery = useDebounce(query, 300)

  // Load saved searches on mount
  useEffect(() => {
    const initializePage = async () => {
      try {
        await loadSavedSearches()
        setIsInitialized(true)
      } catch (error) {
        console.error('Failed to initialize search page:', error)
        setPageError('Failed to initialize search page. Please refresh and try again.')
        setIsInitialized(true)
      }
    }
    initializePage()
  }, [])

  // Get suggestions as user types
  useEffect(() => {
    if (debouncedQuery.length > 2) {
      loadSuggestions(debouncedQuery)
    } else {
      setSuggestions([])
    }
  }, [debouncedQuery])

  const loadSavedSearches = async () => {
    try {
      const data = await getSavedSearches()
      setSavedSearches(data)
    } catch (error) {
      console.error('Failed to load saved searches:', error)
      // Don't set page error for saved searches failure - it's not critical
      setSavedSearches([])
    }
  }

  const loadSuggestions = async (searchQuery: string) => {
    try {
      const data = await getSearchSuggestions(searchQuery)
      setSuggestions(data.slice(0, 5))
    } catch (error) {
      console.error('Failed to load suggestions:', error)
      setSuggestions([])
    }
  }

  const handleSearch = async () => {
    if (!query.trim()) return

    setIsLoading(true)
    try {
      const searchResults = await searchIdeas({
        query,
        type: searchType,
        filters,
        page: 1,
        per_page: 50
      })
      setResults(searchResults)
    } catch (error) {
      console.error('Search failed:', error)
      // Set empty results with error message
      setResults({
        ideas: [],
        total_count: 0,
        facets: {
          categories: {},
          senders: {},
          entity_types: {},
          domains: {}
        },
        query_time_ms: 0
      })
    } finally {
      setIsLoading(false)
    }
  }

  const handleSaveSearch = async () => {
    if (!query.trim()) return

    try {
      const searchName = prompt('Enter a name for this search:')
      if (searchName) {
        await saveSearch({
          name: searchName,
          query,
          type: searchType,
          filters
        })
        loadSavedSearches()
      }
    } catch (error) {
      console.error('Failed to save search:', error)
    }
  }

  const clearFilters = () => {
    setFilters({})
  }

  const getActiveFilterCount = () => {
    return Object.keys(filters).reduce((count, key) => {
      const value = filters[key as keyof SearchFilters]
      if (Array.isArray(value)) return count + value.length
      if (value && typeof value === 'object') return count + 1
      return value ? count + 1 : count
    }, 0)
  }

  // Show loading state while initializing
  if (!isInitialized) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <RefreshCw className="mx-auto h-8 w-8 text-secondary-400 animate-spin" />
          <h3 className="mt-4 text-lg font-medium text-secondary-900">
            Loading Search
          </h3>
          <p className="mt-2 text-sm text-secondary-500">
            Initializing search interface...
          </p>
        </div>
      </div>
    )
  }

  // Show error state if page failed to initialize
  if (pageError) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <AlertCircle className="mx-auto h-8 w-8 text-red-400" />
          <h3 className="mt-4 text-lg font-medium text-secondary-900">
            Search Unavailable
          </h3>
          <p className="mt-2 text-sm text-secondary-500">
            {pageError}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
          >
            Refresh Page
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Advanced Search</h1>
        <p className="mt-1 text-sm text-secondary-600">
          Powerful semantic search across all your email content and extracted knowledge
        </p>
      </div>

      {/* Search Interface */}
      <div className="card">
        <div className="card-body">
          {/* Search Type Toggle */}
          <div className="flex space-x-1 mb-4 p-1 bg-secondary-100 rounded-lg w-fit">
            {[
              { type: 'semantic', icon: Brain, label: 'Semantic' },
              { type: 'keyword', icon: Search, label: 'Keyword' },
              { type: 'entity', icon: Tag, label: 'Entity' }
            ].map(({ type, icon: Icon, label }) => (
              <button
                key={type}
                onClick={() => setSearchType(type as any)}
                                  className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  searchType === type
                    ? 'bg-white text-primary-600 shadow-sm'
                    : 'text-secondary-600 hover:text-secondary-800'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {label}
              </button>
            ))}
          </div>

          {/* Search Bar */}
          <div className="relative">
            <div className="flex">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-secondary-400 w-5 h-5" />
                <input
                  type="text"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
                  placeholder={
                    searchType === 'semantic' 
                      ? 'Describe what you\'re looking for...' 
                      : searchType === 'keyword'
                      ? 'Enter keywords to search...'
                      : 'Search for specific entities...'
                  }
                  className="w-full pl-10 pr-4 py-3 border border-secondary-300 rounded-l-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                {suggestions.length > 0 && (
                  <div className="absolute top-full left-0 right-0 bg-white border border-secondary-200 rounded-lg shadow-lg z-10 mt-1">
                    {suggestions.map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => {
                          setQuery(suggestion)
                          setSuggestions([])
                          setTimeout(handleSearch, 100)
                        }}
                        className="w-full text-left p-3 hover:bg-secondary-50 first:rounded-t-lg last:rounded-b-lg border-b border-secondary-100 last:border-b-0"
                      >
                        <div className="flex items-center">
                          <Clock className="w-4 h-4 text-secondary-400 mr-2" />
                          {suggestion}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`px-4 py-3 border-t border-b border-secondary-300 ${
                  showFilters ? 'bg-secondary-100' : 'bg-white hover:bg-secondary-50'
                } transition-colors relative`}
              >
                <Filter className="w-5 h-5 text-secondary-600" />
                {getActiveFilterCount() > 0 && (
                  <span className="absolute -top-1 -right-1 bg-primary-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
                    {getActiveFilterCount()}
                  </span>
                )}
              </button>
              <button
                onClick={handleSearch}
                disabled={!query.trim() || isLoading}
                className="px-6 py-3 bg-primary-600 text-white rounded-r-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isLoading ? 'Searching...' : 'Search'}
              </button>
            </div>
          </div>

          {/* Search Actions */}
          <div className="flex items-center justify-between mt-4">
            <div className="flex items-center space-x-4">
              {query && (
                <button
                  onClick={handleSaveSearch}
                  className="flex items-center text-sm text-secondary-600 hover:text-secondary-900"
                >
                  <Save className="w-4 h-4 mr-1" />
                  Save Search
                </button>
              )}
            </div>
            
            {/* Saved Searches */}
            {savedSearches.length > 0 && (
              <div className="flex items-center space-x-2">
                <History className="w-4 h-4 text-secondary-400" />
                <span className="text-sm text-secondary-600">Saved:</span>
                {savedSearches.slice(0, 3).map((saved) => (
                  <button
                    key={saved.id}
                    onClick={() => {
                      setQuery(saved.query)
                      setSearchType(saved.type)
                      setFilters(saved.filters || {})
                    }}
                    className="text-sm px-2 py-1 bg-secondary-100 text-secondary-700 rounded hover:bg-secondary-200"
                  >
                    {saved.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div>
          <AdvancedFilters 
            filters={filters}
            onFiltersChange={setFilters}
            onClear={clearFilters}
          />
        </div>
      )}

      {/* Search Results */}
      {results && (
        <SearchResultsView 
          results={results}
          onIdeaSelect={setSelectedIdea}
        />
      )}

      {/* Selected Idea Modal */}
      {selectedIdea && (
        <IdeaDetailModal 
          idea={selectedIdea}
          onClose={() => setSelectedIdea(null)}
        />
      )}
    </div>
  )
}

// Advanced Filters Component
const AdvancedFilters: React.FC<{
  filters: SearchFilters
  onFiltersChange: (filters: SearchFilters) => void
  onClear: () => void
}> = ({ filters, onFiltersChange, onClear }) => {
  const [filterOptions, setFilterOptions] = useState<{
    categories: FilterOption[]
    senders: FilterOption[]
    entityTypes: FilterOption[]
    contentTypes: FilterOption[]
  }>({
    categories: [],
    senders: [],
    entityTypes: [],
    contentTypes: []
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Load filter options from API
    loadFilterOptions()
  }, [])

  const loadFilterOptions = async () => {
    setIsLoading(true)
    setError(null)
    try {
      // Load filter options from API endpoints
      const [categoriesResponse, sendersResponse, entityTypesResponse] = await Promise.all([
        apiService.getCategoryAnalytics(),
        apiService.getSenderAnalytics(),
        apiService.getEntityAnalytics()
      ])

      setFilterOptions({
        categories: categoriesResponse.map(cat => ({
          label: cat.category,
          value: cat.category.toLowerCase(),
          count: cat.count
        })),
        senders: sendersResponse.map(sender => ({
          label: sender.sender_name || sender.sender_email,
          value: sender.sender_email,
          count: sender.total_emails
        })),
        entityTypes: entityTypesResponse.map(entity => ({
          label: entity.entity_value,
          value: entity.entity_type,
          count: entity.frequency
        })),
        contentTypes: [
          { label: 'Email Only', value: 'email', count: 0 },
          { label: 'With URLs', value: 'url', count: 0 },
          { label: 'With Attachments', value: 'attachment', count: 0 },
          { label: 'Mixed Content', value: 'mixed', count: 0 }
        ]
      })
    } catch (error) {
      console.error('Failed to load filter options:', error)
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred'
      setError(`Failed to load filter options: ${errorMessage}. Please check if the backend services are running.`)
      // Set empty options on error
      setFilterOptions({
        categories: [],
        senders: [],
        entityTypes: [],
        contentTypes: []
      })
    } finally {
      setIsLoading(false)
    }
  }

  const updateFilter = (key: keyof SearchFilters, value: any) => {
    onFiltersChange({ ...filters, [key]: value })
  }

  if (isLoading) {
    return (
      <div className="card">
        <div className="card-body">
          <div className="text-center py-8">
            <RefreshCw className="mx-auto h-12 w-12 text-secondary-400 animate-spin" />
            <h3 className="mt-4 text-lg font-medium text-secondary-900">
              Loading Filters
            </h3>
            <p className="mt-2 text-sm text-secondary-500">
              Loading available filter options...
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="card">
        <div className="card-body">
          <div className="text-center py-8">
            <AlertCircle className="mx-auto h-12 w-12 text-red-400" />
            <h3 className="mt-4 text-lg font-medium text-secondary-900">
              Failed to Load Filters
            </h3>
            <p className="mt-2 text-sm text-secondary-500">
              {error}
            </p>
            <button
              onClick={loadFilterOptions}
              className="mt-4 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="card">
      <div className="card-body">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-secondary-900">Advanced Filters</h3>
          <button
            onClick={onClear}
            className="text-sm text-secondary-500 hover:text-secondary-700 flex items-center"
          >
            <X className="w-4 h-4 mr-1" />
            Clear All
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Date Range */}
          <FilterSection title="Date Range" icon={Calendar}>
            <div className="space-y-2">
              <input
                type="date"
                value={filters.date_range?.start || ''}
                onChange={(e) => updateFilter('date_range', {
                  ...filters.date_range,
                  start: e.target.value
                })}
                className="w-full px-3 py-2 border border-secondary-300 rounded-md text-sm"
                placeholder="Start date"
              />
              <input
                type="date"
                value={filters.date_range?.end || ''}
                onChange={(e) => updateFilter('date_range', {
                  ...filters.date_range,
                  end: e.target.value
                })}
                className="w-full px-3 py-2 border border-secondary-300 rounded-md text-sm"
                placeholder="End date"
              />
            </div>
          </FilterSection>

          {/* Categories */}
          <FilterSection title="Categories" icon={Tag}>
            <div className="space-y-2">
              {filterOptions.categories.map((option) => (
                <FilterCheckbox
                  key={option.value}
                  option={option}
                  checked={filters.categories?.includes(option.value) || false}
                  onChange={(checked) => {
                    const current = filters.categories || []
                    if (checked) {
                      updateFilter('categories', [...current, option.value])
                    } else {
                      updateFilter('categories', current.filter(v => v !== option.value))
                    }
                  }}
                />
              ))}
            </div>
          </FilterSection>

          {/* Senders */}
          <FilterSection title="Senders" icon={User}>
            <div className="space-y-2">
              {filterOptions.senders.map((option) => (
                <FilterCheckbox
                  key={option.value}
                  option={option}
                  checked={filters.senders?.includes(option.value) || false}
                  onChange={(checked) => {
                    const current = filters.senders || []
                    if (checked) {
                      updateFilter('senders', [...current, option.value])
                    } else {
                      updateFilter('senders', current.filter(v => v !== option.value))
                    }
                  }}
                />
              ))}
            </div>
          </FilterSection>

          {/* Content Types */}
          <FilterSection title="Content Types" icon={FileText}>
            <div className="space-y-2">
              {filterOptions.contentTypes.map((option) => (
                <FilterCheckbox
                  key={option.value}
                  option={option}
                  checked={filters.content_type?.includes(option.value) || false}
                  onChange={(checked) => {
                    const current = filters.content_type || []
                    if (checked) {
                      updateFilter('content_type', [...current, option.value])
                    } else {
                      updateFilter('content_type', current.filter(v => v !== option.value))
                    }
                  }}
                />
              ))}
            </div>
          </FilterSection>
        </div>

        {/* Priority and Sentiment Ranges */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-6 pt-6 border-t border-secondary-200">
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-2">
              Priority Score Range
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="range"
                min="0"
                max="100"
                value={filters.priority_range?.min || 0}
                onChange={(e) => updateFilter('priority_range', {
                  ...filters.priority_range,
                  min: parseInt(e.target.value)
                })}
                className="flex-1"
              />
              <span className="text-sm text-secondary-600 w-8">
                {filters.priority_range?.min || 0}
              </span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-2">
              Sentiment Score Range
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="range"
                min="-100"
                max="100"
                value={filters.sentiment_range?.min || -100}
                onChange={(e) => updateFilter('sentiment_range', {
                  ...filters.sentiment_range,
                  min: parseInt(e.target.value)
                })}
                className="flex-1"
              />
              <span className="text-sm text-secondary-600 w-12">
                {filters.sentiment_range?.min || -100}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Helper Components
const FilterSection: React.FC<{
  title: string
  icon: React.ComponentType<any>
  children: React.ReactNode
}> = ({ title, icon: Icon, children }) => (
  <div>
    <div className="flex items-center mb-3">
      <Icon className="w-4 h-4 text-secondary-500 mr-2" />
      <h4 className="text-sm font-medium text-secondary-700">{title}</h4>
    </div>
    {children}
  </div>
)

const FilterCheckbox: React.FC<{
  option: FilterOption
  checked: boolean
  onChange: (checked: boolean) => void
}> = ({ option, checked, onChange }) => (
  <label className="flex items-center text-sm">
    <input
      type="checkbox"
      checked={checked}
      onChange={(e) => onChange(e.target.checked)}
      className="mr-2 rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
    />
    <span className="flex-1 text-secondary-700">{option.label}</span>
    {option.count && (
      <span className="text-secondary-500 text-xs">({option.count})</span>
    )}
  </label>
)

// Search Results Component
const SearchResultsView: React.FC<{
  results: SearchResults
  onIdeaSelect: (idea: Idea) => void
}> = ({ results, onIdeaSelect }) => (
  <div className="card">
    <div className="card-body">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-secondary-900">
          Search Results ({results.total_count})
        </h3>
        <div className="text-sm text-secondary-500">
          Found in {results.query_time_ms}ms
        </div>
      </div>

      {/* Search Facets */}
      {results.facets && (
        <div className="mb-6 p-4 bg-secondary-50 rounded-lg">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <div className="font-medium text-secondary-700 mb-2">Categories</div>
              {Object.entries(results.facets.categories).slice(0, 3).map(([key, count]) => (
                <div key={key} className="flex justify-between text-secondary-600">
                  <span>{key}</span>
                  <span>{count}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="font-medium text-secondary-700 mb-2">Senders</div>
              {Object.entries(results.facets.senders).slice(0, 3).map(([key, count]) => (
                <div key={key} className="flex justify-between text-secondary-600">
                  <span className="truncate">{key.split('@')[0]}</span>
                  <span>{count}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="font-medium text-secondary-700 mb-2">Entities</div>
              {Object.entries(results.facets.entity_types).slice(0, 3).map(([key, count]) => (
                <div key={key} className="flex justify-between text-secondary-600">
                  <span>{key}</span>
                  <span>{count}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="font-medium text-secondary-700 mb-2">Domains</div>
              {Object.entries(results.facets.domains).slice(0, 3).map(([key, count]) => (
                <div key={key} className="flex justify-between text-secondary-600">
                  <span>{key}</span>
                  <span>{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Results List */}
      <div className="space-y-4">
        {results.ideas.length === 0 ? (
          <div className="text-center py-8">
            <Search className="mx-auto h-12 w-12 text-secondary-400" />
            <h3 className="mt-4 text-lg font-medium text-secondary-900">
              No Results Found
            </h3>
            <p className="mt-2 text-sm text-secondary-500">
              Try adjusting your search terms or filters to find what you're looking for.
            </p>
          </div>
        ) : (
          results.ideas.map((idea) => (
          <div
            key={idea.id}
            onClick={() => onIdeaSelect(idea)}
            className="p-4 border border-secondary-200 rounded-lg hover:border-primary-300 hover:shadow-sm cursor-pointer transition-all"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h4 className="font-medium text-secondary-900 mb-2">{idea.subject}</h4>
                <p className="text-sm text-secondary-600 mb-2 line-clamp-2">
                  {idea.ai_summary || idea.cleaned_content.substring(0, 200) + '...'}
                </p>
                <div className="flex items-center space-x-4 text-xs text-secondary-500">
                  <span>From: {idea.sender_name || idea.sender_email}</span>
                  <span>{new Date(idea.received_date).toLocaleDateString()}</span>
                  <span className={`px-2 py-1 rounded-full ${
                    idea.category === 'technology' ? 'bg-blue-100 text-blue-800' :
                    idea.category === 'business' ? 'bg-green-100 text-green-800' :
                    idea.category === 'research' ? 'bg-purple-100 text-purple-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {idea.category}
                  </span>
                </div>
              </div>
              <div className="flex items-center space-x-2 ml-4">
                {idea.priority_score && (
                  <div className="text-xs text-secondary-500">
                    Priority: {Math.round(idea.priority_score)}
                  </div>
                )}
                {idea.sentiment_score && (
                  <div className={`text-xs px-2 py-1 rounded-full ${
                    idea.sentiment_score > 0 ? 'bg-green-100 text-green-800' :
                    idea.sentiment_score < 0 ? 'bg-red-100 text-red-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {idea.sentiment_score > 0 ? 'Positive' : 
                     idea.sentiment_score < 0 ? 'Negative' : 'Neutral'}
                  </div>
                )}
              </div>
            </div>
          </div>
          ))
        )}
      </div>
    </div>
  </div>
)

// Idea Detail Modal Component
const IdeaDetailModal: React.FC<{
  idea: Idea
  onClose: () => void
}> = ({ idea, onClose }) => (
  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div className="bg-white rounded-lg shadow-xl max-w-4xl max-h-[90vh] overflow-hidden">
      <div className="p-6 border-b border-secondary-200">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-secondary-900">{idea.subject}</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-secondary-100 rounded-lg"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="mt-2 flex items-center space-x-4 text-sm text-secondary-600">
          <span>From: {idea.sender_name || idea.sender_email}</span>
          <span>{new Date(idea.received_date).toLocaleString()}</span>
          <span className={`px-2 py-1 rounded-full text-xs ${
            idea.category === 'technology' ? 'bg-blue-100 text-blue-800' :
            idea.category === 'business' ? 'bg-green-100 text-green-800' :
            idea.category === 'research' ? 'bg-purple-100 text-purple-800' :
            'bg-gray-100 text-gray-800'
          }`}>
            {idea.category}
          </span>
        </div>
      </div>
      
      <div className="p-6 overflow-y-auto max-h-[60vh]">
        {idea.ai_summary && (
          <div className="mb-6 p-4 bg-primary-50 rounded-lg">
            <h3 className="font-medium text-primary-900 mb-2">AI Summary</h3>
            <p className="text-primary-700">{idea.ai_summary}</p>
          </div>
        )}
        
        <div>
          <h3 className="font-medium text-secondary-900 mb-2">Content</h3>
          <div className="prose max-w-none text-secondary-700">
            {idea.cleaned_content.split('\n').map((paragraph, index) => (
              <p key={index} className="mb-3">{paragraph}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  </div>
)

export default SearchPage 