import { useState, useEffect, useRef } from 'react'
import UploadPage from './pages/UploadPage.jsx'
import RunsPage from './pages/RunsPage.jsx'
import ReviewPage from './pages/ReviewPage.jsx'
import DashboardPage from './pages/DashboardPage.jsx'

const API = 'http://localhost:8000'

/**
 * page values:
 *   'upload'     — landing / upload page
 *   'runs'       — previous runs list
 *   'run-detail' — individual run from runs list (sidebar: Previous Runs active)
 *   'dashboard'  — latest analysis result  (sidebar: Last Result active)
 */
export default function App() {
  const [page, setPage]           = useState('upload')
  const [activeResult, setResult] = useState(null)   // run data currently displayed
  const [lastResult, setLast]     = useState(null)   // most recent from upload flow
  const [runs, setRuns]           = useState([])
  const runsRef                   = useRef(null)

  useEffect(() => {
    fetch(`${API}/api/runs`).then(r => r.json()).then(setRuns).catch(() => {})
  }, [])

  function refreshRuns() {
    fetch(`${API}/api/runs`).then(r => r.json()).then(setRuns).catch(() => {})
  }

  // ── Navigation helpers ───────────────────────────────────────────────────

  function goUpload() { setPage('upload') }

  function goRuns() { setPage('runs'); refreshRuns() }

  function goReview() { setPage('review'); refreshRuns() }

  function goLastResult() {
    if (lastResult) { setResult(lastResult); setPage('dashboard') }
  }

  // Run clicked from the Upload page's mini-table → open in dashboard context
  function openRunFromUpload(runId) {
    fetch(`${API}/api/runs/${runId}`)
      .then(r => r.json())
      .then(data => { setResult(data); setPage('dashboard') })
      .catch(() => {})
  }

  // Run clicked from the Runs page → open in run-detail context
  function openRunFromList(runId) {
    fetch(`${API}/api/runs/${runId}`)
      .then(r => r.json())
      .then(data => { setResult(data); setPage('run-detail') })
      .catch(() => {})
  }

  // New analysis completed
  function handleComplete(data) {
    setResult(data)
    setLast(data)
    setPage('dashboard')
    refreshRuns()
  }

  // Back button inside DashboardPage
  function handleBack() {
    if (page === 'run-detail') setPage('runs')
    else goUpload()
  }

  // ── Render ───────────────────────────────────────────────────────────────

  const reviewCount = runs.filter(r => r.outcome === 'pending_review').length

  const sharedProps = {
    runs,
    onNewAnalysis:   goUpload,
    onPreviousRuns:  goRuns,
    onLastResult:    goLastResult,
    onReviewQueue:   goReview,
    hasLastResult:   !!lastResult,
    reviewCount,
  }

  if (page === 'upload') {
    return (
      <UploadPage
        {...sharedProps}
        api={API}
        runsRef={runsRef}
        onComplete={handleComplete}
        onRunClick={openRunFromUpload}
      />
    )
  }

  if (page === 'runs') {
    return (
      <RunsPage
        {...sharedProps}
        api={API}
        page="runs"
        onRunClick={openRunFromList}
      />
    )
  }

  if (page === 'review') {
    return (
      <ReviewPage
        {...sharedProps}
        api={API}
        page="review"
        onRunClick={openRunFromList}
      />
    )
  }

  // 'dashboard' or 'run-detail'
  return (
    <DashboardPage
      {...sharedProps}
      data={activeResult}
      page={page}
      onBack={handleBack}
      onRunClick={openRunFromList}
    />
  )
}
