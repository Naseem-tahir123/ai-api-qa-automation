const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const SESSION_KEY = 'qa_session'
let refreshInFlight = null

const session = () => {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)) } catch { return null }
}

async function refreshAccessToken() {
  const current = session()
  if (!current?.refresh_token) return null
  if (!refreshInFlight) {
    refreshInFlight = fetch(`${API_URL}/api/v1/auth/refresh`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: current.refresh_token }),
    }).then(async (response) => {
      const payload = await response.json().catch(() => null)
      if (!response.ok || !payload?.access_token) { localStorage.removeItem(SESSION_KEY); return null }
      const updated = { ...current, access_token: payload.access_token }
      localStorage.setItem(SESSION_KEY, JSON.stringify(updated))
      return updated.access_token
    }).catch(() => null).finally(() => { refreshInFlight = null })
  }
  return refreshInFlight
}

async function request(path, options = {}, retried = false) {
  const token = session()?.access_token
  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const response = await fetch(`${API_URL}${path}`, { ...options, headers })
  const payload = response.status === 204 ? null : await response.json().catch(() => null)
  // An access token is intentionally short-lived. Refresh once and replay the
  // original request; never retry a second time to avoid infinite loops.
  if (response.status === 401 && !retried && path !== '/api/v1/auth/refresh') {
    const refreshedToken = await refreshAccessToken()
    if (refreshedToken) return request(path, options, true)
  }
  if (!response.ok) throw new Error(payload?.detail || payload?.message || `Request failed (${response.status})`)
  return payload
}

export const authService = {
  hasSession: () => Boolean(session()?.access_token),
  saveSession: (value) => localStorage.setItem(SESSION_KEY, JSON.stringify(value)),
  clearSession: () => localStorage.removeItem(SESSION_KEY),
  login: (credentials) => request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  signup: (details) => request('/api/v1/auth/signup', { method: 'POST', body: JSON.stringify(details) }),
}

export const projectService = {
  list: () => request('/api/v1/projects/'),
  getById: (id) => request(`/api/v1/projects/${id}`),
  create: (details) => request('/api/v1/projects/', { method: 'POST', body: JSON.stringify(details) }),
  listSpecifications: (projectId) => request(`/api/v1/projects/${projectId}/specifications`),
  listEnvironments: (projectId) => request(`/api/v1/projects/${projectId}/environments`),
}

export const qaService = {
  uploadSpec: (projectId, version, file) => {
    const body = new FormData(); body.append('file', file)
    return request(`/api/v1/projects/${projectId}/specifications?version=${encodeURIComponent(version)}`, { method: 'POST', body })
  },
  importSpecUrl: (projectId, payload) => request(`/api/v1/projects/${projectId}/specifications/import-url`, { method: 'POST', body: JSON.stringify(payload) }),
  parseSpec: (specId) => request(`/api/v1/specifications/${specId}/parse`, { method: 'POST' }),
  listEndpoints: (specId) => request(`/api/v1/specifications/${specId}/endpoints`),
  buildIR: (specId) => request(`/api/v1/qa/specifications/${specId}/ir`, { method: 'POST' }),
  getIR: (specId) => request(`/api/v1/qa/specifications/${specId}/ir`),
  createCoveragePlan: (specId) => request(`/api/v1/qa/specifications/${specId}/coverage-plan`, { method: 'POST' }),
  getCoveragePlan: (specId) => request(`/api/v1/qa/specifications/${specId}/coverage-plan`),
  generate: (specId) => request(`/api/v1/pipelines/generate/${specId}`, { method: 'POST' }),
  listPipelines: (specId) => request(`/api/v1/pipelines/specifications/${specId}`),
  getJob: (taskId) => request(`/api/v1/pipelines/tasks/${taskId}`),
  getDashboard: (specId) => request(`/api/v1/qa/specifications/${specId}/dashboard`),
  getRegressionImpact: (specId) => request(`/api/v1/qa/specifications/${specId}/regression-impact`),
  createEnvironment: (projectId, payload) => request(`/api/v1/projects/${projectId}/environments`, { method: 'POST', body: JSON.stringify(payload) }),
  runPipeline: (pipelineId, payload) => request(`/api/v1/pipelines/run/${pipelineId}`, { method: 'POST', body: JSON.stringify(payload) }),
  runAllPipelines: (specId, payload) => request(`/api/v1/pipelines/run-all/specifications/${specId}`, { method: 'POST', body: JSON.stringify(payload) }),
  listAuthProfiles: (environmentId) => request(`/api/v1/auth-profiles/environment/${environmentId}`),
  createAuthProfile: (payload) => request('/api/v1/auth-profiles/', { method: 'POST', body: JSON.stringify(payload) }),
  listIdentities: (profileId) => request(`/api/v1/auth-profiles/${profileId}/identities`),
  createIdentity: (profileId, payload) => request(`/api/v1/auth-profiles/${profileId}/identities`, { method: 'POST', body: JSON.stringify(payload) }),
}

export { API_URL }
