import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query'

import {
  deleteConversation,
  fetchConversation,
  fetchConversations,
  fetchDashboardStats,
  fetchIndexStatus,
  indexConversation,
  rebuildIndex,
} from '../services/conversations'
import { fetchModelStatus } from '../services/system'

export const queryKeys = {
  stats: ['stats'] as const,
  conversations: ['conversations'] as const,
  conversation: (id: string) => ['conversation', id] as const,
  indexStatus: ['index-status'] as const,
  modelStatus: ['model-status'] as const,
}

export function useInvalidateWorkspace() {
  const queryClient = useQueryClient()

  return () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.stats })
    void queryClient.invalidateQueries({ queryKey: queryKeys.conversations })
    void queryClient.invalidateQueries({ queryKey: queryKeys.indexStatus })
    void queryClient.invalidateQueries({ queryKey: queryKeys.modelStatus })
  }
}

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats,
    queryFn: fetchDashboardStats,
    staleTime: 15_000,
  })
}

export function useConversations(limit = 100) {
  return useQuery({
    queryKey: [...queryKeys.conversations, limit],
    queryFn: () => fetchConversations(limit),
    staleTime: 15_000,
  })
}

export function useConversation(conversationId: string) {
  return useQuery({
    queryKey: queryKeys.conversation(conversationId),
    queryFn: () => fetchConversation(conversationId),
    enabled: Boolean(conversationId),
    staleTime: 30_000,
  })
}

export function useIndexStatus() {
  return useQuery({
    queryKey: queryKeys.indexStatus,
    queryFn: fetchIndexStatus,
    staleTime: 15_000,
  })
}

export function useModelStatus() {
  return useQuery({
    queryKey: queryKeys.modelStatus,
    queryFn: fetchModelStatus,
    staleTime: 15_000,
  })
}

export function useDeleteConversation() {
  const invalidate = useInvalidateWorkspace()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: deleteConversation,
    onSuccess: (result) => {
      queryClient.removeQueries({
        queryKey: queryKeys.conversation(result.conversation_id),
      })
      invalidate()
    },
  })
}

export function useIndexConversation() {
  const invalidate = useInvalidateWorkspace()

  return useMutation({
    mutationFn: ({
      conversationId,
      force = false,
    }: {
      conversationId: string
      force?: boolean
    }) => indexConversation(conversationId, force),
    onSuccess: invalidate,
  })
}

export function useRebuildIndex() {
  const invalidate = useInvalidateWorkspace()

  return useMutation({
    mutationFn: rebuildIndex,
    onSuccess: invalidate,
  })
}
