import { useEffect, useState } from 'react'
import { Bot, Check, CheckCircle2, Circle, Code2, FileJson, Rocket, ShieldCheck, Sparkles, UploadCloud, Zap } from 'lucide-react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import BackButton from '../components/common/BackButton'
import Report from '../components/reports/Report'
import { useToast } from '../context/ToastContext'
import { projectService, qaService } from '../services/api'
import { formatDate, methodClasses } from '../utils/formatters'

const steps = [
  { label: 'Upload spec', help: 'Import JSON or YAML', icon: FileJson },
  { label: 'Parse endpoints', help: 'Discover API routes', icon: Code2 },
  { label: 'Generate tests', help: 'Build cases with AI', icon: Bot },
  { label: 'Run & report', help: 'Execute and inspect', icon: Rocket },
]
const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds))

export default function ProjectWorkspacePage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [project, setProject] = useState(undefined)
  const [stage, setStage] = useState(0)
  const [spec, setSpec] = useState(null)
  const [endpoints, setEndpoints] = useState([])
  const [report, setReport] = useState(null)
  const [busy, setBusy] = useState('')
  const [version, setVersion] = useState('v1')
  const [targetUrl, setTargetUrl] = useState('')
  const [authToken, setAuthToken] = useState('')

  useEffect(() => {
    Promise.all([projectService.getById(projectId), projectService.listSpecifications(projectId)])
      .then(([projectData, specifications]) => {
        setProject(projectData)
        if (specifications[0]) { setSpec(specifications[0]); setStage(1) }
      })
      .catch((error) => { notify(error.message, 'error'); setProject(null) })
  }, [projectId, notify])

  if (project === null) return <Navigate to="/projects" replace />
  if (!project) return <main className="page"><p className="report-loading"><span className="spinner dark"/> Loading project…</p></main>

  const perform = async (name, action, onSuccess) => {
    setBusy(name)
    try { const data = await action(); await onSuccess(data); notify(`${name} completed successfully`) }
    catch (error) { notify(error.message, 'error') }
    finally { setBusy('') }
  }

  const upload = (event) => {
    const file = event.target.files[0]
    if (file) perform('Specification upload', () => qaService.uploadSpec(project.id, version, file), (data) => { setSpec(data); setStage(1) })
  }

  const generateTests = () => perform('AI test generation', async () => {
    const task = await qaService.generateAll(spec.id)
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const taskState = await qaService.getGenerationStatus(task.task_id)
      if (taskState.status === 'completed') return taskState.result
      if (['failed', 'not_found'].includes(taskState.status)) throw new Error(taskState.result?.error || 'Test generation failed')
      await wait(1500)
    }
    throw new Error('Test generation is still running. Please try again shortly.')
  }, () => setStage(3))

  const executeTests = () => {
    if (!targetUrl.trim()) return notify('Enter the target API base URL before running tests.', 'error')
    return perform('Test execution', () => qaService.executeAll(spec.id, {
      target_base_url: targetUrl.trim(),
      auth_config: authToken.trim() ? { token: authToken.trim() } : {},
    }), async () => setReport(await qaService.getReport(spec.id)))
  }

  return <main className="page">
    <BackButton to="/projects" label="All projects"/>
    <div className="page-heading project-title"><div><p className="overline">PROJECT WORKSPACE</p><h1>{project.name}</h1><p>{project.description || 'API quality automation workspace'}</p></div><span className="status-pill"><i/> Connected</span></div>
    <div className="stepper">{steps.map(({ label, icon: Icon }, index) => <div className={`step ${index <= stage ? 'done' : ''} ${index === stage ? 'current' : ''}`} key={label}><span>{index < stage ? <Check/> : <Icon/>}</span><div><small>STEP {index + 1}</small><strong>{label}</strong></div></div>)}</div>
    <div className="workspace-grid">
      <section className="panel workflow">
        <div className="panel-head"><div><p className="overline">SETUP & EXECUTION</p><h2>{steps[stage].label}</h2></div><span className="step-count">{stage + 1} / 4</span></div>
        {stage === 0 && <div className="upload-zone"><UploadCloud/><h3>Drop your OpenAPI spec here</h3><p>JSON, YAML, or YML files are supported</p><div className="upload-controls"><input value={version} onChange={(event) => setVersion(event.target.value)} aria-label="API version"/><label className="btn primary">Choose file<input type="file" accept=".json,.yaml,.yml" onChange={upload}/></label></div>{busy && <p className="working"><span className="spinner dark"/> Uploading specification…</p>}</div>}
        {stage === 1 && <div className="action-state"><div className="file-chip"><FileJson/><div><strong>{spec?.filename}</strong><small>Version {spec?.version} · uploaded {formatDate(spec?.uploaded_at)}</small></div><CheckCircle2/></div><div className="action-copy"><Sparkles/><h3>Ready to discover your API</h3><p>We’ll inspect the specification and store every supported route.</p><button className="btn primary" disabled={busy} onClick={() => perform('Endpoint parsing', () => qaService.parseSpec(spec.id), (data) => { setEndpoints(data); setStage(2) })}>{busy ? <span className="spinner"/> : <><Zap/> Parse endpoints</>}</button></div></div>}
        {stage === 2 && <><div className="result-banner"><CheckCircle2/><div><strong>{endpoints.length} endpoints discovered</strong><small>Your API surface is mapped and ready for AI test generation.</small></div></div><div className="endpoint-list">{endpoints.slice(0, 6).map((endpoint) => <div key={endpoint.id}><span className={methodClasses[endpoint.method]}>{endpoint.method}</span><code>{endpoint.path}</code><small>{endpoint.summary}</small></div>)}</div><div className="sticky-action"><p><Bot/><span><strong>Generate a complete test suite</strong><small>The background worker may take several minutes.</small></span></p><button className="btn primary" disabled={busy} onClick={generateTests}>{busy ? <span className="spinner"/> : <><Sparkles/> Generate with AI</>}</button></div></>}
        {stage === 3 && <div className="run-state"><div className="ready-orbit"><Rocket/></div><h3>Your test suite is ready</h3><p>Provide the target API and optional Bearer token. Requests will be executed by the secured backend engine.</p><div className="execution-form"><label>Target API base URL<input type="url" required placeholder="https://staging-api.example.com" value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)}/></label><label>Bearer token <small>(optional)</small><input type="password" placeholder="Token is sent only for this execution" value={authToken} onChange={(event) => setAuthToken(event.target.value)}/></label></div><button className="btn primary" disabled={busy} onClick={executeTests}>{busy ? <span className="spinner"/> : <><Rocket/> Run all tests</>}</button>{report && <><Report report={report}/><button className="text-btn report-link" onClick={() => navigate(`/projects/${project.id}/report`)}>Open dedicated report</button></>}</div>}
      </section>
      <aside className="help-panel"><p className="overline">WORKFLOW</p><h3>From spec to signal</h3><ul>{steps.map(({ label, help }, index) => <li className={index <= stage ? 'done' : ''} key={label}><span>{index < stage ? <Check/> : <Circle/>}</span><div><strong>{label}</strong><small>{help}</small></div></li>)}</ul><div className="tip"><ShieldCheck/><p><strong>Backend connected</strong><br/>Authentication and target validation are enforced by FastAPI.</p></div></aside>
    </div>
  </main>
}
