import { api } from './api'
import type {
  ChatRequest,
  ChatResponse,
  SearchRequest,
  SearchResponse,
} from '../types/api'

export async function askQuestion(payload: ChatRequest): Promise<ChatResponse> {
  const response = await api.post<ChatResponse>('/chat', payload, {
    timeout: 300_000,
  })

  return response.data
}

export async function semanticSearch(
  payload: SearchRequest,
): Promise<SearchResponse> {
  const response = await api.post<SearchResponse>('/search', payload)
  return response.data
}
