// Standalone browser demo service. Replace this module with HTTP calls when the
// backend integration phase begins; the UI-facing method signatures can remain.
const KEYS = { session: 'qa_demo_session', users: 'qa_demo_users', projects: 'qa_demo_projects' }
const pause = (value, ms = 450) => new Promise((resolve) => setTimeout(() => resolve(value), ms))
const read = (key, fallback) => { try { return JSON.parse(localStorage.getItem(key)) ?? fallback } catch { return fallback } }
const write = (key, value) => localStorage.setItem(key, JSON.stringify(value))
const seedProjects = [
  { id: 101, name: 'Payments API', description: 'Checkout, refunds, and payment method coverage', created_at: '2026-08-21T10:00:00Z', progress: 100, tests: 148, passed: 139, failed: 9, coverage: 96, status: 'Healthy' },
  { id: 102, name: 'Identity Service', description: 'Authentication and account lifecycle APIs', created_at: '2026-08-19T10:00:00Z', progress: 75, tests: 86, passed: 72, failed: 14, coverage: 82, status: 'Review' },
  { id: 103, name: 'Orders Platform', description: 'Order creation, tracking, and fulfilment', created_at: '2026-08-14T10:00:00Z', progress: 50, tests: 42, passed: 39, failed: 3, coverage: 61, status: 'Building' },
]
function projects() { const stored = read(KEYS.projects, null); if (stored) return stored; write(KEYS.projects, seedProjects); return seedProjects }
export function hasSession() { return Boolean(read(KEYS.session, null)) }
export function saveSession(value) { write(KEYS.session, value) }
export function clearSession() { localStorage.removeItem(KEYS.session) }
const demoEndpoints = [
  { id: 1, method: 'GET', path: '/users', summary: 'List all users' }, { id: 2, method: 'POST', path: '/users', summary: 'Create a user' },
  { id: 3, method: 'GET', path: '/users/{id}', summary: 'Get user details' }, { id: 4, method: 'PATCH', path: '/users/{id}', summary: 'Update a user' },
  { id: 5, method: 'DELETE', path: '/users/{id}', summary: 'Delete a user' }, { id: 6, method: 'POST', path: '/auth/token', summary: 'Create access token' },
]
export const api = {
  login: async ({ email, password }) => { const valid = read(KEYS.users, []).some((u) => u.email === email && u.password === password); if (!valid && !(email === 'demo@qapilot.dev' && password === 'demo1234')) throw new Error('Incorrect credentials. Use demo@qapilot.dev / demo1234'); return pause({ access_token: 'demo-session', user: { email } }) },
  signup: async (body) => { const users = read(KEYS.users, []); if (users.some((u) => u.email === body.email)) throw new Error('An account with this email already exists'); write(KEYS.users, [...users, body]); return pause({ id: Date.now(), ...body }) },
  projects: () => pause(projects(), 250),
  createProject: (body) => { const all = projects(); const project = { id: Date.now(), ...body, created_at: new Date().toISOString(), progress: 0, tests: 0, passed: 0, failed: 0, coverage: 0, status: 'New' }; write(KEYS.projects, [project, ...all]); return pause(project) },
  uploadSpec: (_projectId, version, file) => pause({ id: Date.now(), filename: file.name, version, uploaded_at: new Date().toISOString() }, 700),
  parseSpec: () => pause(demoEndpoints, 900), generateAll: () => pause({ total_tests_generated: 74 }, 1200),
  executeAll: () => pause({ tport: () => pause({ total_tests_executed: 74, total_passed: 69, total_failed: 5, pass_rate_percentage: 93.2, coverage_percentage: 88, total_execution_time_ms: 2481, endpoint_details: demoEndpoints.map((ep, i) => ({ endpoint_id: ep.id, method: ep.method, path: ep.path, passed: 10 + (i % 3), failed: i % 3 === 0 ? 1 : 0 })), test_details: [
    { id: 1, method: 'GET', path: '/users', category: 'Positive', name: 'Returns the user collection', expected: 200, actual: 200, passed: true, reason: 'Response status and collection schema matched the OpenAPI contract.' },
    { id: 2, method: 'POST', path: '/users', category: 'Validation', name: 'Rejects a missing email address', expected: 422, actual: 422, passed: true, reason: 'The API correctly rejected the invalid payload with a validation response.' },
    { id: 3, method: 'GET', path: '/users/{id}', category: 'Negative', name: 'Unknown user returns not found', expected: 404, actual: 500, passed: false, reason: 'Expected HTTP 404 but received HTTP 500.', error: 'Unhandled lookup error returned by the service instead of a not-found response.' },
    { id: 4, method: 'PATCH', path: '/users/{id}', category: 'Boundary', name: 'Accepts maximum display-name length', expected: 200, actual: 200, passed: true, reason: 'Boundary payload was accepted and the response matched the expected schema.' },
    { id: 5, method: 'DELETE', path: '/users/{id}', category: 'Authorization', name: 'Blocks deletion without a token', expected: 401, actual: 403, passed: false, reason: 'Expected HTTP 401 but received HTTP 403.', error: 'Authorization behavior differs from the documented contract.' },
  ] }),
}
