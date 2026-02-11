from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import patients, consultations
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Claude Vet AI",
    description="AI-powered veterinary consultation assistant using Claude",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(patients.router, prefix="/api/patients", tags=["patients"])
app.include_router(consultations.router, prefix="/api/consultations", tags=["consultations"])

@app.get("/")
async def root():
    return {
        "message": "Welcome to Claude Vet AI API",
        "version": "0.1.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
