import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return <main className="auth-form-wrap"><div className="empty-state"><p className="overline">404</p><h1>Page not found</h1><p>The page you requested does not exist.</p><Link className="btn primary" to="/dashboard">Return to dashboard</Link></div></main>
}
