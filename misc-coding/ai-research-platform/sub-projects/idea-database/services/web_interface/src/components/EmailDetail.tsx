import React from 'react'
import { X, RefreshCw, Trash2, FileText, Download, Plus, Edit, Network, Eye } from 'lucide-react'
import { format } from 'date-fns'
import { Idea, Attachment, URL } from '../types'
import { useQuery, useMutation, useQueryClient } from 'react-query'
import { apiService } from '../services/api'
import UrlTable from './UrlTable'
import AttachmentTable from './AttachmentTable'

interface EmailDetailProps {
  email: Idea
  onClose: () => void
  onAction: (action: string, email: Idea) => void
}

const EmailDetail: React.FC<EmailDetailProps> = ({ email, onClose, onAction }) => {
  const queryClient = useQueryClient()
  const [showAttachmentModal, setShowAttachmentModal] = React.useState(false)
  const [selectedAttachment, setSelectedAttachment] = React.useState<any>(null)
  const [showKnowledgeGraph, setShowKnowledgeGraph] = React.useState(false)
  const [showEntityModal, setShowEntityModal] = React.useState(false)
  const [showRelationshipModal, setShowRelationshipModal] = React.useState(false)
  const [selectedEntity, setSelectedEntity] = React.useState<any>(null)
  const [isEditingContent, setIsEditingContent] = React.useState(false)
  const [editedContent, setEditedContent] = React.useState('')
  const [newEntity, setNewEntity] = React.useState({
    name: '',
    node_type: 'concept',
    description: '',
    confidence: 0.9
  })
  const [newRelationship, setNewRelationship] = React.useState({
    source_node_id: '',
    target_node_id: '',
    source_entity_name: '',
    target_entity_name: '',
    edge_type: 'relates_to',
    description: '',
    confidence: 0.9
  })

  // Fetch email URLs and attachments directly
  const { data: urlsData, isLoading: urlsLoading } = useQuery(
    ['email-urls', email.id], 
    () => apiService.getEmailUrls(email.id)
  )
  
  const { data: attachmentsData, isLoading: attachmentsLoading } = useQuery(
    ['email-attachments', email.id], 
    () => apiService.getEmailAttachments(email.id)
  )
  
  // Fetch email knowledge graph
  const { data: knowledgeGraphData, isLoading: kgLoading, refetch: refetchKG } = useQuery(
    ['email-knowledge-graph', email.id], 
    () => apiService.getEmailKnowledgeGraph(email.id),
    { enabled: showKnowledgeGraph }
  )
  
  // Extract data from API responses
  const urls: any[] = urlsData?.urls || []
  const attachments: any[] = attachmentsData?.attachments || []
  const entities = knowledgeGraphData?.knowledge_graph?.entities || []
  const relationships = knowledgeGraphData?.knowledge_graph?.relationships || []



  // Entity mutations
  const createEntityMutation = useMutation(
    (entity: typeof newEntity) => apiService.createEmailEntity(email.id, entity),
    {
      onSuccess: () => {
        refetchKG()
        setShowEntityModal(false)
        setNewEntity({ name: '', node_type: 'concept', description: '', confidence: 0.9 })
      },
    }
  )

  const updateEntityMutation = useMutation(
    ({ entityId, updates }: { entityId: string; updates: any }) => 
      apiService.updateEntity(entityId, updates),
    {
      onSuccess: () => {
        refetchKG()
        setShowEntityModal(false)
        setSelectedEntity(null)
      },
    }
  )

  const deleteEntityMutation = useMutation(
    (entityId: string) => apiService.deleteEntity(entityId),
    {
      onSuccess: () => {
        refetchKG()
      },
    }
  )

  // Relationship mutation
  const createRelationshipMutation = useMutation(
    (relationship: typeof newRelationship) => 
      apiService.createEmailRelationship(email.id, relationship),
    {
      onSuccess: () => {
        refetchKG()
        setShowRelationshipModal(false)
        setNewRelationship({
          source_node_id: '',
          target_node_id: '',
          source_entity_name: '',
          target_entity_name: '',
          edge_type: 'relates_to',
          description: '',
          confidence: 0.9
        })
      },
    }
  )

  // Content update mutation
  const updateContentMutation = useMutation(
    (content: string) => apiService.updateEmailContent(email.id, content),
    {
      onSuccess: (data) => {
        setIsEditingContent(false)
        // Update the email object directly
        if (data.email.cleaned_content) {
          email.cleaned_content = data.email.cleaned_content
        }
        // Invalidate email-related queries to refresh the list
        queryClient.invalidateQueries({ predicate: (q) => 
          Array.isArray(q.queryKey) && q.queryKey[0] === 'emails' 
        })
      },
    }
  )



  const handleCreateEntity = () => {
    if (newEntity.name.trim()) {
      createEntityMutation.mutate(newEntity)
    }
  }

  const handleUpdateEntity = () => {
    if (selectedEntity) {
      updateEntityMutation.mutate({
        entityId: selectedEntity.id,
        updates: {
          name: selectedEntity.name,
          description: selectedEntity.description,
          confidence: selectedEntity.confidence
        }
      })
    }
  }

  const handleDeleteEntity = (entityId: string) => {
    if (confirm('Are you sure you want to delete this entity?')) {
      deleteEntityMutation.mutate(entityId)
    }
  }

  const handleCreateRelationship = () => {
    if (newRelationship.source_node_id && newRelationship.target_node_id) {
      createRelationshipMutation.mutate(newRelationship)
    }
  }

  const openEditEntityModal = (entity: any) => {
    setSelectedEntity({ ...entity })
    setShowEntityModal(true)
  }

  const openNewEntityModal = () => {
    setSelectedEntity(null)
    setNewEntity({ name: '', node_type: 'concept', description: '', confidence: 0.9 })
    setShowEntityModal(true)
  }

  const startEditingContent = () => {
    setEditedContent(email.cleaned_content || email.original_content || '')
    setIsEditingContent(true)
  }

  const cancelEditingContent = () => {
    setIsEditingContent(false)
    setEditedContent('')
  }

  const saveContent = () => {
    if (editedContent.trim() !== (email.cleaned_content || email.original_content || '').trim()) {
      updateContentMutation.mutate(editedContent)
    } else {
      setIsEditingContent(false)
    }
  }

  const handleViewAttachment = async (att: Attachment) => {
    try {
      const response = await fetch(`/api/email/attachments/${att.id}/info`)
      const data = await response.json()
      setSelectedAttachment(data)
      setShowAttachmentModal(true)
    } catch (error) {
      console.error('Error fetching attachment:', error)
      alert('Error loading attachment details')
    }
  }

  const handleDownloadAttachment = async (att: Attachment) => {
    try {
      const response = await fetch(`/api/email/attachments/${att.id}/download`)
      
      // Check if response is actually a file (binary) or JSON metadata
      const contentType = response.headers.get('content-type')
      
      if (contentType && contentType.includes('application/json')) {
        // It's JSON metadata - show the modal with download explanation
        const data = await response.json()
        setSelectedAttachment(data)
        setShowAttachmentModal(true)
      } else {
        // It's an actual file - trigger download
        const blob = await response.blob()
        const url = window.URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = att.filename || 'attachment'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        window.URL.revokeObjectURL(url)
      }
    } catch (error) {
      console.error('Error downloading attachment:', error)
      alert('Error downloading attachment')
    }
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-secondary-200">
          <div>
            <h2 className="text-lg font-medium text-secondary-900">
              {email.subject || 'No Subject'}
            </h2>
            <p className="text-sm text-secondary-500">
              from {email.sender_name} ({email.sender_email})
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-secondary-400 hover:text-secondary-600"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {/* Metadata */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Received Date
              </label>
              <p className="text-sm text-secondary-900">
                {format(new Date(email.received_date), 'MMM dd, yyyy HH:mm')}
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Processing Status
              </label>
              <span className="badge badge-secondary">{email.processing_status}</span>
            </div>
            <div>
              <label className="block text-sm font-medium text-secondary-700">
                Content Type
              </label>
              <p className="text-sm text-secondary-900">{email.content_type}</p>
            </div>
          </div>

          {/* AI Summary */}
          {email.ai_summary && (
            <div>
              <label className="block text-sm font-medium text-secondary-700 mb-2">
                AI Summary
              </label>
              <div className="bg-primary-50 p-4 rounded-lg">
                <p className="text-sm text-secondary-900">{email.ai_summary}</p>
              </div>
            </div>
          )}

          {/* Content */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-secondary-700">
                Content
              </label>
              {!isEditingContent ? (
                <button
                  onClick={startEditingContent}
                  className="btn btn-secondary btn-sm"
                >
                  <Edit className="h-4 w-4 mr-1" />
                  Edit Content
                </button>
              ) : (
                <div className="flex items-center space-x-2">
                  <button
                    onClick={cancelEditingContent}
                    className="btn btn-secondary btn-sm"
                    disabled={updateContentMutation.isLoading}
                  >
                    Cancel
                  </button>
                  <button
                    onClick={saveContent}
                    className="btn btn-primary btn-sm"
                    disabled={updateContentMutation.isLoading}
                  >
                    {updateContentMutation.isLoading ? (
                      <RefreshCw className="h-4 w-4 animate-spin mr-1" />
                    ) : null}
                    Save Content
                  </button>
                </div>
              )}
            </div>
            
            {isEditingContent ? (
              <div className="space-y-2">
                <textarea
                  value={editedContent}
                  onChange={(e) => setEditedContent(e.target.value)}
                  className="input min-h-96 font-mono text-sm"
                  placeholder="Email content..."
                />
                <div className="text-xs text-secondary-500">
                  {editedContent.length} characters
                </div>
              </div>
            ) : (
              <div className="bg-secondary-50 p-4 rounded-lg max-h-96 overflow-y-auto">
                <pre className="text-sm text-secondary-900 whitespace-pre-wrap">
                  {email.cleaned_content || email.original_content}
                </pre>
              </div>
            )}
          </div>

          {/* URLs */}
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-2">Extracted URLs</label>
            <UrlTable urls={urls} />
          </div>

          {/* Attachments */}
          <div>
            <label className="block text-sm font-medium text-secondary-700 mb-2">Attachments</label>
            <AttachmentTable atts={attachments} onView={handleViewAttachment} onDownload={handleDownloadAttachment} />
          </div>

          {/* Knowledge Graph Section */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-secondary-700">Knowledge Graph</label>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => setShowKnowledgeGraph(!showKnowledgeGraph)}
                  className="btn btn-secondary btn-sm"
                >
                  <Network className="h-4 w-4 mr-1" />
                  {showKnowledgeGraph ? 'Hide' : 'Show'} Graph
                </button>
                {showKnowledgeGraph && (
                  <>
                    <button
                      onClick={openNewEntityModal}
                      className="btn btn-primary btn-sm"
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add Entity
                    </button>
                    <button
                      onClick={() => setShowRelationshipModal(true)}
                      className="btn btn-primary btn-sm"
                      disabled={entities.length < 2}
                    >
                      <Plus className="h-4 w-4 mr-1" />
                      Add Relationship
                    </button>
                  </>
                )}
              </div>
            </div>

            {showKnowledgeGraph && (
              <div className="bg-secondary-50 p-4 rounded-lg">
                {kgLoading ? (
                  <div className="text-center py-4">
                    <div className="inline-flex items-center">
                      <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                      Loading knowledge graph...
                    </div>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {/* Entities */}
                    <div>
                      <h4 className="text-sm font-medium text-secondary-700 mb-2">
                        Entities ({entities.length})
                      </h4>
                      {entities.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                          {entities.map((entity: any) => (
                            <div
                              key={entity.id}
                              className="bg-white p-3 rounded border border-secondary-200 hover:border-primary-300 transition-colors"
                            >
                              <div className="flex items-center justify-between">
                                <div className="flex-1">
                                  <div className="font-medium text-sm text-secondary-900">
                                    {entity.name}
                                  </div>
                                  <div className="text-xs text-secondary-500">
                                    {entity.type} • {Math.round(entity.confidence * 100)}% confidence
                                  </div>
                                  {entity.description && (
                                    <div className="text-xs text-secondary-600 mt-1 line-clamp-2">
                                      {entity.description}
                                    </div>
                                  )}
                                </div>
                                <div className="flex items-center space-x-1 ml-2">
                                  <button
                                    onClick={() => openEditEntityModal(entity)}
                                    className="p-1 text-secondary-400 hover:text-primary-600"
                                    title="Edit entity"
                                  >
                                    <Edit className="h-3 w-3" />
                                  </button>
                                  <button
                                    onClick={() => handleDeleteEntity(entity.id)}
                                    className="p-1 text-secondary-400 hover:text-error-600"
                                    title="Delete entity"
                                  >
                                    <Trash2 className="h-3 w-3" />
                                  </button>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-sm text-secondary-500 italic">
                          No entities found. Click "Add Entity" to create one.
                        </div>
                      )}
                    </div>

                    {/* Relationships */}
                    <div>
                      <h4 className="text-sm font-medium text-secondary-700 mb-2">
                        Relationships ({relationships.length})
                      </h4>
                      {relationships.length > 0 ? (
                        <div className="space-y-2">
                          {relationships.map((rel: any) => (
                            <div
                              key={rel.id}
                              className="bg-white p-3 rounded border border-secondary-200"
                            >
                              <div className="text-sm">
                                <span className="font-medium text-primary-600">{rel.source}</span>
                                <span className="mx-2 text-secondary-400">→</span>
                                <span className="text-secondary-600">{rel.type}</span>
                                <span className="mx-2 text-secondary-400">→</span>
                                <span className="font-medium text-primary-600">{rel.target}</span>
                              </div>
                              {rel.context && (
                                <div className="text-xs text-secondary-500 mt-1">
                                  {rel.context}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="text-sm text-secondary-500 italic">
                          No relationships found. Click "Add Relationship" to create one.
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end space-x-3 p-6 border-t border-secondary-200">
          <button
            onClick={() => onAction('reprocess', email)}
            className="btn btn-secondary"
          >
            <RefreshCw className="h-4 w-4 mr-2" />
            Reprocess
          </button>
          <button
            onClick={() => onAction('delete', email)}
            className="btn bg-error-600 text-white hover:bg-error-700"
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Delete
          </button>
          <button onClick={onClose} className="btn btn-primary">
            Close
          </button>
        </div>
      </div>

      {/* Attachment Modal */}
      {showAttachmentModal && selectedAttachment && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-60">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-secondary-900 flex items-center">
                <FileText className="h-5 w-5 mr-2" />
                Attachment Details
              </h3>
              <button
                onClick={() => setShowAttachmentModal(false)}
                className="text-secondary-400 hover:text-secondary-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700">Filename</label>
                <p className="text-sm text-secondary-900">{selectedAttachment.attachment?.filename}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-secondary-700">File Type</label>
                <p className="text-sm text-secondary-900">{selectedAttachment.attachment?.file_type}</p>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-secondary-700">File Size</label>
                <p className="text-sm text-secondary-900">
                  {selectedAttachment.attachment?.file_size ? 
                    (selectedAttachment.attachment.file_size / 1024).toFixed(1) + ' KB' : 
                    'Unknown'
                  }
                </p>
              </div>
              
              <div className="bg-blue-50 p-4 rounded-lg">
                <p className="text-sm text-blue-800">
                  <Download className="h-4 w-4 inline mr-1" />
                  {selectedAttachment.message}
                </p>
                {selectedAttachment.attachment?.note && (
                  <p className="text-xs text-blue-600 mt-2">
                    {selectedAttachment.attachment.note}
                  </p>
                )}
                <div className="mt-3 pt-3 border-t border-blue-200">
                  <p className="text-xs text-blue-700">
                    <strong>View:</strong> Shows this metadata info<br/>
                    <strong>Download:</strong> Will download file once Gmail integration is configured
                  </p>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowAttachmentModal(false)}
                className="btn btn-primary"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Entity Modal */}
      {showEntityModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-70">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-secondary-900">
                {selectedEntity ? 'Edit Entity' : 'Add New Entity'}
              </h3>
              <button
                onClick={() => {
                  setShowEntityModal(false)
                  setSelectedEntity(null)
                }}
                className="text-secondary-400 hover:text-secondary-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Name</label>
                <input
                  type="text"
                  value={selectedEntity ? selectedEntity.name : newEntity.name}
                  onChange={(e) => {
                    if (selectedEntity) {
                      setSelectedEntity({ ...selectedEntity, name: e.target.value })
                    } else {
                      setNewEntity({ ...newEntity, name: e.target.value })
                    }
                  }}
                  className="input"
                  placeholder="Entity name"
                />
              </div>

              {!selectedEntity && (
                <div>
                  <label className="block text-sm font-medium text-secondary-700 mb-1">Type</label>
                  <select
                    value={newEntity.node_type}
                    onChange={(e) => setNewEntity({ ...newEntity, node_type: e.target.value })}
                    className="input"
                  >
                    <option value="concept">Concept</option>
                    <option value="organization">Organization</option>
                    <option value="technology">Technology</option>
                  </select>
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Description</label>
                <textarea
                  value={selectedEntity ? selectedEntity.description : newEntity.description}
                  onChange={(e) => {
                    if (selectedEntity) {
                      setSelectedEntity({ ...selectedEntity, description: e.target.value })
                    } else {
                      setNewEntity({ ...newEntity, description: e.target.value })
                    }
                  }}
                  className="input"
                  rows={3}
                  placeholder="Entity description"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">
                  Confidence ({selectedEntity ? Math.round(selectedEntity.confidence * 100) : Math.round(newEntity.confidence * 100)}%)
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={selectedEntity ? selectedEntity.confidence : newEntity.confidence}
                  onChange={(e) => {
                    const confidence = parseFloat(e.target.value)
                    if (selectedEntity) {
                      setSelectedEntity({ ...selectedEntity, confidence })
                    } else {
                      setNewEntity({ ...newEntity, confidence })
                    }
                  }}
                  className="w-full"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowEntityModal(false)
                  setSelectedEntity(null)
                }}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={selectedEntity ? handleUpdateEntity : handleCreateEntity}
                disabled={
                  (selectedEntity ? !selectedEntity.name.trim() : !newEntity.name.trim()) ||
                  createEntityMutation.isLoading ||
                  updateEntityMutation.isLoading
                }
                className="btn btn-primary"
              >
                {createEntityMutation.isLoading || updateEntityMutation.isLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                {selectedEntity ? 'Update' : 'Create'} Entity
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Relationship Modal */}
      {showRelationshipModal && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center p-4 z-70">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-secondary-900">Add New Relationship</h3>
              <button
                onClick={() => setShowRelationshipModal(false)}
                className="text-secondary-400 hover:text-secondary-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Source Entity</label>
                <select
                  value={newRelationship.source_node_id}
                  onChange={(e) => {
                    const entity = entities.find((ent: any) => ent.id === e.target.value)
                    setNewRelationship({
                      ...newRelationship,
                      source_node_id: e.target.value,
                      source_entity_name: entity?.name || ''
                    })
                  }}
                  className="input"
                >
                  <option value="">Select source entity</option>
                  {entities.map((entity: any) => (
                    <option key={entity.id} value={entity.id}>
                      {entity.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Relationship Type</label>
                <select
                  value={newRelationship.edge_type}
                  onChange={(e) => setNewRelationship({ ...newRelationship, edge_type: e.target.value })}
                  className="input"
                >
                  <option value="relates_to">relates to</option>
                  <option value="supports">supports</option>
                  <option value="enables">enables</option>
                  <option value="uses">uses</option>
                  <option value="implements">implements</option>
                  <option value="depends_on">depends on</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Target Entity</label>
                <select
                  value={newRelationship.target_node_id}
                  onChange={(e) => {
                    const entity = entities.find((ent: any) => ent.id === e.target.value)
                    setNewRelationship({
                      ...newRelationship,
                      target_node_id: e.target.value,
                      target_entity_name: entity?.name || ''
                    })
                  }}
                  className="input"
                >
                  <option value="">Select target entity</option>
                  {entities.map((entity: any) => (
                    <option key={entity.id} value={entity.id}>
                      {entity.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-secondary-700 mb-1">Description</label>
                <textarea
                  value={newRelationship.description}
                  onChange={(e) => setNewRelationship({ ...newRelationship, description: e.target.value })}
                  className="input"
                  rows={2}
                  placeholder="Describe the relationship"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowRelationshipModal(false)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateRelationship}
                disabled={
                  !newRelationship.source_node_id ||
                  !newRelationship.target_node_id ||
                  newRelationship.source_node_id === newRelationship.target_node_id ||
                  createRelationshipMutation.isLoading
                }
                className="btn btn-primary"
              >
                {createRelationshipMutation.isLoading ? (
                  <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                Create Relationship
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default EmailDetail 