export interface Message {
  role: string
  content: string
  position: number
}

export interface ConversationListItem {
  conversation_id: string
  title: string
  created_at: string
  message_count: number
}

export interface ConversationListResponse {
  total: number
  items: ConversationListItem[]
}

export interface ConversationDetail {
  conversation_id: string
  title: string
  source_url: string
  created_at: string
  message_count: number
  messages: Message[]
}

export interface DeleteConversationResponse {
  conversation_id: string
  status: 'deleted'
  deleted_messages: number
  deleted_vectors: number | null
}

export interface ImportResponse {
  status: 'success' | 'already_exists'
  conversation_id: string
  title: string
  message_count: number
  messages: Message[]
}

export interface IndexConversationResponse {
  conversation_id: string
  status: 'indexed' | 'already_indexed'
  chunks: number
  embedding_model: string
  chunking_version: string
  indexed_at: string | null
}

export interface IndexResult {
  conversation_id: string
  status: 'indexed' | 'already_indexed' | 'failed'
  chunks: number
  error: string | null
}

export interface IndexAllResponse {
  status: 'completed' | 'partial' | 'failed' | 'nothing_to_do'
  total: number
  indexed: number
  skipped: number
  failed: number
  results: IndexResult[]
}

export interface RebuildIndexResponse extends IndexAllResponse {
  collection: string
}

export interface IndexConversationCounts {
  total: number
  indexed: number
  not_indexed: number
  indexing: number
  failed: number
  stale: number
}

export interface IndexStatus {
  collection: string
  embedding_model: string
  embedding_dimension: number | null
  chunking_version: string
  chunk_size_tokens: number
  chunk_overlap_tokens: number
  chunk_min_tokens: number
  token_counting: string
  conversations: IndexConversationCounts
  chunks_recorded: number
  vectors: number | null
  vector_store_available: boolean
  vector_store_error: string | null
  rebuild_required: boolean
  rebuild_reason: string | null
}

export interface DashboardStats {
  conversations_total: number
  messages_total: number
  indexed_conversations: number
  not_indexed_conversations: number
  indexing_conversations: number
  failed_conversations: number
  stale_conversations: number
  chunks_indexed: number
  vectors: number | null
  vector_store_available: boolean
  vector_store_error: string | null
  recent_imports: ConversationListItem[]
}

export interface SearchRequest {
  query: string
  limit?: number
  conversation_id?: string
}

export interface SearchResultItem {
  conversation_id: string
  conversation_title: string
  role: string
  message_position: number
  chunk_index: number
  text: string
  distance: number
}

export interface SearchResponse {
  query: string
  total: number
  results: SearchResultItem[]
}

export interface ChatTurn {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatRequest {
  message: string
  history?: ChatTurn[]
  top_k?: number
}

export interface ChatSource extends SearchResultItem {
  index: number
}

export interface ChatResponse {
  status: 'answered' | 'no_sources'
  answer: string
  model: string | null
  sources: ChatSource[]
}

export interface OllamaModelInfo {
  name: string
  size: number | null
  modified_at: string | null
}

export interface OllamaStatus {
  base_url: string
  available: boolean
  error: string | null
}

export interface ModelAvailability {
  name: string
  available: boolean
}

export interface VectorStoreStatus {
  collection: string
  available: boolean
  vectors: number | null
  embedding_dimension: number | null
  error: string | null
}

export interface DatabaseStatus {
  engine: 'sqlite'
  conversations: number
  messages: number
}

export interface IndexSummary {
  total: number
  indexed: number
  not_indexed: number
  indexing: number
  failed: number
  stale: number
  chunks_recorded: number
  rebuild_required: boolean
  rebuild_reason: string | null
}

export interface ModelStatus {
  ollama: OllamaStatus
  chat_model: ModelAvailability
  embedding_model: ModelAvailability
  installed_models: OllamaModelInfo[]
  vector_store: VectorStoreStatus
  database: DatabaseStatus
  index: IndexSummary
}
