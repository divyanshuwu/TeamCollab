import { supabase } from '../utils/supabase'

const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function apiRequest(path, options = {}) {
  const { data: { session } } = await supabase.auth.getSession()
  const token = session?.access_token || localStorage.getItem('access_token')

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    const message =
      data?.detail || `Request failed with status ${response.status}`

    throw new Error(
      typeof message === 'string' ? message : JSON.stringify(message)
    )
  }

  return data
}