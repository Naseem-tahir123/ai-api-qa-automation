import { useState } from 'react'
import { ArrowRight, Code2, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import BackButton from '../components/common/BackButton'
import EmptyProjects from '../components/common/EmptyProjects'
import CreateProjectModal from '../components/projects/CreateProjectModal'
import { useProjects } from '../hooks/useProjects'
import { useToast } from '../context/ToastContext'
import { formatDate } from '../utils/formatters'

export default function ProjectsPage() {
  const [modalOpen, setModalOpen] = useState(false)
  const { projects, createProject } = useProjects()
  const { notify } = useToast()
  const navigate = useNavigate()
  const handleCreated = async (input) => { const project = await createProject(input); setModalOpen(false); notify('Project created'); navigate(`/projects/${project.id}`) }
  return <main className="page"><BackButton to="/dashboard" label="Dashboard"/><div className="page-heading"><div><p className="overline">YOUR WORK</p><h1>Projects</h1><p>Manage API specifications, tests, and quality reports.</p></div><button className="btn primary" onClick={() => setModalOpen(true)}><Plus/> New project</button></div>{projects.length ? <div className="card-grid">{projects.map((project) => <button className="project-card" key={project.id} onClick={() => navigate(`/projects/${project.id}`)}><div className="project-card-top"><span className="project-mark"><Code2/></span><span className="status-pill"><i/> Active</span></div><h3>{project.name}</h3><p>{project.description || 'No description provided.'}</p><div className="card-footer"><span>{formatDate(project.created_at)}</span><span>Open project <ArrowRight/></span></div></button>)}</div> : <section className="panel"><EmptyProjects onCreate={() => setModalOpen(true)}/></section>}{modalOpen && <CreateProjectModal onClose={() => setModalOpen(false)} onCreate={handleCreated}/>}</main>
}
