// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authService, projectService, qaService } from './api'

describe('standalone frontend services', () => {
  beforeEach(() => { localStorage.clear(); global.fetch = vi.fn() })

  it('uses backend login and stores the JWT session', async () => {
    fetch.mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'access', refresh_token: 'refresh', token_type: 'bearer' }), { status: 200 }))
    const session = await authService.login({ email: 'qa@example.com', password: 'password1' })
    authService.saveSession(session)
    expect(authService.hasSession()).toBe(true)
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/auth/login')
    authService.clearSession()
    expect(authService.hasSession()).toBe(false)
  })

  it('uses backend signup and refresh endpoints', async () => {
    fetch.mockResolvedValueOnce(new Response(JSON.stringify({ id: 1, email: 'qa@example.com', username: 'qa-user' }), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ access_token: 'new-access', token_type: 'bearer' }), { status: 200 }))
    await authService.signup({ email: 'qa@example.com', username: 'qa-user', password: 'password1' })
    authService.saveSession({ access_token: 'old-access', refresh_token: 'refresh' })
    expect((await authService.refresh()).access_token).toBe('new-access')
    expect(fetch.mock.calls[0][0]).toBe('/api/v1/auth/signup')
    expect(fetch.mock.calls[1][0]).toBe('/api/v1/auth/refresh')
  })

  it('seeds dashboard projects and supports direct project lookup', async () => {
    const projects = await projectService.list()
    expect(projects).toHaveLength(3)
    expect(projects.every((project) => typeof project.progress === 'number')).toBe(true)
    expect(projects.reduce((sum, project) => sum + project.tests, 0)).toBe(276)
    expect((await projectService.getById(101)).name).toBe('Payments API')
  })

  it('creates and persists a frontend-only project', async () => {
    const created = await projectService.create({ name: 'Catalog API', description: 'Demo project' })
    const projects = await projectService.list()
    expect(created.status).toBe('New')
    expect(projects[0].name).toBe('Catalog API')
  })

  it('simulates the complete spec-to-report workflow', async () => {
    const file = new File(['{}'], 'openapi.json', { type: 'application/json' })
    const spec = await qaService.uploadSpec(101, 'v1', file)
    const endpoints = await qaService.parseSpec(spec.id)
    const generation = await qaService.generateAll(spec.id)
    const execution = await qaService.executeAll(spec.id)
    const report = await qaService.getReport(spec.id)
    expect(spec.filename).toBe('openapi.json')
    expect(endpoints).toHaveLength(6)
    expect(generation.total_tests_generated).toBe(74)
    expect(execution.total_tests_executed).toBe(74)
    expect(report.pass_rate_percentage).toBeGreaterThan(90)
    expect(report.test_details.every((test) => test.reason.length > 0)).toBe(true)
    expect(report.test_details.filter((test) => !test.passed).every((test) => test.error)).toBe(true)
  })
})
