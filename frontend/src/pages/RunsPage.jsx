import { useState, useEffect } from 'react'
import {
  History, ChevronRight, TrendingUp, AlertTriangle,
  CheckCircle, Building2, Calendar, BarChart2, Search, RefreshCw
} from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'

function ConfBadge({ conf }) {
  const pct = Math.round((conf || 0) * 100)
  if (conf >= 0.85) return <span className="tag tag--success">{pct}%</span>
  if (conf >= 0.75) return <span className="tag tag--warning">{pct}%</span>
  return <span className="tag tag--danger">{pct}%</span>
}

function StatCard({ icon, label, value, sub }) {
  return (
    <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-5)', padding: 'var(--space-6) var(--space-7)' }}>
      <div style={{
        width: 40, height: 40, borderRadius: 'var(--radius-md)',
        background: 'var(--color-primary-subtle)', color: 'var(--color-primary)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 22, fontWeight: 'var(--weight-semibold)', color: 'var(--color-text-strong)', lineHeight: 1.2 }}>
          {value}
        </div>
        <div style={{ fontSize: 'var(--text-caption)', color: 'var(--color-text-muted)', marginTop: 2 }}>
          {label}
          {sub && <span style={{ marginLeft: 6, color: 'var(--color-text-placeholder)' }}>{sub}</span>}
        </div>
      </div>
    </div>
  )
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

export default function RunsPage({
  api, runs, page,
  onNewAnalysis, onPreviousRuns, onLastResult, onReviewQueue, reviewCount,
  hasLastResult,
  onRunClick,
}) {
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
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

  const filtered = localRuns
    .filter(r =>
      !search || r.company?.toLowerCase().includes(search.toLowerCase()) ||
      r.run_id?.toLowerCase().includes(search.toLowerCase())
    )
    .sort((a, b) => new Date(b.started_at || 0) - new Date(a.started_at || 0))

  // Stats
  const total = localRuns.length
  const avgConf = total
    ? Math.round(localRuns.reduce((a, r) => a + (r.confidence || 0), 0) / total * 100)
    : 0
  const flagged = localRuns.filter(r => r.flags_count > 0).length
  const companies = [...new Set(localRuns.map(r => r.company).filter(Boolean))].length

  return (
    <div className="app-shell">
      <Sidebar
        page={page}
        runsCount={localRuns.length}
        onNewAnalysis={onNewAnalysis}
        onPreviousRuns={onPreviousRuns}
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

        {/* Page header */}
        <div className="page-header">
          <div>
            <h1 className="page-header__title">Previous Runs</h1>
            <p className="page-header__meta">All sales call analyses. Click any run to view the full intelligence report.</p>
          </div>
          <div className="page-header__actions">
            <button className="btn btn--secondary btn--sm" onClick={refresh} disabled={loading}>
              <RefreshCw size={14} style={{ animation: loading ? 'spin 0.8s linear infinite' : 'none' }} />
              Refresh
            </button>
            <button className="btn btn--primary btn--sm" onClick={onNewAnalysis}>
              New Analysis
            </button>
          </div>
        </div>

        {/* Stats strip */}
        {total > 0 && (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(4, 1fr)',
            gap: 'var(--space-5)',
            marginBottom: 'var(--space-7)',
          }}>
            <StatCard icon={<History size={18} />} label="Total Runs" value={total} />
            <StatCard icon={<Building2 size={18} />} label="Companies" value={companies} />
            <StatCard icon={<BarChart2 size={18} />} label="Avg Confidence" value={`${avgConf}%`} />
            <StatCard icon={<AlertTriangle size={18} />} label="Runs Flagged" value={flagged} sub={total > 0 ? `of ${total}` : ''} />
          </div>
        )}

        {/* Search */}
        {total > 0 && (
          <div style={{ marginBottom: 'var(--space-5)' }}>
            <div className="input--with-trailing" style={{ maxWidth: 320 }}>
              <input
                className="input"
                placeholder="Search by company or run ID..."
                value={search}
                onChange={e => setSearch(e.target.value)}
              />
              <button className="input__trailing-btn">
                <Search size={14} />
              </button>
            </div>
          </div>
        )}

        {/* Runs table */}
        {filtered.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__icon"><History size={32} /></div>
            <h3 className="empty-state__title">
              {search ? 'No matching runs' : 'No runs yet'}
            </h3>
            <p className="empty-state__body">
              {search
                ? `No runs found for "${search}". Try a different search.`
                : 'Upload and analyze your first sales call to see results here.'}
            </p>
            {!search && (
              <button className="btn btn--primary" onClick={onNewAnalysis}>
                Start First Analysis
              </button>
            )}
          </div>
        ) : (
          <div className="table-card">
            <div className="filter-bar" style={{ borderBottom: 'var(--border-1)', paddingBottom: 'var(--space-5)' }}>
              <span className="t-overline" style={{ color: 'var(--color-text-muted)' }}>
                {filtered.length} run{filtered.length !== 1 ? 's' : ''}
                {search && ` matching "${search}"`}
              </span>
            </div>
            <table className="table">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Call Date</th>
                  <th>Analyzed</th>
                  <th>Pain Points</th>
                  <th>Status</th>
                  <th>Input</th>
                  <th>Confidence</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map(r => (
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
                      {r.outcome === 'auto_approved'
                        ? <span className="tag tag--success"><CheckCircle size={11} style={{ display: 'inline', marginRight: 3 }} />Auto Approved</span>
                        : r.outcome === 'rejected'
                          ? <span className="tag tag--danger">Auto Rejected</span>
                          : r.outcome === 'pending_review'
                            ? <span className="tag tag--warning"><AlertTriangle size={11} style={{ display: 'inline', marginRight: 3 }} />Human Review Required</span>
                            : r.outcome === 'human_approved'
                              ? <span className="tag tag--success"><CheckCircle size={11} style={{ display: 'inline', marginRight: 3 }} />Approved after Review</span>
                              : r.outcome === 'human_rejected'
                                ? <span className="tag tag--danger">Rejected after Review</span>
                                : <span className="tag tag--success"><CheckCircle size={11} style={{ display: 'inline', marginRight: 3 }} />Auto Approved</span>
                      }
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

// Deterministic color from company name
function stringToColor(str) {
  if (!str) return '#2563EB'
  const colors = ['#2563EB', '#15814C', '#5B2A9D', '#0B7B8A', '#C7660A', '#D62E78', '#01346B', '#8A6D2A']
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}
