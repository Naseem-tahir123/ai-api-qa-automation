import { useState } from 'react'
import { Plus, X, XCircle } from 'lucide-react'

export default function CreateProjectModal({ onClose, onCreate }) {
  const [form, setForm] = useState({ name: '', description: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError('')
    try { await onCreate(form) }
    catch (submitError) { setError(submitError.message) }
    finally { setBusy(false) }
  }
  return <div className="modal-backdrop" onMouseDown={(event) => event.target === event.currentTarget && onClose()}><form className="modal" onSubmit={submit}><div className="modal-head"><div><p className="overline">NEW WORKSPACE</p><h2>Create a project</h2></div><button type="button" className="icon-btn" aria-label="Close" onClick={onClose}><X/></button></div><p className="muted">Give this API testing workspace a clear name.</p>{error && <div className="error-banner"><XCircle/>{error}</div>}<label>Project name<input required autoFocus placeholder="e.g. Payments API" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })}/></label><label>Description<textarea rows="3" placeholder="What are you testing?" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })}/></label><div className="modal-actions"><button type="button" className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" disabled={busy}>{busy ? <span className="spinner"/> : <><Plus/>Create project</>}</button></div></form></div>
}
