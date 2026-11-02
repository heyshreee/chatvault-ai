import { api } from './api'
import type { ModelStatus } from '../types/api'

export async function fetchModelStatus(): Promise<ModelStatus> {
  const response = await api.get<ModelStatus>('/models/status')
  return response.data
}
