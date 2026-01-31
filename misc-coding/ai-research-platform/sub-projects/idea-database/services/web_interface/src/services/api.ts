import axios, { AxiosInstance, AxiosResponse } from 'axios'
import {
  Idea,
  URL,
  Attachment,
  Entity,
  ProcessingSummary,
  SearchQuery,
  DashboardStats,
  SearchFilters,
  SearchResults,
  KnowledgeGraphData,
  CategoryAnalytics,
  SenderAnalytics,
  EntityAnalytics,
  ProcessingConfig,
  ApiResponse,
  PaginatedResponse,
  TimeSeriesData,
} from '../types'

class ApiService {
  private api: AxiosInstance

  constructor() {
    this.api = axios.create({
      baseURL: '/api/email',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // Response interceptor
    this.api.interceptors.response.use(
      (response: AxiosResponse) => {
        return response
      },
      (error) => {
        console.error('API Error:', error.response?.data || error.message)
        return Promise.reject(error)
      }
    )
  }

  // Dashboard endpoints
  async getDashboardStats(): Promise<DashboardStats> {
    const response = await this.api.get<ApiResponse<DashboardStats>>('/dashboard/stats')
    return response.data.data
  }

  async getRecentActivity(limit = 20): Promise<any[]> {
    const response = await this.api.get<ApiResponse<any[]>>(`/dashboard/activity?limit=${limit}`)
    return response.data.data
  }

  // Ideas endpoints
  async getIdeas(
    page = 1,
    per_page = 20,
    filters?: SearchFilters
  ): Promise<PaginatedResponse<Idea>> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    })

    if (filters) {
      if (filters.entity_types?.length) {
        params.append('categories', filters.entity_types.join(','))  // Note: using 'categories' param for backend compatibility
      }
      if (filters.senders?.length) {
        params.append('senders', filters.senders.join(','))
      }
      if (filters.processing_status?.length) {
        params.append('status', filters.processing_status.join(','))
      }
      if (filters.date_range) {
        params.append('start_date', filters.date_range.start)
        params.append('end_date', filters.date_range.end)
      }
    }

    const response = await this.api.get<ApiResponse<PaginatedResponse<Idea>>>(
      `/ideas?${params.toString()}`
    )
    return response.data.data
  }

  async getIdea(id: string): Promise<Idea> {
    const response = await this.api.get<ApiResponse<Idea>>(`/ideas/${id}`)
    return response.data.data
  }

  async updateIdea(id: string, updates: Partial<Idea>): Promise<Idea> {
    const response = await this.api.patch<ApiResponse<Idea>>(`/ideas/${id}`, updates)
    return response.data.data
  }

  async deleteIdea(id: string): Promise<void> {
    await this.api.delete(`/ideas/${id}`)
  }

  async reprocessIdea(id: string): Promise<void> {
    await this.api.post(`/ideas/${id}/reprocess`)
  }

  // URLs endpoints
  async getIdeaUrls(ideaId: string): Promise<URL[]> {
    const response = await this.api.get<ApiResponse<URL[]>>(`/ideas/${ideaId}/urls`)
    return response.data.data
  }

  async refetchUrl(urlId: string): Promise<URL> {
    const response = await this.api.post<ApiResponse<URL>>(`/urls/${urlId}/refetch`)
    return response.data.data
  }

  // Attachments endpoints
  async getIdeaAttachments(ideaId: string): Promise<Attachment[]> {
    const response = await this.api.get<ApiResponse<Attachment[]>>(`/ideas/${ideaId}/attachments`)
    return response.data.data
  }

  async downloadAttachment(attachmentId: string): Promise<Blob> {
    const response = await this.api.get(`/attachments/${attachmentId}/download`, {
      responseType: 'blob',
    })
    return response.data
  }

  // Entities endpoints
  async getIdeaEntities(ideaId: string): Promise<Entity[]> {
    const response = await this.api.get<ApiResponse<Entity[]>>(`/ideas/${ideaId}/entities`)
    return response.data.data
  }

  async getAllEntities(
    page = 1,
    per_page = 50,
    entity_type?: string
  ): Promise<PaginatedResponse<Entity>> {
    const params = new URLSearchParams({
      page: page.toString(),
      per_page: per_page.toString(),
    })

    if (entity_type) {
      params.append('type', entity_type)
    }

    const response = await this.api.get<ApiResponse<PaginatedResponse<Entity>>>(
      `/entities?${params.toString()}`
    )
    return response.data.data
  }

  // Search endpoints
  async search(
    query: string,
    type: 'semantic' | 'keyword' | 'entity' = 'semantic',
    filters?: SearchFilters,
    page = 1,
    per_page = 20
  ): Promise<SearchResults> {
    const payload = {
      query,
      type,
      filters,
      page,
      per_page,
    }

    const response = await this.api.post<ApiResponse<SearchResults>>('/search', payload)
    return response.data.data
  }

  async getSearchSuggestions(query: string): Promise<string[]> {
    const response = await this.api.get<ApiResponse<string[]>>(
      `/search/suggestions?q=${encodeURIComponent(query)}`
    )
    return response.data.data
  }

  // Knowledge Graph endpoints
  async getKnowledgeGraph(limit = 200): Promise<KnowledgeGraphData> {
    const response = await this.api.get<KnowledgeGraphData>(`/knowledge-graph?limit=${limit}`);
    return response.data;
  }

  async updateNodeLabel(nodeId: string, label: string): Promise<{ status: string; node_id: string; node_type: string; new_label: string; message: string }> {
    const response = await this.api.put<{ status: string; node_id: string; node_type: string; new_label: string; message: string }>(`/knowledge-graph/nodes/${nodeId}`, { label });
    return response.data;
  }

  // Email-specific Knowledge Graph endpoints
  async getEmailKnowledgeGraph(emailId: string): Promise<{
    status: string;
    email: { id: string; subject: string; sender: string };
    knowledge_graph: {
      entities: Array<{
        id: string;
        name: string;
        type: string;
        description: string;
        confidence: number;
        created_at: string;
      }>;
      relationships: Array<{
        id: string;
        source: string;
        target: string;
        type: string;
        weight: number;
        context: string;
        created_at: string;
      }>;
    };
  }> {
    const response = await this.api.get(`/source-emails/${emailId}/knowledge-graph`);
    return response.data;
  }

  async createEmailEntity(emailId: string, entity: {
    name: string;
    node_type: string;
    description: string;
    confidence?: number;
  }): Promise<{
    status: string;
    message: string;
    entity: {
      id: string;
      name: string;
      type: string;
      description: string;
      email_id: string;
    };
  }> {
    const response = await this.api.post(`/source-emails/${emailId}/entities`, entity);
    return response.data;
  }

  async updateEntity(entityId: string, updates: {
    name?: string;
    description?: string;
    confidence?: number;
  }): Promise<{
    status: string;
    message: string;
    entity: {
      id: string;
      name: string;
      type: string;
      description: string;
      email_id: string;
    };
  }> {
    const response = await this.api.put(`/entities/${entityId}`, updates);
    return response.data;
  }

  async deleteEntity(entityId: string): Promise<{
    status: string;
    message: string;
    deleted_entity: {
      id: string;
      name: string;
      email_id: string;
    };
  }> {
    const response = await this.api.delete(`/entities/${entityId}`);
    return response.data;
  }

  async createEmailRelationship(emailId: string, relationship: {
    source_node_id: string;
    target_node_id: string;
    source_entity_name: string;
    target_entity_name: string;
    edge_type: string;
    description: string;
    confidence?: number;
  }): Promise<{
    status: string;
    message: string;
    relationship: {
      id: string;
      source: string;
      target: string;
      type: string;
      context: string;
      weight: number;
      email_id: string;
    };
  }> {
    const response = await this.api.post(`/source-emails/${emailId}/relationships`, relationship);
    return response.data;
  }

  // Email-specific URLs and Attachments endpoints
  async getEmailUrls(emailId: string): Promise<{
    status: string;
    email_id: string;
    urls: Array<{
      id: string;
      url: string;
      domain: string;
      title: string;
      description: string;
      content_type: string;
      fetch_status: string;
      word_count: number;
      fetch_date: string | null;
      processing_status: string;
      has_content: boolean;
    }>;
    count: number;
  }> {
    const response = await this.api.get(`/source-emails/${emailId}/urls`);
    return response.data;
  }

  async getEmailAttachments(emailId: string): Promise<{
    status: string;
    email_id: string;
    attachments: Array<{
      id: string;
      filename: string;
      original_filename: string;
      file_type: string;
      file_size: number;
      content_hash: string;
      processing_status: string;
      conversion_status: string;
      storage_type: string;
      gmail_message_id: string;
      gmail_attachment_id: string;
      created_at: string;
    }>;
    count: number;
  }> {
    const response = await this.api.get(`/source-emails/${emailId}/attachments`);
    return response.data;
  }

  async updateEmailContent(emailId: string, content: string): Promise<{
    status: string;
    message: string;
    email: {
      id: string;
      subject: string;
      cleaned_content: string;
    };
  }> {
    const response = await this.api.put(`/source-emails/${emailId}/content`, { content });
    return response.data;
  }

  // Analytics endpoints
  async getTimeSeriesData(
    metric: 'ideas' | 'entities' | 'processing_time',
    period: 'day' | 'week' | 'month' = 'day',
    days = 30
  ): Promise<TimeSeriesData[]> {
    const response = await this.api.get<ApiResponse<TimeSeriesData[]>>(
      `/processing/timeseries?metric=${metric}&period=${period}&days=${days}`
    )
    return response.data.data
  }

  async getCategoryAnalytics(): Promise<CategoryAnalytics[]> {
    const response = await this.api.get<ApiResponse<CategoryAnalytics[]>>('/analytics/categories')
    return response.data.data
  }

  async getSenderAnalytics(limit = 20): Promise<SenderAnalytics[]> {
    const response = await this.api.get<ApiResponse<SenderAnalytics[]>>(
      `/analytics/senders?limit=${limit}`
    )
    return response.data.data
  }

  async getEntityAnalytics(
    entity_type?: string,
    limit = 50
  ): Promise<EntityAnalytics[]> {
    const params = new URLSearchParams({ limit: limit.toString() })
    if (entity_type) {
      params.append('type', entity_type)
    }

    const response = await this.api.get<ApiResponse<EntityAnalytics[]>>(
      `/analytics/entities?${params.toString()}`
    )
    return response.data.data
  }

  // Processing endpoints
  /**
   * Manually trigger an email sync / processing run.
   * Maps to the backend Email-Processor endpoint POST /process-emails.
   */
  async triggerProcessing(options?: { force_reprocess?: boolean; max_emails?: number }): Promise<void> {
    await this.api.post('/process-emails', {
      force_reprocess: options?.force_reprocess ?? false,
      max_emails: options?.max_emails ?? 50,
    })
  }

  async getProcessingStatus(): Promise<{
    status: 'idle' | 'processing' | 'error'
    current_task?: string
    progress?: number
    estimated_completion?: string
  }> {
    const response = await this.api.get('/processing/status')
    return response.data.data
  }

  async getProcessingSummary(days = 7): Promise<ProcessingSummary[]> {
    const response = await this.api.get<ApiResponse<ProcessingSummary[]>>(
      `/processing/summary?days=${days}`
    )
    return response.data.data
  }

  // Configuration endpoints
  async getConfig(): Promise<ProcessingConfig> {
    const response = await this.api.get<ApiResponse<ProcessingConfig>>('/config')
    return response.data.data
  }

  async updateConfig(config: Partial<ProcessingConfig>): Promise<ProcessingConfig> {
    const response = await this.api.patch<ApiResponse<ProcessingConfig>>('/config', config)
    return response.data.data
  }

  // Health check
  async healthCheck(): Promise<{
    status: 'healthy' | 'degraded' | 'unhealthy'
    services: Record<string, 'up' | 'down'>
    timestamp: string
  }> {
    const response = await this.api.get('/health')
    return response.data.data
  }

  // Search suggestions
  async getSearchSuggestionsFromAPI(query: string): Promise<string[]> {
    const response = await this.api.get<ApiResponse<string[]>>('/search/suggestions', {
      params: { query }
    })
    return response.data.data
  }

  // Saved searches
  async getSavedSearchesFromAPI(): Promise<any[]> {
    const response = await this.api.get<ApiResponse<any[]>>('/search/saved')
    return response.data.data
  }

  // Save search
  async saveSearchToAPI(searchData: {
    name: string
    query: string
    type: 'semantic' | 'keyword' | 'entity'
    filters: SearchFilters
  }): Promise<void> {
    await this.api.post('/search/saved', searchData)
  }

  // Node details
  async getNodeDetailsFromAPI(nodeId: string): Promise<any> {
    const response = await this.api.get<ApiResponse<any>>(`/knowledge-graph/nodes/${nodeId}`)
    return response.data.data
  }

  // ------------------------------------------------------------------
  // X API (Tweets)
  // ------------------------------------------------------------------

  async getXApiUsage(): Promise<{ month: string; calls_used: number; calls_limit: number }> {
    const response = await this.api.get<ApiResponse<any>>('/x-posts/api-usage')
    return response.data.data || response.data
  }

  async getXPosts(page = 1, limit = 20): Promise<PaginatedResponse<any>> {
    const offset = (page - 1) * limit
    const response = await this.api.get<ApiResponse<any>>(`/x-posts?limit=${limit}&offset=${offset}`)
    return response.data.data || response.data
  }

  async fetchXPosts(urls: string[]): Promise<any> {
    const response = await this.api.post<ApiResponse<any>>('/x-posts/fetch', { urls })
    return response.data.data || response.data
  }
}

export const apiService = new ApiService()
export default apiService

// Advanced Search Functions
export const searchIdeas = async (params: {
  query: string
  type: 'semantic' | 'keyword' | 'entity'
  filters: SearchFilters
  page: number
  per_page: number
}): Promise<SearchResults> => {
  // For now, use the main API service
  return apiService.search(params.query, params.type, params.filters, params.page, params.per_page)
}

export const getSearchSuggestions = async (query: string): Promise<string[]> => {
  return apiService.getSearchSuggestionsFromAPI(query)
}

export const getSavedSearches = async (): Promise<any[]> => {
  return apiService.getSavedSearchesFromAPI()
}

export const saveSearch = async (searchData: {
  name: string
  query: string
  type: 'semantic' | 'keyword' | 'entity'
  filters: SearchFilters
}): Promise<void> => {
  return apiService.saveSearchToAPI(searchData)
}

export const getKnowledgeGraph = async (limit: number = 200): Promise<KnowledgeGraphData> => {
    return apiService.getKnowledgeGraph(limit)
}

export const getNodeDetails = async (nodeId: string): Promise<any> => {
    return apiService.getNodeDetailsFromAPI(nodeId)
}

// Analytics Functions
export const getAnalytics = async (timeRange: string = '30d'): Promise<any> => {
  // Use existing methods from ApiService or create a generic analytics endpoint
  const [categoryData, senderData, entityData] = await Promise.all([
    apiService.getCategoryAnalytics(),
    apiService.getSenderAnalytics(),
    apiService.getEntityAnalytics()
  ])
  
  return {
    categories: categoryData,
    senders: senderData,
    entities: entityData,
    time_range: timeRange
  }
}

export const getCategoryAnalytics = async (): Promise<CategoryAnalytics[]> => {
  return apiService.getCategoryAnalytics()
}

export const getSenderAnalytics = async (): Promise<SenderAnalytics[]> => {
  return apiService.getSenderAnalytics()
}

export const getEntityAnalytics = async (): Promise<EntityAnalytics[]> => {
  return apiService.getEntityAnalytics()
}

export const getTimeSeriesData = async (
  metric: string,
  timeRange: string = '30d'
): Promise<TimeSeriesData[]> => {
  return apiService.getTimeSeriesData(
    metric as 'ideas' | 'entities' | 'processing_time',
    'day',
    parseInt(timeRange.replace('d', ''))
  )
}

// Real-time Functions
export const subscribeToUpdates = (callback: (data: any) => void) => {
  // WebSocket connection for real-time updates
  const ws = new WebSocket(`ws://localhost:3002/ws`)
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    callback(data)
  }
  
  return ws
}

export const getProcessingStatus = async (): Promise<{
  is_processing: boolean
  current_batch: number
  total_batches: number
  eta_minutes: number
}> => {
  const status = await apiService.getProcessingStatus()
  return {
    is_processing: status.status === 'processing',
    current_batch: status.progress || 0,
    total_batches: 100,
    eta_minutes: status.estimated_completion ? 
      Math.ceil((new Date(status.estimated_completion).getTime() - Date.now()) / 60000) : 0
  }
} 