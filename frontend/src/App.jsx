import { useState, useRef, useCallback, useEffect } from 'react'
import './App.css'

const API_BASE = 'http://127.0.0.1:8000'
const STREAM_TIMEOUT_MS = 60000  // 60 s hard ceiling for the full stream

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
// Shared fetch headers — bypasses ngrok interstitial
// ─────────────────────────────────────────────
const NGROK_HEADERS = {
  'ngrok-skip-browser-warning': 'true',
}

// ─────────────────────────────────────────────
// fetchWithTimeout  (used by FilePanel only)
// ─────────────────────────────────────────────
async function fetchWithTimeout(url, options, timeoutMs = 30000) {
  const controller = new AbortController()
  const timerId = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, {
      ...options,
      headers: { ...NGROK_HEADERS, ...(options.headers ?? {}) },
      signal: controller.signal,
    })
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
// Markdown Renderer (Custom & Lightweight)
// ─────────────────────────────────────────────
function renderInlineMarkdown(text) {
  if (!text) return ''
  let parts = [text]

  // 1. Parse bold (**text**)
  parts = parts.flatMap((part) => {
    if (typeof part !== 'string') return part
    const split = part.split(/\*\*([^*]+)\*\*/g)
    return split.map((s, idx) => (idx % 2 === 1 ? <strong key={idx}>{s}</strong> : s))
  })

  // 2. Parse links ([label](url))
  parts = parts.flatMap((part) => {
    if (typeof part !== 'string') return part
    const split = part.split(/\[([^\]]+)\]\(([^)]+)\)/g)
    const result = []
    let i = 0
    while (i < split.length) {
      if (i + 2 < split.length) {
        result.push(split[i])
        const label = split[i + 1]
        const url = split[i + 2]
        result.push(
          <a key={`link-${i}`} href={url} target="_blank" rel="noopener noreferrer">
            {label}
          </a>
        )
        i += 3
      } else {
        result.push(split[i])
        i++
      }
    }
    return result
  })

  // 3. Parse inline code (`code`)
  parts = parts.flatMap((part) => {
    if (typeof part !== 'string') return part
    const split = part.split(/`([^`]+)`/g)
    return split.map((s, idx) => (idx % 2 === 1 ? <code key={idx} className="inline-code">{s}</code> : s))
  })

  return parts
}

function renderMarkdown(text) {
  if (!text) return null
  const lines = text.split('\n')
  const elements = []
  let inCodeBlock = false
  let codeLanguage = ''
  let codeLines = []
  let inList = false
  let listType = null // 'ul' or 'ol'
  let listItems = []
  let key = 0

  const flushList = () => {
    if (listItems.length > 0) {
      const Tag = listType === 'ol' ? 'ol' : 'ul'
      elements.push(
        <Tag key={`list-${key++}`} className="markdown-list">
          {listItems.map((item, idx) => (
            <li key={idx}>{renderInlineMarkdown(item)}</li>
          ))}
        </Tag>
      )
      listItems = []
      inList = false
    }
  }

  const flushCodeBlock = () => {
    if (inCodeBlock) {
      const codeContent = codeLines.join('\n')
      elements.push(
        <div key={`code-${key++}`} className="markdown-code-block-container">
          <div className="markdown-code-block-header">
            <span>{codeLanguage || 'code'}</span>
            <button
              type="button"
              className="copy-code-btn"
              onClick={() => navigator.clipboard.writeText(codeContent)}
            >
              Copy
            </button>
          </div>
          <pre>
            <code className={`language-${codeLanguage}`}>{codeContent}</code>
          </pre>
        </div>
      )
      codeLines = []
      inCodeBlock = false
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]

    // Code Blocks
    if (line.trim().startsWith('```')) {
      if (inCodeBlock) {
        flushCodeBlock()
      } else {
        flushList()
        inCodeBlock = true
        codeLanguage = line.trim().slice(3).trim()
      }
      continue
    }

    if (inCodeBlock) {
      codeLines.push(line)
      continue
    }

    // Unordered List (- or *)
    const ulMatch = line.match(/^(\s*)([-*])\s+(.*)/)
    if (ulMatch) {
      if (inList && listType !== 'ul') {
        flushList()
      }
      inList = true
      listType = 'ul'
      listItems.push(ulMatch[3])
      continue
    }

    // Ordered List (1. 2.)
    const olMatch = line.match(/^(\s*)(\d+)\.\s+(.*)/)
    if (olMatch) {
      if (inList && listType !== 'ol') {
        flushList()
      }
      inList = true
      listType = 'ol'
      listItems.push(olMatch[3])
      continue
    }

    // Headers
    const headerMatch = line.match(/^(#{1,6})\s+(.*)/)
    if (headerMatch) {
      flushList()
      const level = headerMatch[1].length
      const title = headerMatch[2]
      const HeaderTag = `h${level}`
      elements.push(
        <HeaderTag key={`h-${key++}`} className={`markdown-h${level}`}>
          {renderInlineMarkdown(title)}
        </HeaderTag>
      )
      continue
    }

    // Horizontal Rule
    if (line.trim() === '---' || line.trim() === '***') {
      flushList()
      elements.push(<hr key={`hr-${key++}`} className="markdown-hr" />)
      continue
    }

    // Blockquote
    if (line.trim().startsWith('>')) {
      flushList()
      const quoteText = line.trim().slice(1).trim()
      elements.push(
        <blockquote key={`quote-${key++}`} className="markdown-blockquote">
          {renderInlineMarkdown(quoteText)}
        </blockquote>
      )
      continue
    }

    // Empty space/paragraph
    if (line.trim() === '') {
      flushList()
      continue
    }

    flushList()
    elements.push(
      <p key={`p-${key++}`} className="markdown-p">
        {renderInlineMarkdown(line)}
      </p>
    )
  }

  flushList()
  flushCodeBlock()

  return <div className="markdown-content">{elements}</div>
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
// ResponseBox  — renders live markdown text
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
            type="button"
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
        {loading && !response ? (
          <Spinner />
        ) : (
          <div className="response-box__text">
            {renderMarkdown(response)}
            {loading && <span className="streaming-cursor" aria-hidden="true" />}
          </div>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────
// TextPanel  —  ChatGPT-style conversational UI
// ─────────────────────────────────────────────
function TextPanel({ accent }) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [copiedId, setCopiedId] = useState(null)

  // Message list initialized with a welcoming assistant message
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: 'Hello! I am your TIAV assistant. Ask me anything, and I will stream responses back to you.',
      timestamp: new Date(),
    },
  ])

  const controllerRef = useRef(null)
  const listRef = useRef(null)

  // Auto-scroll to the bottom on new tokens or messages
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages])

  const startGeneration = async (text, assistantMsgId, currentMessages) => {
    if (controllerRef.current) {
      controllerRef.current.abort()
    }

    const controller = new AbortController()
    controllerRef.current = controller
    const timerId = setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS)

    setLoading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('prompt', text)

      const res = await fetch(`${API_BASE}/text`, {
        method: 'POST',
        body: formData,
        headers: { ...NGROK_HEADERS },
        signal: controller.signal,
      })

      if (!res.ok) {
        throw new Error(`Server error ${res.status} — please retry.`)
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let fullText = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        if (chunk) {
          fullText += chunk
          setMessages((prev) =>
            prev.map((msg) => (msg.id === assistantMsgId ? { ...msg, content: fullText } : msg))
          )
        }
      }

      const tail = decoder.decode()
      if (tail) {
        fullText += tail
        setMessages((prev) =>
          prev.map((msg) => (msg.id === assistantMsgId ? { ...msg, content: fullText } : msg))
        )
      }
    } catch (err) {
      if (err.name === 'AbortError') {
        // Keeps partial text but updates stream tag
      } else if (!navigator.onLine) {
        setError('No internet connection detected.')
      } else {
        setError(err.message || 'Network error occurred. Please retry.')
      }
    } finally {
      clearTimeout(timerId)
      setLoading(false)
      setMessages((prev) =>
        prev.map((msg) => (msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg))
      )
      controllerRef.current = null
    }
  }

  const handleSubmit = (e) => {
    if (e) e.preventDefault()
    const text = prompt.trim()
    if (!text || loading) return

    setPrompt('')

    // 1. Append User Bubble
    const userMsgId = Date.now().toString()
    const userMsg = {
      id: userMsgId,
      role: 'user',
      content: text,
      timestamp: new Date(),
    }

    // 2. Append Assistant Bubble placeholder
    const assistantMsgId = (Date.now() + 1).toString()
    const assistantMsg = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    }

    const nextMessages = [...messages, userMsg, assistantMsg]
    setMessages(nextMessages)
    startGeneration(text, assistantMsgId, nextMessages)
  }

  const handleStopGeneration = () => {
    if (controllerRef.current) {
      controllerRef.current.abort()
    }
  }

  const handleClearChat = () => {
    handleStopGeneration()
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content: 'Hello! I am your TIAV assistant. Ask me anything, and I will stream responses back to you.',
        timestamp: new Date(),
      },
    ])
    setError('')
  }

  const handleCopyMessage = (msgId, content) => {
    navigator.clipboard.writeText(content).then(() => {
      setCopiedId(msgId)
      setTimeout(() => setCopiedId(null), 2000)
    })
  }

  const handleRegenerate = (msgId) => {
    const idx = messages.findIndex((m) => m.id === msgId)
    if (idx === -1) return

    let userPrompt = ''
    let messagesToKeep = []

    if (messages[idx].role === 'assistant') {
      const prevMsg = messages[idx - 1]
      if (prevMsg && prevMsg.role === 'user') {
        userPrompt = prevMsg.content
        messagesToKeep = messages.slice(0, idx)
      }
    } else if (messages[idx].role === 'user') {
      userPrompt = messages[idx].content
      messagesToKeep = messages.slice(0, idx + 1)
    }

    if (!userPrompt) return

    const newAssistantMsgId = Date.now().toString()
    const newAssistantMsg = {
      id: newAssistantMsgId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    }

    const nextMessages = [...messagesToKeep, newAssistantMsg]
    setMessages(nextMessages)
    startGeneration(userPrompt, newAssistantMsgId, nextMessages)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="panel" style={{ '--tab-accent': accent }}>
      <div className="chat-container">
        {/* Chat Header Actions */}
        <div className="chat-header">
          <span>Conversation History</span>
          <div className="chat-header__actions">
            <button type="button" className="chat-header__btn" onClick={handleClearChat}>
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polyline points="3 6 5 6 21 6" />
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
              </svg>
              Clear Conversation
            </button>
          </div>
        </div>

        {/* Messages List Area */}
        <div className="message-list" ref={listRef}>
          {messages.map((msg) => (
            <div key={msg.id} className={`message-row message-row--${msg.role}`}>
              <div className={`message-bubble message-bubble--${msg.role}`}>
                {/* Conversational Text & Markdown */}
                {msg.role === 'assistant' && msg.content === '' && msg.isStreaming ? (
                  <div className="typing-dots">
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                    <div className="typing-dot" />
                  </div>
                ) : (
                  renderMarkdown(msg.content)
                )}

                {/* Live stream blinking cursor */}
                {msg.role === 'assistant' && msg.isStreaming && msg.content !== '' && (
                  <span className="streaming-cursor" aria-hidden="true" />
                )}

                {/* Custom Action Buttons under assistant response */}
                {msg.role === 'assistant' && !msg.isStreaming && (
                  <div className="message-actions">
                    <button
                      type="button"
                      className="message-action-btn"
                      onClick={() => handleCopyMessage(msg.id, msg.content)}
                      title="Copy response"
                    >
                      {copiedId === msg.id ? (
                        <span style={{ fontSize: '11px', color: '#6EE7B7' }}>Copied!</span>
                      ) : (
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <rect x="9" y="9" width="13" height="13" rx="2" />
                          <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                        </svg>
                      )}
                    </button>
                    {msg.id !== 'welcome' && (
                      <button
                        type="button"
                        className="message-action-btn"
                        onClick={() => handleRegenerate(msg.id)}
                        title="Regenerate response"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                        </svg>
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input Footer Area */}
        <div className="chat-input-area">
          <div className="chat-input-wrapper">
            <textarea
              className="chat-textarea"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={loading ? "AI is generating..." : "Type your message... (Enter to send, Shift+Enter for new line)"}
              rows={1}
              disabled={loading}
            />
            <div className="chat-input-actions">
              {loading ? (
                <button
                  type="button"
                  className="chat-stop-btn"
                  onClick={handleStopGeneration}
                  title="Stop generating"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                    <rect x="4" y="4" width="16" height="16" rx="2" />
                  </svg>
                </button>
              ) : (
                <button
                  type="button"
                  className="chat-send-btn"
                  onClick={handleSubmit}
                  disabled={!prompt.trim()}
                  title="Send message"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
      {error && <p className="error-msg">{error}</p>}
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
      const text = (data && data.response) || ''
      if (text) {
        setResponse(text)
      } else {
        setError('No response returned from server.')
      }
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
