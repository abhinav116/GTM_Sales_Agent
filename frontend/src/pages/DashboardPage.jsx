import { useState } from 'react'
import {
  ArrowLeft, AlertTriangle, Users,
  ShieldAlert, ArrowRight, CheckCircle,
  User, Calendar, FileText, Mail, Building2, TrendingUp, Mic,
  Code2, Download, X, XCircle, Clock, Edit2
} from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'

const API = 'http://localhost:8000'

function HumanReviewPanel({ flags, runId, onApproved }) {
  const bantFlags = flags.filter(f => f.field.startsWith('bant.'))
  const [edits, setEdits]         = useState(
    Object.fromEntries(bantFlags.map(f => [f.field.replace('bant.', ''), f.value || '']))
  )
  const [approving, setApproving] = useState(false)
  const [rejecting, setRejecting] = useState(false)
  const [outcome, setOutcome]     = useState(null) // 'approved' | 'rejected'

  async function handleApprove() {
    setApproving(true)
    try {
      const res = await fetch(`${API}/api/runs/${runId}/approve`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ bant_edits: edits }),
      })
      if (res.ok) { setOutcome('approved'); onApproved?.() }
    } finally { setApproving(false) }
  }

  async function handleReject() {
    setRejecting(true)
    try {
      const res = await fetch(`${API}/api/runs/${runId}/reject`, { method: 'POST' })
      if (res.ok) setOutcome('rejected')
    } finally { setRejecting(false) }
  }

  if (outcome === 'approved') return (
    <div className="alert alert--success" style={{ marginBottom: 'var(--space-6)' }}>
      <span className="alert__icon"><CheckCircle size={16} /></span>
      <span><strong>Approved.</strong> Fields pushed to CRM.</span>
    </div>
  )

  if (outcome === 'rejected') return (
    <div className="alert alert--danger" style={{ marginBottom: 'var(--space-6)' }}>
      <span className="alert__icon"><XCircle size={16} /></span>
      <span><strong>Rejected.</strong> This run will not be pushed to CRM.</span>
    </div>
  )

  return (
    <div className="intel-card span-full" style={{ marginBottom: 'var(--space-8)' }}>
      <div className="intel-card__header">
        <div className="intel-card__header-left">
          <div className="intel-card__icon" style={{ background: 'var(--color-warning-bg)', color: 'var(--color-warning)' }}>
            <AlertTriangle size={14} />
          </div>
          <p className="intel-card__title">Human Review Required</p>
        </div>
        <span className="tag tag--warning">
          <Clock size={11} style={{ display: 'inline', marginRight: 3 }} />
          {bantFlags.length} field{bantFlags.length !== 1 ? 's' : ''} pending
        </span>
      </div>
      <div className="intel-card__body">
        {bantFlags.map((f, i) => {
          const key = f.field.replace('bant.', '')
          return (
            <div key={i} style={{ marginBottom: 'var(--space-5)', padding: 'var(--space-4)', background: 'var(--color-warning-bg)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-warning)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
                <span className="tag tag--warning"><Edit2 size={11} style={{ display: 'inline', marginRight: 3 }} />Needs review</span>
                <strong style={{ fontSize: 'var(--text-sm)', textTransform: 'capitalize' }}>{key}</strong>
                <span className="t-caption" style={{ color: 'var(--color-text-muted)' }}>conf {Math.round(f.confidence * 100)}%</span>
              </div>
              <p className="t-caption" style={{ color: 'var(--color-text-muted)', marginBottom: 'var(--space-2)' }}>
                AI extracted: {f.value || 'Not identified'}
              </p>
              <input
                className="input"
                style={{ width: '100%' }}
                placeholder={`Correct or confirm ${key}...`}
                value={edits[key] || ''}
                onChange={e => setEdits(prev => ({ ...prev, [key]: e.target.value }))}
              />
            </div>
          )
        })}
        <div style={{ display: 'flex', gap: 'var(--space-4)', marginTop: 'var(--space-4)' }}>
          <button
            className="btn btn--primary"
            onClick={handleApprove}
            disabled={approving || rejecting}
          >
            <CheckCircle size={14} />
            {approving ? 'Pushing to CRM...' : 'Approve & Push to CRM'}
          </button>
          <button
            className="btn btn--secondary"
            onClick={handleReject}
            disabled={approving || rejecting}
            style={{ color: 'var(--color-danger)', borderColor: 'var(--color-danger)' }}
          >
            <XCircle size={14} />
            {rejecting ? 'Rejecting...' : 'Reject'}
          </button>
        </div>
      </div>
    </div>
  )
}

function JsonModal({ data, onClose }) {
  const json = JSON.stringify(data, null, 2)

  function handleDownload() {
    const runId = data.run_meta?.run_id || 'result'
    const blob = new Blob([json], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `raapid_run_${runId}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="processing-overlay" onClick={onClose}>
      <div
        className="processing-card"
        style={{ maxWidth: 720, width: '90vw', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-5)' }}>
          <h3 className="processing-card__title" style={{ margin: 0 }}>Raw JSON Output</h3>
          <div style={{ display: 'flex', gap: 'var(--space-3)' }}>
            <button className="btn btn--secondary btn--sm" onClick={handleDownload}>
              <Download size={14} /> Download
            </button>
            <button className="btn btn--secondary btn--sm" onClick={onClose}>
              <X size={14} />
            </button>
          </div>
        </div>
        <pre style={{
          flex: 1, overflow: 'auto', background: 'var(--color-bg-page)',
          border: 'var(--border-1)', borderRadius: 'var(--radius-md)',
          padding: 'var(--space-5)', fontSize: 12,
          fontFamily: 'var(--font-mono)', color: 'var(--color-text-body)',
          margin: 0, textAlign: 'left',
        }}>
          {json}
        </pre>
      </div>
    </div>
  )
}

function getInitials(name) {
  if (!name) return 'U'
  return name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
}

function confClass(score) {
  if (score >= 0.85) return 'high'
  if (score >= 0.75) return 'medium'
  return 'low'
}

function ConfBadge({ score }) {
  const pct = Math.round((score || 0) * 100)
  if (score >= 0.85) return <span className="tag tag--success">{pct}%</span>
  if (score >= 0.75) return <span className="tag tag--warning">{pct}%</span>
  return <span className="tag tag--danger">{pct}%</span>
}

function SeverityTag({ severity }) {
  const map = { critical: 'danger', high: 'warning', medium: 'info', low: 'success' }
  return <span className={`tag tag--${map[severity] || 'info'}`}>{severity}</span>
}

function RoleTag({ role }) {
  const map = {
    decision_maker: 'info',
    champion: 'success',
    influencer: 'purple',
    blocker: 'danger',
  }
  const label = role?.replace(/_/g, ' ') || 'unknown'
  return <span className={`tag tag--${map[role] || 'info'}`}>{label}</span>
}

function StatusTag({ status }) {
  if (status === 'addressed') return <span className="tag tag--success">Addressed</span>
  if (status === 'unresolved') return <span className="tag tag--danger">Unresolved</span>
  return <span className="tag tag--warning">Raised</span>
}

function dotClass(severity) {
  if (severity === 'critical') return 'intel-item__dot--danger'
  if (severity === 'high') return 'intel-item__dot--warning'
  return ''
}

export default function DashboardPage({
  data, runs = [], page = 'dashboard',
  onBack, onNewAnalysis, onPreviousRuns, onLastResult, onReviewQueue, onRunClick,
  hasLastResult, reviewCount,
}) {
  const [showJson, setShowJson] = useState(false)
  if (!data) return null

  const intel = data.intel || {}
  const meta = intel.metadata || {}
  const bant = intel.bant || {}
  const painPoints = intel.pain_points || []
  const stakeholders = intel.stakeholders || []
  const objections = intel.objections || []
  const nextSteps = intel.next_steps || []
  const compIntel = intel.competitive_intel || {}
  const flags = data.flags || []
  const humanReview = data.human_review || {}
  const summary = data.deal_summary || ''
  const email = data.email_draft || ''
  const transcript = data.transcript || ''

  // Avg BANT confidence
  const bantKeys = ['budget', 'authority', 'need', 'timeline']
  const bantScores = bantKeys.map(k => bant[k]?.confidence || 0)
  const avgConf = bantScores.reduce((a, b) => a + b, 0) / bantScores.length

  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        runsCount={runs.length}
        onNewAnalysis={onNewAnalysis || onBack}
        onPreviousRuns={onPreviousRuns || onBack}
        onLastResult={onLastResult}
        onReviewQueue={onReviewQueue}
        reviewCount={reviewCount}
        hasLastResult={hasLastResult}
      />

      {/* Topbar */}
      <header className="topbar">
        <div className="topbar__org-chip">
          <div className="topbar__org-mark">R</div>
          <div className="topbar__org-meta">
            <div className="topbar__org-name">RAAPID INC</div>
            <div className="topbar__org-tag">GTM Intelligence</div>
          </div>
        </div>
      </header>

      {/* Main */}
      <main className="app-main">
        {/* Back */}
        <button className="back-btn" onClick={onBack}>
          <ArrowLeft size={14} />
          {page === 'run-detail' ? 'Back to Previous Runs' : 'Back to Upload'}
        </button>

        {/* Page header */}
        <div className="page-header">
          <div>
            <h1 className="page-header__title">{meta.prospect_company || 'Call Analysis'}</h1>
            <p className="page-header__meta">
              {meta.call_date && `${meta.call_date}  ·  `}
              {meta.duration_minutes && `${meta.duration_minutes} min  ·  `}
              Run {data.run_meta?.run_id || '—'}
            </p>
          </div>
          <div className="page-header__actions">
            {humanReview.outcome === 'auto_approved' && (
              <span className="tag tag--success" style={{ height: 'auto', padding: '6px 12px', fontSize: '12px' }}>
                <CheckCircle size={12} style={{ marginRight: 4, display: 'inline' }} />
                Auto Approved
              </span>
            )}
            {humanReview.outcome === 'pending_review' && (
              <a href="#human-review" className="btn btn--warning btn--sm" style={{ textDecoration: 'none' }}>
                <AlertTriangle size={14} />
                Human Review Required
              </a>
            )}
            {humanReview.outcome === 'rejected' && (
              <span className="tag tag--danger" style={{ height: 'auto', padding: '6px 12px', fontSize: '12px' }}>
                <XCircle size={12} style={{ marginRight: 4, display: 'inline' }} />
                Auto Rejected
              </span>
            )}
            {humanReview.outcome === 'human_approved' && (
              <span className="tag tag--success" style={{ height: 'auto', padding: '6px 12px', fontSize: '12px' }}>
                <CheckCircle size={12} style={{ marginRight: 4, display: 'inline' }} />
                Approved after Review
              </span>
            )}
            {humanReview.outcome === 'human_rejected' && (
              <span className="tag tag--danger" style={{ height: 'auto', padding: '6px 12px', fontSize: '12px' }}>
                <XCircle size={12} style={{ marginRight: 4, display: 'inline' }} />
                Rejected after Review
              </span>
            )}
            <button className="btn btn--secondary btn--sm" onClick={() => setShowJson(true)}>
              <Code2 size={14} /> View JSON
            </button>
          </div>
        </div>

        {/* Confidence summary bar */}
        <div className="conf-summary">
          <span className="conf-summary__label">Overall Confidence</span>
          <span className="conf-summary__score">{Math.round(avgConf * 100)}%</span>
          <div className="conf-summary__bar">
            <div
              className={`conf-summary__bar-fill conf-bar__fill--${confClass(avgConf)}`}
              style={{ width: `${Math.round(avgConf * 100)}%` }}
            />
          </div>
          <ConfBadge score={avgConf} />
        </div>

        {/* Grid: Pain Points + Stakeholders */}
        <div className="dashboard-grid" style={{ marginBottom: 'var(--space-6)' }}>

          {/* Pain Points */}
          <div className="intel-card">
            <div className="intel-card__header">
              <div className="intel-card__header-left">
                <div className="intel-card__icon"><AlertTriangle size={14} /></div>
                <p className="intel-card__title">Pain Points</p>
              </div>
              <span className="tag tag--danger">{painPoints.length}</span>
            </div>
            <div className="intel-card__body">
              {painPoints.map((p, i) => (
                <div key={i} className="intel-item">
                  <span className={`intel-item__dot ${dotClass(p.severity)}`} />
                  <div className="intel-item__content">
                    <p className="intel-item__text">{p.description}</p>
                    <div className="intel-item__tags">
                      <SeverityTag severity={p.severity} />
                      <ConfBadge score={p.confidence} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Stakeholders */}
          <div className="intel-card">
            <div className="intel-card__header">
              <div className="intel-card__header-left">
                <div className="intel-card__icon"><Users size={14} /></div>
                <p className="intel-card__title">Stakeholders</p>
              </div>
              <span className="tag tag--info">{stakeholders.length}</span>
            </div>
            <div className="intel-card__body">
              {stakeholders.map((s, i) => (
                <div key={i} className="stakeholder-item">
                  <div className="stakeholder-avatar">{getInitials(s.name)}</div>
                  <div className="stakeholder-info">
                    <p className="stakeholder-name">{s.name}</p>
                    <p className="stakeholder-title">{s.title}</p>
                  </div>
                  <RoleTag role={s.role_in_deal} />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* BANT — full width */}
        <div className="intel-card span-full" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="intel-card__header">
            <div className="intel-card__header-left">
              <div className="intel-card__icon"><TrendingUp size={14} /></div>
              <p className="intel-card__title">BANT</p>
            </div>
            <span className="t-caption" style={{ color: 'var(--color-text-muted)' }}>
              Budget · Authority · Need · Timeline
            </span>
          </div>
          <div className="bant-grid">
            {bantKeys.map(k => {
              const field = bant[k] || {}
              const cls = confClass(field.confidence || 0)
              return (
                <div key={k} className="bant-field">
                  <div className="bant-field__label">
                    <span>{k.charAt(0).toUpperCase() + k.slice(1)}</span>
                    <ConfBadge score={field.confidence || 0} />
                  </div>
                  <p className={`bant-field__value ${!field.value ? 'is-null' : ''}`}>
                    {field.value || 'Not identified'}
                  </p>
                  <div className="conf-bar">
                    <div
                      className={`conf-bar__fill conf-bar__fill--${cls}`}
                      style={{ width: `${Math.round((field.confidence || 0) * 100)}%` }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Grid: Objections + Next Steps */}
        <div className="dashboard-grid" style={{ marginBottom: 'var(--space-6)' }}>

          {/* Objections */}
          <div className="intel-card">
            <div className="intel-card__header">
              <div className="intel-card__header-left">
                <div className="intel-card__icon"><ShieldAlert size={14} /></div>
                <p className="intel-card__title">Objections</p>
              </div>
              <span className="tag tag--warning">{objections.length}</span>
            </div>
            <div className="intel-card__body">
              {objections.map((o, i) => (
                <div key={i} className="intel-item">
                  <span className={`intel-item__dot ${o.status === 'unresolved' ? 'intel-item__dot--danger' : o.status === 'addressed' ? 'intel-item__dot--success' : 'intel-item__dot--warning'}`} />
                  <div className="intel-item__content">
                    <p className="intel-item__text">{o.description}</p>
                    <div className="intel-item__tags">
                      <StatusTag status={o.status} />
                      <ConfBadge score={o.confidence} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Next Steps */}
          <div className="intel-card">
            <div className="intel-card__header">
              <div className="intel-card__header-left">
                <div className="intel-card__icon"><ArrowRight size={14} /></div>
                <p className="intel-card__title">Next Steps</p>
              </div>
              <span className="tag tag--info">{nextSteps.length}</span>
            </div>
            <div className="intel-card__body">
              {nextSteps.map((ns, i) => (
                <div key={i} className="next-step-item">
                  <div className="next-step-num">{i + 1}</div>
                  <div className="next-step-content">
                    <p className="next-step-action">{ns.action}</p>
                    <div className="next-step-meta">
                      {ns.owner && (
                        <span className="next-step-owner">
                          <User size={11} /> {ns.owner}
                        </span>
                      )}
                      {ns.deadline && (
                        <span className="next-step-deadline">
                          <Calendar size={11} /> {ns.deadline}
                        </span>
                      )}
                      <ConfBadge score={ns.confidence} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Competitive Intel */}
        {(compIntel.current_vendor || compIntel.contract_renewal) && (
          <div className="competitive-strip span-full" style={{ marginBottom: 'var(--space-6)' }}>
            <Building2 size={16} />
            <span>
              <strong>Competitive:</strong>{' '}
              Current vendor is <strong>{compIntel.current_vendor}</strong>
              {compIntel.contract_renewal && ` — contract up for renewal ${compIntel.contract_renewal}`}.
              {' '}Natural displacement window.
            </span>
            <ConfBadge score={compIntel.confidence} />
          </div>
        )}

        {/* Deal Summary + Email */}
        <div className="dashboard-grid" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="intel-card">
            <div className="intel-card__header">
              <div className="intel-card__header-left">
                <div className="intel-card__icon"><FileText size={14} /></div>
                <p className="intel-card__title">Deal Summary</p>
              </div>
              <span className="tag tag--info">CRM-ready</span>
            </div>
            <div className="intel-card__body">
              <div className="text-panel">{summary}</div>
            </div>
          </div>

          <div className="intel-card">
            <div className="intel-card__header">
              <div className="intel-card__header-left">
                <div className="intel-card__icon"><Mail size={14} /></div>
                <p className="intel-card__title">Follow-up Email Draft</p>
              </div>
              <span className="tag tag--warning">Pending AE send</span>
            </div>
            <div className="intel-card__body">
              <div className="text-panel">{email}</div>
            </div>
          </div>
        </div>

        {/* Transcript */}
        {transcript && (
          <div className="intel-card span-full" style={{ marginBottom: 'var(--space-8)' }}>
            <div className="intel-card__header">
              <div className="intel-card__header-left">
                <div className="intel-card__icon"><Mic size={14} /></div>
                <p className="intel-card__title">Transcript</p>
              </div>
              <span className="t-caption" style={{ color: 'var(--color-text-muted)' }}>
                {transcript.split(' ').length} words
              </span>
            </div>
            <div className="intel-card__body">
              <div className="transcript-panel">{transcript}</div>
            </div>
          </div>
        )}

        {/* Human review panel — 3-tier confidence gate */}
        {flags.length > 0 && (
          <div id="human-review"><HumanReviewPanel
            flags={flags}
            runId={data.run_meta?.run_id}
            onApproved={() => {}}
          /></div>
        )}
      </main>

      {showJson && <JsonModal data={data} onClose={() => setShowJson(false)} />}
    </div>
  )
}
