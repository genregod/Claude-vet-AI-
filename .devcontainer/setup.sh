#!/bin/bash

echo "Setting up Claude Vet AI development environment..."

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Copy environment files if they don't exist
if [ ! -f backend/.env ]; then
    echo "Creating backend .env file..."
    cp backend/.env.example backend/.env
    echo "⚠️  Please update backend/.env with your ANTHROPIC_API_KEY"
fi

if [ ! -f frontend/.env ]; then
    echo "Creating frontend .env file..."
    cp frontend/.env.example frontend/.env
fi

echo "✅ Setup complete!"
echo ""
echo "To start the development environment:"
echo "  1. Update backend/.env with your ANTHROPIC_API_KEY"
echo "  2. Run 'npm run dev' in the frontend directory"
echo "  3. Run 'python -m app.main' in the backend directory"
echo ""
echo "Or use the provided start scripts:"
echo "  ./start-dev.sh - Starts both frontend and backend"
