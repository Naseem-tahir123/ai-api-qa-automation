import { FileJson, Plus } from 'lucide-react'

export default function EmptyProjects({ onCreate }) {
  return <div className="empty-state"><div className="empty-icon"><FileJson /></div><h3>No API projects yet</h3><p>Create your first project and upload an OpenAPI specification to begin.</p><button className="btn primary" onClick={onCreate}><Plus /> New project</button></div>
}
