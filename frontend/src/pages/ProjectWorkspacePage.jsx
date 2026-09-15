import { useEffect, useState } from 'react'
import { Bot, Check, CheckCircle2, Circle, Code2, FileJson, KeyRound, Play, Rocket, ShieldAlert, ShieldCheck, Sparkles, UploadCloud, Zap, XCircle } from 'lucide-react'
import { Navigate, useParams } from 'react-router-dom'
import BackButton from '../components/common/BackButton'
import { useToast } from '../context/ToastContext'
import { projectService, qaService } from '../services/api'
import { formatDate, methodClasses } from '../utils/formatters'

const steps = [['Upload spec', FileJson], ['Parse endpoints', Code2], ['Build QA-IR', Sparkles], ['Plan coverage', ShieldCheck], ['Generate pipelines', Bot], ['Run suite & evidence', Rocket]]
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
async function waitForJob(taskId) { for (let n = 0; n < 180; n += 1) { await wait(2000); const job = await qaService.getJob(taskId); if (job.status === 'completed') return job.result; if (job.status === 'failed') throw new Error(job.result?.error || 'Background job failed') } throw new Error('Job is still running; refresh this workspace to reconnect.') }
const successful = (result) => result.status === 'fulfilled' ? result.value : null

export default function ProjectWorkspacePage() {
  const { projectId } = useParams(); const { notify } = useToast()
  const [project, setProject] = useState(); const [spec, setSpec] = useState(null); const [endpoints, setEndpoints] = useState([]); const [ir, setIr] = useState(null); const [plan, setPlan] = useState(null); const [pipelines, setPipelines] = useState([]); const [dashboard, setDashboard] = useState(null); const [environments, setEnvironments] = useState([]); const [busy, setBusy] = useState(''); const [version, setVersion] = useState('v1'); const [sourceUrl, setSourceUrl] = useState(''); const [sourceKind, setSourceKind] = useState('auto'); const [environmentId, setEnvironmentId] = useState(''); const [pipelineId, setPipelineId] = useState(''); const [identityId, setIdentityId] = useState(''); const [identities, setIdentities] = useState([]); const [allowDestructive, setAllowDestructive] = useState(false); const [environment, setEnvironment] = useState({ name: 'QA sandbox', base_url: '', is_production: false, verify_tls: true }); const [login, setLogin] = useState({ login_path: '/auth/login', username_field: 'email', password_field: 'password', access_token_json_path: '$.access_token', username: '', password: '', role: 'qa-user' })

  const reload = async () => {
    try {
      const p = await projectService.getById(projectId); setProject(p)
      const specs = await projectService.listSpecifications(projectId); const latest = specs[0] || null; setSpec(latest)
      const envs = await projectService.listEnvironments(projectId); setEnvironments(envs); if (!environmentId && envs[0]) setEnvironmentId(String(envs[0].id))
      if (!latest) return
      const [eps, savedIr, savedPlan, savedPipelines, savedDashboard] = await Promise.allSettled([qaService.listEndpoints(latest.id), qaService.getIR(latest.id), qaService.getCoveragePlan(latest.id), qaService.listPipelines(latest.id), qaService.getDashboard(latest.id)])
      setEndpoints(successful(eps) || []); setIr(successful(savedIr)); setPlan(successful(savedPlan)); const listed = successful(savedPipelines) || []; setPipelines(listed); if (!pipelineId && listed[0]) setPipelineId(String(listed[0].id)); setDashboard(successful(savedDashboard))
    } catch (error) { notify(error.message, 'error'); setProject(null) }
  }
  useEffect(() => { reload() }, [projectId])
  useEffect(() => { if (!environmentId) return; qaService.listAuthProfiles(environmentId).then(async (profiles) => { const all = await Promise.all(profiles.map((profile) => qaService.listIdentities(profile.id))); setIdentities(all.flat()) }).catch(() => setIdentities([])) }, [environmentId])
  if (project === null) return <Navigate to="/projects" replace />
  if (!project) return <main className="page"><p className="report-loading"><span className="spinner dark"/> Restoring workspace…</p></main>
  const stage = !spec ? 0 : !endpoints.length ? 1 : !ir ? 2 : !plan ? 3 : !pipelines.length ? 4 : 5
  const perform = async (name, action) => { setBusy(name); try { const data = await action(); notify(`${name} completed`); return data } catch (error) { notify(error.message, 'error'); return null } finally { setBusy('') } }
  const upload = (event) => { const file = event.target.files[0]; if (file) perform('Specification upload', () => qaService.uploadSpec(project.id, version, file)).then((data) => { if (data) { setSpec(data); setEndpoints([]); setIr(null); setPlan(null); setPipelines([]); setDashboard(null) } }) }
  const importUrl = () => perform('Specification URL import', () => qaService.importSpecUrl(project.id, { url: sourceUrl, version, source_kind: sourceKind })).then((data) => { if (data) { setSpec(data); setEndpoints([]); setIr(null); setPlan(null); setPipelines([]); setDashboard(null) } })
  const buildAuth = () => perform('Automatic-login profile', async () => { if (!environmentId || !login.username || !login.password) throw new Error('Choose an environment and enter test username/email and password.')
    const profile = await qaService.createAuthProfile({ environment_id: Number(environmentId), name: `Login: ${login.role}`, auth_type: 'login', injection_rules: { target: 'header', name: 'Authorization', prefix: 'Bearer ' }, login_config: { login_path: login.login_path, method: 'POST', username_field: login.username_field, password_field: login.password_field, access_token_json_path: login.access_token_json_path } })
    const identity = await qaService.createIdentity(profile.id, { name: login.role, role: login.role, secrets: { username: login.username, password: login.password } }); setIdentities((items) => [identity, ...items]); setIdentityId(String(identity.id)); setLogin((current) => ({ ...current, password: '' })); return identity })
  const runPayload = () => ({ environment_id: Number(environmentId), ...(identityId ? { test_identity_id: Number(identityId) } : {}), allow_destructive: allowDestructive })
  const runAll = () => perform('Full suite execution', async () => { if (!environmentId) throw new Error('Create or choose a QA environment first.'); const job = await qaService.runAllPipelines(spec.id, runPayload()); await waitForJob(job.task_id); const [nextDashboard, impact] = await Promise.all([qaService.getDashboard(spec.id), qaService.getRegressionImpact(spec.id).catch(() => null)]); setDashboard({ ...nextDashboard, regression: impact }) })
  return <main className="page"><BackButton to="/projects" label="All projects"/><div className="page-heading project-title"><div><p className="overline">PERSISTENT QA WORKSPACE</p><h1>{project.name}</h1><p>{spec ? `${spec.filename} · ${spec.version} · saved workflow restored automatically` : 'Create or upload a specification to begin.'}</p></div><button className="btn secondary" disabled={busy} onClick={reload}>Refresh workspace</button></div>
    <div className="stepper">{steps.map(([label, Icon], index) => <div className={`step ${index < stage ? 'done' : ''} ${index === stage ? 'current' : ''}`} key={label}><span>{index < stage ? <Check/> : <Icon/>}</span><div><small>STEP {index + 1}</small><strong>{label}</strong></div></div>)}</div>
    <div className="workspace-grid"><section className="panel workflow"><div className="panel-head"><div><p className="overline">BACKEND-DRIVEN DELIVERY</p><h2>{steps[stage][0]}</h2></div><span className="step-count">{stage + 1}/{steps.length}</span></div>
      {stage === 0 && <div className="upload-zone"><UploadCloud/><h3>Add an OpenAPI specification</h3><p>Upload a JSON/YAML file, or import a hosted OpenAPI document / Swagger UI URL. New versions are saved separately for regression comparison.</p><div className="upload-controls"><input value={version} onChange={(e) => setVersion(e.target.value)} aria-label="Version"/><label className="btn primary">Choose file<input type="file" accept=".json,.yaml,.yml" onChange={upload}/></label></div><div className="url-import"><strong>Import from URL</strong><input type="url" placeholder="https://api.example.com/openapi.json" value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)}/><select value={sourceKind} onChange={(e) => setSourceKind(e.target.value)}><option value="auto">Auto-detect OpenAPI / Swagger UI</option><option value="openapi">Direct OpenAPI JSON or YAML</option><option value="swagger_ui">Swagger UI page</option></select><button className="btn secondary" disabled={busy || !sourceUrl} onClick={importUrl}>Import URL</button></div></div>}
      {stage === 1 && <Action icon={Code2} title="Parse endpoint catalog" text="Read routes, contracts, parameters, security, and tags from the saved specification." button="Parse endpoints" busy={busy} onClick={() => perform('Endpoint parsing', () => qaService.parseSpec(spec.id)).then((data) => { if (data) setEndpoints(data) })}/>}
      {stage === 2 && <><EndpointList endpoints={endpoints}/><Action icon={Sparkles} title="Build persistent QA-IR" text="Creates the resource/dependency model, risk tags, CRUD classification, and schema fingerprints." button="Build QA-IR" busy={busy} onClick={() => perform('QA-IR build', () => qaService.buildIR(spec.id)).then(setIr)}/></>}
      {stage === 3 && <Action icon={ShieldCheck} title="Plan deterministic coverage" text={`QA-IR contains ${ir?.endpoints?.length || 0} endpoints. Select happy path, validation, auth, boundary, contract, pagination, and regression intents.`} button="Create coverage plan" busy={busy} onClick={() => perform('Coverage planning', () => qaService.createCoveragePlan(spec.id)).then(setPlan)}/>}
      {stage === 4 && <><Coverage plan={plan}/><Action icon={Bot} title="Generate richer domain pipelines" text={`${plan?.selected_intents?.length || 0} planned intents will be grouped by resource/domain. Generated endpoint references are validated before saving.`} button="Generate pipelines" busy={busy} onClick={() => perform('Pipeline generation', async () => { const job = await qaService.generate(spec.id); await waitForJob(job.task_id); return qaService.listPipelines(spec.id) }).then((data) => { if (data) { setPipelines(data); setPipelineId(String(data[0]?.id || '')) } })}/></>}
      {stage === 5 && <><ExecutionSetup environments={environments} environmentId={environmentId} setEnvironmentId={setEnvironmentId} environment={environment} setEnvironment={setEnvironment} create={() => perform('Environment creation', () => qaService.createEnvironment(project.id, environment)).then((data) => { if (data) { setEnvironments([data, ...environments]); setEnvironmentId(String(data.id)) } })} login={login} setLogin={setLogin} identities={identities} identityId={identityId} setIdentityId={setIdentityId} buildAuth={buildAuth} busy={busy}/><PipelineList pipelines={pipelines} pipelineId={pipelineId} setPipelineId={setPipelineId}/><label className="approval"><input type="checkbox" checked={allowDestructive} onChange={(e) => setAllowDestructive(e.target.checked)}/> I explicitly approve destructive requests against this selected environment.</label><div className="run-actions"><button className="btn secondary" disabled={busy || !pipelineId || !environmentId} onClick={() => perform('Pipeline execution', async () => { const job = await qaService.runPipeline(pipelineId, runPayload()); await waitForJob(job.task_id); return qaService.getDashboard(spec.id) }).then((data) => data && setDashboard(data))}><Play/> Run selected</button><button className="btn primary" disabled={busy || !environmentId} onClick={runAll}><Rocket/> Run all pipelines</button></div>{dashboard && <Evidence dashboard={dashboard}/>}</>}
    </section><aside className="help-panel"><p className="overline">WORKFLOW STATE</p><h3>Safe, resumable QA</h3><ul>{steps.map(([label], index) => <li className={index <= stage ? 'done' : ''} key={label}><span>{index < stage ? <Check/> : <Circle/>}</span><div><strong>{label}</strong><small>{index < stage ? 'Persisted in PostgreSQL' : 'Waiting'}</small></div></li>)}</ul><div className="tip"><ShieldAlert/><p><strong>Coverage note</strong><br/>Use Run all pipelines to verify the full generated suite. One pipeline can only cover its own steps.</p></div></aside>
  </div></main>
}
function Action({ icon: Icon, title, text, button, busy, onClick }) { return <div className="action-copy"><Icon/><h3>{title}</h3><p>{text}</p><button className="btn primary" disabled={busy} onClick={onClick}>{busy ? <span className="spinner"/> : button}</button></div> }
function EndpointList({ endpoints }) { return <div className="endpoint-list">{endpoints.slice(0, 10).map((e) => <div key={e.id}><span className={methodClasses[e.method]}>{e.method}</span><code>{e.path}</code><small>{e.summary}</small></div>)}</div> }
function Coverage({ plan }) { return <div className="result-banner"><ShieldCheck/><div><strong>{plan?.selected_intents?.length || 0} intents planned</strong><small>{plan?.coverage_matrix?.map((row) => row.endpoint).slice(0, 3).join(' · ')}</small></div></div> }
function ExecutionSetup({ environments, environmentId, setEnvironmentId, environment, setEnvironment, create, login, setLogin, identities, identityId, setIdentityId, buildAuth, busy }) { return <div className="execution-setup"><h3>Target environment & automatic login</h3><p>Credentials are encrypted by the backend; JWT is acquired at runtime and never shown or stored in the browser.</p><label>Saved environment<select value={environmentId} onChange={(e) => setEnvironmentId(e.target.value)}><option value="">Create/select an environment</option>{environments.map((e) => <option key={e.id} value={e.id}>{e.name} — {e.base_url}</option>)}</select></label><label>New environment base URL<input placeholder="https://qa.example.com" value={environment.base_url} onChange={(e) => setEnvironment({ ...environment, base_url: e.target.value })}/></label><button className="btn secondary" disabled={busy || !environment.base_url} onClick={create}>Save environment</button><details><summary><KeyRound/> Configure automatic login</summary><div className="auth-fields"><label>Login path<input value={login.login_path} onChange={(e) => setLogin({ ...login, login_path: e.target.value })}/></label><label>Username field<input value={login.username_field} onChange={(e) => setLogin({ ...login, username_field: e.target.value })}/></label><label>Password field<input value={login.password_field} onChange={(e) => setLogin({ ...login, password_field: e.target.value })}/></label><label>Token JSONPath<input value={login.access_token_json_path} onChange={(e) => setLogin({ ...login, access_token_json_path: e.target.value })}/></label><label>Test email/username<input value={login.username} onChange={(e) => setLogin({ ...login, username: e.target.value })}/></label><label>Test password<input type="password" value={login.password} onChange={(e) => setLogin({ ...login, password: e.target.value })}/></label><button className="btn secondary" disabled={busy || !environmentId} onClick={buildAuth}>Save automatic login</button></div></details><label>Test identity<select value={identityId} onChange={(e) => setIdentityId(e.target.value)}><option value="">No authentication</option>{identities.map((identity) => <option key={identity.id} value={identity.id}>{identity.name}{identity.role ? ` (${identity.role})` : ''}</option>)}</select></label></div> }
function PipelineList({ pipelines, pipelineId, setPipelineId }) { return <label>Pipeline for targeted run<select value={pipelineId} onChange={(e) => setPipelineId(e.target.value)}>{pipelines.map((p) => <option value={p.id} key={p.id}>{p.name} · {p.steps} steps{p.has_destructive_step ? ' · destructive' : ''}</option>)}</select></label> }
function Evidence({ dashboard }) { 
  const c = dashboard.coverage || {}; 
  const e = dashboard.execution || {}; 
  const p = dashboard.pipelines || {}; 
  
  // State for filter tabs: 'all', 'failed', 'passed'
  const [filter, setFilter] = useState('all');

  const allEvidence = dashboard.all_test_evidence || dashboard.actionable_failures || [];
  const failures = allEvidence.filter(item => !item.is_passed);
  const passed = allEvidence.filter(item => item.is_passed);

  const displayedList = filter === 'failed' ? failures : filter === 'passed' ? passed : allEvidence;

  // CSV BUG SHEET DOWNLOAD FUNCTION
  const exportBugSheet = () => {
    if (!failures.length) {
      alert("No failures found to export!");
      return;
    }

    const headers = ["Bug ID", "Method", "Endpoint", "Pipeline Scenario", "Expected Status", "Actual Status", "Payload Sent", "API Response", "Diagnostic Error"];
    
    const rows = failures.map((fail, index) => [
      `BUG-${index + 1}`,
      fail.method,
      `"${fail.path}"`,
      `"${fail.scenario_name}"`,
      fail.expected_status,
      fail.actual_status || "Network Error",
      `"${JSON.stringify(fail.payload || {}).replace(/"/g, '""')}"`,
      `"${JSON.stringify(fail.response_body || {}).replace(/"/g, '""')}"`,
      `"${(fail.error_message || '').replace(/"/g, '""')}"`
    ]);

    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map(row => row.join(","))].join("\n");

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `QA_Bug_Sheet_Spec_${dashboard.specification_id || "Report"}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="report">
      <div className="report-title">
        <div><p className="overline">QA EVIDENCE</p><h2>Execution and coverage</h2></div>
        <span className="status-pill"><i/> {dashboard.release_risk} risk</span>
      </div>
      
      <div className="report-summary">
        <div className="ring" style={{ '--value': `${(c.percentage || 0) * 3.6}deg` }}><span>{Math.round(c.percentage || 0)}<small>%</small></span></div>
        <div><strong>{e.passed || 0} passed</strong><span>{e.failed || 0} failed</span><small>{c.endpoints_executed || 0}/{c.endpoints_total || 0} endpoints executed · {p.executed || 0}/{p.total || 0} pipelines run</small></div>
      </div>
      
      <div className="evidence-grid">
        <p><strong>Failure classes</strong>{Object.entries(e.failure_classes || {}).map(([type, count]) => `${type}: ${count}`).join(' · ') || 'None'}</p>
        <p><strong>Cleanup</strong>{e.failed_cleanup || 0} failed cleanup step(s)</p>
        {dashboard.regression && <p><strong>Regression impact</strong>{dashboard.regression.impacted_endpoints?.length || 0} impacted endpoint(s)</p>}
      </div>
      
      <div className="coverage-table">
        {dashboard.endpoint_coverage?.map((row) => <div className={row.status} key={row.endpoint}><code>{row.endpoint}</code><span>{row.status === 'executed' ? `${row.passed} passed · ${row.failed} failed` : 'Not executed'}</span></div>)}
      </div>

      {/* FULL TEST AUDIT EVIDENCE SECTION */}
      <div className="test-evidence" style={{ marginTop: '35px' }}>
        <div className="evidence-heading" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <h3>Test Execution Evidence</h3>
            <p>Open any step to inspect sent payload, response body, and status codes.</p>
          </div>

          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {/* FILTER TABS */}
            <div style={{ display: 'inline-flex', background: '#eef1ee', borderRadius: '8px', padding: '3px' }}>
              <button 
                className={`btn ${filter === 'all' ? 'primary' : 'secondary'}`} 
                onClick={() => setFilter('all')}
                style={{ padding: '5px 12px', fontSize: '11px', borderRadius: '6px' }}
              >
                All ({allEvidence.length})
              </button>
              <button 
                className={`btn ${filter === 'passed' ? 'primary' : 'secondary'}`} 
                onClick={() => setFilter('passed')}
                style={{ padding: '5px 12px', fontSize: '11px', borderRadius: '6px', color: filter === 'passed' ? 'white' : '#287757' }}
              >
                Passed ({passed.length})
              </button>
              <button 
                className={`btn ${filter === 'failed' ? 'primary' : 'secondary'}`} 
                onClick={() => setFilter('failed')}
                style={{ padding: '5px 12px', fontSize: '11px', borderRadius: '6px', color: filter === 'failed' ? 'white' : '#a33d37' }}
              >
                Failed ({failures.length})
              </button>
            </div>

            {/* CSV EXPORT BUTTON */}
            {failures.length > 0 && (
              <button 
                className="btn secondary" 
                onClick={exportBugSheet}
                style={{ padding: '7px 12px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                📥 Export Bug Sheet (CSV)
              </button>
            )}
          </div>
        </div>
        
        {displayedList.length === 0 ? (
          <div style={{ padding: '25px', background: '#f8faf7', borderRadius: '10px', border: '1px solid var(--line)', textAlign: 'center', color: 'var(--muted)' }}>
            No tests found for the selected filter ({filter.toUpperCase()}).
          </div>
        ) : (
          displayedList.map((test, idx) => {
            const isPass = test.is_passed;
            return (
              <details className={`test-result ${isPass ? 'passed' : 'failed'}`} key={idx} open={!isPass && idx === 0}>
                <summary>
                  <span className="result-symbol">
                    {isPass ? <CheckCircle2 size={15} style={{ color: '#287757' }}/> : <XCircle size={15} style={{ color: '#a33d37' }}/>}
                  </span>
                  <span className={methodClasses[test.method] || 'method-get'}>{test.method}</span>
                  <span className="result-name">
                    <strong>{test.path}</strong>
                    <small>{test.scenario_name} {test.execution_time_ms ? `· ${test.execution_time_ms}ms` : ''}</small>
                  </span>
                  <span className="result-code" style={{ color: isPass ? '#287757' : '#a33d37', fontWeight: 'bold' }}>
                    HTTP {test.actual_status || 'ERR'}
                  </span>
                </summary>
                
                <div className="result-explanation" style={{ gridTemplateColumns: '1fr', gap: '12px' }}>
                  <div style={{ display: 'flex', gap: '25px', borderBottom: '1px solid var(--line)', paddingBottom: '10px' }}>
                    <div><span>Expected Status</span><strong>HTTP {test.expected_status}</strong></div>
                    <div>
                      <span>Actual Status</span>
                      <strong style={{ color: isPass ? '#287757' : '#b34840' }}>
                        HTTP {test.actual_status || 'Network Error'} {isPass ? '✓' : '✗'}
                      </strong>
                    </div>
                  </div>
                  
                  {test.payload && Object.keys(test.payload).length > 0 && (
                    <div>
                      <span>Payload Sent</span>
                      <pre style={{ margin: '4px 0 0', fontSize: '11px', background: '#f5f8f4', padding: '10px', borderRadius: '8px', overflowX: 'auto', border: '1px solid var(--line)' }}>
                        {JSON.stringify(test.payload, null, 2)}
                      </pre>
                    </div>
                  )}
                  
                  {test.response_body && (
                    <div>
                      <span>Target API Response</span>
                      <pre style={{ margin: '4px 0 0', fontSize: '11px', background: isPass ? '#f2f9f4' : '#fff0ee', padding: '10px', borderRadius: '8px', overflowX: 'auto', border: `1px solid ${isPass ? '#cce9d7' : '#efcfcc'}`, color: isPass ? '#1c5e3f' : '#8b3833' }}>
                        {JSON.stringify(test.response_body, null, 2)}
                      </pre>
                    </div>
                  )}
                  
                  {test.error_message && (
                    <div className="diagnostic">
                      <span>Diagnostic Error</span>
                      <strong>{test.error_message}</strong>
                    </div>
                  )}
                </div>
              </details>
            );
          })
        )}
      </div>

    </div>
  );
}