import { ArrowRight, Code2, FlaskConical, Gauge, Plus, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import CreateProjectModal from '../components/projects/CreateProjectModal'
import EmptyProjects from '../components/common/EmptyProjects'
import Metric from '../components/common/Metric'
import { useToast } from '../context/ToastContext'
import { useProjects } from '../hooks/useProjects'
import { formatDate } from '../utils/formatters'

export default function DashboardPage() {
  const { projects, createProject } = useProjects()
  const [modalOpen, setModalOpen] = useState(false)
  const navigate = useNavigate()
  const { notify } = useToast()
  const totals = projects.reduce((value, project) => ({ tests: value.tests + project.tests, passed: value.passed + project.passed, failed: value.failed + project.failed }), { tests: 0, passed: 0, failed: 0 })
  const passRate = totals.tests ? Math.round(totals.passed / totals.tests * 100) : 0
  const handleCreated = async (input) => { const project = await createProject(input); setModalOpen(false); notify('Project created'); navigate(`/projects/${project.id}`) }

  return <main className="page">
    <div className="page-heading"><div><p className="overline">COMMAND CENTER</p><h1>Good morning, QA team.</h1><p>Here’s what’s happening across your API quality workspace.</p></div><button className="btn primary" onClick={() => setModalOpen(true)}><Plus /> New project</button></div>
    <div className="demo-banner"><span><Sparkles/></span><div><strong>Backend integration active</strong><small>Projects and QA workflows use your authenticated FastAPI endpoints.</small></div><span className="status-pill"><i/> Connected</span></div>
    <div className="metrics-grid"><Metric icon={Code2} label="Projects" value={projects.length} note="stored in the API" tone="mint"/><Metric icon={FlaskConical} label="Tests executed" value={totals.tests} note={`${totals.failed} failures`} tone="violet"/><Metric icon={Gauge} label="Pass rate" value={`${passRate}%`} note={`${totals.passed} checks passing`} tone="amber"/></div>
    <section className="panel"><div className="panel-head"><div><h2>Recent projects</h2><p>Your API testing workspaces</p></div><button className="text-btn" onClick={() => setModalOpen(true)}>Create project <ArrowRight /></button></div>{projects.length ? <div className="project-list">{projects.slice(0, 5).map((project) => <button key={project.id} className="project-row" onClick={() => navigate(`/projects/${project.id}`)}><span className="project-mark"><Code2/></span><span className="project-copy"><strong>{project.name}</strong><small>{project.description || 'API quality automation project'}</small></span><span className="project-date">{formatDate(project.created_at)}</span><ArrowRight/></button>)}</div> : <EmptyProjects onCreate={() => setModalOpen(true)}/>}</section>
    {modalOpen && <CreateProjectModal onClose={() => setModalOpen(false)} onCreate={handleCreated}/>}
  </main>
}
