import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import ChatPage from './pages/ChatPage'
import LoginPage from './pages/LoginPage'
import ConsentPage from './pages/ConsentPage'
import EvaluatePage from './pages/EvaluatePage'
import { getProfile, logout as apiLogout } from './api'

export default function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    const token = localStorage.getItem('access_token')
    if (token) {
      getProfile()
        .then(setUser)
        .catch(() => localStorage.clear())
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  const handleLogout = async () => {
    await apiLogout()
    setUser(null)
    navigate('/')
  }

  const handleLogin = (userData) => {
    setUser(userData)
  }

  if (loading) return <div className="loading"><span className="spinner" /> Loading...</div>

  return (
    <div className="app-container">
      <header className="navbar">
        <Link to="/" style={{ textDecoration: 'none' }}>
          <h1>VALOR ASSIST</h1>
        </Link>
        <nav>
          <Link to="/">Chat</Link>
          <Link to="/evaluate">Case Evaluation</Link>
          {user ? (
            <>
              <span style={{ color: '#C5A55A', fontSize: '0.85rem' }}>
                {user.first_name || user.email}
                {user.veteran_status_confirmed && ' \u2605'}
              </span>
              <VerificationBadge level={user.verification_level} />
              <button onClick={handleLogout}>Logout</button>
            </>
          ) : (
            <Link to="/login">Sign In</Link>
          )}
        </nav>
      </header>

      <div className="main-content">
        <Routes>
          <Route path="/" element={<ChatPage user={user} />} />
          <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
          <Route path="/consent" element={<ConsentPage user={user} onComplete={(u) => setUser(u)} />} />
          <Route
            path="/evaluate"
            element={<EvaluatePage user={user} />}
          />
        </Routes>
      </div>
    </div>
  )
}

function VerificationBadge({ level }) {
  const config = {
    veteran: { label: 'Veteran Verified', cls: 'badge-green' },
    loa3: { label: 'ID Verified', cls: 'badge-green' },
    loa1: { label: 'Basic', cls: 'badge-yellow' },
    unverified: { label: 'Unverified', cls: 'badge-red' },
  }
  const c = config[level] || config.unverified
  return <span className={`badge ${c.cls}`}>{c.label}</span>
}
