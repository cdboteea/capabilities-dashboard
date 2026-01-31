// Core data types based on the database schema
export interface Idea {
  id: string
  email_id: string
  message_id: string
  subject: string
  sender_email: string
  sender_name: string
  received_date: string
  processed_date?: string
  content_type: 'email' | 'url' | 'attachment' | 'mixed'
  category: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  ai_summary?: string
  original_content: string
  cleaned_content: string
  language: string
  needs_manual_review: boolean
  priority_score?: number
  sentiment_score?: number
  created_at: string
  updated_at: string
}

export interface URL {
  id: string
  idea_id: string
  url: string
  domain: string
  title?: string
  description?: string
  content_type: string
  fetch_status: 'pending' | 'fetched' | 'failed' | 'blocked'
  archive_path?: string
  word_count?: number
  fetch_date?: string
  created_at: string
}

export interface Attachment {
  id: string
  idea_id: string
  filename: string
  original_filename: string
  file_type: string
  file_size: number
  file_path: string
  content_hash: string
  extracted_text?: string
  processing_status: 'pending' | 'processing' | 'completed' | 'failed'
  created_at: string
}

export interface Entity {
  id: string
  idea_id: string
  entity_type: string
  entity_value: string
  normalized_value: string
  confidence_score: number
  context_snippet: string
  source_type: 'content' | 'url' | 'attachment'
  source_id?: string
  created_at: string
}

export interface ProcessingSummary {
  id: string
  processing_date: string
  emails_processed: number
  urls_extracted: number
  entities_found: number
  categories_distribution: Record<string, number>
  processing_time_minutes: number
  errors_count: number
  created_at: string
}

export interface SearchQuery {
  id: string
  query_text: string
  query_type: 'semantic' | 'keyword' | 'entity'
  results_count: number
  response_time_ms: number
  user_satisfaction?: number
  created_at: string
}

// UI-specific types
export interface DashboardStats {
  total_ideas: number
  processed_today: number
  pending_processing: number
  total_entities: number
  total_urls: number
  total_attachments: number
  avg_processing_time: number
  categories_breakdown: Record<string, number>
  recent_activity: ActivityItem[]
}

export interface ActivityItem {
  id: string
  type: 'email_processed' | 'entity_extracted' | 'url_fetched' | 'error'
  description: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface SearchFilters {
  categories?: string[]
  date_range?: {
    start: string
    end: string
  }
  senders?: string[]
  entity_types?: string[]
  processing_status?: string[]
  content_type?: string[]
  sentiment_range?: {
    min: number
    max: number
  }
  priority_range?: {
    min: number
    max: number
  }
}

export interface SearchResults {
  ideas: Idea[]
  total_count: number
  facets: {
    categories: Record<string, number>
    senders: Record<string, number>
    entity_types: Record<string, number>
    domains: Record<string, number>
  }
  query_time_ms: number
}

export interface KnowledgeGraphNode {
  id: string
  label: string
  type: 'idea' | 'entity' | 'category' | 'sender'
  size: number
  color: string
  metadata: Record<string, any>
}

export interface KnowledgeGraphEdge {
  id: string
  source: string
  target: string
  type: 'contains' | 'related_to' | 'sent_by' | 'categorized_as'
  weight: number
  label?: string
}

export interface KnowledgeGraphData {
  nodes: KnowledgeGraphNode[]
  edges: KnowledgeGraphEdge[]
  stats: {
    total_nodes: number
    total_edges: number
    clusters: number
    density: number
  }
}

// Analytics types
export interface TimeSeriesData {
  date: string
  value: number
  category?: string
}

export interface CategoryAnalytics {
  category: string
  count: number
  percentage: number
  trend: 'up' | 'down' | 'stable'
  change_percent: number
}

export interface SenderAnalytics {
  sender_email: string
  sender_name: string
  total_emails: number
  avg_priority: number
  avg_sentiment: number
  categories: Record<string, number>
  last_email: string
}

export interface EntityAnalytics {
  entity_type: string
  entity_value: string
  frequency: number
  avg_confidence: number
  related_categories: string[]
  first_seen: string
  last_seen: string
}

// API response types
export interface ApiResponse<T> {
  data: T
  success: boolean
  message?: string
  error?: string
  timestamp: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// Configuration types
export interface ProcessingConfig {
  auto_processing_enabled: boolean
  batch_size: number
  processing_interval_minutes: number
  email_fetch_limit: number
  url_fetch_timeout_seconds: number
  ai_model_config: {
    model_name: string
    temperature: number
    max_tokens: number
  }
  categories: string[]
  entity_types: string[]
}

// Component props types
export interface TableColumn<T> {
  key: keyof T | string
  title: string
  render?: (value: any, record: T) => React.ReactNode
  sortable?: boolean
  width?: string
  align?: 'left' | 'center' | 'right'
}

export interface ChartData {
  name: string
  value: number
  color?: string
  [key: string]: any
}

export interface FilterOption {
  label: string
  value: string
  count?: number
}

export interface NotificationItem {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
} 