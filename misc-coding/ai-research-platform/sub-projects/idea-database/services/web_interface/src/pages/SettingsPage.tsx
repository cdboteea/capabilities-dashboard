import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import {
  Settings as SettingsIcon,
  Shield,
  Mail,
  Tags,
  Cpu,
  Save,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  XCircle,
  Clock,
  User,
  Key,
  Edit,
  Trash2,
  Plus,
  Database,
  Brain,
  Zap,
} from 'lucide-react'
import { format } from 'date-fns'

// Type definitions
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

interface AIModel {
  id: string
  name: string
  description: string
}

const SettingsPage: React.FC = () => {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState<'oauth' | 'models' | 'processing' | 'taxonomy' | 'database'>('oauth')
  const [refreshingGmail, setRefreshingGmail] = useState(false)
  const [refreshingDrive, setRefreshingDrive] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)
  const [cleaningDatabase, setCleaningDatabase] = useState(false)
  const [cleanupMessage, setCleanupMessage] = useState<{type: 'success' | 'error', text: string} | null>(null)

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

  // Query for AI models
  const {
    data: modelsData,
    isLoading: modelsLoading,
    refetch: refetchModels,
  } = useQuery<{ models: AIModel[] }>(
    'models',
    async () => {
      const response = await fetch('/api/email/settings/models')
      if (!response.ok) throw new Error('Failed to fetch models')
      return response.json()
    }
  )

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

  // OAuth refresh functions
  const refreshGmailOAuth = async () => {
    setRefreshingGmail(true)
    setRefreshMessage(null)
    try {
      const response = await fetch('/api/email/oauth/refresh/gmail', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const result = await response.json()
      
      if (result.status === 'success') {
        setRefreshMessage({ type: 'success', text: result.message })
        // Refetch OAuth status to update UI
        refetchOAuth()
      } else {
        setRefreshMessage({ type: 'error', text: result.message })
      }
    } catch (error) {
      setRefreshMessage({ type: 'error', text: 'Failed to refresh Gmail OAuth token' })
    } finally {
      setRefreshingGmail(false)
      // Clear message after 5 seconds
      setTimeout(() => setRefreshMessage(null), 5000)
    }
  }

  const refreshDriveOAuth = async () => {
    setRefreshingDrive(true)
    setRefreshMessage(null)
    try {
      const response = await fetch('/api/email/oauth/refresh/drive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const result = await response.json()
      
      if (result.status === 'success') {
        setRefreshMessage({ type: 'success', text: result.message })
        // Refetch OAuth status to update UI
        refetchOAuth()
      } else {
        setRefreshMessage({ type: 'error', text: result.message })
      }
    } catch (error) {
      setRefreshMessage({ type: 'error', text: 'Failed to refresh Drive OAuth token' })
    } finally {
      setRefreshingDrive(false)
      // Clear message after 5 seconds
      setTimeout(() => setRefreshMessage(null), 5000)
    }
  }

  // Database cleanup function
  const cleanupDatabase = async () => {
    const confirmMessage = `⚠️ DATABASE CLEANUP WARNING ⚠️

This will DELETE all email-related data including:
• All processed emails and content
• All attachments and file metadata  
• All extracted URLs and entities
• All knowledge graph connections
• All processing history

✅ PROTECTED (will NOT be deleted):
• Taxonomy node types (essential for AI processing)
• Taxonomy edge types (essential for knowledge graph)

This action cannot be undone. Are you sure you want to proceed?

Tip: Use "Force reprocess" in the top header after cleanup to reprocess all emails.`

    if (!window.confirm(confirmMessage)) {
      return
    }

    setCleaningDatabase(true)
    setCleanupMessage(null)
    
    try {
      const response = await fetch('/api/email/database/cleanup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      const result = await response.json()
      
      if (result.success) {
        setCleanupMessage({ 
          type: 'success', 
          text: `Database cleanup completed! ${result.statistics.total_records_deleted} records deleted. Taxonomy preserved: ${result.statistics.taxonomy_preserved.node_types} node types, ${result.statistics.taxonomy_preserved.edge_types} edge types.`
        })
        
        // Invalidate relevant queries to refresh UI
        queryClient.invalidateQueries('dashboard-stats')
        queryClient.invalidateQueries('recent-activity')
        queryClient.invalidateQueries('driveFiles')
        queryClient.invalidateQueries('urls')
      } else {
        setCleanupMessage({ type: 'error', text: result.message || 'Database cleanup failed' })
      }
    } catch (error) {
      setCleanupMessage({ type: 'error', text: 'Failed to connect to database cleanup service' })
    } finally {
      setCleaningDatabase(false)
      // Clear message after 10 seconds
      setTimeout(() => setCleanupMessage(null), 10000)
    }
  }

  // Tab navigation
  const tabs = [
    { id: 'oauth', name: 'OAuth', icon: Shield },
    { id: 'models', name: 'AI Models', icon: Cpu },
    { id: 'processing', name: 'Processing', icon: Zap },
    { id: 'taxonomy', name: 'Taxonomy', icon: Tags },
    { id: 'database', name: 'Database', icon: Database },
  ]

  // Taxonomy state
  const [taxonomyNodes, setTaxonomyNodes] = useState<any[]>([])
  const [taxonomyEdges, setTaxonomyEdges] = useState<any[]>([])
  const [taxonomyLoading, setTaxonomyLoading] = useState(false)

  const fetchTaxonomy = async () => {
    setTaxonomyLoading(true)
    try {
      const [nodesRes, edgesRes] = await Promise.all([
        fetch('/taxonomy/nodes'),
        fetch('/taxonomy/edges'),
      ])
      const nodes = await nodesRes.json()
      const edges = await edgesRes.json()
      setTaxonomyNodes(nodes)
      setTaxonomyEdges(edges)
    } catch (e) {
      // TODO: error handling
    }
    setTaxonomyLoading(false)
  }

  React.useEffect(() => {
    if (activeTab === 'taxonomy') fetchTaxonomy()
  }, [activeTab])

  // Add after taxonomy state
  const [showNodeModal, setShowNodeModal] = useState(false)
  const [editingNode, setEditingNode] = useState<any | null>(null)
  const [showEdgeModal, setShowEdgeModal] = useState(false)
  const [editingEdge, setEditingEdge] = useState<any | null>(null)
  const [deleteNodeId, setDeleteNodeId] = useState<string | null>(null)
  const [deleteEdgeId, setDeleteEdgeId] = useState<string | null>(null)

  // Handlers for Node CRUD
  const handleAddNode = () => { setEditingNode(null); setShowNodeModal(true) }
  const handleEditNode = (node: any) => { setEditingNode(node); setShowNodeModal(true) }
  const handleDeleteNode = async (id: string) => {
    if (!window.confirm('Delete this node type?')) return
    await fetch(`/taxonomy/nodes/${id}`, { method: 'DELETE' })
    fetchTaxonomy()
  }

  // Handlers for Edge CRUD
  const handleAddEdge = () => { setEditingEdge(null); setShowEdgeModal(true) }
  const handleEditEdge = (edge: any) => { setEditingEdge(edge); setShowEdgeModal(true) }
  const handleDeleteEdge = async (id: string) => {
    if (!window.confirm('Delete this edge type?')) return
    await fetch(`/taxonomy/edges/${id}`, { method: 'DELETE' })
    fetchTaxonomy()
  }

  // Node Modal Form
  const NodeModal = ({ node, onClose }: { node: any, onClose: () => void }) => {
    const [form, setForm] = useState<any>(node || { name: '', color: '#3B82F6', definition: '', example: '', attributes: {} })
    const [saving, setSaving] = useState(false)
    const handleChange = (e: any) => {
      const { name, value } = e.target
      setForm((f: any) => ({ ...f, [name]: value }))
    }
    const handleAttrChange = (e: any) => {
      try { setForm((f: any) => ({ ...f, attributes: JSON.parse(e.target.value) })) } catch {}
    }
    const handleSubmit = async (e: any) => {
      e.preventDefault(); setSaving(true)
      const method = node ? 'PUT' : 'POST'
      const url = node ? `/taxonomy/nodes/${node.id}` : '/taxonomy/nodes'
      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      setSaving(false); onClose(); fetchTaxonomy()
    }
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <form className="bg-white rounded-lg p-6 w-full max-w-lg space-y-4" onSubmit={handleSubmit}>
          <h3 className="text-lg font-semibold mb-2">{node ? 'Edit' : 'Add'} Node Type</h3>
          <div>
            <label className="block text-sm font-medium">Name</label>
            <input name="name" value={form.name} onChange={handleChange} required className="input w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium">Color</label>
            <input name="color" type="color" value={form.color} onChange={handleChange} className="w-12 h-8 p-0 border-none" />
          </div>
          <div>
            <label className="block text-sm font-medium">Definition</label>
            <textarea name="definition" value={form.definition} onChange={handleChange} required className="input w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium">Example</label>
            <input name="example" value={form.example} onChange={handleChange} className="input w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium">Attributes (JSON)</label>
            <textarea name="attributes" value={JSON.stringify(form.attributes, null, 2)} onChange={handleAttrChange} className="input w-full font-mono" />
          </div>
          <div className="flex justify-end space-x-2">
            <button type="button" onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
          </div>
        </form>
      </div>
    )
  }

  // Edge Modal Form
  const EdgeModal = ({ edge, onClose }: { edge: any, onClose: () => void }) => {
    const [form, setForm] = useState<any>(edge || { name: '', color: '#F59E42', definition: '', example: '', directionality: 'directed' })
    const [saving, setSaving] = useState(false)
    const handleChange = (e: any) => {
      const { name, value } = e.target
      setForm((f: any) => ({ ...f, [name]: value }))
    }
    const handleSubmit = async (e: any) => {
      e.preventDefault(); setSaving(true)
      const method = edge ? 'PUT' : 'POST'
      const url = edge ? `/taxonomy/edges/${edge.id}` : '/taxonomy/edges'
      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      setSaving(false); onClose(); fetchTaxonomy()
    }
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <form className="bg-white rounded-lg p-6 w-full max-w-lg space-y-4" onSubmit={handleSubmit}>
          <h3 className="text-lg font-semibold mb-2">{edge ? 'Edit' : 'Add'} Edge Type</h3>
          <div>
            <label className="block text-sm font-medium">Name</label>
            <input name="name" value={form.name} onChange={handleChange} required className="input w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium">Color</label>
            <input name="color" type="color" value={form.color} onChange={handleChange} className="w-12 h-8 p-0 border-none" />
          </div>
          <div>
            <label className="block text-sm font-medium">Definition</label>
            <textarea name="definition" value={form.definition} onChange={handleChange} required className="input w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium">Example</label>
            <input name="example" value={form.example} onChange={handleChange} className="input w-full" />
          </div>
          <div>
            <label className="block text-sm font-medium">Directionality</label>
            <select name="directionality" value={form.directionality} onChange={handleChange} className="input w-full">
              <option value="directed">Directed</option>
              <option value="undirected">Undirected</option>
            </select>
          </div>
          <div className="flex justify-end space-x-2">
            <button type="button" onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
          </div>
        </form>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-secondary-900">Settings</h1>
        <p className="mt-1 text-sm text-secondary-600">
          Configure your email processing and system preferences
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-secondary-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-2 px-1 border-b-2 font-medium text-sm flex items-center ${
                  activeTab === tab.id
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-secondary-500 hover:text-secondary-700 hover:border-secondary-300'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {tab.name}
              </button>
            )
          })}
        </nav>
      </div>

      {/* OAuth Tab */}
      {activeTab === 'oauth' && (
        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-secondary-900 flex items-center">
                <Shield className="w-5 h-5 mr-2" />
                OAuth Authentication
              </h3>
              <p className="text-sm text-secondary-600">
                Manage your OAuth credentials for Gmail and Google Drive
              </p>
            </div>
            <div className="card-body">
              {oauthLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-secondary-400" />
                </div>
              ) : oauthStatus ? (
                <div className="space-y-6">
                  {/* Gmail OAuth */}
                  <div className="border border-secondary-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-secondary-900 flex items-center">
                        <Mail className="w-5 h-5 mr-2" />
                        Gmail OAuth
                      </h4>
                      <div className={`flex items-center ${getOAuthStatusColor(oauthStatus.oauth_status.gmail.enabled, oauthStatus.oauth_status.gmail.configured)}`}>
                        {getOAuthStatusIcon(oauthStatus.oauth_status.gmail.enabled, oauthStatus.oauth_status.gmail.configured)}
                        <span className="ml-2 text-sm font-medium">
                          {oauthStatus.oauth_status.gmail.enabled && oauthStatus.oauth_status.gmail.configured ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">User Email:</span>
                        <span className="text-sm text-secondary-900">
                          {oauthStatus.oauth_status.gmail.user_email || 'Not configured'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">Status:</span>
                        <span className="text-sm text-secondary-900">
                          {oauthStatus.oauth_status.gmail.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-secondary-100">
                      <button
                        onClick={refreshGmailOAuth}
                        disabled={refreshingGmail}
                        className="flex items-center px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <RefreshCw className={`w-4 h-4 mr-2 ${refreshingGmail ? 'animate-spin' : ''}`} />
                        {refreshingGmail ? 'Refreshing...' : 'Refresh Token'}
                      </button>
                    </div>
                  </div>

                  {/* Drive OAuth */}
                  <div className="border border-secondary-200 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h4 className="font-medium text-secondary-900 flex items-center">
                        <Database className="w-5 h-5 mr-2" />
                        Google Drive OAuth
                      </h4>
                      <div className={`flex items-center ${getOAuthStatusColor(oauthStatus.oauth_status.drive.enabled, oauthStatus.oauth_status.drive.configured)}`}>
                        {getOAuthStatusIcon(oauthStatus.oauth_status.drive.enabled, oauthStatus.oauth_status.drive.configured)}
                        <span className="ml-2 text-sm font-medium">
                          {oauthStatus.oauth_status.drive.enabled && oauthStatus.oauth_status.drive.configured ? 'Active' : 'Inactive'}
                        </span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">User Email:</span>
                        <span className="text-sm text-secondary-900">
                          {oauthStatus.oauth_status.drive.user_email || 'Not configured'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">Auth Method:</span>
                        <span className="text-sm text-secondary-900">
                          {oauthStatus.oauth_status.drive.auth_method || 'None'}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-secondary-600">Status:</span>
                        <span className="text-sm text-secondary-900">
                          {oauthStatus.oauth_status.drive.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </div>
                    <div className="mt-3 pt-3 border-t border-secondary-100">
                      <button
                        onClick={refreshDriveOAuth}
                        disabled={refreshingDrive}
                        className="flex items-center px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        <RefreshCw className={`w-4 h-4 mr-2 ${refreshingDrive ? 'animate-spin' : ''}`} />
                        {refreshingDrive ? 'Refreshing...' : 'Refresh Token'}
                      </button>
                    </div>
                  </div>

                  {/* Message Display */}
                  {refreshMessage && (
                    <div className={`rounded-lg p-4 ${refreshMessage.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
                      <div className="flex items-center">
                        {refreshMessage.type === 'success' ? (
                          <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                        ) : (
                          <AlertCircle className="w-5 h-5 text-red-600 mr-2" />
                        )}
                        <span className={`text-sm font-medium ${refreshMessage.type === 'success' ? 'text-green-800' : 'text-red-800'}`}>
                          {refreshMessage.text}
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Global Actions */}
                  <div className="pt-4 border-t border-secondary-200">
                    <button
                      onClick={() => refetchOAuth()}
                      className="flex items-center px-4 py-2 bg-secondary-200 text-secondary-800 rounded-lg hover:bg-secondary-300"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Refresh Status
                    </button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center py-8 text-secondary-500">
                  <AlertCircle className="w-6 h-6 mr-2" />
                  Failed to load OAuth status
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* AI Models Tab */}
      {activeTab === 'models' && (
        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-secondary-900 flex items-center">
                <Cpu className="w-5 h-5 mr-2" />
                AI Models
              </h3>
              <p className="text-sm text-secondary-600">
                Available AI models for email processing and analysis
              </p>
            </div>
            <div className="card-body">
              {modelsLoading ? (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="w-6 h-6 animate-spin text-secondary-400" />
                </div>
              ) : modelsData ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {modelsData.models.map((model) => (
                    <div
                      key={model.id}
                      className="border border-secondary-200 rounded-lg p-4 hover:bg-secondary-50"
                    >
                      <div className="flex items-center mb-2">
                        <Brain className="w-5 h-5 text-primary-600 mr-2" />
                        <h4 className="font-medium text-secondary-900">{model.name}</h4>
                      </div>
                      <p className="text-sm text-secondary-600">{model.description}</p>
                      <div className="mt-3 flex items-center justify-between">
                        <span className="text-xs text-secondary-500">Model ID: {model.id}</span>
                        <button className="text-xs text-primary-600 hover:text-primary-800">
                          Configure
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center py-8 text-secondary-500">
                  <AlertCircle className="w-6 h-6 mr-2" />
                  Failed to load AI models
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Processing Tab */}
      {activeTab === 'processing' && (
        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-secondary-900 flex items-center">
                <Zap className="w-5 h-5 mr-2" />
                Processing Settings
              </h3>
              <p className="text-sm text-secondary-600">
                Configure email processing rules and behavior
              </p>
            </div>
            <div className="card-body">
              <div className="space-y-6">
                {/* Processing Rules */}
                <div>
                  <h4 className="font-medium text-secondary-900 mb-3">Processing Rules</h4>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h5 className="text-sm font-medium text-secondary-900">Auto-process new emails</h5>
                        <p className="text-sm text-secondary-600">Automatically process incoming emails</p>
                      </div>
                      <input
                        type="checkbox"
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-secondary-300 rounded"
                        defaultChecked
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <h5 className="text-sm font-medium text-secondary-900">Extract URLs</h5>
                        <p className="text-sm text-secondary-600">Extract and process URLs from emails</p>
                      </div>
                      <input
                        type="checkbox"
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-secondary-300 rounded"
                        defaultChecked
                      />
                    </div>
                    <div className="flex items-center justify-between">
                      <div>
                        <h5 className="text-sm font-medium text-secondary-900">Process attachments</h5>
                        <p className="text-sm text-secondary-600">Process and convert email attachments</p>
                      </div>
                      <input
                        type="checkbox"
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-secondary-300 rounded"
                        defaultChecked
                      />
                    </div>
                  </div>
                </div>

                {/* Processing Limits */}
                <div>
                  <h4 className="font-medium text-secondary-900 mb-3">Processing Limits</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-secondary-700 mb-2">
                        Max emails per batch
                      </label>
                      <input
                        type="number"
                        className="block w-full border border-secondary-300 rounded-lg px-3 py-2 text-sm"
                        defaultValue="50"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-secondary-700 mb-2">
                        Processing interval (minutes)
                      </label>
                      <input
                        type="number"
                        className="block w-full border border-secondary-300 rounded-lg px-3 py-2 text-sm"
                        defaultValue="15"
                      />
                    </div>
                  </div>
                </div>

                {/* Save Button */}
                <div className="pt-4 border-t border-secondary-200">
                  <button className="flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700">
                    <Save className="w-4 h-4 mr-2" />
                    Save Settings
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Taxonomy Tab */}
      {activeTab === 'taxonomy' && (
        <div className="space-y-8">
          <h2 className="text-xl font-semibold text-secondary-900 flex items-center">
            <Database className="w-5 h-5 mr-2" /> Knowledge Graph Taxonomy
          </h2>
          <div>
            <h3 className="text-lg font-medium text-secondary-800 mb-2">Node Types</h3>
            {taxonomyLoading ? (
              <div>Loading...</div>
            ) : (
              <table className="min-w-full border text-sm">
                <thead>
                  <tr>
                    <th className="border px-2 py-1">Name</th>
                    <th className="border px-2 py-1">Color</th>
                    <th className="border px-2 py-1">Definition</th>
                    <th className="border px-2 py-1">Example</th>
                    <th className="border px-2 py-1">Attributes</th>
                    <th className="border px-2 py-1">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {taxonomyNodes.map((node) => (
                    <tr key={node.id}>
                      <td className="border px-2 py-1">{node.name}</td>
                      <td className="border px-2 py-1"><span style={{background: node.color, padding: '2px 8px', borderRadius: 4, color: '#fff'}}>{node.color}</span></td>
                      <td className="border px-2 py-1">{node.definition}</td>
                      <td className="border px-2 py-1">{node.example}</td>
                      <td className="border px-2 py-1">{JSON.stringify(node.attributes)}</td>
                      <td className="border px-2 py-1">
                        <button className="btn btn-xs btn-primary mr-1" onClick={() => handleEditNode(node)}>Edit</button>
                        <button className="btn btn-xs btn-error" onClick={() => handleDeleteNode(node.id)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div>
            <h3 className="text-lg font-medium text-secondary-800 mb-2">Edge Types</h3>
            {taxonomyLoading ? (
              <div>Loading...</div>
            ) : (
              <table className="min-w-full border text-sm">
                <thead>
                  <tr>
                    <th className="border px-2 py-1">Name</th>
                    <th className="border px-2 py-1">Color</th>
                    <th className="border px-2 py-1">Definition</th>
                    <th className="border px-2 py-1">Example</th>
                    <th className="border px-2 py-1">Directionality</th>
                    <th className="border px-2 py-1">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {taxonomyEdges.map((edge) => (
                    <tr key={edge.id}>
                      <td className="border px-2 py-1">{edge.name}</td>
                      <td className="border px-2 py-1"><span style={{background: edge.color, padding: '2px 8px', borderRadius: 4, color: '#fff'}}>{edge.color}</span></td>
                      <td className="border px-2 py-1">{edge.definition}</td>
                      <td className="border px-2 py-1">{edge.example}</td>
                      <td className="border px-2 py-1">{edge.directionality}</td>
                      <td className="border px-2 py-1">
                        <button className="btn btn-xs btn-primary mr-1" onClick={() => handleEditEdge(edge)}>Edit</button>
                        <button className="btn btn-xs btn-error" onClick={() => handleDeleteEdge(edge.id)}>Delete</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <button className="btn btn-sm btn-primary mb-2" onClick={handleAddNode}>Add Node Type</button>
          <button className="btn btn-sm btn-primary mb-2" onClick={handleAddEdge}>Add Edge Type</button>
        </div>
      )}

      {/* Database Tab */}
      {activeTab === 'database' && (
        <div className="space-y-6">
          <div className="card">
            <div className="card-header">
              <h3 className="text-lg font-medium text-secondary-900 flex items-center">
                <Database className="w-5 h-5 mr-2" />
                Database Management
              </h3>
              <p className="text-sm text-secondary-600">
                Clean up email-related data while preserving taxonomy configuration
              </p>
            </div>
            <div className="card-body">
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
                <div className="flex items-start">
                  <AlertCircle className="w-5 h-5 text-yellow-600 mt-0.5 mr-3 flex-shrink-0" />
                  <div>
                    <h4 className="text-sm font-medium text-yellow-800 mb-1">
                      Database Cleanup Information
                    </h4>
                    <div className="text-sm text-yellow-700 space-y-1">
                      <p><strong>What gets deleted:</strong> All processed emails, attachments, URLs, entities, and knowledge graph connections</p>
                      <p><strong>What is preserved:</strong> Taxonomy node types and edge types (essential for AI processing)</p>
                      <p><strong>After cleanup:</strong> Use the "Force reprocess" button in the top header to reprocess all emails</p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="border border-secondary-200 rounded-lg p-4">
                  <h4 className="font-medium text-secondary-900 mb-2 flex items-center">
                    <Trash2 className="w-4 h-4 mr-2" />
                    Email Data Cleanup
                  </h4>
                  <p className="text-sm text-secondary-600 mb-4">
                    Remove all processed email data, attachments, and extracted content while preserving your taxonomy configuration.
                    This is useful for starting fresh or troubleshooting processing issues.
                  </p>
                  
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
                    <div className="flex items-start">
                      <XCircle className="w-4 h-4 text-red-600 mt-0.5 mr-2 flex-shrink-0" />
                      <div className="text-sm text-red-700">
                        <p className="font-medium mb-1">⚠️ This action cannot be undone</p>
                        <p>All email processing history will be permanently deleted. Make sure you want to proceed.</p>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={cleanupDatabase}
                    disabled={cleaningDatabase}
                    className="flex items-center px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Trash2 className={`w-4 h-4 mr-2 ${cleaningDatabase ? 'animate-pulse' : ''}`} />
                    {cleaningDatabase ? 'Cleaning Database...' : 'Clean Email Data'}
                  </button>

                  {/* Cleanup message */}
                  {cleanupMessage && (
                    <div className={`mt-4 p-3 rounded-lg border ${
                      cleanupMessage.type === 'success' 
                        ? 'bg-green-50 border-green-200 text-green-700' 
                        : 'bg-red-50 border-red-200 text-red-700'
                    }`}>
                      <div className="flex items-start">
                        {cleanupMessage.type === 'success' ? (
                          <CheckCircle className="w-4 h-4 mt-0.5 mr-2 flex-shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 mt-0.5 mr-2 flex-shrink-0" />
                        )}
                        <p className="text-sm">{cleanupMessage.text}</p>
                      </div>
                    </div>
                  )}
                </div>

                <div className="border border-secondary-200 rounded-lg p-4">
                  <h4 className="font-medium text-secondary-900 mb-2 flex items-center">
                    <Brain className="w-4 h-4 mr-2" />
                    Protected Taxonomy System
                  </h4>
                  <p className="text-sm text-secondary-600 mb-3">
                    Your modern 9-node taxonomy system is automatically protected during cleanup operations.
                  </p>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <div className="flex items-start">
                      <CheckCircle className="w-4 h-4 text-green-600 mt-0.5 mr-2 flex-shrink-0" />
                      <div className="text-sm text-green-700">
                        <p className="font-medium mb-1">✅ Always Preserved</p>
                        <ul className="space-y-1">
                          <li>• Taxonomy node types (idea, evidence, method, etc.)</li>
                          <li>• Taxonomy edge types (supports, contradicts, etc.)</li>
                          <li>• AI processing configuration</li>
                          <li>• Knowledge graph visualization settings</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {showNodeModal && (
        <NodeModal node={editingNode} onClose={() => { setShowNodeModal(false); setEditingNode(null) }} />
      )}
      {showEdgeModal && (
        <EdgeModal edge={editingEdge} onClose={() => { setShowEdgeModal(false); setEditingEdge(null) }} />
      )}
    </div>
  )
}

export default SettingsPage 