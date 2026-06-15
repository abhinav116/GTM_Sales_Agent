import { useState, useEffect } from 'react'
import { AlertTriangle, ChevronRight, Building2, Calendar, BarChart2, RefreshCw } from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'

function ConfBadge({ conf }) {
  const pct = Math.round((conf || 0) * 100)
  if (conf >= 0.85) return <span className="tag tag--success">{pct}%</span>
  if (conf >= 0.75) return <span className="tag tag--warning">{pct}%</span>
  return <span className="tag tag--danger">{pct}%</span>
}

function formatDateTime(iso) {
  if (!iso) return { date: '—', time: '' }
  try {
    const d = new Date(iso)
    return {
      date: d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }),
      time: d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true }),
    }
  } catch { return { date: iso, time: '' } }
}

function stringToColor(str) {
  if (!str) return '#2563EB'
  const colors = ['#2563EB', '#15814C', '#5B2A9D', '#0B7B8A', '#C7660A', '#D62E78', '#01346B', '#8A6D2A']
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

export default function ReviewPage({
  api, runs, page,
  onNewAnalysis, onPreviousRuns, onLastResult, onReviewQueue,
  hasLastResult, onRunClick,
}) {
  const [loading, setLoading]     = useState(false)
  const [localRuns, setLocalRuns] = useState(runs)

  useEffect(() => { setLocalRuns(runs) }, [runs])

  async function refresh() {
    setLoading(true)
    try {
      const data = await fetch(`${api}/api/runs`).then(r => r.json())
      setLocalRuns(data)
    } catch {}
    setLoading(false)
  }

  const pending = localRuns
    .filter(r => r.outcome === 'pending_review')
    .sort((a, b) => new Date(b.started_at || 0) - new Date(a.started_at || 0))

  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        runsCount={localRuns.length}
        onNewAnalysis={onNewAnalysis}
        onPreviousRuns={onPreviousRuns}
        onLastResult={onLastResult}
        onReviewQueue={onReviewQueue}
        hasLastResult={hasLastResult}
        reviewCount={pending.length}
      />

      <header className="topbar">
        <div className="topbar__org-chip">
          <div className="topbar__org-mark">R</div>
          <div className="topbar__org-meta">
            <div className="topbar__org-name">RAAPID INC</div>
            <div className="topbar__org-tag">GTM Intelligence</div>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="page-header">
          <div>
            <h1 className="page-header__title">Review Queue</h1>
            <p className="page-header__meta">Runs with confidence 50–80% that need AE sign-off before pushing to CRM.</p>
          </div>
          <div className="page-header__actions">
            <button className="btn btn--secondary btn--sm" onClick={refresh} disabled={loading}>
              <RefreshCw size={14} style={{ animation: loading ? 'spin 0.8s linear infinite' : 'none' }} />
              Refresh
            </button>
          </div>
        </div>

        {pending.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon"><AlertTriangle size={32} /></div>
            <h3 className="empty-state__title">No runs pending review</h3>
            <p className="empty-state__body">All analyzed runs have been auto-approved or rejected. Nothing needs your attention right now.</p>
          </div>
        ) : (
          <div className="table-card">
            <div className="filter-bar" style={{ borderBottom: 'var(--border-1)', paddingBottom: 'var(--space-5)' }}>
              <span className="t-overline" style={{ color: 'var(--color-text-muted)' }}>
                {pending.length} run{pending.length !== 1 ? 's' : ''} awaiting review
              </span>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Call Date</th>
                  <th>Analyzed</th>
                  <th>Pain Points</th>
                  <th>Input</th>
                  <th>Confidence</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {pending.map(r => (
                  <tr
                    key={r.run_id}
                    className="run-row-clickable"
                    onClick={() => onRunClick(r.run_id)}
                  >
                    <td>
                      <div className="table-cell-primary">
                        <div
                          className="table-cell-primary__logo"
                          style={{ background: stringToColor(r.company) }}
                        >
                          {r.company?.[0]?.toUpperCase() || 'U'}
                        </div>
                        <div>
                          <p className="table-cell-primary__name">{r.company || 'Unknown'}</p>
                          <p className="table-cell-primary__sub" style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                            {r.run_id}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                        <Calendar size={13} style={{ color: 'var(--color-text-muted)' }} />
                        {r.call_date || '—'}
                      </span>
                    </td>
                    <td>
                      {(() => { const { date, time } = formatDateTime(r.started_at); return (
                        <div>
                          <div style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-default)' }}>{date}</div>
                          {time && <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 1 }}>{time}</div>}
                        </div>
                      )})()}
                    </td>
                    <td>
                      <span style={{ fontWeight: 'var(--weight-semibold)', color: 'var(--color-text-strong)' }}>
                        {r.pain_points_count ?? '—'}
                      </span>
                    </td>
                    <td>
                      <span className="tag tag--info" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        {r.input_type || 'audio'}
                      </span>
                    </td>
                    <td><ConfBadge conf={r.confidence} /></td>
                    <td>
                      <ChevronRight size={16} style={{ color: 'var(--color-text-muted)' }} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </main>
    </div>
  )
}
