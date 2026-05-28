import { useState, useRef, useCallback } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'
const REQUEST_TIMEOUT_MS = 20000

// ─────────────────────────────────────────────
// Tab config
// ─────────────────────────────────────────────
const TABS = [
  {
    id: 'text',
    label: 'Text',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    ),
    accent: '#6EE7B7',
  },
  {
    id: 'image',
    label: 'Image',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <circle cx="8.5" cy="8.5" r="1.5" />
        <polyline points="21 15 16 10 5 21" />
      </svg>
    ),
    accent: '#93C5FD',
  },
  {
    id: 'audio',
    label: 'Audio',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M9 18V5l12-2v13" />
        <circle cx="6" cy="18" r="3" />
        <circle cx="18" cy="16" r="3" />
      </svg>
    ),
    accent: '#F9A8D4',
  },
  {
    id: 'video',
    label: 'Video',
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="23 7 16 12 23 17 23 7" />
        <rect x="1" y="5" width="15" height="14" rx="2" />
      </svg>
    ),
    accent: '#FCD34D',
  },
]

const ACCEPT = {
  image: 'image/*',
  audio: 'audio/*',
  video: 'video/*',
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

/** Creates a fetch with a hard timeout via AbortController. Returns { data, error }. */
async function fetchWithTimeout(url, options, timeoutMs = REQUEST_TIMEOUT_MS) {
  const controller = new AbortController()
  const timerId = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, { ...options, signal: controller.signal })
    clearTimeout(timerId)
    if (!res.ok) throw new Error(`Server responded with ${res.status}`)
    const data = await res.json()
    return { data, error: null }
  } catch (err) {
    clearTimeout(timerId)
    if (err.name === 'AbortError') {
      return { data: null, error: 'Request timed out — the server is taking too long. Please try again.' }
    }
    if (!navigator.onLine) {
      return { data: null, error: 'No internet connection detected. Please check your network.' }
    }
    return { data: null, error: err.message || 'Something went wrong. Please retry.' }
  }
}

// ─────────────────────────────────────────────
// Spinner
// ─────────────────────────────────────────────
function Spinner() {
  return (
    <div className="spinner-wrap" aria-label="Loading">
      <div className="spinner" />
    </div>
  )
}

// ─────────────────────────────────────────────
// DropZone
// ─────────────────────────────────────────────
function DropZone({ tabId, file, onFile, accent }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragging(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) onFile(dropped)
  }, [onFile])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => setDragging(false), [])

  const label = tabId === 'image' ? 'image' : tabId === 'audio' ? 'audio file' : 'video file'
  const formats =
    tabId === 'image'
      ? 'PNG, JPG, WEBP, GIF'
      : tabId === 'audio'
        ? 'MP3, WAV, M4A, OGG'
        : 'MP4, MOV, WEBM, AVI'

  return (
    <div
      className={`dropzone${dragging ? ' dropzone--dragging' : ''}${file ? ' dropzone--filled' : ''}`}
      style={{ '--tab-accent': accent }}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onClick={() => inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      aria-label={`Upload ${label}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT[tabId]}
        className="dropzone__input"
        onChange={(e) => e.target.files[0] && onFile(e.target.files[0])}
      />
      {file ? (
        <div className="dropzone__preview">
          <div className="dropzone__file-icon">
            {tabId === 'image' ? (
              <img
                src={URL.createObjectURL(file)}
                alt="Preview"
                className="dropzone__img-preview"
              />
            ) : (
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                style={{ color: accent }}
              >
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
            )}
          </div>
          <div className="dropzone__meta">
            <span className="dropzone__filename">{file.name}</span>
            <span className="dropzone__filesize">
              {(file.size / 1024).toFixed(1)} KB — click to change
            </span>
          </div>
        </div>
      ) : (
        <div className="dropzone__empty">
          <div className="dropzone__upload-icon" style={{ color: accent }}>
            <svg
              width="28"
              height="28"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="16 16 12 12 8 16" />
              <line x1="12" y1="12" x2="12" y2="21" />
              <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
            </svg>
          </div>
          <p className="dropzone__title">Drop your {label} here</p>
          <p className="dropzone__subtitle">
            or <span style={{ color: accent }}>click to browse</span>
          </p>
          <p className="dropzone__formats">{formats}</p>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────
// ResponseBox
// ─────────────────────────────────────────────
function ResponseBox({ response, loading, accent }) {
  const [copied, setCopied] = useState(false)

  if (!response && !loading) return null

  const handleCopy = () => {
    navigator.clipboard.writeText(response).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div className="response-box" style={{ '--tab-accent': accent }}>
      <div className="response-box__header">
        <span className="response-box__label">Response</span>
        {response && (
          <button
            className="response-box__copy"
            onClick={handleCopy}
            title="Copy to clipboard"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <rect x="9" y="9" width="13" height="13" rx="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        )}
      </div>
      <div className="response-box__body">
        {loading ? <Spinner /> : <p className="response-box__text">{response}</p>}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// TextPanel
// ─────────────────────────────────────────────
function TextPanel({ accent }) {
  const [prompt, setPrompt] = useState('')
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!prompt.trim()) return

    setLoading(true)
    setError('')
    setResponse('')

    try {
      const controller = new AbortController()
      const timerId = setTimeout(() => controller.abort(), 20000)

      let res
      try {
        const formData = new FormData()
        formData.append('prompt', prompt.trim())

        res = await fetch(`${API_BASE}/text`, {
          method: 'POST',
          body: formData,
          // No Content-Type header — browser sets multipart boundary automatically
          signal: controller.signal,
        })
      } finally {
        clearTimeout(timerId)
      }

      if (!res.ok) {
        throw new Error(`Server error ${res.status} — please retry.`)
      }

      const data = await res.json()

      // Use || not ?? so empty string "" also triggers the fallback
      const text = (data && data.response) || ''
      if (text) {
        setResponse(text)
      } else {
        setError('AI returned an empty response. Try rephrasing your prompt.')
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('Request timed out after 20 s — server is slow. Please retry.')
      } else if (!navigator.onLine) {
        setError('No internet connection. Please check your network.')
      } else {
        setError(err.message || 'Network error. Please retry.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="panel">
      <form onSubmit={handleSubmit} className="panel__form">
        <label className="field-label">Your prompt</label>
        <textarea
          className="textarea"
          style={{ '--tab-accent': accent }}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Ask anything… describe a scene, request an analysis, start a conversation."
          rows={5}
          disabled={loading}
        />
        <button
          type="submit"
          className="btn-primary"
          style={{ '--tab-accent': accent }}
          disabled={loading || !prompt.trim()}
        >
          {loading ? (
            <Spinner />
          ) : (
            <>
              Send
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </>
          )}
        </button>
      </form>
      {error && <p className="error-msg">{error}</p>}
      <ResponseBox response={response} loading={loading} accent={accent} />
    </div>
  )
}

// ─────────────────────────────────────────────
// FilePanel  (image / audio / video)
// ─────────────────────────────────────────────
function FilePanel({ tabId, accent }) {
  const [file, setFile] = useState(null)
  const [response, setResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return

    setLoading(true)
    setError('')
    setResponse('')

    const fd = new FormData()
    fd.append('file', file)

    const { data, error: fetchError } = await fetchWithTimeout(
      `${API_BASE}/${tabId}`,
      { method: 'POST', body: fd }
    )

    if (fetchError) {
      setError(fetchError)
    } else {
      setResponse(data.response ?? 'No response returned from server.')
    }

    setLoading(false)
  }

  const actionLabel =
    tabId === 'image'
      ? 'Analyse Image'
      : tabId === 'audio'
        ? 'Transcribe Audio'
        : 'Analyse Video'

  return (
    <div className="panel">
      <form onSubmit={handleSubmit} className="panel__form">
        <DropZone tabId={tabId} file={file} onFile={setFile} accent={accent} />
        <button
          type="submit"
          className="btn-primary"
          style={{ '--tab-accent': accent }}
          disabled={loading || !file}
        >
          {loading ? (
            <Spinner />
          ) : (
            <>
              {actionLabel}
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
            </>
          )}
        </button>
      </form>
      {error && <p className="error-msg">{error}</p>}
      <ResponseBox response={response} loading={loading} accent={accent} />
    </div>
  )
}

// ─────────────────────────────────────────────
// App  (root)
// ─────────────────────────────────────────────
export default function App() {
  const [activeTab, setActiveTab] = useState('text')
  const tab = TABS.find((t) => t.id === activeTab)

  return (
    <div className="app">
      <div className="bg-grid" aria-hidden="true" />

      <header className="header">
        <div className="header__badge">
          <span className="header__dot" style={{ background: tab.accent }} />
          Multimodal AI
        </div>
        <h1 className="header__title">TIAV Studio</h1>
        <p className="header__sub">
          Interact with AI through <em>text</em>, <em>images</em>, <em>audio</em> and <em>video</em>
        </p>
      </header>

      <main className="main">
        <div className="card">
          <nav className="tabs" role="tablist" aria-label="Modality">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={activeTab === t.id}
                className={`tab${activeTab === t.id ? ' tab--active' : ''}`}
                style={{ '--tab-accent': t.accent }}
                onClick={() => setActiveTab(t.id)}
              >
                <span className="tab__icon">{t.icon}</span>
                <span className="tab__label">{t.label}</span>
              </button>
            ))}
            <div
              className="tab-indicator"
              style={{
                '--indicator-left': `${TABS.findIndex((t) => t.id === activeTab) * 25}%`,
                '--indicator-color': tab.accent,
              }}
            />
          </nav>

          <div className="card__body">
            {activeTab === 'text' && <TextPanel accent={tab.accent} />}
            {activeTab === 'image' && <FilePanel key="image" tabId="image" accent={tab.accent} />}
            {activeTab === 'audio' && <FilePanel key="audio" tabId="audio" accent={tab.accent} />}
            {activeTab === 'video' && <FilePanel key="video" tabId="video" accent={tab.accent} />}
          </div>
        </div>
      </main>

      <footer className="footer">
        <span>TIAV Multimodal Demo</span>
        <span className="footer__sep">·</span>
        <span>FastAPI + React</span>
      </footer>
    </div>
  )
}
