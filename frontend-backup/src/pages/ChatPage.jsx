import { useState, useEffect, useRef } from 'react'
import { createChatSession, sendMessage, sendQuickAction } from '../api'

const QUICK_ACTIONS = [
  { key: 'check_claim_status', label: 'Check claim status' },
  { key: 'file_new_claim', label: 'File a new claim' },
  { key: 'upload_documents', label: 'Upload documents' },
  { key: 'learn_appeals', label: 'Learn about appeals' },
]

export default function ChatPage({ user }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        "Hello! I'm Valor Assist, here to help you with your VA claims. " +
        "How can I assist you today?\n\n" +
        "You can type a question below or use the quick action buttons.",
    },
  ])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const messagesEnd = useRef(null)

  useEffect(() => {
    createChatSession()
      .then((data) => setSessionId(data.session_id))
      .catch(() => {})
  }, [])

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async () => {
    if (!input.trim() || loading) return
    const question = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: question }])
    setLoading(true)
    setError(null)

    try {
      const res = await sendMessage(question, sessionId)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.answer, sources: res.sources },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleQuickAction = async (action) => {
    if (loading) return
    setMessages((prev) => [
      ...prev,
      { role: 'system', content: `Quick action: ${action.label}` },
    ])
    setLoading(true)
    setError(null)

    try {
      const res = await sendQuickAction(action.key, sessionId)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: res.answer, sources: res.sources },
      ])
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="card chat-container">
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            {msg.content}
            {msg.sources && msg.sources.length > 0 && (
              <div className="sources">
                Sources:{' '}
                {msg.sources.map((s, j) => (
                  <span key={j}>
                    {s.source_type} ({s.source_file})
                    {j < msg.sources.length - 1 ? ', ' : ''}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-bubble assistant">
            <span className="spinner" /> Analyzing regulations...
          </div>
        )}
        {error && <div className="error-msg">{error}</div>}
        <div ref={messagesEnd} />
      </div>

      <div className="quick-actions">
        {QUICK_ACTIONS.map((a) => (
          <button key={a.key} onClick={() => handleQuickAction(a)} disabled={loading}>
            {a.label}
          </button>
        ))}
      </div>

      <div className="chat-input-bar">
        <input
          type="text"
          placeholder="Ask about your VA claim..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button className="btn btn-navy" onClick={handleSend} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>
    </div>
  )
}
