# 🎖️ Valor Assist

AI-powered VA disability claims assistant for veterans using Anthropic's Claude AI. Valor Assist helps new filers and current veterans looking to appeal their initial VA determination.

## Features

- **Veteran Profile Management**: Create and manage veteran profiles with service history
- **Claims Assistance**: Get AI-powered guidance for both initial claims and appeals
- **Evidence Analysis**: Understand what documentation you need for your claim
- **Service Connection Guidance**: Help articulating how conditions relate to service
- **Appeal Strategies**: Specific guidance for strengthening appeals
- **Modern UI**: Clean, responsive interface for easy use
- **REST API**: Full-featured API with automatic documentation

## Important Disclaimer

**Valor Assist is for informational and educational purposes only.** This application:
- Does NOT replace an accredited Veterans Service Officer (VSO) or attorney
- Does NOT file claims on your behalf
- Does NOT provide legal advice
- Should be used as a supplementary research tool

Always consult with an accredited VSO or attorney for official VA claims representation.

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

### Veterans
- `GET /api/veterans` - List all veteran profiles
- `GET /api/veterans/{id}` - Get a specific veteran profile
- `POST /api/veterans` - Create a new veteran profile
- `PUT /api/veterans/{id}` - Update a veteran profile
- `DELETE /api/veterans/{id}` - Delete a veteran profile

### Claims
- `GET /api/claims` - List all claims
- `GET /api/claims/{id}` - Get a specific claim
- `POST /api/claims` - Submit a claim and get AI assistance

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

## How It Works

1. **Create a Veteran Profile**: Enter service history and contact information
2. **Submit Claim Details**: Describe conditions, service connection, and available evidence
3. **Get AI Assistance**: Claude analyzes your claim and provides:
   - Assessment of claim strength
   - Required evidence and documentation
   - Next steps in the claims process
   - Common pitfalls to avoid
   - Timeline expectations
   - Appeal strategies (if applicable)
4. **Review Guidance**: Use the AI-generated guidance to prepare your claim
5. **Consult a VSO**: Take the information to an accredited VSO or attorney

## Project Structure

```
Claude-vet-AI-/
├── backend/                    # Python FastAPI backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── routes/            # API endpoints
│   │   │   ├── veterans.py   # Veteran profile management
│   │   │   └── claims.py     # Claims assistance
│   │   ├── services/          # Business logic
│   │   │   └── claude_service.py  # Claude AI integration
│   │   └── models/            # Data models
│   │       └── schemas.py    # Pydantic schemas
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

## VA Claims Resources

- [VA.gov - How to File a Claim](https://www.va.gov/disability/how-to-file-claim/)
- [VA.gov - Evidence Requirements](https://www.va.gov/disability/how-to-file-claim/evidence-needed/)
- [Find a VSO](https://www.va.gov/vso/)
- [VA Decision Review Options](https://www.va.gov/decision-reviews/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License. 
