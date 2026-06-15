import { Mic, History, Info, LayoutDashboard, AlertTriangle } from 'lucide-react'

/**
 * page values:
 *   'upload'     → New Analysis active
 *   'runs'       → Previous Runs active
 *   'run-detail' → Previous Runs active (still inside runs context)
 *   'dashboard'  → Last Result active
 */
export default function Sidebar({
  page, runsCount, reviewCount,
  onNewAnalysis, onPreviousRuns, onLastResult, onReviewQueue,
  hasLastResult,
}) {
  const runsActive   = page === 'runs' || page === 'run-detail'
  const uploadActive = page === 'upload'
  const dashActive   = page === 'dashboard'
  const reviewActive = page === 'review'

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__brand-lockup">
          <div className="brand-mark">R</div>
          <div className="sidebar__brand-name">
            <span className="sidebar__brand-name-tag">RAAPID</span>
            <span className="sidebar__brand-name-main">Sales Intel</span>
          </div>
        </div>
      </div>

      <ul className="sidebar__nav">
        <li className="sidebar__group">Workspace</li>

        <li>
          <a
            className={`sidebar__item ${uploadActive ? 'is-active' : ''}`}
            href="#"
            onClick={e => { e.preventDefault(); onNewAnalysis() }}
          >
            <span className="sidebar__item-icon"><Mic size={18} /></span>
            <span className="sidebar__item-label">New Analysis</span>
          </a>
        </li>

        <li>
          <a
            className={`sidebar__item ${runsActive ? 'is-active' : ''}`}
            href="#"
            onClick={e => { e.preventDefault(); onPreviousRuns() }}
          >
            <span className="sidebar__item-icon"><History size={18} /></span>
            <span className="sidebar__item-label">Previous Runs</span>
            {runsCount > 0 && (
              <span className={`sidebar__item-badge ${runsActive ? '' : ''}`}>
                {runsCount}
              </span>
            )}
          </a>
        </li>

        {hasLastResult && (
          <li>
            <a
              className={`sidebar__item ${dashActive ? 'is-active' : ''}`}
              href="#"
              onClick={e => { e.preventDefault(); onLastResult?.() }}
            >
              <span className="sidebar__item-icon"><LayoutDashboard size={18} /></span>
              <span className="sidebar__item-label">Last Result</span>
            </a>
          </li>
        )}

        <li>
          <a
            className={`sidebar__item ${reviewActive ? 'is-active' : ''}`}
            href="#"
            onClick={e => { e.preventDefault(); onReviewQueue?.() }}
          >
            <span className="sidebar__item-icon"><AlertTriangle size={18} /></span>
            <span className="sidebar__item-label">Review Queue</span>
            {reviewCount > 0 && (
              <span className="sidebar__item-badge" style={{ background: 'var(--color-warning)', color: '#fff' }}>
                {reviewCount}
              </span>
            )}
          </a>
        </li>

        <li className="sidebar__group">Info</li>

        <li>
          <a className="sidebar__item" href="#" onClick={e => e.preventDefault()}>
            <span className="sidebar__item-icon"><Info size={18} /></span>
            <span className="sidebar__item-label">Architecture</span>
            <span className="sidebar__item-chip">v1</span>
          </a>
        </li>
      </ul>

      <div className="sidebar__profile">
        <div className="sidebar__profile-avatar">AM</div>
        <div className="sidebar__profile-meta">
          <div className="sidebar__profile-name">Abhinav Marda</div>
        </div>
      </div>
    </aside>
  )
}
