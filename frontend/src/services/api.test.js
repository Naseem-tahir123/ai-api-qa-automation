// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { authService, projectService, qaService } from './api'

const response = (body, ok = true, status = 200) => ({ ok, status, json: vi.fn().mockResolvedValue(body) })

describe('backend API adapter', () => {
  beforeEach(() => { localStorage.clear(); global.fetch = vi.fn() })

  it('stores a token returned by the backend login endpoint', async () => {
    fetch.mockResolvedValueOnce(response({ access_token: 'jwt', refresh_token: 'refresh', token_type: 'bearer' }))
    const value = await authService.login({ email: 'qa@example.com', password: 'password1' })
    authService.saveSession(value)
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/api/v1/auth/login'), expect.objectContaining({ method: 'POST' }))
    expect(authService.hasSession()).toBe(true)
  })

  it('sends the bearer token when loading projects', async () => {
    authService.saveSession({ access_token: 'jwt' }); fetch.mockResolvedValueOnce(response([{ id: 1, name: 'Orders' }]))
    await projectService.list()
    expect(fetch.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer jwt')
  })

  it('calls the new QA-IR and coverage endpoints', async () => {
    authService.saveSession({ access_token: 'jwt' }); fetch.mockResolvedValueOnce(response({ fingerprint: 'abc' })).mockResolvedValueOnce(response({ selected_intents: [] }))
    await qaService.buildIR(7); await qaService.createCoveragePlan(7)
    expect(fetch.mock.calls[0][0]).toContain('/api/v1/qa/specifications/7/ir')
    expect(fetch.mock.calls[1][0]).toContain('/api/v1/qa/specifications/7/coverage-plan')
  })

  it('imports a hosted specification URL with its selected source kind', async () => {
    authService.saveSession({ access_token: 'jwt' }); fetch.mockResolvedValueOnce(response({ id: 9, source_type: 'openapi_url' }))
    await qaService.importSpecUrl(3, { url: 'https://example.com/openapi.json', version: 'v2', source_kind: 'openapi' })
    expect(fetch.mock.calls[0][0]).toContain('/api/v1/projects/3/specifications/import-url')
    expect(fetch.mock.calls[0][1].body).toContain('"source_kind":"openapi"')
  })

  it('refreshes an expired access token and retries the original request once', async () => {
    authService.saveSession({ access_token: 'expired', refresh_token: 'refresh-token' })
    fetch.mockResolvedValueOnce(response({ detail: 'Access token expired' }, false, 401))
      .mockResolvedValueOnce(response({ access_token: 'renewed', token_type: 'bearer' }))
      .mockResolvedValueOnce(response([{ id: 1, name: 'Orders' }]))
    await projectService.list()
    expect(fetch.mock.calls).toHaveLength(3)
    expect(fetch.mock.calls[1][0]).toContain('/api/v1/auth/refresh')
    expect(fetch.mock.calls[2][1].headers.get('Authorization')).toBe('Bearer renewed')
    expect(JSON.parse(localStorage.getItem('qa_session')).access_token).toBe('renewed')
  })
})
