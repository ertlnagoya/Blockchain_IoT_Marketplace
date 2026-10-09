import { useMemo, useState } from 'react'

type PlannerDiagnostics = {
  status: 'ok' | 'fallback'
  severity: 'info' | 'warning' | 'error'
  label: string
  color_hint: 'green' | 'amber' | 'red'
  code: string
  category: 'success' | 'provider' | 'validation' | 'planner'
  user_message: string
  summary?: string | null
  suggestion?: string | null
  provider_name?: string
  planner_mode?: string
  used_fallback?: boolean
  error_type?: string | null
  error_message?: string | null
}

type ActionCommand = {
  action_type: string
  target: string
  parameters: Record<string, unknown>
}

type ExecutionPlan = {
  planner_name: string
  intent: string
  target_area: string
  time_window_minutes: number
  watch_events: string[]
  thresholds: Record<string, number>
  actions: ActionCommand[]
  original_request: string
}

type PlanResponse = {
  status: 'planned'
  plan: ExecutionPlan
  planner_diagnostics: PlannerDiagnostics
}

type ExecuteResponse = {
  status: 'executed'
  execution: {
    request_text: string
    plan: ExecutionPlan
    planner_diagnostics: PlannerDiagnostics
    evaluation: {
      triggered: boolean
      matched_counts: Record<string, number>
      reason: string
    }
    actions_executed: ActionCommand[]
  }
}

type BadgeViewModel = {
  label: string
  tone: 'success' | 'warning' | 'danger' | 'neutral'
  detail: string
  code: string
  category: string
}

const requestTemplates = {
  park: '公園北側でポイ捨てや危険行動が増えていたら教えて。必要なら照明をつけて管理者に通知して。',
  station: 'If suspicious activity increases near the station front, show a warning and notify the manager.',
}

function diagnosticsToBadge(diagnostics: PlannerDiagnostics): BadgeViewModel {
  const toneMap: Record<PlannerDiagnostics['color_hint'], BadgeViewModel['tone']> = {
    green: 'success',
    amber: 'warning',
    red: 'danger',
  }

  return {
    label: diagnostics.label,
    tone: toneMap[diagnostics.color_hint] ?? 'neutral',
    detail: diagnostics.user_message,
    code: diagnostics.code,
    category: diagnostics.category,
  }
}

async function postJson<T>(baseUrl: string, path: string, payload: Record<string, unknown>): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(`HTTP ${response.status}: ${text}`)
  }

  return response.json() as Promise<T>
}

async function getJson<T>(baseUrl: string, path: string): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`)
  if (!response.ok) {
    const text = await response.text()
    throw new Error(`HTTP ${response.status}: ${text}`)
  }
  return response.json() as Promise<T>
}

export default function App() {
  const [apiBaseUrl, setApiBaseUrl] = useState('http://localhost:8090')
  const [requestText, setRequestText] = useState(requestTemplates.park)
  const [planResult, setPlanResult] = useState<PlanResponse | null>(null)
  const [executeResult, setExecuteResult] = useState<ExecuteResponse | null>(null)
  const [executions, setExecutions] = useState<unknown>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<'plan' | 'execute' | 'history' | null>(null)

  const diagnostics = planResult?.planner_diagnostics ?? executeResult?.execution.planner_diagnostics ?? null
  const badge = useMemo(() => (diagnostics ? diagnosticsToBadge(diagnostics) : null), [diagnostics])

  async function handlePlan() {
    setBusyAction('plan')
    setErrorMessage(null)
    try {
      const result = await postJson<PlanResponse>(apiBaseUrl, '/assistant/plan', { request_text: requestText })
      setPlanResult(result)
      setExecuteResult(null)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error))
    } finally {
      setBusyAction(null)
    }
  }

  async function handleExecute() {
    setBusyAction('execute')
    setErrorMessage(null)
    try {
      const result = await postJson<ExecuteResponse>(apiBaseUrl, '/assistant/execute', { request_text: requestText })
      setExecuteResult(result)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error))
    } finally {
      setBusyAction(null)
    }
  }

  async function handleLoadExecutions() {
    setBusyAction('history')
    setErrorMessage(null)
    try {
      const result = await getJson<unknown>(apiBaseUrl, '/assistant/executions')
      setExecutions(result)
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : String(error))
    } finally {
      setBusyAction(null)
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">IW3IP Phase 3</p>
        <h1>Regional Safety Assistant Demo</h1>
        <p className="hero-copy">
          Human request -&gt; planner -&gt; diagnostics badge -&gt; execution result. This screen is a minimal
          frontend for the Phase 3 assistant API.
        </p>
      </section>

      <section className="card stack-lg">
        <div className="grid-two">
          <label className="field">
            <span>Assistant API Base URL</span>
            <input value={apiBaseUrl} onChange={(e) => setApiBaseUrl(e.target.value)} />
          </label>
          <div className="field">
            <span>Quick Templates</span>
            <div className="button-row">
              <button type="button" className="secondary" onClick={() => setRequestText(requestTemplates.park)}>
                Park Safety (JA)
              </button>
              <button type="button" className="secondary" onClick={() => setRequestText(requestTemplates.station)}>
                Station Warning (EN)
              </button>
            </div>
          </div>
        </div>

        <label className="field">
          <span>Request Text</span>
          <textarea rows={5} value={requestText} onChange={(e) => setRequestText(e.target.value)} />
        </label>

        <div className="button-row">
          <button type="button" onClick={handlePlan} disabled={busyAction !== null}>
            {busyAction === 'plan' ? 'Planning...' : 'POST /assistant/plan'}
          </button>
          <button type="button" onClick={handleExecute} disabled={busyAction !== null}>
            {busyAction === 'execute' ? 'Executing...' : 'POST /assistant/execute'}
          </button>
          <button type="button" className="secondary" onClick={handleLoadExecutions} disabled={busyAction !== null}>
            {busyAction === 'history' ? 'Loading...' : 'GET /assistant/executions'}
          </button>
        </div>

        {errorMessage ? <div className="alert alert-red"><strong>Request Error</strong><p>{errorMessage}</p></div> : null}
      </section>

      {badge ? (
        <section className="card stack-md">
          <div className="section-heading">
            <h2>Planner Diagnostics</h2>
            <span className={`badge badge-${diagnostics?.color_hint}`}>{badge.label}</span>
          </div>
          <div className={`alert alert-${diagnostics?.color_hint}`}>
            <strong>{diagnostics?.label}</strong>
            <p>{diagnostics?.user_message}</p>
            <small>
              code={badge.code} / category={badge.category} / severity={diagnostics?.severity}
            </small>
            {diagnostics?.suggestion ? <p>Next: {diagnostics.suggestion}</p> : null}
          </div>
        </section>
      ) : null}

      <section className="grid-panels">
        <article className="card stack-md">
          <div className="section-heading">
            <h2>Plan Result</h2>
            <span className="pill">JSON</span>
          </div>
          <pre>{planResult ? JSON.stringify(planResult, null, 2) : 'Run /assistant/plan to inspect the plan.'}</pre>
        </article>

        <article className="card stack-md">
          <div className="section-heading">
            <h2>Execution Result</h2>
            <span className="pill">JSON</span>
          </div>
          <pre>{executeResult ? JSON.stringify(executeResult, null, 2) : 'Run /assistant/execute to inspect actions.'}</pre>
        </article>
      </section>

      <section className="card stack-md">
        <div className="section-heading">
          <h2>Execution History</h2>
          <span className="pill">GET /assistant/executions</span>
        </div>
        <pre>{executions ? JSON.stringify(executions, null, 2) : 'Load execution history after executing a request.'}</pre>
      </section>
    </main>
  )
}
