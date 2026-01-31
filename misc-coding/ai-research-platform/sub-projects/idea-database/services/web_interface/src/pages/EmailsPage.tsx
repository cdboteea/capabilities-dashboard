import { useState } from 'react'
import { useQuery, useQueryClient } from 'react-query'
import {
  Search,
  Filter,
  RefreshCw,
  Eye,
  Edit,
  Trash2,
  Download,
  MoreVertical,
  Clock,
  CheckCircle,
  AlertCircle,
  XCircle,
} from 'lucide-react'
import { format } from 'date-fns'
import { apiService } from '../services/api'
import { Idea, SearchFilters } from '../types'
import EmailTable from '../components/EmailTable'
import EmailFilters from '../components/EmailFilters'
import EmailDetail from '../components/EmailDetail'

const EmailsPage = () => {
  const queryClient = useQueryClient()
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [searchQuery, setSearchQuery] = useState('')
  const [filters, setFilters] = useState<SearchFilters>({})
  const [selectedEmail, setSelectedEmail] = useState<Idea | null>(null)
  const [showFilters, setShowFilters] = useState(false)

  const {
    data: emailsResponse,
    isLoading,
    error,
    refetch,
  } = useQuery<any>(
    ['emails', currentPage, pageSize, filters, searchQuery],
    () => {
      if (searchQuery.trim()) {
        return apiService.search(searchQuery, 'semantic', filters, currentPage, pageSize)
      }
      return apiService.getIdeas(currentPage, pageSize, filters)
    },
    {
      keepPreviousData: true,
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  )

  const handleSearch = (query: string) => {
    setSearchQuery(query)
    setCurrentPage(1)
  }

  const handleFilterChange = (newFilters: SearchFilters) => {
    setFilters(newFilters)
    setCurrentPage(1)
  }

  const handlePageChange = (page: number) => {
    setCurrentPage(page)
  }

  const handlePageSizeChange = (size: number) => {
    setPageSize(size)
    setCurrentPage(1)
  }

  const handleEmailSelect = (email: Idea) => {
    setSelectedEmail(email)
  }

  const handleEmailAction = async (action: string, email: Idea) => {
    try {
      switch (action) {
        case 'reprocess':
          await apiService.reprocessIdea(email.id)
          refetch()
          break
        case 'delete':
          if (confirm('Are you sure you want to delete this email?')) {
            await apiService.deleteIdea(email.id)
            refetch()
            // Invalidate dashboard stats and activity after delete
            queryClient.invalidateQueries('dashboard-stats')
            queryClient.invalidateQueries('recent-activity')
          }
          break
        default:
          console.log(`Action ${action} not implemented`)
      }
    } catch (error) {
      console.error(`Failed to ${action} email:`, error)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-success-500" />
      case 'processing':
        return <RefreshCw className="h-4 w-4 text-primary-500 animate-spin" />
      case 'pending':
        return <Clock className="h-4 w-4 text-warning-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-error-500" />
      default:
        return <AlertCircle className="h-4 w-4 text-secondary-500" />
    }
  }

  const getStatusBadge = (status: string) => {
    const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium'
    switch (status) {
      case 'completed':
        return `${baseClasses} bg-success-100 text-success-800`
      case 'processing':
        return `${baseClasses} bg-primary-100 text-primary-800`
      case 'pending':
        return `${baseClasses} bg-warning-100 text-warning-800`
      case 'failed':
        return `${baseClasses} bg-error-100 text-error-800`
      default:
        return `${baseClasses} bg-secondary-100 text-secondary-800`
    }
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="mx-auto h-12 w-12 text-error-400" />
        <h3 className="mt-2 text-sm font-medium text-secondary-900">Unable to load emails</h3>
        <p className="mt-1 text-sm text-secondary-500">
          There was an error loading email data. Please try again.
        </p>
        <button
          onClick={() => refetch()}
          className="mt-4 btn btn-primary"
        >
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Email Ideas</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Browse and manage processed email content and extracted insights
          </p>
        </div>
        <div className="flex items-center space-x-3">
          <button
            onClick={() => refetch()}
            className="btn btn-secondary"
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card">
        <div className="card-body">
          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-secondary-400" />
                <input
                  type="text"
                  placeholder="Search emails, content, entities..."
                  className="input pl-10"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                />
              </div>
            </div>
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`btn ${showFilters ? 'btn-primary' : 'btn-secondary'}`}
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </button>
          </div>

          {showFilters && (
            <div className="mt-4 pt-4 border-t border-secondary-200">
              <EmailFilters
                filters={filters}
                onFiltersChange={handleFilterChange}
              />
            </div>
          )}
        </div>
      </div>

      {/* Results Summary */}
      {emailsResponse && (
        <div className="flex items-center justify-between text-sm text-secondary-600">
          <div>
            Showing {((currentPage - 1) * pageSize) + 1} to{' '}
            {Math.min(currentPage * pageSize, (emailsResponse as any).total_count || (emailsResponse as any).total)} of{' '}
            {(emailsResponse as any).total_count || (emailsResponse as any).total} results
            {searchQuery && (
              <span className="ml-2">
                for "<span className="font-medium">{searchQuery}</span>"
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <span>Show:</span>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="input py-1 px-2 text-sm"
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>
        </div>
      )}

      {/* Email Table */}
      <div className="card">
        <EmailTable
          emails={(emailsResponse as any)?.items || (emailsResponse as any)?.ideas || []}
          loading={isLoading}
          onEmailSelect={handleEmailSelect}
          onEmailAction={handleEmailAction}
          getStatusIcon={getStatusIcon}
          getStatusBadge={getStatusBadge}
        />
      </div>

      {/* Pagination */}
      {emailsResponse && (emailsResponse as any).total_pages > 1 && (
        <div className="flex items-center justify-between">
          <button
            onClick={() => handlePageChange(currentPage - 1)}
            disabled={currentPage === 1}
            className="btn btn-secondary disabled:opacity-50"
          >
            Previous
          </button>
          
          <div className="flex items-center space-x-2">
            {Array.from({ length: Math.min(5, (emailsResponse as any).total_pages) }, (_, i) => {
              const page = i + 1
              return (
                <button
                  key={page}
                  onClick={() => handlePageChange(page)}
                  className={`px-3 py-1 text-sm rounded ${
                    page === currentPage
                      ? 'bg-primary-600 text-white'
                      : 'text-secondary-600 hover:bg-secondary-100'
                  }`}
                >
                  {page}
                </button>
              )
            })}
            {(emailsResponse as any).total_pages > 5 && (
              <>
                <span className="text-secondary-400">...</span>
                <button
                  onClick={() => handlePageChange((emailsResponse as any).total_pages)}
                  className={`px-3 py-1 text-sm rounded ${
                    (emailsResponse as any).total_pages === currentPage
                      ? 'bg-primary-600 text-white'
                      : 'text-secondary-600 hover:bg-secondary-100'
                  }`}
                >
                  {(emailsResponse as any).total_pages}
                </button>
              </>
            )}
          </div>

          <button
            onClick={() => handlePageChange(currentPage + 1)}
            disabled={currentPage === (emailsResponse as any).total_pages}
            className="btn btn-secondary disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}

      {/* Email Detail Modal */}
      {selectedEmail && (
        <EmailDetail
          email={selectedEmail}
          onClose={() => setSelectedEmail(null)}
          onAction={handleEmailAction}
        />
      )}
    </div>
  )
}

export default EmailsPage 