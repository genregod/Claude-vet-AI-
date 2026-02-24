import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getConsentChallenge, submitConsent, getProfile } from '../api'

export default function ConsentPage({ user, onComplete }) {
  const [challenge, setChallenge] = useState(null)
  const [checked, setChecked] = useState({})
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!user) {
      navigate('/login')
      return
    }
    if (user.consent_given) {
      navigate('/evaluate')
      return
    }
    getConsentChallenge()
      .then(setChallenge)
      .catch((err) => setError(err.message))
  }, [user, navigate])

  const allChecked =
    challenge &&
    challenge.statements.every((s) => !s.required || checked[s.id])

  const handleSubmit = async () => {
    if (!allChecked || loading) return
    setLoading(true)
    setError(null)

    const responses = challenge.statements.map((s) => ({
      statement_id: s.id,
      confirmed: !!checked[s.id],
    }))

    try {
      await submitConsent(challenge.challenge_id, responses)
      const profile = await getProfile()
      onComplete(profile)
      navigate('/evaluate')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!challenge) {
    return <div className="loading"><span className="spinner" /> Loading consent form...</div>
  }

  return (
    <div style={{ maxWidth: 640, margin: '2rem auto' }}>
      <div className="card">
        <h2>Authorization & Consent</h2>
        <p style={{ color: 'var(--gray-500)', marginBottom: '1.5rem' }}>
          Before we can evaluate your case, please review and acknowledge
          the following statements. This protects both you and us.
        </p>

        {error && <div className="error-msg">{error}</div>}

        {challenge.statements.map((statement) => (
          <div
            key={statement.id}
            className={`consent-statement ${checked[statement.id] ? 'checked' : ''}`}
          >
            <input
              type="checkbox"
              checked={!!checked[statement.id]}
              onChange={(e) =>
                setChecked((prev) => ({ ...prev, [statement.id]: e.target.checked }))
              }
            />
            <div>
              <p>{statement.text}</p>
              {statement.required && (
                <span style={{ fontSize: '0.75rem', color: 'var(--red)' }}>Required</span>
              )}
            </div>
          </div>
        ))}

        <button
          className="btn btn-primary"
          style={{ width: '100%', marginTop: '1rem' }}
          onClick={handleSubmit}
          disabled={!allChecked || loading}
        >
          {loading ? 'Processing...' : 'Confirm and Continue to Case Evaluation'}
        </button>
      </div>
    </div>
  )
}
