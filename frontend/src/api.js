const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function apiRequest(path, options = {}, token) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  })

  if (!response.ok) {
    const raw = await response.text()
    let message = raw || `Request failed: ${response.status}`
    try {
      const parsed = JSON.parse(raw)
      if (typeof parsed?.detail === 'string') {
        message = parsed.detail
      } else if (Array.isArray(parsed?.detail)) {
        message = parsed.detail.map((item) => item.msg || item.type || 'Validation error').join(', ')
      }
    } catch {
      // Keep original raw text as message fallback.
    }
    throw new Error(message)
  }

  return response.status === 204 ? null : response.json()
}
