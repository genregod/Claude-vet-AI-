# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.0.1] - 2026-02-13

### Added

- **FastAPI Backend** with RAG pipeline powered by Claude 3.5 Sonnet and ChromaDB vector store
- **React Frontend** with chat widget, claim evaluation, and Start Your Claim flow
- **Authentication** via ID.me OAuth integration with JWT session tokens
- **PII Shield** middleware to protect veteran personal information
- **VA.gov Integration** via Lighthouse API for real-time benefits data
- **Security Middleware** with CORS, HSTS, CSP headers, and per-IP rate limiting
- **Encrypted Sessions** using Fernet symmetric encryption
- **Knowledge Base Ingestion** pipeline for 38 CFR regulations and VA benefit documents
- **Docker Compose** full-stack local development environment
- **CI/CD Pipeline** with GitHub Actions for linting, testing, and AWS ECR deployment
- **Security Audit** workflow with Trivy, pip-audit, npm audit, and TruffleHog
- **AWS Architecture** documentation for production deployment
- **Military Records Upload** with AI auto-fill for claim forms
