import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
  Link as LinkIcon,
  ExternalLink,
  Eye,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Filter,
  Copy,
  Share2,
  Globe,
  FileText,
  Image,
  Play,
  Pause,
  X,
} from 'lucide-react'
import { format } from 'date-fns'
import { apiService } from '../services/api'
import XPostsTab from '../components/XPostsTab'

// Type definitions
interface UrlItem {
  id: string
  url: string
  title: string
  description: string
  content_length: number
  processing_status: string
  created_at: string
  email_subject: string
  email_sender: string
}

interface UrlDetails {
  url: {
    id: string
    url: string
    title: string
    description: string
    content_length: number
    processing_status: string
    markdown_content: string
    created_at: string
    updated_at: string
    email_subject: string
    email_sender: string
    email_created: string
  }
}

interface UrlPreview {
  preview: {
    url: string
    title: string
    description: string
    content_preview: string
    content_length: number
    has_full_content: boolean
  }
}

const UrlsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedUrl, setSelectedUrl] = useState<UrlItem | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showPreview, setShowPreview] = useState(false)
  const [previewUrl, setPreviewUrl] = useState<UrlPreview | null>(null)
  const [showDetails, setShowDetails] = useState(false)
  const [detailsUrl, setDetailsUrl] = useState<UrlDetails | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [itemsPerPage] = useState(20)

  // sub-tab state: 'urls' | 'xposts'
  const [activeTab, setActiveTab] = useState<'urls' | 'xposts'>('urls')

  // Query for URLs
  const {
    data: urlsData,
    isLoading: urlsLoading,
    error: urlsError,
    refetch: refetchUrls,
  } = useQuery<{ urls: UrlItem[]; total: number; limit: number; offset: number }>(
    ['urls', currentPage, itemsPerPage],
    async () => {
      const offset = (currentPage - 1) * itemsPerPage
      const response = await fetch(`/api/email/urls?limit=${itemsPerPage}&offset=${offset}`)
      if (!response.ok) throw new Error('Failed to fetch URLs')
      return response.json()
    },
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  )

  // Mutation for reprocessing URLs
  const reprocessUrlMutation = useMutation(
    async (urlId: string) => {
      const response = await fetch(`/api/email/urls/${urlId}/process`, {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to reprocess URL')
      return response.json()
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('urls')
      },
    }
  )

  // Handle URL preview
  const handlePreview = async (url: UrlItem) => {
    try {
      const response = await fetch(`/api/email/urls/${url.id}/preview`)
      if (!response.ok) throw new Error('Failed to fetch URL preview')
      const preview = await response.json()
      setPreviewUrl(preview)
      setShowPreview(true)
    } catch (error) {
      console.error('Error fetching URL preview:', error)
    }
  }

  // Handle URL details
  const handleViewDetails = async (url: UrlItem) => {
    try {
      const response = await fetch(`/api/email/urls/${url.id}`)
      if (!response.ok) throw new Error('Failed to fetch URL details')
      const details = await response.json()
      setDetailsUrl(details)
      setShowDetails(true)
    } catch (error) {
      console.error('Error fetching URL details:', error)
    }
  }

  // Handle URL opening
  const handleOpenUrl = (url: string) => {
    window.open(url, '_blank')
  }

  // Handle URL copy
  const handleCopyUrl = (url: string) => {
    navigator.clipboard.writeText(url)
    // Could add a toast notification here
  }

  // Handle URL reprocessing
  const handleReprocess = (url: UrlItem) => {
    reprocessUrlMutation.mutate(url.id)
  }

  // Filter URLs based on search query
  const filteredUrls = urlsData?.urls.filter(url =>
    url.url.toLowerCase().includes(searchQuery.toLowerCase()) ||
    url.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    url.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    url.email_subject?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    url.email_sender?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  // Get processing status color
  const getProcessingStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100'
      case 'processing':
        return 'text-yellow-600 bg-yellow-100'
      case 'failed':
        return 'text-red-600 bg-red-100'
      default:
        return 'text-gray-600 bg-gray-100'
    }
  }

  // Get processing status icon
  const getProcessingStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4" />
      case 'processing':
        return <Clock className="w-4 h-4" />
      case 'failed':
        return <XCircle className="w-4 h-4" />
      default:
        return <Clock className="w-4 h-4" />
    }
  }

  // Format content length
  const formatContentLength = (length: number): string => {
    if (length === 0) return '0 chars'
    if (length < 1000) return `${length} chars`
    if (length < 1000000) return `${(length / 1000).toFixed(1)}K chars`
    return `${(length / 1000000).toFixed(1)}M chars`
  }

  // Get domain from URL
  const getDomain = (url: string): string => {
    try {
      return new URL(url).hostname
    } catch {
      return 'Invalid URL'
    }
  }

  // Calculate pagination
  const totalPages = Math.ceil((urlsData?.total || 0) / itemsPerPage)
  const hasNextPage = currentPage < totalPages
  const hasPrevPage = currentPage > 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">URLs</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Manage URLs extracted from emails
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => refetchUrls()}
            disabled={urlsLoading}
            className="flex items-center px-3 py-2 text-sm bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${urlsLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Sub-tabs selector */}
      <div className="flex space-x-4 border-b">
        <button
          className={`pb-2 font-medium ${activeTab === 'urls' ? 'border-b-2 border-primary-600' : 'text-secondary-500'}`}
          onClick={() => setActiveTab('urls')}
        >
          URLs
        </button>
        <button
          className={`pb-2 font-medium ${activeTab === 'xposts' ? 'border-b-2 border-primary-600' : 'text-secondary-500'}`}
          onClick={() => setActiveTab('xposts')}
        >
          X Posts
        </button>
      </div>

      {activeTab === 'urls' && (
        <>
          {/* URL Management */}
          <div className="card">
            <div className="card-header">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-medium text-secondary-900 flex items-center">
                  <LinkIcon className="w-5 h-5 mr-2" />
                  URLs ({filteredUrls.length})
                </h3>
                <div className="flex items-center space-x-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-secondary-400 w-4 h-4" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      placeholder="Search URLs..."
                      className="pl-10 pr-4 py-2 border border-secondary-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    />
                  </div>
                </div>
              </div>
            </div>
            <div className="card-body">
              {urlsLoading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="w-8 h-8 animate-spin text-secondary-400" />
                </div>
              ) : urlsError ? (
                <div className="flex items-center justify-center py-12 text-red-500">
                  <AlertCircle className="w-8 h-8 mr-2" />
                  Failed to load URLs
                </div>
              ) : filteredUrls.length === 0 ? (
                <div className="text-center py-12">
                  <LinkIcon className="mx-auto h-16 w-16 text-secondary-400" />
                  <h3 className="mt-4 text-lg font-medium text-secondary-900">
                    No URLs found
                  </h3>
                  <p className="mt-2 text-sm text-secondary-500">
                    {searchQuery ? 'Try adjusting your search query.' : 'URLs will appear here once emails with URLs are processed.'}
                  </p>
                </div>
              ) : (
                <>
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-secondary-200">
                      <thead className="bg-secondary-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                            URL
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                            Content
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                            Status
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                            Email Source
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                            Created
                          </th>
                          <th className="px-6 py-3 text-right text-xs font-medium text-secondary-500 uppercase tracking-wider">
                            Actions
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-secondary-200">
                        {filteredUrls.map((url) => (
                          <tr key={url.id} className="hover:bg-secondary-50">
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center">
                                <div className="flex-shrink-0 mr-3 text-secondary-400">
                                  <Globe className="w-5 h-5" />
                                </div>
                                <div>
                                  <div className="text-sm font-medium text-secondary-900">
                                    {url.title || getDomain(url.url)}
                                  </div>
                                  <div className="text-sm text-secondary-500 max-w-xs truncate">
                                    {url.url}
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-secondary-900">
                                {formatContentLength(url.content_length)}
                              </div>
                              <div className="text-sm text-secondary-500 max-w-xs truncate">
                                {url.description || 'No description'}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getProcessingStatusColor(url.processing_status)}`}>
                                {getProcessingStatusIcon(url.processing_status)}
                                <span className="ml-1 capitalize">{url.processing_status || 'pending'}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="text-sm text-secondary-900">
                                {url.email_subject || 'No subject'}
                              </div>
                              <div className="text-sm text-secondary-500">
                                {url.email_sender}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-500">
                              {format(new Date(url.created_at), 'MMM dd, yyyy')}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                              <div className="flex items-center justify-end space-x-2">
                                <button
                                  onClick={() => handlePreview(url)}
                                  className="text-secondary-600 hover:text-secondary-900"
                                  title="Preview"
                                >
                                  <Eye className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleViewDetails(url)}
                                  className="text-secondary-600 hover:text-secondary-900"
                                  title="View Details"
                                >
                                  <FileText className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleOpenUrl(url.url)}
                                  className="text-secondary-600 hover:text-secondary-900"
                                  title="Open URL"
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleCopyUrl(url.url)}
                                  className="text-secondary-600 hover:text-secondary-900"
                                  title="Copy URL"
                                >
                                  <Copy className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={() => handleReprocess(url)}
                                  disabled={reprocessUrlMutation.isLoading}
                                  className="text-secondary-600 hover:text-secondary-900 disabled:opacity-50"
                                  title="Reprocess"
                                >
                                  <RefreshCw className={`w-4 h-4 ${reprocessUrlMutation.isLoading ? 'animate-spin' : ''}`} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between px-6 py-4 border-t border-secondary-200">
                      <div className="flex items-center text-sm text-secondary-600">
                        Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, urlsData?.total || 0)} of {urlsData?.total || 0} URLs
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => setCurrentPage(currentPage - 1)}
                          disabled={!hasPrevPage}
                          className="px-3 py-2 text-sm bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 disabled:opacity-50"
                        >
                          Previous
                        </button>
                        <span className="text-sm text-secondary-600">
                          Page {currentPage} of {totalPages}
                        </span>
                        <button
                          onClick={() => setCurrentPage(currentPage + 1)}
                          disabled={!hasNextPage}
                          className="px-3 py-2 text-sm bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 disabled:opacity-50"
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </>
      )}

      {activeTab === 'xposts' && <XPostsTab />}

      {/* URL Preview Modal */}
      {showPreview && previewUrl && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-secondary-900">URL Preview</h2>
                <button
                  onClick={() => setShowPreview(false)}
                  className="text-secondary-400 hover:text-secondary-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div className="space-y-4">
                <div className="flex items-center space-x-2">
                  <Globe className="w-5 h-5 text-secondary-400" />
                  <a
                    href={previewUrl.preview.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary-600 hover:text-primary-800 font-medium"
                  >
                    {previewUrl.preview.url}
                  </a>
                </div>

                {previewUrl.preview.title && (
                  <div>
                    <h3 className="font-medium text-secondary-900 mb-2">Title</h3>
                    <p className="text-secondary-800">{previewUrl.preview.title}</p>
                  </div>
                )}

                {previewUrl.preview.description && (
                  <div>
                    <h3 className="font-medium text-secondary-900 mb-2">Description</h3>
                    <p className="text-secondary-600">{previewUrl.preview.description}</p>
                  </div>
                )}

                {previewUrl.preview.content_preview && (
                  <div>
                    <h3 className="font-medium text-secondary-900 mb-2">Content Preview</h3>
                    <div className="bg-secondary-50 p-4 rounded-lg">
                      <pre className="text-sm text-secondary-800 whitespace-pre-wrap">
                        {previewUrl.preview.content_preview}
                      </pre>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between text-sm text-secondary-600">
                  <span>Content Length: {formatContentLength(previewUrl.preview.content_length)}</span>
                  <span>Full Content: {previewUrl.preview.has_full_content ? 'Available' : 'Not available'}</span>
                </div>

                <div className="flex justify-end space-x-2 pt-4 border-t border-secondary-200">
                  <button
                    onClick={() => window.open(previewUrl.preview.url, '_blank')}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    Open URL
                  </button>
                  <button
                    onClick={() => setShowPreview(false)}
                    className="px-4 py-2 bg-secondary-200 text-secondary-800 rounded-lg hover:bg-secondary-300"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* URL Details Modal */}
      {showDetails && detailsUrl && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-secondary-900">URL Details</h2>
                <button
                  onClick={() => setShowDetails(false)}
                  className="text-secondary-400 hover:text-secondary-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div className="space-y-4">
                {/* URL Information */}
                <div>
                  <h3 className="font-medium text-secondary-900 mb-2">URL Information</h3>
                  <div className="bg-secondary-50 p-3 rounded-lg space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">URL:</span>
                      <a
                        href={detailsUrl.url.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-primary-600 hover:text-primary-800"
                      >
                        {detailsUrl.url.url}
                      </a>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Title:</span>
                      <span className="text-sm text-secondary-900">{detailsUrl.url.title || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Content Length:</span>
                      <span className="text-sm text-secondary-900">{formatContentLength(detailsUrl.url.content_length)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Processing Status:</span>
                      <span className={`text-sm px-2 py-1 rounded ${getProcessingStatusColor(detailsUrl.url.processing_status)}`}>
                        {detailsUrl.url.processing_status || 'pending'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Email Information */}
                <div>
                  <h3 className="font-medium text-secondary-900 mb-2">Email Information</h3>
                  <div className="bg-secondary-50 p-3 rounded-lg space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Subject:</span>
                      <span className="text-sm text-secondary-900">{detailsUrl.url.email_subject || 'N/A'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Sender:</span>
                      <span className="text-sm text-secondary-900">{detailsUrl.url.email_sender}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Email Created:</span>
                      <span className="text-sm text-secondary-900">
                        {detailsUrl.url.email_created ? format(new Date(detailsUrl.url.email_created), 'MMM dd, yyyy HH:mm') : 'N/A'}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Content Preview */}
                {detailsUrl.url.markdown_content && (
                  <div>
                    <h3 className="font-medium text-secondary-900 mb-2">Content</h3>
                    <div className="bg-secondary-50 p-4 rounded-lg max-h-60 overflow-y-auto">
                      <pre className="text-sm text-secondary-800 whitespace-pre-wrap">
                        {detailsUrl.url.markdown_content}
                      </pre>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end space-x-2 pt-4 border-t border-secondary-200">
                  <button
                    onClick={() => window.open(detailsUrl.url.url, '_blank')}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    Open URL
                  </button>
                  <button
                    onClick={() => setShowDetails(false)}
                    className="px-4 py-2 bg-secondary-200 text-secondary-800 rounded-lg hover:bg-secondary-300"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UrlsPage 