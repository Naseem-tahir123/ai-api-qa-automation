import { useEffect, useState } from 'react'
import BackButton from '../components/common/BackButton'
import Report from '../components/reports/Report'
import { projectService, qaService } from '../services/api'

export default function ReportsPage() {
  const [report, setReport] = useState(null)
  useEffect(() => {
    projectService.list().then(async (projects) => {
      for (const project of projects) {
        const specifications = await projectService.listSpecifications(project.id)
        if (specifications[0]) { setReport(await qaService.getReport(specifications[0].id)); return }
      }
      setReport(false)
    }).catch(() => setReport(false))
  }, [])
  return <main className="page"><BackButton to="/dashboard" label="Dashboard"/><div className="page-heading"><div><p className="overline">QUALITY INTELLIGENCE</p><h1>Reports</h1><p>Review pass/fail evidence and actionable diagnostics.</p></div></div><section className="panel report-page">{report === null ? <p className="report-loading"><span className="spinner dark"/> Loading reports…</p> : report ? <Report report={report}/> : <div className="empty-state"><h3>No reports available</h3><p>Execute a project test suite to generate your first report.</p></div>}</section></main>
}
