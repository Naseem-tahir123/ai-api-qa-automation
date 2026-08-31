import { useState } from 'react'
import { ArrowRight, Sparkles, XCircle } from 'lucide-react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import Brand from '../components/common/Brand'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const { isAuthenticated, login, signup: createAccount } = useAuth()
  const [signup, setSignup] = useState(false)
  const [form, setForm] = useState({ email: '', username: '', password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  if (isAuthenticated) return <Navigate to="/dashboard" replace />
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    try {
      if (signup) await createAccount(form)
      else await login({ email: form.email, password: form.password })
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true })
    } catch (submitError) { setError(submitError.message) }
    finally { setBusy(false) }
  }
  return <main className="auth-page"><section className="auth-story"><Brand light/><div className="story-content"><div className="eyebrow"><Sparkles /> AI-powered quality engineering</div><h1>Ship APIs with<br/><em>quiet confidence.</em></h1><p>Turn any OpenAPI specification into a complete, executable test suite in minutes—not weeks.</p><div className="story-proof"><div className="proof-stack"><span>AI</span><span>QA</span><span>✓</span></div><small>Built for modern QA teams</small></div></div><div className="grid-art" /></section><section className="auth-form-wrap"><form className="auth-card" onSubmit={submit}><Brand mobile/><p className="overline">{signup ? 'GET STARTED' : 'WELCOME BACK'}</p><h2>{signup ? 'Create your workspace' : 'Sign in to QA Pilot'}</h2><p className="muted">{signup ? 'Start testing smarter today.' : 'Continue building reliable APIs.'}</p>{!signup && <div className="demo-login"><strong>Demo access</strong><span>demo@qapilot.dev</span><span>demo1234</span></div>}{error && <div className="error-banner"><XCircle />{error}</div>}<label>Email address<input type="email" required placeholder="you@company.com" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })}/></label>{signup && <label>Username<input required placeholder="Your name" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })}/></label>}<label>Password<input type="password" required minLength="8" placeholder="••••••••" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })}/></label><button className="btn primary full" disabled={busy}>{busy ? <span className="spinner"/> : <>{signup ? 'Create account' : 'Sign in'}<ArrowRight /></>}</button><p className="switch">{signup ? 'Already have an account?' : 'New to QA Pilot?'} <button type="button" onClick={() => { setSignup(!signup); setError('') }}>{signup ? 'Sign in' : 'Create an account'}</button></p></form></section></main>
}
