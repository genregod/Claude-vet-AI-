import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [veterans, setVeterans] = useState([])
  const [selectedVeteran, setSelectedVeteran] = useState(null)
  const [newVeteran, setNewVeteran] = useState({
    name: '',
    service_branch: '',
    service_dates: '',
    discharge_status: '',
    email: '',
    phone: ''
  })
  const [claimType, setClaimType] = useState('initial')
  const [conditions, setConditions] = useState('')
  const [serviceConnection, setServiceConnection] = useState('')
  const [evidenceDescription, setEvidenceDescription] = useState('')
  const [aiResponse, setAiResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchVeterans()
  }, [])

  const fetchVeterans = async () => {
    try {
      const response = await fetch(`${API_URL}/api/veterans`)
      const data = await response.json()
      setVeterans(data)
    } catch (err) {
      console.error('Error fetching veterans:', err)
    }
  }

  const handleCreateVeteran = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const response = await fetch(`${API_URL}/api/veterans`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newVeteran)
      })
      if (response.ok) {
        setNewVeteran({
          name: '',
          service_branch: '',
          service_dates: '',
          discharge_status: '',
          email: '',
          phone: ''
        })
        fetchVeterans()
      } else {
        setError('Failed to create veteran profile')
      }
    } catch (err) {
      setError('Error creating veteran profile: ' + err.message)
    }
  }

  const handleClaimSubmission = async (e) => {
    e.preventDefault()
    if (!selectedVeteran) {
      setError('Please select a veteran first')
      return
    }
    setError('')
    setLoading(true)
    setAiResponse('')
    
    try {
      const response = await fetch(`${API_URL}/api/claims`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          veteran_id: selectedVeteran.id,
          claim_type: claimType,
          conditions,
          service_connection: serviceConnection,
          evidence_description: evidenceDescription
        })
      })
      const data = await response.json()
      if (response.ok) {
        setAiResponse(data.ai_response)
        setConditions('')
        setServiceConnection('')
        setEvidenceDescription('')
      } else {
        setError('Failed to get claim assistance')
      }
    } catch (err) {
      setError('Error getting claim assistance: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <div className="header">
        <h1>🎖️ Valor Assist</h1>
        <p>AI-powered VA disability claims assistance for veterans</p>
      </div>

      <div className="content">
        <div className="panel">
          <h2>Veteran Profile</h2>
          <form onSubmit={handleCreateVeteran}>
            <div className="form-group">
              <label>Full Name *</label>
              <input
                type="text"
                value={newVeteran.name}
                onChange={(e) => setNewVeteran({...newVeteran, name: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>Service Branch *</label>
              <select
                value={newVeteran.service_branch}
                onChange={(e) => setNewVeteran({...newVeteran, service_branch: e.target.value})}
                required
              >
                <option value="">Select branch</option>
                <option value="Army">Army</option>
                <option value="Navy">Navy</option>
                <option value="Air Force">Air Force</option>
                <option value="Marine Corps">Marine Corps</option>
                <option value="Coast Guard">Coast Guard</option>
                <option value="Space Force">Space Force</option>
              </select>
            </div>
            <div className="form-group">
              <label>Service Dates</label>
              <input
                type="text"
                placeholder="e.g., 2010-2015"
                value={newVeteran.service_dates}
                onChange={(e) => setNewVeteran({...newVeteran, service_dates: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>Discharge Status</label>
              <select
                value={newVeteran.discharge_status}
                onChange={(e) => setNewVeteran({...newVeteran, discharge_status: e.target.value})}
              >
                <option value="">Select status</option>
                <option value="Honorable">Honorable</option>
                <option value="General">General</option>
                <option value="Other Than Honorable">Other Than Honorable</option>
                <option value="Bad Conduct">Bad Conduct</option>
                <option value="Dishonorable">Dishonorable</option>
              </select>
            </div>
            <div className="form-group">
              <label>Email *</label>
              <input
                type="email"
                value={newVeteran.email}
                onChange={(e) => setNewVeteran({...newVeteran, email: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>Phone</label>
              <input
                type="tel"
                value={newVeteran.phone}
                onChange={(e) => setNewVeteran({...newVeteran, phone: e.target.value})}
              />
            </div>
            <button type="submit">Create Profile</button>
          </form>

          <div className="patient-list">
            <h3>Veterans ({veterans.length})</h3>
            {veterans.map(veteran => (
              <div
                key={veteran.id}
                className={`patient-item ${selectedVeteran?.id === veteran.id ? 'selected' : ''}`}
                onClick={() => setSelectedVeteran(veteran)}
              >
                <strong>{veteran.name}</strong> - {veteran.service_branch}
                <br />
                <small>{veteran.service_dates || 'Service dates not provided'}</small>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <h2>VA Claims Assistance</h2>
          {selectedVeteran ? (
            <>
              <div style={{background: '#f0f0f0', padding: '10px', borderRadius: '5px', marginBottom: '15px'}}>
                <strong>Selected Veteran:</strong> {selectedVeteran.name}<br />
                <small>{selectedVeteran.service_branch} • {selectedVeteran.discharge_status || 'Discharge status not provided'}</small>
              </div>
              
              <form onSubmit={handleClaimSubmission}>
                <div className="form-group">
                  <label>Claim Type *</label>
                  <select
                    value={claimType}
                    onChange={(e) => setClaimType(e.target.value)}
                    required
                  >
                    <option value="initial">Initial Claim</option>
                    <option value="appeal">Appeal</option>
                  </select>
                </div>
                <div className="form-group">
                  <label>Conditions/Disabilities *</label>
                  <textarea
                    value={conditions}
                    onChange={(e) => setConditions(e.target.value)}
                    placeholder="List the conditions you're claiming (e.g., PTSD, hearing loss, knee injury, tinnitus)"
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Service Connection *</label>
                  <textarea
                    value={serviceConnection}
                    onChange={(e) => setServiceConnection(e.target.value)}
                    placeholder="Explain how these conditions are related to your military service..."
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Evidence Available</label>
                  <textarea
                    value={evidenceDescription}
                    onChange={(e) => setEvidenceDescription(e.target.value)}
                    placeholder="Describe what evidence you have (medical records, buddy statements, service records, etc.)"
                  />
                </div>
                <button type="submit" disabled={loading}>
                  {loading ? 'Getting AI Assistance...' : 'Get Claim Assistance'}
                </button>
              </form>

              {error && <div className="error">{error}</div>}
              
              {loading && <div className="loading">Analyzing your claim with AI assistance...</div>}
              
              {aiResponse && (
                <div className="ai-response">
                  <strong>AI Claim Assistance:</strong>
                  <div style={{marginTop: '10px'}}>{aiResponse}</div>
                  <div style={{marginTop: '15px', padding: '10px', background: '#fff3cd', borderRadius: '5px', fontSize: '12px'}}>
                    <strong>⚠️ Important:</strong> This is for informational purposes only. Always consult with an accredited VSO (Veterans Service Officer) or attorney for official representation.
                  </div>
                </div>
              )}
            </>
          ) : (
            <p style={{color: '#999', textAlign: 'center', padding: '40px'}}>
              Select a veteran profile from the list to begin claim assistance
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
