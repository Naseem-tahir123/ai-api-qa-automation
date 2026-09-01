const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const SESSION_KEY = 'qa_session'
const PROJECT_SPECS_KEY = 'qa_project_specs'

function readJson(key, fallback = null) {
  try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback }
}

function writeJson(key, value) { localStorage.setItem(key, JSON.stringify(value)) }
function getSession() { return readJson(SESSION_KEY, {}) }

export class ApiError extends Error {
  constructor(message, status, details) { super(message); this.name = 'ApiError'; this.status = status; this.details = details }
}

function errorMessage(payload, fallback) {
  if (Array.isArray(payload?.detail)) return payload.detail.map((item) => item.msg).join(', ')
  return payload?.detail || payload?.user_message || payload?.message || fallback
}

async function refreshAccessToken(refreshToken) {
  const response = await fetch(`${API_URL}/api/v1/auth/refresh`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh_token: refreshToken }),
  })
  if (!response.ok) return false
  writeJson(SESSION_KEY, { ...getSession(), ...(await response.json()) })
  return true
}

async function request(path, options = {}, canRetry = true) {
  const session = getSession()
  const headers = new Headers(options.headers || {})
  if (!(options.body instanceof FormData) && options.body !== undefined) headers.set('Content-Type', 'application/json')
  if (session.access_token) headers.set('Authorization', `Bearer ${session.access_token}`)
  let response
  try { response = await fetch(`${API_URL}${path}`, { ...options, headers }) }
  catch (error) { throw new ApiError('Cannot connect to the API. Confirm the backend is running on port 8000.', 0, error) }
  if (response.status === 401 && canRetry && session.refresh_token) {
    if (await refreshAccessToken(session.refresh_token)) return request(path, options, false)
    localStorage.removeItem(SESSION_KEY)
  }
  if (!response.ok) {
    let payload = null
    try { payload = await response.json() } catch { /* response has no JSON body */ }
    throw new ApiError(errorMessage(payload, `Request failed with HTTP ${response.status}`), response.status, payload)
  }
  if (response.status === 204) return null
  return response.json()
}

function rememberSpecification(projectId, specification) {
  const specs = readJson(PROJECT_SPECS_KEY, {})
  specs[String(projectId)] = specification
  writeJson(PROJECT_SPECS_KEY, specs)
}

function getRememberedSpecification(projectId) {
  return readJson(PROJECT_SPECS_KEY, {})[String(projectId)] || null
}

function normalizeProject(project) {
  return { progress: 0, tests: 0, passed: 0, failed: 0, coverage: 0, status: 'Ready', ...project }
}

function normalizeReport(report) {
  return {
    ...report,
    test_details: (report.test_evidence || []).map((test) => ({
      id: test.id, method: test.method, path: test.endpoint_path, category: test.category,
      name: test.description, expected: test.expected_status, actual: test.actual_status,
      passed: test.is_passed, reason: test.reason, error: test.error_message,
    })),
  }
}

export const authService = {
  hasSession: () => Boolean(getSession().access_token),
  saveSession: (session) => writeJson(SESSION_KEY, session),
  clearSession: () => localStorage.removeItem(SESSION_KEY),
  login: (credentials) => request('/api/v1/auth/login', { method: 'POST', body: JSON.stringify(credentials) }),
  signup: (details) => request('/api/v1/auth/signup', { method: 'POST', body: JSON.stringify(details) }),
  logout: async () => {
    const { refresh_token } = getSession()
    try { if (refresh_token) await request('/api/v1/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token }) }, false) }
    finally { localStorage.removeItem(SESSION_KEY) }
  },
}

export const projectService = {
  list: async () => (await request('/api/v1/projects/')).map(normalizeProject),
  getById: async (projectId) => {
    try { return normalizeProject(await request(`/api/v1/projects/${projectId}`)) }
    catch (error) { if (error.status === 404) return null; throw error }
  },
  create: async (details) => normalizeProject(await request('/api/v1/projects/', { method: 'POST', body: JSON.stringify(details) })),
  listSpecifications: (projectId) => request(`/api/v1/projects/${projectId}/specifications`),
  getSpecification: getRememberedSpecification,
}

export const qaService = {
  uploadSpec: async (projectId, version, file) => {
    const form = new FormData(); form.append('file', file)
    const spec = await request(`/api/v1/projects/${projectId}/specifications?version=${encodeURIComponent(version)}`, { method: 'POST', body: form })
    rememberSpecification(projectId, spec)
    return spec
  },
  parseSpec: (specId) => request(`/api/v1/specifications/${specId}/parse`, { method: 'POST' }),
  generateAll: (specId) => request(`/api/v1/test-cases/generate-all/${specId}`, { method: 'POST' }),
  getGenerationStatus: (taskId) => request(`/api/v1/test-cases/tasks/${taskId}`),
  executeAll: (specId, execution) => request(`/api/v1/execution/run-all/${specId}`, { method: 'POST', body: JSON.stringify(execution) }),
  getReport: async (specId) => normalizeReport(await request(`/api/v1/reports/specifications/${specId}`)),
}
