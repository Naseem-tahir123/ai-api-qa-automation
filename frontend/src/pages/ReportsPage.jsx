import { useEffect, useState } from 'react'
import BackButton from '../components/common/BackButton'
import Report from '../components/reports/Report'
import { qaService } from '../services/api'

export default function ReportsPage() {
  const [report, setReport] = useState(null)
  useEffect(() => { qaService.getReport().then(setReport) }, [])
  return <main className="page"><BackButton to="/dashboard" label="Dashboard"/><div className="page-heading"><div><p className="overline">QUALITY INTELLIGENCE</p><h1>Reports</h1><p>Review pass/fail evidence and actionable diagnostics.</p></div></div><section className="panel report-page">{report ? <Report report={report}/> : <p className="report-loading"><span className="spinner dark"/> Loading demo report…</p>}</section></main>
}
