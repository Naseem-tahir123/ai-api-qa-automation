import { BarChart3 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function ReportsPage() {
  const navigate = useNavigate()
  return <main className="page"><div className="page-heading"><div><p className="overline">QUALITY INTELLIGENCE</p><h1>Evidence is specification-scoped</h1><p>Open a project workspace, execute a pipeline, and review persisted evidence in its final step.</p></div></div><section className="panel empty-state"><span className="empty-icon"><BarChart3/></span><h3>Select a project to view its QA dashboard</h3><p>The dashboard contains executed endpoint coverage, pass/fail totals, cleanup failures, failure classes, and release risk.</p><button className="btn primary" onClick={() => navigate('/projects')}>Open projects</button></section></main>
}
