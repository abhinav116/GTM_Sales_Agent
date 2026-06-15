import { useState, useRef } from 'react'
import {
  Upload, FileAudio, FileText, X, Play, AlertTriangle,
} from 'lucide-react'
import Sidebar from '../components/Sidebar.jsx'

const PROCESSING_STEPS = [
  'Uploading file...',
  'Transcribing with Whisper AI...',
  'Extracting deal intelligence...',
  'Scoring confidence fields...',
  'Generating deal summary...',
  'Drafting follow-up email...',
  'Writing CRM payload...',
]

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function ConfBadge({ conf }) {
  if (conf >= 0.85) return <span className="tag tag--success">{Math.round(conf * 100)}%</span>
  if (conf >= 0.75) return <span className="tag tag--warning">{Math.round(conf * 100)}%</span>
  return <span className="tag tag--danger">{Math.round(conf * 100)}%</span>
}

function isTextFile(name) {
  return name?.toLowerCase().endsWith('.txt') || name?.toLowerCase().endsWith('.text')
}

export default function UploadPage({
  api,
  onComplete,
  onNewAnalysis, onPreviousRuns, onLastResult, onReviewQueue, hasLastResult, reviewCount,
}) {
  const [file, setFile] = useState(null)
  const [dragging, setDragging] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [stepIdx, setStepIdx] = useState(0)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)

  function handleFile(f) {
    setError(null)
    setFile(f)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  async function handleSubmit() {
    if (!file) return
    setProcessing(true)
    setStepIdx(0)
    setError(null)

    // Skip transcription step label for text files
    const steps = isTextFile(file.name)
      ? ['Reading transcript...', ...PROCESSING_STEPS.slice(2)]
      : PROCESSING_STEPS

    const interval = setInterval(() => {
      setStepIdx(prev => (prev < steps.length - 1 ? prev + 1 : prev))
    }, 1800)

    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${api}/api/analyze`, { method: 'POST', body: form })
      clearInterval(interval)
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Analysis failed')
      }
      setStepIdx(steps.length - 1)
      const data = await res.json()
      setTimeout(() => onComplete(data), 400)
    } catch (err) {
      clearInterval(interval)
      setProcessing(false)
      setError(err.message)
    }
  }

  // Determine processing step labels dynamically
  const activeSteps = file && isTextFile(file.name)
    ? ['Reading transcript...', ...PROCESSING_STEPS.slice(2)]
    : PROCESSING_STEPS

  return (
    <div className="app-shell">
      <Sidebar
        page="upload"
        runsCount={0}
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
        {/* Welcome banner */}
        <div className="welcome-banner" style={{ marginBottom: 'var(--space-8)' }}>
          <span className="welcome-banner__eyebrow">Sales Call Intelligence Agent</span>
          <h1 className="welcome-banner__heading">
            Upload a call recording.
            Get <span className="welcome-banner__name">deal intelligence</span> in seconds.
          </h1>
          
        </div>

        {/* Upload card */}
        <div className="upload-card">
          <h2 className="upload-card__title">Analyze Your Sales Call</h2>
          <p className="upload-card__lede">
            Supports audio recordings (.mp3, .wav, .m4a, .ogg) and plain text transcripts (.txt).
           
          </p>

          {/* Dropzone */}
          <div
            className="upload-dropzone"
            style={dragging ? { borderColor: 'var(--color-primary)', background: 'var(--color-primary-subtle)' } : {}}
            onClick={() => inputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
          >
            <div className="upload-dropzone__icon">
              <Upload size={20} />
            </div>
            <p className="upload-dropzone__primary">
              <strong>Click to upload</strong> or drag and drop
            </p>
            <p className="upload-dropzone__hint">MP3 · WAV · M4A · OGG · TXT</p>
            <input
              ref={inputRef}
              type="file"
              accept="audio/*,.txt,.text"
              style={{ display: 'none' }}
              onChange={e => e.target.files[0] && handleFile(e.target.files[0])}
            />
          </div>

          {/* File preview */}
          {file && (
            <div className="audio-preview">
              <div className="audio-preview__icon">
                {isTextFile(file.name) ? <FileText size={20} /> : <FileAudio size={20} />}
              </div>
              <div className="audio-preview__info">
                <p className="audio-preview__name">{file.name}</p>
                <p className="audio-preview__size">
                  {formatSize(file.size)}
                  {isTextFile(file.name) && ' · Text transcript · No transcription needed'}
                </p>
              </div>
              <button
                className="audio-preview__remove"
                onClick={e => { e.stopPropagation(); setFile(null) }}
              >
                <X size={16} />
              </button>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="alert alert--danger" style={{ marginTop: 'var(--space-5)' }}>
              <span className="alert__icon"><AlertTriangle size={16} /></span>
              <span><strong>Error:</strong> {error}</span>
            </div>
          )}

          {/* Submit */}
          <button
            className="btn btn--primary"
            style={{ width: '100%', marginTop: 'var(--space-6)' }}
            disabled={!file || processing}
            onClick={handleSubmit}
          >
            <Play size={16} />
            {processing ? 'Analyzing...' : 'Run Analysis'}
          </button>
        </div>

      </main>

      {/* Processing overlay */}
      {processing && (
        <div className="processing-overlay">
          <div className="processing-card">
            <div className="processing-card__icon">
              <div className="spinner" />
            </div>
            <h3 className="processing-card__title">Analyzing your call</h3>
            <p className="processing-card__sub">Running 9-step intelligence pipeline...</p>
            <div className="processing-steps">
              {activeSteps.map((step, i) => (
                <div
                  key={i}
                  className={`processing-step ${i < stepIdx ? 'is-done' : i === stepIdx ? 'is-active' : ''}`}
                >
                  <span className="processing-step__dot" />
                  {step}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
