import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import BackButton from '../components/common/BackButton'
import Report from '../components/reports/Report'
import { projectService, qaService } from '../services/api'

export default function ProjectReportPage() {
  const { projectId } = useParams()
  const [data, setData] = useState({ project: null, report: null })
  useEffect(() => {
    Promise.all([projectService.getById(projectId), projectService.listSpecifications(projectId)])
      .then(async ([project, specifications]) => setData({ project, report: specifications[0] ? await qaService.getReport(specifications[0].id) : false }))
      .catch(() => setData({ project: null, report: false }))
  }, [projectId])
  return <main className="page"><BackButton to={`/projects/${projectId}`} label="Project workspace"/><div className="page-heading"><div><p className="overline">PROJECT REPORT</p><h1>{data.project?.name || 'Quality report'}</h1><p>Detailed results and actionable diagnostics for this project.</p></div></div><section className="panel report-page">{data.report === null ? <p className="report-loading"><span className="spinner dark"/> Loading report…</p> : data.report ? <Report report={data.report}/> : <div className="empty-state"><h3>No report available</h3><p>Upload a specification and execute its tests to generate this report.</p></div>}</section></main>
}
