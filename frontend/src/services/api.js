// Browser-local adapter used by the frontend preview. The exported service
// boundaries can later delegate to HTTP without changing page components.
const STORAGE_KEYS = { session: 'qa_demo_session', users: 'qa_demo_users', projects: 'qa_demo_projects' }
const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
const delay = (value, milliseconds = 450) => new Promise((resolve) => setTimeout(() => resolve(value), milliseconds))
const readStorage = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback } }
const writeStorage = (key, value) => localStorage.setItem(key, JSON.stringify(value))

async function authRequest(path, body) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    })
  } catch {
    throw new Error('Cannot connect to authentication service. Confirm FastAPI is running on port 8000.')
  }
  if (!response.ok) {
    let payload = null
    try { payload = await response.json() } catch { /* response body is empty */ }
    throw new Error(payload?.detail || payload?.user_message || 'Authentication request failed.')
  }
  return response.status === 204 ? null : response.json()
}

const seedProjects = [
  { id: 101, name: 'Payments API', description: 'Checkout, refunds, and payment method coverage', created_at: '2026-08-21T10:00:00Z', progress: 100, tests: 148, passed: 139, failed: 9, coverage: 96, status: 'Healthy' },
  { id: 102, name: 'Identity Service', description: 'Authentication and account lifecycle APIs', created_at: '2026-08-19T10:00:00Z', progress: 75, tests: 86, passed: 72, failed: 14, coverage: 82, status: 'Review' },
  { id: 103, name: 'Orders Platform', description: 'Order creation, tracking, and fulfilment', created_at: '2026-08-14T10:00:00Z', progress: 50, tests: 42, passed: 39, failed: 3, coverage: 61, status: 'Building' },
]
const demoEndpoints = [
  { id: 1, method: 'GET', path: '/users', summary: 'List all users' },
  { id: 2, method: 'POST', path: '/users', summary: 'Create a user' },
  { id: 3, method: 'GET', path: '/users/{id}', summary: 'Get user details' },
  { id: 4, method: 'PATCH', path: '/users/{id}', summary: 'Update a user' },
  { id: 5, method: 'DELETE', path: '/users/{id}', summary: 'Delete a user' },
  { id: 6, method: 'POST', path: '/auth/token', summary: 'Create access token' },
]

function getProjects() {
  const stored = readStorage(STORAGE_KEYS.projects, null)
  if (stored) return stored
  writeStorage(STORAGE_KEYS.projects, seedProjects)
  return seedProjects
}

export const authService = {
  hasSession: () => Boolean(readStorage(STORAGE_KEYS.session, null)),
  saveSession: (session) => writeStorage(STORAGE_KEYS.session, session),
  clearSession: () => localStorage.removeItem(STORAGE_KEYS.session),
  login: (credentials) => authRequest('/api/v1/auth/login', credentials),
  signup: (details) => authRequest('/api/v1/auth/signup', details),
  refresh: async () => {
    const session = readStorage(STORAGE_KEYS.session, {})
    if (!session.refresh_token) return null
    const access = await authRequest('/api/v1/auth/refresh', { refresh_token: session.refresh_token })
    const refreshed = { ...session, ...access }
    writeStorage(STORAGE_KEYS.session, refreshed)
    return refreshed
  },
  logout: async () => {
    const session = readStorage(STORAGE_KEYS.session, {})
    try { if (session.refresh_token) await authRequest('/api/v1/auth/logout', { refresh_token: session.refresh_token }) }
    finally { localStorage.removeItem(STORAGE_KEYS.session) }
  },
}

export const projectService = {
  list: () => delay(getProjects(), 250),
  getById: async (projectId) => delay(getProjects().find((project) => String(project.id) === String(projectId)) ?? null, 150),
  create: (details) => {
    const project = { id: Date.now(), ...details, created_at: new Date().toISOString(), progress: 0, tests: 0, passed: 0, failed: 0, coverage: 0, status: 'New' }
    writeStorage(STORAGE_KEYS.projects, [project, ...getProjects()])
    return delay(project)
  },
}

export const qaService = {
  uploadSpec: (_projectId, version, file) => delay({ id: Date.now(), filename: file.name, version, uploaded_at: new Date().toISOString() }, 700),
  parseSpec: () => delay(demoEndpoints, 900),
  generateAll: () => delay({ total_tests_generated: 74 }, 1200),
  executeAll: () => delay({ total_tests_executed: 74, total_passed: 69, total_failed: 5 }, 1400),
  getReport: () => delay({
    total_tests_executed: 74, total_passed: 69, total_failed: 5, pass_rate_percentage: 93.2, coverage_percentage: 88, total_execution_time_ms: 2481,
    endpoint_details: demoEndpoints.map((endpoint, index) => ({ endpoint_id: endpoint.id, method: endpoint.method, path: endpoint.path, passed: 10 + (index % 3), failed: index % 3 === 0 ? 1 : 0 })),
    test_details: [
      { id: 1, method: 'GET', path: '/users', category: 'Positive', name: 'Returns the user collection', expected: 200, actual: 200, passed: true, reason: 'Response status and collection schema matched the OpenAPI contract.' },
      { id: 2, method: 'POST', path: '/users', category: 'Validation', name: 'Rejects a missing email address', expected: 422, actual: 422, passed: true, reason: 'The API correctly rejected the invalid payload with a validation response.' },
      { id: 3, method: 'GET', path: '/users/{id}', category: 'Negative', name: 'Unknown user returns not found', expected: 404, actual: 500, passed: false, reason: 'Expected HTTP 404 but received HTTP 500.', error: 'Unhandled lookup error returned by the service instead of a not-found response.' },
      { id: 4, method: 'PATCH', path: '/users/{id}', category: 'Boundary', name: 'Accepts maximum display-name length', expected: 200, actual: 200, passed: true, reason: 'Boundary payload was accepted and the response matched the expected schema.' },
      { id: 5, method: 'DELETE', path: '/users/{id}', category: 'Authorization', name: 'Blocks deletion without a token', expected: 401, actual: 403, passed: false, reason: 'Expected HTTP 401 but received HTTP 403.', error: 'Authorization behavior differs from the documented contract.' },
    ],
  }),
}
