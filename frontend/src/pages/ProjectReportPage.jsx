import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import BackButton from '../components/common/BackButton'
import Report from '../components/reports/Report'
import { projectService, qaService } from '../services/api'

export default function ProjectReportPage() {
  const { projectId } = useParams()
  const [data, setData] = useState({ project: null, report: null })
  useEffect(() => { Promise.all([projectService.getById(projectId), qaService.getReport(projectId)]).then(([project, report]) => setData({ project, report })) }, [projectId])
  return <main className="page"><BackButton to={`/projects/${projectId}`} label="Project workspace"/><div className="page-heading"><div><p className="overline">PROJECT REPORT</p><h1>{data.project?.name || 'Quality report'}</h1><p>Detailed results and actionable diagnostics for this project.</p></div></div><section className="panel report-page">{data.report ? <Report report={data.report}/> : <p className="report-loading"><span className="spinner dark"/> Loading report…</p>}</section></main>
}
