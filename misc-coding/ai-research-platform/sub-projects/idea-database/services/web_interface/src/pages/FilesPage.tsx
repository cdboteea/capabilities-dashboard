import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
  HardDrive,
  Download,
  Trash2,
  Share2,
  Eye,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Filter,
  Upload,
  Settings,
  User,
  Shield,
  Database,
  BarChart3,
  FileText,
  Image,
  Archive,
  Play,
  Pause,
  X,
  Mail,
  Link,
  Globe,
} from 'lucide-react'
import { format } from 'date-fns'
import { apiService } from '../services/api'

// Type definitions
interface DriveFile {
  id: string
  filename: string
  file_type: string
  file_size: number
  drive_file_id: string
  created_at: string
  updated_at: string
  email_subject: string
  email_sender: string
}

interface DriveFileDetails {
  drive_metadata: {
    id: string
    name: string
    size: number
    mime_type: string
    created_time: string
    web_view_link: string
  }
  database_info: {
    id: string
    filename: string
    file_type: string
    file_size: number
    conversion_status: string
    has_markdown: boolean
    created_at: string
    email_subject: string
    email_sender: string
  }
}

interface OAuthStatus {
  oauth_status: {
    gmail: {
      enabled: boolean
      configured: boolean
      user_email: string
    }
    drive: {
      enabled: boolean
      configured: boolean
      user_email: string
      auth_method: string
    }
  }
}

interface StorageStats {
  storage_stats: {
    total_drive_files: number
    total_drive_size: number
    conversion_stats: Record<string, number>
    storage_by_type: Record<string, { count: number; size: number }>
  }
  drive_integration: {
    enabled: boolean
    folder_configured: boolean
  }
}

const FilesPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [selectedFile, setSelectedFile] = useState<DriveFile | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showDetails, setShowDetails] = useState(false)
  const [detailsFile, setDetailsFile] = useState<DriveFileDetails | null>(null)
  const [showShareModal, setShowShareModal] = useState(false)
  const [shareFile, setShareFile] = useState<DriveFile | null>(null)
  const [shareEmail, setShareEmail] = useState('')
  const [sharePermission, setSharePermission] = useState<'reader' | 'commenter' | 'writer'>('reader')
  const [sendNotification, setSendNotification] = useState(true)
  const [generateLink, setGenerateLink] = useState(false)

  // Query for Drive files
  const {
    data: driveFiles,
    isLoading: filesLoading,
    error: filesError,
    refetch: refetchFiles,
  } = useQuery<{ files: DriveFile[]; total: number }>(
    'driveFiles',
    async () => {
      const response = await fetch('/api/email/drive/files')
      if (!response.ok) throw new Error('Failed to fetch Drive files')
      return response.json()
    },
    {
      refetchInterval: 30000, // Refresh every 30 seconds
    }
  )

  // Query for OAuth status
  const {
    data: oauthStatus,
    isLoading: oauthLoading,
    refetch: refetchOAuth,
  } = useQuery<OAuthStatus>(
    'oauthStatus',
    async () => {
      const response = await fetch('/api/email/settings/oauth')
      if (!response.ok) throw new Error('Failed to fetch OAuth status')
      return response.json()
    }
  )

  // Query for storage statistics
  const {
    data: storageStats,
    isLoading: storageLoading,
    refetch: refetchStorage,
  } = useQuery<StorageStats>(
    'storageStats',
    async () => {
      const response = await fetch('/api/email/conversion/stats')
      if (!response.ok) throw new Error('Failed to fetch storage stats')
      return response.json()
    }
  )

  // Mutation for refreshing OAuth token
  const refreshOAuthMutation = useMutation(
    async () => {
      const response = await fetch('/api/email/drive/oauth/refresh', {
        method: 'POST',
      })
      if (!response.ok) throw new Error('Failed to refresh OAuth token')
      return response.json()
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('oauthStatus')
        queryClient.invalidateQueries('driveFiles')
      },
    }
  )

  // Mutation for deleting files
  const deleteFileMutation = useMutation(
    async (fileId: string) => {
      const response = await fetch(`/api/email/drive/files/${fileId}`, {
        method: 'DELETE',
      })
      if (!response.ok) throw new Error('Failed to delete file')
      return response.json()
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('driveFiles')
        queryClient.invalidateQueries('storageStats')
      },
    }
  )

  // Mutation for sharing files
  const shareFileMutation = useMutation(
    async (shareData: {
      fileId: string
      recipientEmail?: string
      permission?: string
      sendNotification?: boolean
      generateLink?: boolean
    }) => {
      const response = await fetch(`/api/email/drive/share/${shareData.fileId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          recipient_email: shareData.recipientEmail,
          permission: shareData.permission,
          send_notification: shareData.sendNotification,
          generate_link: shareData.generateLink,
        }),
      })
      if (!response.ok) throw new Error('Failed to share file')
      return response.json()
    },
    {
      onSuccess: (data) => {
        // Show success message or handle response
        console.log('File shared successfully:', data)
        setShowShareModal(false)
        setShareEmail('')
        setShareFile(null)
      },
    }
  )

  // Handle file details
  const handleViewDetails = async (file: DriveFile) => {
    try {
      const response = await fetch(`/api/email/drive/files/${file.drive_file_id}`)
      if (!response.ok) throw new Error('Failed to fetch file details')
      const details = await response.json()
      setDetailsFile(details)
      setShowDetails(true)
    } catch (error) {
      console.error('Error fetching file details:', error)
    }
  }

  // Handle file download
  const handleDownload = (file: DriveFile) => {
    window.open(`/api/email/attachments/${file.id}/download`, '_blank')
  }

  // Handle file sharing - opens share modal
  const handleShare = (file: DriveFile) => {
    setShareFile(file)
    setShowShareModal(true)
  }

  // Handle actual sharing with recipient
  const handleShareSubmit = () => {
    if (!shareFile) return
    
    shareFileMutation.mutate({
      fileId: shareFile.drive_file_id,
      recipientEmail: shareEmail || undefined,
      permission: sharePermission,
      sendNotification,
      generateLink,
    })
  }

  // Handle file deletion
  const handleDelete = (file: DriveFile) => {
    if (window.confirm(`Are you sure you want to delete "${file.filename}"?`)) {
      deleteFileMutation.mutate(file.drive_file_id)
    }
  }

  // Filter files based on search query
  const filteredFiles = driveFiles?.files.filter(file =>
    file.filename.toLowerCase().includes(searchQuery.toLowerCase()) ||
    file.email_subject?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    file.email_sender?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  // Format file size
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  // Calculate total statistics across all storage types
  const getTotalStats = () => {
    if (!storageStats?.storage_stats) {
      return { totalFiles: 0, totalSize: 0 }
    }

    let totalFiles = 0
    let totalSize = 0

    // Sum up all storage types
    Object.values(storageStats.storage_stats.storage_by_type || {}).forEach(storage => {
      totalFiles += storage.count || 0
      totalSize += storage.size || 0
    })

    return { totalFiles, totalSize }
  }

  // Get file type icon
  const getFileTypeIcon = (fileType: string) => {
    if (fileType?.includes('image')) return <Image className="w-5 h-5" />
    if (fileType?.includes('pdf')) return <FileText className="w-5 h-5" />
    if (fileType?.includes('zip') || fileType?.includes('archive')) return <Archive className="w-5 h-5" />
    return <FileText className="w-5 h-5" />
  }

  // Get OAuth status color
  const getOAuthStatusColor = (enabled: boolean, configured: boolean) => {
    if (enabled && configured) return 'text-green-600'
    if (enabled) return 'text-yellow-600'
    return 'text-red-600'
  }

  // Get OAuth status icon
  const getOAuthStatusIcon = (enabled: boolean, configured: boolean) => {
    if (enabled && configured) return <CheckCircle className="w-5 h-5" />
    if (enabled) return <Clock className="w-5 h-5" />
    return <XCircle className="w-5 h-5" />
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-secondary-900">Files</h1>
          <p className="mt-1 text-sm text-secondary-600">
            Manage your Google Drive files and storage
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => refetchFiles()}
            disabled={filesLoading}
            className="flex items-center px-3 py-2 text-sm bg-secondary-100 text-secondary-700 rounded-lg hover:bg-secondary-200 disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${filesLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* OAuth Status Card */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-secondary-900 flex items-center">
            <Shield className="w-5 h-5 mr-2" />
            OAuth Authentication Status
          </h3>
        </div>
        <div className="card-body">
          {oauthLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-secondary-400" />
            </div>
          ) : oauthStatus ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Gmail OAuth */}
              <div className="flex items-center space-x-3">
                <div className={getOAuthStatusColor(oauthStatus.oauth_status.gmail.enabled, oauthStatus.oauth_status.gmail.configured)}>
                  {getOAuthStatusIcon(oauthStatus.oauth_status.gmail.enabled, oauthStatus.oauth_status.gmail.configured)}
                </div>
                <div>
                  <h4 className="font-medium text-secondary-900">Gmail</h4>
                  <p className="text-sm text-secondary-600">
                    {oauthStatus.oauth_status.gmail.user_email || 'Not configured'}
                  </p>
                </div>
              </div>

              {/* Drive OAuth */}
              <div className="flex items-center space-x-3">
                <div className={getOAuthStatusColor(oauthStatus.oauth_status.drive.enabled, oauthStatus.oauth_status.drive.configured)}>
                  {getOAuthStatusIcon(oauthStatus.oauth_status.drive.enabled, oauthStatus.oauth_status.drive.configured)}
                </div>
                <div>
                  <h4 className="font-medium text-secondary-900">Google Drive</h4>
                  <p className="text-sm text-secondary-600">
                    {oauthStatus.oauth_status.drive.user_email || 'Not configured'}
                  </p>
                  <p className="text-xs text-secondary-500">
                    Method: {oauthStatus.oauth_status.drive.auth_method || 'None'}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-8 text-secondary-500">
              <AlertCircle className="w-6 h-6 mr-2" />
              Failed to load OAuth status
            </div>
          )}

          {/* Refresh OAuth Button */}
          <div className="mt-4 pt-4 border-t border-secondary-200">
            <button
              onClick={() => refreshOAuthMutation.mutate()}
              disabled={refreshOAuthMutation.isLoading}
              className="flex items-center px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${refreshOAuthMutation.isLoading ? 'animate-spin' : ''}`} />
              Refresh OAuth Token
            </button>
          </div>
        </div>
      </div>

      {/* Storage Analytics Card */}
      <div className="card">
        <div className="card-header">
          <h3 className="text-lg font-medium text-secondary-900 flex items-center">
            <BarChart3 className="w-5 h-5 mr-2" />
            Storage Analytics
          </h3>
        </div>
        <div className="card-body">
          {storageLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="w-6 h-6 animate-spin text-secondary-400" />
            </div>
          ) : storageStats ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-secondary-900">
                  {storageStats.storage_stats.total_drive_files}
                </div>
                <div className="text-sm text-secondary-600">Total Files</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-secondary-900">
                  {formatFileSize(storageStats.storage_stats.total_drive_size)}
                </div>
                <div className="text-sm text-secondary-600">Total Size</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-secondary-900">
                  {storageStats.drive_integration.enabled ? 'Active' : 'Inactive'}
                </div>
                <div className="text-sm text-secondary-600">Drive Integration</div>
              </div>
            </div>
          ) : (
            <div className="flex items-center justify-center py-8 text-secondary-500">
              <AlertCircle className="w-6 h-6 mr-2" />
              Failed to load storage statistics
            </div>
          )}
        </div>
      </div>

      {/* File Management */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium text-secondary-900 flex items-center">
              <HardDrive className="w-5 h-5 mr-2" />
              Drive Files ({filteredFiles.length})
            </h3>
            <div className="flex items-center space-x-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-secondary-400 w-4 h-4" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search files..."
                  className="pl-10 pr-4 py-2 border border-secondary-300 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </div>
          </div>
        </div>
        <div className="card-body">
          {filesLoading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-8 h-8 animate-spin text-secondary-400" />
            </div>
          ) : filesError ? (
            <div className="flex items-center justify-center py-12 text-red-500">
              <AlertCircle className="w-8 h-8 mr-2" />
              Failed to load files
            </div>
          ) : filteredFiles.length === 0 ? (
            <div className="text-center py-12">
              <HardDrive className="mx-auto h-16 w-16 text-secondary-400" />
              <h3 className="mt-4 text-lg font-medium text-secondary-900">
                No files found
              </h3>
              <p className="mt-2 text-sm text-secondary-500">
                {searchQuery ? 'Try adjusting your search query.' : 'Files will appear here once emails with attachments are processed.'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-secondary-200">
                <thead className="bg-secondary-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                      File
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-secondary-500 uppercase tracking-wider">
                      Size
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
                  {filteredFiles.map((file) => (
                    <tr key={file.id} className="hover:bg-secondary-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="flex-shrink-0 mr-3 text-secondary-400">
                            {getFileTypeIcon(file.file_type)}
                          </div>
                          <div>
                            <div className="text-sm font-medium text-secondary-900">
                              {file.filename}
                            </div>
                            <div className="text-sm text-secondary-500">
                              {file.file_type}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-900">
                        {formatFileSize(file.file_size)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm text-secondary-900">
                          {file.email_subject || 'No subject'}
                        </div>
                        <div className="text-sm text-secondary-500">
                          {file.email_sender}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-secondary-500">
                        {format(new Date(file.created_at), 'MMM dd, yyyy')}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => handleViewDetails(file)}
                            className="text-secondary-600 hover:text-secondary-900"
                            title="View Details"
                          >
                            <Eye className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDownload(file)}
                            className="text-secondary-600 hover:text-secondary-900"
                            title="Download"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleShare(file)}
                            disabled={shareFileMutation.isLoading}
                            className="text-secondary-600 hover:text-secondary-900 disabled:opacity-50"
                            title="Share"
                          >
                            <Share2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => handleDelete(file)}
                            disabled={deleteFileMutation.isLoading}
                            className="text-red-600 hover:text-red-900 disabled:opacity-50"
                            title="Delete"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* File Details Modal */}
      {showDetails && detailsFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-secondary-900">File Details</h2>
                <button
                  onClick={() => setShowDetails(false)}
                  className="text-secondary-400 hover:text-secondary-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div className="space-y-4">
                {/* Drive Metadata */}
                <div>
                  <h3 className="font-medium text-secondary-900 mb-2">Drive Information</h3>
                  <div className="bg-secondary-50 p-3 rounded-lg space-y-2">
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Name:</span>
                      <span className="text-sm text-secondary-900">{detailsFile.drive_metadata.name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Size:</span>
                      <span className="text-sm text-secondary-900">{formatFileSize(detailsFile.drive_metadata.size)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Type:</span>
                      <span className="text-sm text-secondary-900">{detailsFile.drive_metadata.mime_type}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-sm text-secondary-600">Created:</span>
                      <span className="text-sm text-secondary-900">
                        {format(new Date(detailsFile.drive_metadata.created_time), 'MMM dd, yyyy HH:mm')}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Database Information */}
                {detailsFile.database_info && (
                  <div>
                    <h3 className="font-medium text-secondary-900 mb-2">Database Information</h3>
                    <div className="bg-secondary-50 p-3 rounded-lg space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">Email Subject:</span>
                        <span className="text-sm text-secondary-900">{detailsFile.database_info.email_subject || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">Email Sender:</span>
                        <span className="text-sm text-secondary-900">{detailsFile.database_info.email_sender}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">Conversion Status:</span>
                        <span className="text-sm text-secondary-900">{detailsFile.database_info.conversion_status || 'N/A'}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">Has Markdown:</span>
                        <span className="text-sm text-secondary-900">{detailsFile.database_info.has_markdown ? 'Yes' : 'No'}</span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex justify-end space-x-2 pt-4 border-t border-secondary-200">
                  <button
                    onClick={() => window.open(detailsFile.drive_metadata.web_view_link, '_blank')}
                    className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
                  >
                    View in Drive
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

      {/* Share Modal */}
      {showShareModal && shareFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-bold text-secondary-900">Share File</h2>
                <button
                  onClick={() => setShowShareModal(false)}
                  className="text-secondary-400 hover:text-secondary-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="space-y-4">
                {/* File Info */}
                <div className="bg-secondary-50 p-3 rounded-lg">
                  <div className="flex items-center space-x-3">
                    <div className="text-secondary-400">
                      {getFileTypeIcon(shareFile.file_type)}
                    </div>
                    <div>
                      <p className="font-medium text-secondary-900">{shareFile.filename}</p>
                      <p className="text-sm text-secondary-500">{formatFileSize(shareFile.file_size)}</p>
                    </div>
                  </div>
                </div>

                {/* Sharing Options */}
                <div className="space-y-4">
                  {/* Email Recipient */}
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      <Mail className="w-4 h-4 inline mr-2" />
                      Share with email (optional)
                    </label>
                    <input
                      type="email"
                      value={shareEmail}
                      onChange={(e) => setShareEmail(e.target.value)}
                      placeholder="Enter email address"
                      className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    />
                    <p className="text-xs text-secondary-500 mt-1">
                      Leave empty to generate a shareable link only
                    </p>
                  </div>

                  {/* Permission Level */}
                  <div>
                    <label className="block text-sm font-medium text-secondary-700 mb-2">
                      Permission Level
                    </label>
                    <select
                      value={sharePermission}
                      onChange={(e) => setSharePermission(e.target.value as 'reader' | 'commenter' | 'writer')}
                      className="w-full px-3 py-2 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                    >
                      <option value="reader">Reader - Can view only</option>
                      <option value="commenter">Commenter - Can view and comment</option>
                      <option value="writer">Writer - Can view, comment, and edit</option>
                    </select>
                  </div>

                  {/* Options */}
                  <div className="space-y-3">
                    {shareEmail && (
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={sendNotification}
                          onChange={(e) => setSendNotification(e.target.checked)}
                          className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                        />
                        <span className="ml-2 text-sm text-secondary-700">
                          Send email notification to recipient
                        </span>
                      </label>
                    )}

                    <label className="flex items-center">
                      <input
                        type="checkbox"
                        checked={generateLink}
                        onChange={(e) => setGenerateLink(e.target.checked)}
                        className="rounded border-secondary-300 text-primary-600 focus:ring-primary-500"
                      />
                      <span className="ml-2 text-sm text-secondary-700">
                        <Link className="w-4 h-4 inline mr-1" />
                        Generate shareable link
                      </span>
                    </label>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex justify-end space-x-3 pt-4 border-t border-secondary-200">
                  <button
                    onClick={() => setShowShareModal(false)}
                    className="px-4 py-2 text-sm bg-secondary-200 text-secondary-800 rounded-lg hover:bg-secondary-300"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleShareSubmit}
                    disabled={shareFileMutation.isLoading || (!shareEmail && !generateLink)}
                    className="px-4 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {shareFileMutation.isLoading ? (
                      <RefreshCw className="w-4 h-4 animate-spin inline mr-2" />
                    ) : (
                      <Share2 className="w-4 h-4 inline mr-2" />
                    )}
                    Share File
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

export default FilesPage 