# 🐾 Claude Vet AI

AI-powered veterinary consultation assistant using Anthropic's Claude AI.

## Features

- **Patient Management**: Create and manage pet patient records
- **AI Consultations**: Get AI-powered veterinary insights using Claude
- **Modern UI**: Clean, responsive interface for easy use
- **REST API**: Full-featured API with automatic documentation

## Tech Stack

**Backend:**
- Python 3.11+
- FastAPI
- Anthropic Claude API
- Uvicorn

**Frontend:**
- React 18
- Vite
- Modern CSS

## Quick Start with GitHub Codespaces

1. Click "Code" → "Create codespace on main"
2. Wait for the environment to set up automatically
3. Update `backend/.env` with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_actual_api_key_here
   ```
4. Run the start script:
   ```bash
   ./start-dev.sh
   ```
5. Access the application:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Local Development Setup

### Prerequisites

- Python 3.11 or higher
- Node.js 18 or higher
- npm or yarn

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/genregod/Claude-vet-AI-.git
   cd Claude-vet-AI-
   ```

2. Set up the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

3. Set up the frontend:
   ```bash
   cd ../frontend
   npm install
   cp .env.example .env
   ```

### Running the Application

**Option 1: Using the start script (recommended)**
```bash
./start-dev.sh
```

**Option 2: Manually start each service**

Terminal 1 (Backend):
```bash
cd backend
python -m app.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

**Option 3: Using Docker Compose**
```bash
docker-compose up
```

## API Endpoints

### Patients
- `GET /api/patients` - List all patients
- `GET /api/patients/{id}` - Get a specific patient
- `POST /api/patients` - Create a new patient
- `PUT /api/patients/{id}` - Update a patient
- `DELETE /api/patients/{id}` - Delete a patient

### Consultations
- `GET /api/consultations` - List all consultations
- `GET /api/consultations/{id}` - Get a specific consultation
- `POST /api/consultations` - Create a consultation and get AI response

### Health Check
- `GET /health` - Check API health status

For complete API documentation, visit http://localhost:8000/docs when the backend is running.

## Configuration

### Backend (.env)
```
ANTHROPIC_API_KEY=your_api_key_here
PORT=8000
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:8000
```

## Getting an Anthropic API Key

1. Sign up at https://www.anthropic.com/
2. Navigate to API Keys in your account settings
3. Create a new API key
4. Copy it to your `backend/.env` file

## Project Structure

```
Claude-vet-AI-/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── routes/            # API endpoints
│   │   ├── services/          # Business logic (Claude integration)
│   │   └── models/            # Data models
│   ├── requirements.txt       # Python dependencies
│   └── .env.example          # Environment template
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── App.jsx           # Main application component
│   │   ├── main.jsx          # Entry point
│   │   └── index.css         # Styles
│   ├── package.json          # Node.js dependencies
│   └── .env.example          # Environment template
├── .devcontainer/             # GitHub Codespaces configuration
│   ├── devcontainer.json     # Codespace settings
│   └── setup.sh              # Setup script
├── docker-compose.yml         # Docker orchestration
├── start-dev.sh              # Development startup script
└── README.md                 # This file
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License.

## Disclaimer

This application is for informational purposes only and should not replace professional veterinary care. Always consult with a licensed veterinarian for medical advice. 
