const API_URL = import.meta.env.VITE_API_URL || ''

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status }
}

function tokens() {
  try { return JSON.parse(localStorage.getItem('qa_tokens')) || {} } catch { return {} }
}

export function hasSession() { return Boolean(tokens().access_token) }
export function saveSession(value) { localStorage.setItem('qa_tokens', JSON.stringify(value)) }
export function clearSession() { localStorage.removeItem('qa_tokens') }

async function request(path, options = {}, retry = true) {
  const session = tokens()
  const headers = new Headers(options.headers || {})
  if (!(options.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (session.access_token) headers.set('Authorization', `Bearer ${session.access_token}`)
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })

  if (response.status === 401 && retry && session.refresh_token) {
    const refreshed = await fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    })
    if (refreshed.ok) {
      saveSession({ ...session, ...(await refreshed.json()) })
      return request(path, options, false)
    }
    clearSession()
  }

  if (!response.ok) {
    let data = {}
    try { data = await response.json() } catch { /* empty response */ }
    const message = Array.isArray(data.detail)
      ? data.detail.map((item) => item.msg).join(', ')
      : data.detail || `Request failed (${response.status})`
    throw new ApiError(message, response.status)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  health: () => request('/health'),
  login: (body) => request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(body) }),
  signup: (body) => request('/api/v1/auth/signup', { method: 'POST', body: JSON.stringify(body) }),
  projects: () => request('/api/v1/projects/'),
  project: (id) => request(`/api/v1/projects/${id}`),
  createProject: (body) => request('/api/v1/projects/', { method: 'POST', body: JSON.stringify(body) }),
  uploadSpec: (projectId, version, file) => {
    const body = new FormData(); body.append('file', file)
    return request(`/api/v1/projects/${projectId}/specifications?version=${encodeURIComponent(version)}`, { method: 'POST', body })
  },
  parseSpec: (id) => request(`/api/v1/specifications/${id}/parse`, { method: 'POST' }),
  generateAll: (id) => request(`/api/v1/test-cases/generate-all/${id}`, { method: 'POST' }),
  executeAll: (id, body) => request(`/api/v1/execution/run-all/${id}`, { method: 'POST', body: JSON.stringify(body) }),
  report: (id) => request(`/api/v1/reports/specifications/${id}`),
}
