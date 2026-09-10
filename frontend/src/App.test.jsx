// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import App from './App'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'

function renderRoute(route) {
  return render(<MemoryRouter initialEntries={[route]}><AuthProvider><ToastProvider><App /></ToastProvider></AuthProvider></MemoryRouter>)
}

describe('application routing', () => {
  beforeEach(() => localStorage.clear())
  afterEach(cleanup)

  it('protects the dashboard and redirects to login', () => {
    renderRoute('/dashboard')
    expect(screen.getByRole('heading', { name: 'Sign in to QA Pilot' })).toBeTruthy()
  })

  it('renders the dashboard for an authenticated session', async () => {
    localStorage.setItem('qa_demo_session', JSON.stringify({ access_token: 'demo-session' }))
    renderRoute('/dashboard')
    expect(await screen.findByRole('heading', { name: 'Good morning, QA team.' })).toBeTruthy()
    expect(screen.getByText('Automation progress')).toBeTruthy()
  })

  it('supports a direct dynamic project URL', async () => {
    localStorage.setItem('qa_demo_session', JSON.stringify({ access_token: 'demo-session' }))
    renderRoute('/projects/101')
    expect(await screen.findByRole('heading', { name: 'Payments API' })).toBeTruthy()
    expect(screen.getByRole('heading', { name: 'Upload spec' })).toBeTruthy()
  })

  it('supports direct project report URLs', async () => {
    localStorage.setItem('qa_demo_session', JSON.stringify({ access_token: 'demo-session' }))
    renderRoute('/projects/101/report')
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Quality snapshot' })).toBeTruthy())
    expect(screen.getByText('Test evidence')).toBeTruthy()
  })

  it('renders a useful not-found page', () => {
    renderRoute('/not-a-real-page')
    expect(screen.getByRole('heading', { name: 'Page not found' })).toBeTruthy()
  })
})
