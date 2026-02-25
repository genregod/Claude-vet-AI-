# Deploying Valor Assist to AWS ECS (No-ALB Mode)

This guide covers deploying the Valor Assist backend and frontend to
AWS ECS Fargate using GitHub Actions.  No Application Load Balancer is required
for single-task or internal deployments — ECS tasks are accessed directly via
their assigned public or private IP.

---

## Prerequisites

| Resource | Notes |
|---|---|
| **ECR repositories** | `valor-assist-backend`, `valor-assist-frontend` (region: `us-east-1`) — auto-created by CI if missing |
| **ECS cluster** | `valor-assist-cluster` — auto-created by CI if missing |
| **ECS services** | `valor-assist-backend`, `valor-assist-frontend` — auto-created by CI if missing |
| **IAM role** | See [IAM Permissions](#iam-permissions) below |

---

## GitHub Repository Variables

Configure these under **Settings → Secrets and variables → Actions → Variables**
(not Secrets).

### Required

| Variable | Value |
|---|---|
| `AWS_ROLE_TO_ASSUME` | ARN of the IAM role GitHub Actions will assume via OIDC, e.g. `arn:aws:iam::123456789012:role/github-actions-valor-deploy` |
| `ECS_TASK_EXECUTION_ROLE_ARN` | ARN of the ECS task execution role, e.g. `arn:aws:iam::123456789012:role/ecsTaskExecutionRole` |

### Optional (networking)

| Variable | Value |
|---|---|
| `ECS_SUBNET_IDS` | Comma-separated subnet IDs for ECS tasks. If omitted, the CI pipeline discovers default VPC subnets automatically. |
| `ECS_SECURITY_GROUP_ID` | Security group ID for ECS tasks. If omitted, the default VPC security group is used. |

> **Note:** OIDC authentication is used — no long-lived `AWS_ACCESS_KEY_ID` /
> `AWS_SECRET_ACCESS_KEY` secrets are required.

---

## IAM Permissions

The GitHub Actions deploy identity (OIDC role) requires the following
least-privilege policy.  Replace `<account-id>` and `<region>` with your values.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "ECRImagePush",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage",
        "ecr:DescribeRepositories",
        "ecr:CreateRepository"
      ],
      "Resource": [
        "arn:aws:ecr:<region>:<account-id>:repository/valor-assist-backend",
        "arn:aws:ecr:<region>:<account-id>:repository/valor-assist-frontend"
      ]
    },
    {
      "Sid": "ECSDeployment",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCluster",
        "ecs:DescribeClusters",
        "ecs:CreateService",
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition",
        "ecs:ListTasks",
        "ecs:DescribeTasks"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassTaskExecutionRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole"
    },
    {
      "Sid": "NetworkDiscovery",
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVpcs",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## OIDC Setup

1. **Create an OIDC identity provider** in the AWS IAM console:
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`

2. **Create an IAM role** (`github-actions-valor-deploy`) with the following
   trust policy:

   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Principal": {
           "Federated": "arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com"
         },
         "Action": "sts:AssumeRoleWithWebIdentity",
         "Condition": {
           "StringEquals": {
             "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
           },
           "StringLike": {
             "token.actions.githubusercontent.com:sub": "repo:genregod/Claude-vet-AI-:ref:refs/heads/main"
           }
         }
       }
     ]
   }
   ```

3. **Attach the least-privilege policy** from [IAM Permissions](#iam-permissions)
   to this role.

4. **Add the GitHub repository variable** `AWS_ROLE_TO_ASSUME` with the role ARN.

---

## CI/CD Pipeline Overview

The pipeline (`.github/workflows/ci-cd.yml`) has three jobs:

1. **test** — Runs on every push and PR: Python linting (ruff), TypeScript
   checks, and frontend build.
2. **build-and-push** — After tests pass, builds backend and frontend Docker
   images and pushes to ECR. Auto-creates ECR repositories if missing.
3. **deploy** — Registers ECS task definitions, ensures the ECS cluster exists,
   creates or updates services, and waits for stability.

### Trigger conditions

| Event | test | build-and-push | deploy |
|---|---|---|---|
| Push to `main` or `develop` | ✅ | ✅ | ✅ |
| PR targeting `main` | ✅ | ✅ | ✅ |
| `workflow_dispatch` (manual) | ✅ | ✅ | ✅ |

---

## Dockerfile Reference

### Backend (`Dockerfile` at repo root)

- **Base image**: `python:3.11-slim`
- **Exposed port**: `8000`
- **Start command**: `uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 2`
- **Health check**: `GET http://localhost:8000/health` (30 s interval, 5 s timeout)
- **Non-root user**: runs as `valoruser`

### Frontend (`frontend/Dockerfile`)

- **Build stage**: `node:20-alpine` — installs deps, runs `npm run build`
- **Serve stage**: `nginx:alpine` — serves static files
- **Exposed port**: `80`

---

## Verification Steps

### 1 — Confirm images were pushed to ECR

```bash
aws ecr list-images \
  --repository-name valor-assist-backend \
  --region us-east-1 \
  --query 'imageIds[*].imageTag' \
  --output table
```

### 2 — Check ECS service deployment status

```bash
aws ecs describe-services \
  --cluster valor-assist-cluster \
  --services valor-assist-backend valor-assist-frontend \
  --region us-east-1 \
  --query 'services[*].{Name:serviceName,Status:status,Running:runningCount,Desired:desiredCount}'
```

### 3 — Wait for service stability

```bash
aws ecs wait services-stable \
  --cluster valor-assist-cluster \
  --services valor-assist-backend valor-assist-frontend \
  --region us-east-1
```

### 4 — Hit the health endpoint directly

```bash
TASK_ARN=$(aws ecs list-tasks \
  --cluster valor-assist-cluster \
  --service-name valor-assist-backend \
  --region us-east-1 \
  --query 'taskArns[0]' --output text)

ENI_ID=$(aws ecs describe-tasks \
  --cluster valor-assist-cluster \
  --tasks "$TASK_ARN" \
  --region us-east-1 \
  --query 'tasks[0].attachments[0].details[?name==`networkInterfaceId`].value' --output text)

PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --network-interface-ids "$ENI_ID" \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

curl http://$PUBLIC_IP:8000/health
# Expected: {"status":"healthy","service":"valor-assist"}
```

---

## Related Documents

- [`infrastructure/aws-architecture.md`](../infrastructure/aws-architecture.md) — full production architecture
- [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) — CI/CD pipeline
- [`.github/workflows/security-audit.yml`](../.github/workflows/security-audit.yml) — weekly security scanning
