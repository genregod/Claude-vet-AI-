#!/bin/bash

# Start development environment for Valor Assist

echo "🎖️ Starting Valor Assist Development Environment..."
echo ""

# Check if .env files exist
if [ ! -f backend/.env ]; then
    echo "⚠️  Backend .env file not found. Creating from template..."
    cp backend/.env.example backend/.env
    echo "⚠️  Please update backend/.env with your ANTHROPIC_API_KEY before the backend will work properly"
fi

if [ ! -f frontend/.env ]; then
    echo "Creating frontend .env file..."
    cp frontend/.env.example frontend/.env
fi

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo "Starting backend server on port 8000..."
cd backend
python -m app.main &
BACKEND_PID=$!
cd ..

# Wait a bit for backend to start
sleep 2

# Start frontend
echo "Starting frontend dev server on port 3000..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Development environment is running!"
echo ""
echo "Frontend: http://localhost:3000"
echo "Backend API: http://localhost:8000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for processes
wait
