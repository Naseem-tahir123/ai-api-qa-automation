import { useEffect, useMemo, useState } from 'react'
import {
  Activity, ArrowRight, Beaker, Bot, Check, CheckCircle2, ChevronRight, Circle, Clock3,
  Code2, FileJson, FlaskConical, Gauge, LayoutDashboard, LogOut, Menu, Plus,
  Rocket, Search, Settings, ShieldCheck, Sparkles, UploadCloud, X, XCircle, Zap,
} from 'lucide-react'
import { api, clearSession, hasSession, saveSession } from './api'

const methodColors = { GET: 'method-get', POST: 'method-post', PUT: 'method-put', PATCH: 'method-patch', DELETE: 'method-delete' }
const date = (value) => value ? new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) : 'Today'

function Toast({ toast, close }) {
  if (!toast) return null
  return <div className={`toast ${toast.type || ''}`}><span>{toast.type === 'error' ? <XCircle /> : <CheckCircle2 />}</span><p>{toast.message}</p><button onClick={close}><X /></button></div>
}

function Auth({ onDone }) {
  const [signup, setSignup] = useState(false)
  const [form, setForm] = useState({ email: '', username: '', password: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('')
    try {
      if (signup) await api.signup(form)
      const session = await api.login({ email: form.email, password: form.password })
      saveSession(session); onDone()
    } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <main className="auth-page">
    <section className="auth-story">
      <div className="brand light"><span><Beaker /></span> QA Pilot</div>
      <div className="story-content">
        <div className="eyebrow"><Sparkles /> AI-powered quality engineering</div>
        <h1>Ship APIs with<br/><em>quiet confidence.</em></h1>
        <p>Turn any OpenAPI specification into a complete, executable test suite in minutes—not weeks.</p>
        <div className="story-proof"><div className="proof-stack"><span>AI</span><span>QA</span><span>✓</span></div><small>Built for modern QA teams</small></div>
      </div>
      <div className="grid-art" />
    </section>
    <section className="auth-form-wrap">
      <form className="auth-card" onSubmit={submit}>
        <div className="mobile-brand brand"><span><Beaker /></span> QA Pilot</div>
        <p className="overline">{signup ? 'GET STARTED' : 'WELCOME BACK'}</p>
        <h2>{signup ? 'Create your workspace' : 'Sign in to QA Pilot'}</h2>
        <p className="muted">{signup ? 'Start testing smarter today.' : 'Continue building reliable APIs.'}</p>
        {!signup && <div className="demo-login"><strong>Demo access</strong><span>demo@qapilot.dev</span><span>demo1234</span></div>}
        {error && <div className="error-banner"><XCircle />{error}</div>}
        <label>Email address<input type="email" required placeholder="you@company.com" value={form.email} onChange={e => setForm({...form, email:e.target.value})}/></label>
        {signup && <label>Username<input required placeholder="Your name" value={form.username} onChange={e => setForm({...form, username:e.target.value})}/></label>}
        <label>Password<input type="password" required minLength="8" placeholder="••••••••" value={form.password} onChange={e => setForm({...form, password:e.target.value})}/></label>
        <button className="btn primary full" disabled={busy}>{busy ? <span className="spinner"/> : <>{signup ? 'Create account' : 'Sign in'}<ArrowRight /></>}</button>
        <p className="switch">{signup ? 'Already have an account?' : 'New to QA Pilot?'} <button type="button" onClick={() => {setSignup(!signup);setError('')}}>{signup ? 'Sign in' : 'Create an account'}</button></p>
      </form>
    </section>
  </main>
}

function Shell({ page, setPage, children, logout }) {
  const [open, setOpen] = useState(false)
  const nav = [['overview','Overview',LayoutDashboard],['projects','Projects',Code2],['reports','Reports',Activity]]
  return <div className="app-shell">
    <aside className={open ? 'open' : ''}>
      <div className="brand"><span><Beaker /></span> QA Pilot</div>
      <nav>{nav.map(([id,label,Icon]) => <button key={id} className={page===id?'active':''} onClick={()=>{setPage(id);setOpen(false)}}><Icon />{label}</button>)}</nav>
      <div className="aside-bottom"><div className="mini-status"><span/><div><strong>Preview mode</strong><small>Local demo data</small></div></div><button onClick={logout}><LogOut /> Sign out</button></div>
    </aside>
    <div className="main-wrap">
      <header><button className="menu" onClick={()=>setOpen(!open)}><Menu /></button><div className="crumb">Workspace <ChevronRight /> <strong>{page[0].toUpperCase()+page.slice(1)}</strong></div><div className="header-actions"><button className="icon-btn"><Search /></button><div className="avatar">QA</div></div></header>
      {children}
    </div>
  </div>
}

function EmptyProjects({ onCreate }) {
  return <div className="empty-state"><div className="empty-icon"><FileJson /></div><h3>No API projects yet</h3><p>Create your first project and upload an OpenAPI specification to begin.</p><button className="btn primary" onClick={onCreate}><Plus /> New project</button></div>
}

function Metric({ icon: Icon, label, value, note, tone }) {
  return <div className="metric"><div className={`metric-icon ${tone}`}><Icon /></div><div><p>{label}</p><strong>{value}</strong><small>{note}</small></div></div>
}

function Overview({ projects, onCreate, onSelect }) {
  const totals = projects.reduce((a,p)=>({tests:a.tests+(p.tests||0),passed:a.passed+(p.passed||0),failed:a.failed+(p.failed||0)}),{tests:0,passed:0,failed:0})
  const passRate = totals.tests ? Math.round(totals.passed/totals.tests*100) : 0
  const workflow = [{label:'Projects configured',value:projects.length,max:5},{label:'Specs analyzed',value:projects.filter(p=>p.progress>=50).length,max:projects.length||1},{label:'Test suites ready',value:projects.filter(p=>p.progress>=75).length,max:projects.length||1},{label:'Runs completed',value:projects.filter(p=>p.progress===100).length,max:projects.length||1}]
  return <main className="page"><div className="page-heading"><div><p className="overline">COMMAND CENTER</p><h1>Good morning, QA team.</h1><p>Here’s what’s happening across your API quality workspace.</p></div><button className="btn primary" onClick={onCreate}><Plus /> New project</button></div>
    <div className="demo-banner"><span><Sparkles/></span><div><strong>Frontend preview mode</strong><small>Explore every workflow with local demo data. No backend connection is being used.</small></div><span className="status-pill"><i/> Demo ready</span></div>
    <div className="metrics-grid"><Metric icon={Code2} label="Active projects" value={projects.length} note="in this workspace" tone="mint"/><Metric icon={FlaskConical} label="Tests generated" value={totals.tests} note={`${totals.failed} need attention`} tone="violet"/><Metric icon={Gauge} label="Pass rate" value={`${passRate}%`} note={`${totals.passed} checks passing`} tone="amber"/></div>
    <div className="dashboard-grid"><section className="panel"><div className="panel-head"><div><h2>Automation progress</h2><p>Workspace readiness across the QA lifecycle</p></div><span className="live-label"><i/> Live demo</span></div><div className="progress-body">{workflow.map(item=><div className="progress-item" key={item.label}><div><span>{item.label}</span><strong>{item.value}/{item.max}</strong></div><div className="progress-track"><i style={{width:`${Math.min(100,item.value/item.max*100)}%`}}/></div></div>)}</div></section><section className="panel"><div className="panel-head"><div><h2>Recent activity</h2><p>Latest workspace events</p></div></div><div className="activity-list"><div><span className="activity-icon success"><CheckCircle2/></span><p><strong>Payments API run completed</strong><small>139 tests passed · 12 min ago</small></p></div><div><span className="activity-icon ai"><Bot/></span><p><strong>Identity test suite generated</strong><small>86 cases · 1 hour ago</small></p></div><div><span className="activity-icon neutral"><Clock3/></span><p><strong>Orders spec analyzed</strong><small>18 endpoints · Yesterday</small></p></div></div></section></div>
    <section className="panel"><div className="panel-head"><div><h2>Recent projects</h2><p>Your API testing workspaces</p></div><button className="text-btn" onClick={()=>onCreate()}>Create project <ArrowRight /></button></div>
      {projects.length ? <div className="project-list">{projects.slice(0,5).map(p=><button key={p.id} className="project-row" onClick={()=>onSelect(p)}><span className="project-mark"><Code2/></span><span className="project-copy"><strong>{p.name}</strong><small>{p.description || 'API quality automation project'}</small></span><span className="row-progress"><i style={{width:`${p.progress||0}%`}}/><small>{p.progress||0}% complete</small></span><span className="project-date">{p.status||date(p.created_at)}</span><ChevronRight/></button>)}</div> : <EmptyProjects onCreate={onCreate}/>}</section>
  </main>
}

function Projects({ projects, onCreate, onSelect }) {
  return <main className="page"><div className="page-heading"><div><p className="overline">YOUR WORK</p><h1>Projects</h1><p>Manage API specifications, tests, and quality reports.</p></div><button className="btn primary" onClick={onCreate}><Plus/> New project</button></div>
    {projects.length ? <div className="card-grid">{projects.map(p=><button className="project-card" key={p.id} onClick={()=>onSelect(p)}><div className="project-card-top"><span className="project-mark"><Code2/></span><span className="status-pill"><i/> Active</span></div><h3>{p.name}</h3><p>{p.description || 'No description provided.'}</p><div className="card-footer"><span>{date(p.created_at)}</span><span>Open project <ArrowRight/></span></div></button>)}</div> : <section className="panel"><EmptyProjects onCreate={onCreate}/></section>}
  </main>
}

function CreateProject({ close, created }) {
  const [form,setForm]=useState({name:'',description:''}); const [busy,setBusy]=useState(false); const [error,setError]=useState('')
  const submit=async(e)=>{e.preventDefault();setBusy(true);try{created(await api.createProject(form))}catch(err){setError(err.message)}finally{setBusy(false)}}
  return <div className="modal-backdrop" onMouseDown={e=>e.target===e.currentTarget&&close()}><form className="modal" onSubmit={submit}><div className="modal-head"><div><p className="overline">NEW WORKSPACE</p><h2>Create a project</h2></div><button type="button" className="icon-btn" onClick={close}><X/></button></div><p className="muted">Give this API testing workspace a clear name.</p>{error&&<div className="error-banner"><XCircle/>{error}</div>}<label>Project name<input required autoFocus placeholder="e.g. Payments API" value={form.name} onChange={e=>setForm({...form,name:e.target.value})}/></label><label>Description<textarea rows="3" placeholder="What are you testing?" value={form.description} onChange={e=>setForm({...form,description:e.target.value})}/></label><div className="modal-actions"><button type="button" className="btn secondary" onClick={close}>Cancel</button><button className="btn primary" disabled={busy}>{busy?<span className="spinner"/>:<><Plus/>Create project</>}</button></div></form></div>
}

function ProjectWorkspace({ project, notify }) {
  const [stage,setStage]=useState(0), [spec,setSpec]=useState(null), [endpoints,setEndpoints]=useState([]), [report,setReport]=useState(null), [busy,setBusy]=useState(''), [version,setVersion]=useState('v1')
  const act=async(name,fn,onSuccess)=>{setBusy(name);try{const data=await fn();onSuccess(data);notify(`${name} completed successfully`)}catch(e){notify(e.message,'error')}finally{setBusy('')}}
  const upload=e=>{const file=e.target.files[0];if(file)act('Specification upload',()=>api.uploadSpec(project.id,version,file),d=>{setSpec(d);setStage(1)})}
  const steps=[['Upload spec',FileJson],['Parse endpoints',Code2],['Generate tests',Bot],['Run & report',Rocket]]
  return <main className="page"><div className="page-heading project-title"><div><button className="back-link" onClick={()=>history.back()}>Projects /</button><h1>{project.name}</h1><p>{project.description || 'API quality automation workspace'}</p></div><span className="status-pill"><i/> Active</span></div>
    <div className="stepper">{steps.map(([label,Icon],i)=><div className={`step ${i<=stage?'done':''} ${i===stage?'current':''}`} key={label}><span>{i<stage?<Check/>:<Icon/>}</span><div><small>STEP {i+1}</small><strong>{label}</strong></div></div>)}</div>
    <div className="workspace-grid"><section className="panel workflow"><div className="panel-head"><div><p className="overline">SETUP & EXECUTION</p><h2>{steps[stage][0]}</h2></div><span className="step-count">{stage+1} / 4</span></div>
      {stage===0&&<div className="upload-zone"><UploadCloud/><h3>Drop your OpenAPI spec here</h3><p>JSON, YAML, or YML files are supported</p><div className="upload-controls"><input value={version} onChange={e=>setVersion(e.target.value)} aria-label="API version"/><label className="btn primary">Choose file<input type="file" accept=".json,.yaml,.yml" onChange={upload}/></label></div>{busy&&<p className="working"><span className="spinner dark"/> Uploading specification…</p>}</div>}
      {stage===1&&<div className="action-state"><div className="file-chip"><FileJson/><div><strong>{spec?.filename}</strong><small>Version {spec?.version} · uploaded {date(spec?.uploaded_at)}</small></div><CheckCircle2/></div><div className="action-copy"><Sparkles/><h3>Ready to discover your API</h3><p>We’ll inspect the specification and map every supported route.</p><button className="btn primary" disabled={busy} onClick={()=>act('Endpoint parsing',()=>api.parseSpec(spec.id),d=>{setEndpoints(d);setStage(2)})}>{busy?<span className="spinner"/>:<><Zap/> Parse endpoints</>}</button></div></div>}
      {stage===2&&<><div className="result-banner"><CheckCircle2/><div><strong>{endpoints.length} endpoints discovered</strong><small>Your API surface is mapped and ready for AI test generation.</small></div></div><div className="endpoint-list">{endpoints.slice(0,6).map(ep=><div key={ep.id}><span className={methodColors[ep.method]}>{ep.method}</span><code>{ep.path}</code><small>{ep.summary}</small></div>)}</div><div className="sticky-action"><p><Bot/><span><strong>Generate a complete test suite</strong><small>Positive, negative, boundary, auth, and edge cases.</small></span></p><button className="btn primary" disabled={busy} onClick={()=>act('AI test generation',()=>api.generateAll(spec.id),()=>setStage(3))}>{busy?<span className="spinner"/>:<><Sparkles/> Generate with AI</>}</button></div></>}
      {stage===3&&<div className="run-state"><div className="ready-orbit"><Rocket/></div><h3>Your demo test suite is ready</h3><p>Run the simulation to preview loading states, results, and the quality report without contacting any backend or target API.</p><div className="simulation-note"><ShieldCheck/><span><strong>Safe frontend simulation</strong><small>No network request or real API execution will occur.</small></span></div><button className="btn primary" disabled={busy} onClick={()=>act('Demo test execution',()=>api.executeAll(spec.id),async()=>{const r=await api.report(spec.id);setReport(r)})}>{busy?<span className="spinner"/>:<><Rocket/> Run demo tests</>}</button>{report&&<Report report={report}/>}</div>}
    </section><aside className="help-panel"><p className="overline">WORKFLOW</p><h3>From spec to signal</h3><ul>{steps.map(([label],i)=><li className={i<=stage?'done':''} key={label}><span>{i<stage?<Check/>:<Circle/>}</span><div><strong>{label}</strong><small>{['Import JSON or YAML','Discover API routes','Build cases with AI','Execute and inspect'][i]}</small></div></li>)}</ul><div className="tip"><ShieldCheck/><p><strong>Safe by design</strong><br/>Target URL validation and auth stay in your backend.</p></div></aside></div>
  </main>
}

function Ring({value}) { return <div className="ring" style={{'--value':`${value*3.6}deg`}}><span>{Math.round(value)}<small>%</small></span></div> }
function Report({ report }) {
  return <div className="report"><div className="report-title"><div><p className="overline">LATEST REPORT</p><h2>Quality snapshot</h2></div><span className="status-pill"><i/> Complete</span></div><div className="report-summary"><Ring value={report.pass_rate_percentage}/><div><strong>{report.total_passed} passed</strong><span>{report.total_failed} failed</span><small>{report.total_tests_executed} total tests · {report.coverage_percentage}% coverage</small></div></div><div className="endpoint-report">{report.endpoint_details?.map(ep=><div key={ep.endpoint_id}><span className={methodColors[ep.method]}>{ep.method}</span><code>{ep.path}</code><span className="pass"><Check/> {ep.passed}</span><span className="fail"><X/> {ep.failed}</span></div>)}</div></div>
}

export default function App() {
  const [authed,setAuthed]=useState(hasSession()), [page,setPage]=useState('overview'), [projects,setProjects]=useState([]), [selected,setSelected]=useState(null), [modal,setModal]=useState(false), [toast,setToast]=useState(null)
  const notify=(message,type='success')=>{setToast({message,type});setTimeout(()=>setToast(null),4000)}
  const load=()=>api.projects().then(setProjects).catch(e=>notify(e.message,'error'))
  useEffect(()=>{if(authed)load()},[authed])
  const content=useMemo(()=>selected?<ProjectWorkspace project={selected} notify={notify}/>:page==='projects'?<Projects projects={projects} onCreate={()=>setModal(true)} onSelect={setSelected}/>:page==='reports'?<main className="page"><div className="page-heading"><div><p className="overline">QUALITY INTELLIGENCE</p><h1>Reports</h1><p>Open a project and complete a run to view its latest report.</p></div></div><section className="panel"><EmptyProjects onCreate={()=>setPage('projects')}/></section></main>:<Overview projects={projects} onCreate={()=>setModal(true)} onSelect={setSelected}/>,[page,projects,selected])
  if(!authed)return <Auth onDone={()=>setAuthed(true)}/>
  return <><Shell page={selected?'projects':page} setPage={p=>{setSelected(null);setPage(p)}} logout={()=>{clearSession();setAuthed(false)}}>{content}</Shell>{modal&&<CreateProject close={()=>setModal(false)} created={p=>{setProjects([p,...projects]);setModal(false);setSelected(p);notify('Project created')}}/>}<Toast toast={toast} close={()=>setToast(null)}/></>
}
