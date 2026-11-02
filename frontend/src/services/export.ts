import { api } from './api'

export type ExportFormat = 'pdf' | 'docx'

function filenameFromDisposition(
  disposition: string | undefined,
  fallback: string,
): string {
  if (!disposition) {
    return fallback
  }

  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition)

  if (utf8?.[1]) {
    try {
      return decodeURIComponent(utf8[1])
    } catch {
      return fallback
    }
  }

  const quoted = /filename="([^"]+)"/i.exec(disposition)

  if (quoted?.[1]) {
    return quoted[1]
  }

  const plain = /filename=([^;]+)/i.exec(disposition)

  if (plain?.[1]) {
    return plain[1].trim()
  }

  return fallback
}

export async function downloadConversationExport(
  conversationId: string,
  format: ExportFormat,
): Promise<string> {
  const response = await api.get<Blob>(
    `/conversations/${encodeURIComponent(conversationId)}/export/${format}`,
    {
      responseType: 'blob',
      timeout: 120_000,
    },
  )

  const fallback = `chatvault-${conversationId}.${format}`
  const filename = filenameFromDisposition(
    response.headers['content-disposition'] as string | undefined,
    fallback,
  )
  const blobUrl = URL.createObjectURL(response.data)
  const link = document.createElement('a')

  link.href = blobUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()

  window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1_000)

  return filename
}
