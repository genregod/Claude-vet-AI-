import { useState, useEffect } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const [patients, setPatients] = useState([])
  const [selectedPatient, setSelectedPatient] = useState(null)
  const [newPatient, setNewPatient] = useState({
    name: '',
    species: '',
    breed: '',
    age: '',
    owner_name: '',
    owner_contact: ''
  })
  const [symptoms, setSymptoms] = useState('')
  const [aiResponse, setAiResponse] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchPatients()
  }, [])

  const fetchPatients = async () => {
    try {
      const response = await fetch(`${API_URL}/api/patients`)
      const data = await response.json()
      setPatients(data)
    } catch (err) {
      console.error('Error fetching patients:', err)
    }
  }

  const handleCreatePatient = async (e) => {
    e.preventDefault()
    setError('')
    try {
      const response = await fetch(`${API_URL}/api/patients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...newPatient,
          age: newPatient.age ? parseInt(newPatient.age) : null
        })
      })
      if (response.ok) {
        setNewPatient({
          name: '',
          species: '',
          breed: '',
          age: '',
          owner_name: '',
          owner_contact: ''
        })
        fetchPatients()
      } else {
        setError('Failed to create patient')
      }
    } catch (err) {
      setError('Error creating patient: ' + err.message)
    }
  }

  const handleConsultation = async (e) => {
    e.preventDefault()
    if (!selectedPatient) {
      setError('Please select a patient first')
      return
    }
    setError('')
    setLoading(true)
    setAiResponse('')
    
    try {
      const response = await fetch(`${API_URL}/api/consultations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_id: selectedPatient.id,
          symptoms
        })
      })
      const data = await response.json()
      if (response.ok) {
        setAiResponse(data.ai_response)
        setSymptoms('')
      } else {
        setError('Failed to get consultation')
      }
    } catch (err) {
      setError('Error getting consultation: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <div className="header">
        <h1>🐾 Claude Vet AI</h1>
        <p>AI-powered veterinary consultation assistant</p>
      </div>

      <div className="content">
        <div className="panel">
          <h2>Add New Patient</h2>
          <form onSubmit={handleCreatePatient}>
            <div className="form-group">
              <label>Patient Name *</label>
              <input
                type="text"
                value={newPatient.name}
                onChange={(e) => setNewPatient({...newPatient, name: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>Species *</label>
              <select
                value={newPatient.species}
                onChange={(e) => setNewPatient({...newPatient, species: e.target.value})}
                required
              >
                <option value="">Select species</option>
                <option value="Dog">Dog</option>
                <option value="Cat">Cat</option>
                <option value="Bird">Bird</option>
                <option value="Rabbit">Rabbit</option>
                <option value="Other">Other</option>
              </select>
            </div>
            <div className="form-group">
              <label>Breed</label>
              <input
                type="text"
                value={newPatient.breed}
                onChange={(e) => setNewPatient({...newPatient, breed: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>Age (years)</label>
              <input
                type="number"
                value={newPatient.age}
                onChange={(e) => setNewPatient({...newPatient, age: e.target.value})}
              />
            </div>
            <div className="form-group">
              <label>Owner Name *</label>
              <input
                type="text"
                value={newPatient.owner_name}
                onChange={(e) => setNewPatient({...newPatient, owner_name: e.target.value})}
                required
              />
            </div>
            <div className="form-group">
              <label>Owner Contact *</label>
              <input
                type="text"
                value={newPatient.owner_contact}
                onChange={(e) => setNewPatient({...newPatient, owner_contact: e.target.value})}
                required
              />
            </div>
            <button type="submit">Add Patient</button>
          </form>

          <div className="patient-list">
            <h3>Patients ({patients.length})</h3>
            {patients.map(patient => (
              <div
                key={patient.id}
                className={`patient-item ${selectedPatient?.id === patient.id ? 'selected' : ''}`}
                onClick={() => setSelectedPatient(patient)}
              >
                <strong>{patient.name}</strong> - {patient.species} ({patient.breed || 'Unknown breed'})
                <br />
                <small>Owner: {patient.owner_name}</small>
              </div>
            ))}
          </div>
        </div>

        <div className="panel">
          <h2>AI Consultation</h2>
          {selectedPatient ? (
            <>
              <div style={{background: '#f0f0f0', padding: '10px', borderRadius: '5px', marginBottom: '15px'}}>
                <strong>Selected Patient:</strong> {selectedPatient.name}<br />
                <small>{selectedPatient.species} - {selectedPatient.age} years old</small>
              </div>
              
              <form onSubmit={handleConsultation}>
                <div className="form-group">
                  <label>Symptoms *</label>
                  <textarea
                    value={symptoms}
                    onChange={(e) => setSymptoms(e.target.value)}
                    placeholder="Describe the symptoms..."
                    required
                  />
                </div>
                <button type="submit" disabled={loading}>
                  {loading ? 'Getting AI Consultation...' : 'Get AI Consultation'}
                </button>
              </form>

              {error && <div className="error">{error}</div>}
              
              {loading && <div className="loading">Consulting with Claude AI...</div>}
              
              {aiResponse && (
                <div className="ai-response">
                  <strong>AI Response:</strong>
                  <div style={{marginTop: '10px'}}>{aiResponse}</div>
                </div>
              )}
            </>
          ) : (
            <p style={{color: '#999', textAlign: 'center', padding: '40px'}}>
              Select a patient from the list to start a consultation
            </p>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
