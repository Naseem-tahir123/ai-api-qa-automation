// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authService, projectService, qaService } from './api'

const response = (body, status = 200) => Promise.resolve(new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))

describe('FastAPI frontend services', () => {
  beforeEach(() => { localStorage.clear(); global.fetch = vi.fn() })

  it('authenticates and stores the backend JWT session', async () => {
    fetch.mockReturnValueOnce(response({ access_token: 'access', refresh_token: 'refresh', token_type: 'bearer' }))
    const session = await authService.login({ email: 'qa@example.com', password: 'password1' })
    authService.saveSession(session)
    expect(authService.hasSession()).toBe(true)
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/auth/login')
  })

  it('sends authenticated project requests', async () => {
    authService.saveSession({ access_token: 'access', refresh_token: 'refresh' })
    fetch.mockReturnValueOnce(response([{ id: 1, name: 'Payments', created_at: '2026-01-01' }]))
    const projects = await projectService.list()
    expect(projects[0].status).toBe('Ready')
    expect(fetch.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer access')
  })

  it('uploads specification files as multipart form data', async () => {
    fetch.mockReturnValueOnce(response({ id: 7, project_id: 1, filename: 'openapi.json', version: 'v1' }, 201))
    const spec = await qaService.uploadSpec(1, 'v1', new File(['{}'], 'openapi.json'))
    expect(spec.id).toBe(7)
    expect(fetch.mock.calls[0][0]).toContain('/api/v1/projects/1/specifications?version=v1')
    expect(fetch.mock.calls[0][1].body).toBeInstanceOf(FormData)
  })

  it('uses the background generation task endpoints', async () => {
    fetch.mockReturnValueOnce(response({ task_id: 'job-1', status: 'queued' }, 202)).mockReturnValueOnce(response({ task_id: 'job-1', status: 'completed', result: { total_tests_generated: 12 } }))
    expect((await qaService.generateAll(7)).task_id).toBe('job-1')
    expect((await qaService.getGenerationStatus('job-1')).status).toBe('completed')
  })

  it('normalizes backend test evidence for the report UI', async () => {
    fetch.mockReturnValueOnce(response({ total_tests_executed: 1, total_passed: 1, total_failed: 0, pass_rate_percentage: 100, coverage_percentage: 100, endpoint_details: [], test_evidence: [{ id: 3, endpoint_path: '/users', method: 'GET', category: 'Positive', description: 'Lists users', expected_status: 200, actual_status: 200, is_passed: true, reason: 'Expected status received', error_message: null }] }))
    const report = await qaService.getReport(7)
    expect(report.test_details[0]).toMatchObject({ path: '/users', name: 'Lists users', passed: true })
  })
})
