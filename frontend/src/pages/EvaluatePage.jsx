import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitEvaluation } from '../api'

const BRANCHES = ['Army', 'Navy', 'Air Force', 'Marines', 'Coast Guard', 'Space Force']
const RATINGS = ['Not yet rated', '0%', '10%', '20%', '30%', '40%', '50%', '60%', '70%', '80%', '90%', '100%']

export default function EvaluatePage({ user }) {
  const [form, setForm] = useState({
    service_branch: '',
    current_rating: '',
    primary_concerns: '',
    additional_details: '',
  })
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleChange = (field) => (e) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async (e) => {
    e.preventDefault()

    if (!user) {
      navigate('/login')
      return
    }
    if (!user.consent_given) {
      navigate('/consent')
      return
    }

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const res = await submitEvaluation(form)
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 720, margin: '0 auto' }}>
      <div className="card">
        <h2>Free Case Evaluation</h2>
        <p style={{ color: 'var(--gray-500)', marginBottom: '1.5rem' }}>
          Tell us about your situation and we'll provide a preliminary
          assessment grounded in VA regulations.
          {!user && (
            <span style={{ color: 'var(--red)' }}>
              {' '}You must sign in and verify your identity first.
            </span>
          )}
        </p>

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div style={{ display: 'flex', gap: '1rem' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Service Branch</label>
              <select value={form.service_branch} onChange={handleChange('service_branch')} required>
                <option value="">Select branch...</option>
                {BRANCHES.map((b) => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Current VA Rating</label>
              <select value={form.current_rating} onChange={handleChange('current_rating')} required>
                <option value="">Select rating...</option>
                {RATINGS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
            </div>
          </div>

          <div className="form-group">
            <label>Primary Concerns</label>
            <textarea
              rows={4}
              placeholder="Describe your main claim concerns (e.g., PTSD from combat deployment, tinnitus, knee injury)..."
              value={form.primary_concerns}
              onChange={handleChange('primary_concerns')}
              required
              minLength={10}
            />
          </div>

          <div className="form-group">
            <label>Additional Details (optional)</label>
            <textarea
              rows={3}
              placeholder="Service dates, prior denials, separation code issues, etc..."
              value={form.additional_details}
              onChange={handleChange('additional_details')}
            />
          </div>

          <button className="btn btn-primary" style={{ width: '100%' }} disabled={loading}>
            {loading ? (
              <><span className="spinner" /> Analyzing your case...</>
            ) : (
              'Get Free Case Evaluation'
            )}
          </button>
        </form>
      </div>

      {result && (
        <div className="card" style={{ borderLeft: '4px solid var(--gold)' }}>
          <h2>Preliminary Assessment</h2>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
            {result.assessment}
          </div>
          {result.sources && result.sources.length > 0 && (
            <div className="sources" style={{ marginTop: '1rem' }}>
              <strong>Sources consulted:</strong>
              <ul style={{ marginTop: '0.3rem', paddingLeft: '1.25rem' }}>
                {result.sources.map((s, i) => (
                  <li key={i}>{s.source_type} — {s.source_file}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
