import { api } from './api'
import type {
  ConversationDetail,
  ConversationListResponse,
  DashboardStats,
  DeleteConversationResponse,
  ImportResponse,
  IndexConversationResponse,
  IndexStatus,
  RebuildIndexResponse,
} from '../types/api'

export async function fetchConversations(
  limit = 100,
  skip = 0,
): Promise<ConversationListResponse> {
  const response = await api.get<ConversationListResponse>('/conversations', {
    params: { limit, skip },
  })

  return response.data
}

export async function fetchConversation(
  conversationId: string,
): Promise<ConversationDetail> {
  const response = await api.get<ConversationDetail>(
    `/conversations/${encodeURIComponent(conversationId)}`,
  )

  return response.data
}

export async function deleteConversation(
  conversationId: string,
): Promise<DeleteConversationResponse> {
  const response = await api.delete<DeleteConversationResponse>(
    `/conversations/${encodeURIComponent(conversationId)}`,
  )

  return response.data
}

export async function importConversation(url: string): Promise<ImportResponse> {
  const response = await api.post<ImportResponse>('/import/url', { url })
  return response.data
}

export async function indexConversation(
  conversationId: string,
  force = false,
): Promise<IndexConversationResponse> {
  const response = await api.post<IndexConversationResponse>(
    `/index/${encodeURIComponent(conversationId)}`,
    null,
    { params: force ? { force: true } : undefined },
  )

  return response.data
}

export async function fetchIndexStatus(): Promise<IndexStatus> {
  const response = await api.get<IndexStatus>('/index/status')
  return response.data
}

export async function rebuildIndex(): Promise<RebuildIndexResponse> {
  const response = await api.post<RebuildIndexResponse>('/index/rebuild')
  return response.data
}

export async function fetchDashboardStats(): Promise<DashboardStats> {
  const response = await api.get<DashboardStats>('/stats')
  return response.data
}
