// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from 'vitest'
import { api, clearSession, hasSession, saveSession } from './api'

describe('standalone frontend data service', () => {
  beforeEach(() => localStorage.clear())

  it('supports the built-in demo login and browser session', async () => {
    const session = await api.login({ email: 'demo@qapilot.dev', password: 'demo1234' })
    saveSession(session)
    expect(hasSession()).toBe(true)
    clearSession()
    expect(hasSession()).toBe(false)
  })

  it('supports local signup followed by login', async () => {
    await api.signup({ email: 'qa@example.com', username: 'qa-user', password: 'password1' })
    const session = await api.login({ email: 'qa@example.com', password: 'password1' })
    expect(session.access_token).toBe('demo-session')
  })

  it('seeds dashboard projects with measurable progress', async () => {
    const projects = await api.projects()
    expect(projects).toHaveLength(3)
    expect(projects.every((project) => typeof project.progress === 'number')).toBe(true)
    expect(projects.reduce((sum, project) => sum + project.tests, 0)).toBe(276)
  })

  it('creates and persists a frontend-only project', async () => {
    const created = await api.createProject({ name: 'Catalog API', description: 'Demo project' })
    const projects = await api.projects()
    expect(created.status).toBe('New')
    expect(projects[0].name).toBe('Catalog API')
  })

  it('simulates the complete spec-to-report workflow', async () => {
    const file = new File(['{}'], 'openapi.json', { type: 'application/json' })
    const spec = await api.uploadSpec(101, 'v1', file)
    const endpoints = await api.parseSpec(spec.id)
    const generation = await api.generateAll(spec.id)
    const execution = await api.executeAll(spec.id)
    const report = await api.report(spec.id)
    expect(spec.filename).toBe('openapi.json')
    expect(endpoints).toHaveLength(6)
    expect(generation.total_tests_generated).toBe(74)
    expect(execution.total_tests_executed).toBe(74)
    expect(report.pass_rate_percentage).toBeGreaterThan(90)
    expect(report.test_details.every((test) => test.reason.length > 0)).toBe(true)
    expect(report.test_details.filter((test) => !test.passed).every((test) => test.error)).toBe(true)
  })
})
