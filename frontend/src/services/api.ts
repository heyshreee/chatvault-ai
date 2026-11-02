import axios from 'axios'
import type { AxiosError } from 'axios'

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ??
  'http://127.0.0.1:8000/api/v1'

export class ApiError extends Error {
  status?: number
  detail?: unknown

  constructor(message: string, status?: number, detail?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

function detailMessage(data: unknown): string {
  if (typeof data === 'string' && data.trim()) {
    return data
  }

  if (!data || typeof data !== 'object') {
    return ''
  }

  const detail = (data as { detail?: unknown }).detail

  if (typeof detail === 'string') {
    return detail
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const message = (item as { msg?: unknown }).msg
          return typeof message === 'string' ? message : ''
        }

        return ''
      })
      .filter(Boolean)
      .join(' ')
  }

  return ''
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (!error.response) {
      return Promise.reject(
        new ApiError(
          `Cannot reach the ChatVault API at ${API_BASE_URL}. Is the backend running?`,
        ),
      )
    }

    const message =
      detailMessage(error.response.data) ||
      `The API returned HTTP ${error.response.status}.`

    return Promise.reject(
      new ApiError(message, error.response.status, error.response.data),
    )
  },
)

export function getErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.message
  }

  if (error instanceof Error && error.message) {
    return error.message
  }

  if (typeof error === 'string' && error) {
    return error
  }

  return 'Something went wrong. Please try again.'
}
