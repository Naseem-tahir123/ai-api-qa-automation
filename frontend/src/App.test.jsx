// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'

function renderRoute(route) {
  return render(<MemoryRouter initialEntries={[route]}><AuthProvider><ToastProvider><App /></ToastProvider></AuthProvider></MemoryRouter>)
}

describe('application routing', () => {
  beforeEach(() => {
    localStorage.clear()
    global.fetch = vi.fn((url) => {
      if (url === '/api/v1/projects/') return Promise.resolve(new Response(JSON.stringify([{ id: 101, name: 'Payments API', description: 'Payment coverage', created_at: '2026-01-01' }]), { status: 200 }))
      if (url === '/api/v1/projects/101') return Promise.resolve(new Response(JSON.stringify({ id: 101, name: 'Payments API', description: 'Payment coverage', created_at: '2026-01-01' }), { status: 200 }))
      if (url === '/api/v1/projects/101/specifications') return Promise.resolve(new Response(JSON.stringify([{ id: 7, project_id: 101, filename: 'openapi.json', version: 'v1', uploaded_at: '2026-01-01' }]), { status: 200 }))
      if (url === '/api/v1/reports/specifications/7') return Promise.resolve(new Response(JSON.stringify({ total_tests_executed: 1, total_passed: 1, total_failed: 0, pass_rate_percentage: 100, coverage_percentage: 100, endpoint_details: [], test_evidence: [{ id: 1, endpoint_path: '/users', method: 'GET', category: 'Positive', description: 'Lists users', expected_status: 200, actual_status: 200, is_passed: true, reason: 'Expected status received', error_message: null }] }), { status: 200 }))
      return Promise.resolve(new Response(JSON.stringify({ detail: 'Not found' }), { status: 404 }))
    })
  })
  afterEach(cleanup)

  it('protects the dashboard and redirects to login', () => {
    renderRoute('/dashboard')
    expect(screen.getByRole('heading', { name: 'Sign in to QA Pilot' })).toBeTruthy()
  })

  it('renders the dashboard for an authenticated session', async () => {
    localStorage.setItem('qa_session', JSON.stringify({ access_token: 'access' }))
    renderRoute('/dashboard')
    expect(await screen.findByRole('heading', { name: 'Good morning, QA team.' })).toBeTruthy()
    expect(screen.getByText('Backend integration active')).toBeTruthy()
  })

  it('supports a direct dynamic project URL', async () => {
    localStorage.setItem('qa_session', JSON.stringify({ access_token: 'access' }))
    renderRoute('/projects/101')
    expect(await screen.findByRole('heading', { name: 'Payments API' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Parse endpoints' })).toBeTruthy()
  })

  it('supports direct project report URLs', async () => {
    localStorage.setItem('qa_session', JSON.stringify({ access_token: 'access' }))
    renderRoute('/projects/101/report')
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Quality snapshot' })).toBeTruthy())
    expect(screen.getByText('Test evidence')).toBeTruthy()
  })

  it('renders a useful not-found page', () => {
    renderRoute('/not-a-real-page')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeTruthy()
  })
})
