# Valor Assist — AWS Production Architecture

## Overview

This document outlines the recommended AWS deployment architecture for
the Valor Assist backend, optimized for security (PII/PHI handling),
scalability, and cost efficiency.

## Architecture Diagram

```
                     ┌──────────────┐
                     │  CloudFront  │
                     │   (CDN)      │
                     └──────┬───────┘
                            │
                     ┌──────┴───────┐
                     │ AWS WAF      │
                     │ (Rate limit  │
                     │  + DDoS)     │
                     └──────┬───────┘
                            │
                     ┌──────┴───────┐
                     │   ALB        │
                     │ (HTTPS only) │
                     └──────┬───────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
        │  ECS      │ │  ECS      │ │  ECS      │
        │  Fargate  │ │  Fargate  │ │  Fargate  │
        │  Task 1   │ │  Task 2   │ │  Task N   │
        └─────┬─────┘ └─────┬─────┘ └─────┬─────┘
              │             │             │
              └─────────────┼─────────────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
        ┌─────┴─────┐ ┌─────┴─────┐ ┌─────┴─────┐
        │ DynamoDB  │ │    S3     │ │  Secrets  │
        │ (Sessions │ │ (Docs +  │ │  Manager  │
        │  + Chat)  │ │ ChromaDB)│ │ (API keys)│
        └───────────┘ └──────────┘ └───────────┘
```

## Services

### Compute: ECS Fargate
- **Why**: Serverless containers — no EC2 management, auto-scaling
- **Config**: 2 vCPU / 4 GB RAM per task (sufficient for embeddings + API)
- **Auto-scaling**: Target tracking on CPU utilization (60%) and request count
- **Container**: Docker image from ECR (built via CodePipeline)

### Storage: S3 + EFS
- **S3 bucket**: Raw legal documents, uploaded veteran evidence (encrypted at rest with SSE-S3)
- **EFS mount**: ChromaDB persistent storage (shared across Fargate tasks)
- **Lifecycle**: S3 Intelligent-Tiering for archived documents

### Database: DynamoDB
- **Sessions table**: Replace in-memory SessionStore for production
  - Partition key: `session_id`
  - TTL attribute: auto-expire sessions (matches session_ttl_seconds)
  - Encryption: AWS-managed KMS key
- **Chat history**: Conversation turns stored as encrypted items

### Security
- **Secrets Manager**: Store ANTHROPIC_API_KEY, VOYAGE_API_KEY, ENCRYPTION_KEY
- **WAF**: Rate limiting (replaces app-level middleware), SQL injection protection
- **ALB**: HTTPS termination with ACM certificate
- **VPC**: Private subnets for Fargate tasks, NAT gateway for outbound API calls
- **IAM**: Least-privilege task roles (only S3 read/write, DynamoDB, Secrets)
- **CloudTrail**: Audit logging for all API access
- **KMS**: Customer-managed key for encrypting PII in DynamoDB and S3

### Monitoring
- **CloudWatch**: Application logs from Fargate (structured JSON logging)
- **CloudWatch Alarms**: Error rate > 5%, latency p99 > 10s, 5xx > 1%
- **X-Ray**: Distributed tracing (Anthropic API call latency tracking)

## Environment Variables (Production)

Set these in ECS Task Definition environment or Secrets Manager:

```
ANTHROPIC_API_KEY=<from Secrets Manager>
EMBEDDING_PROVIDER=voyageai
VOYAGE_API_KEY=<from Secrets Manager>
ENCRYPTION_KEY=<from Secrets Manager>
ALLOWED_ORIGINS=["https://valorassist.com"]
ENABLE_HSTS=true
RATE_LIMIT_MAX_REQUESTS=30
SESSION_TTL_SECONDS=3600
```

## Estimated Monthly Cost (moderate traffic)

| Service           | Estimate        |
|-------------------|-----------------|
| ECS Fargate (2 tasks) | ~$60        |
| ALB               | ~$20            |
| DynamoDB (on-demand)  | ~$5         |
| S3                 | ~$2            |
| CloudFront         | ~$10           |
| Secrets Manager    | ~$2            |
| NAT Gateway        | ~$35           |
| **Total**          | **~$134/mo**   |

*Anthropic API costs are usage-based and separate.*
