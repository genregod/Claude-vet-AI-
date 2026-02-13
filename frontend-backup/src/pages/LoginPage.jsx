import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { signup, getIdmeLoginUrl, getProfile } from '../api'

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState('choice') // 'choice' | 'signup'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleIdmeLogin = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getIdmeLoginUrl()
      // In production, redirect to ID.me. For local testing, show the URL.
      if (data.authorization_url) {
        window.location.href = data.authorization_url
      }
    } catch (err) {
      setError(
        'ID.me is not configured yet. Use email signup for testing, or ' +
        'set IDME_CLIENT_ID and IDME_CLIENT_SECRET in your .env file.'
      )
    } finally {
      setLoading(false)
    }
  }

  const handleSignup = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      await signup(email, password, firstName, lastName)
      const profile = await getProfile()
      onLogin(profile)
      navigate('/consent')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  if (mode === 'choice') {
    return (
      <div style={{ maxWidth: 440, margin: '2rem auto' }}>
        <div className="card" style={{ textAlign: 'center' }}>
          <h2 style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>
            Welcome to Valor Assist
          </h2>
          <p style={{ color: 'var(--gray-500)', marginBottom: '2rem' }}>
            Verify your identity to access your free case evaluation.
            Your data is encrypted and protected.
          </p>

          {error && <div className="error-msg">{error}</div>}

          <button
            className="btn btn-navy"
            style={{ width: '100%', marginBottom: '1rem', padding: '0.9rem' }}
            onClick={handleIdmeLogin}
            disabled={loading}
          >
            Sign in with ID.me (Recommended)
          </button>
          <p style={{ fontSize: '0.8rem', color: 'var(--gray-500)', marginBottom: '1.5rem' }}>
            Verifies your veteran status automatically.
            <br />
            Highest level of identity assurance (LOA3).
          </p>

          <div style={{
            borderTop: '1px solid var(--gray-200)',
            padding: '1.5rem 0 0.5rem',
            marginTop: '0.5rem'
          }}>
            <p style={{ fontSize: '0.85rem', color: 'var(--gray-500)', marginBottom: '1rem' }}>
              or for testing purposes:
            </p>
            <button
              className="btn btn-outline"
              style={{ width: '100%' }}
              onClick={() => setMode('signup')}
            >
              Sign up with Email
            </button>
          </div>
        </div>

        <div className="card" style={{ background: '#FFFBEB', fontSize: '0.85rem' }}>
          <strong>Why identity verification?</strong>
          <p style={{ marginTop: '0.3rem', color: 'var(--gray-700)' }}>
            Because your VA claim data contains sensitive personal information
            (medical records, service history, ratings), we require identity
            verification before accessing case evaluation features. This
            protects you from unauthorized access.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 440, margin: '2rem auto' }}>
      <div className="card">
        <h2>Create Account</h2>
        <p style={{ color: 'var(--gray-500)', marginBottom: '1rem', fontSize: '0.9rem' }}>
          Email signup for testing. For full identity verification, use ID.me.
        </p>

        {error && <div className="error-msg">{error}</div>}

        <form onSubmit={handleSignup}>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>First Name</label>
              <input value={firstName} onChange={(e) => setFirstName(e.target.value)} />
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>Last Name</label>
              <input value={lastName} onChange={(e) => setLastName(e.target.value)} />
            </div>
          </div>

          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>

          <div className="form-group">
            <label>Password (min 12 characters)</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={12} />
          </div>

          <button className="btn btn-navy" style={{ width: '100%' }} disabled={loading}>
            {loading ? 'Creating account...' : 'Create Account'}
          </button>
        </form>

        <button
          style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--blue)', background: 'none', border: 'none', cursor: 'pointer' }}
          onClick={() => setMode('choice')}
        >
          Back to login options
        </button>
      </div>
    </div>
  )
}
