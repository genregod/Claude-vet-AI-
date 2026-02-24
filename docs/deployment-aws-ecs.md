# Deploying Valor Assist to AWS ECS (No-ALB Mode)

This guide covers deploying the Valor Assist backend (FastAPI, port 8000) to
AWS ECS Fargate using GitHub Actions.  No Application Load Balancer is required
for single-task or internal deployments — ECS tasks are accessed directly via
their assigned public or private IP.

---

## Prerequisites

| Resource | Notes |
|---|---|
| **ECR repository** | `valor-assist-backend` (region: `us-east-1`) |
| **ECS cluster** | `valor-assist-cluster` |
| **ECS service** | `valor-assist-backend` (task definition must expose port 8000) |
| **IAM role / user** | See [IAM Permissions](#iam-permissions) below |

---

## GitHub Secrets

Configure these secrets in **Settings → Secrets and variables → Actions**.

### Recommended: OIDC (no long-lived credentials)

| Secret | Value |
|---|---|
| `AWS_ROLE_TO_ASSUME` | ARN of the IAM role GitHub Actions will assume, e.g. `arn:aws:iam::123456789012:role/github-actions-valor-deploy` |

OIDC lets GitHub Actions obtain short-lived tokens automatically — no static
AWS keys are stored in the repository.  See [OIDC Setup](#oidc-setup) below.

### Fallback: Static IAM Access Keys

If OIDC cannot be configured, use long-lived credentials instead:

| Secret | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Access key ID for a dedicated deploy IAM user |
| `AWS_SECRET_ACCESS_KEY` | Corresponding secret access key |

> **Security note**: Rotate static keys regularly and never commit them to
> source code.  Prefer OIDC wherever possible.

---

## IAM Permissions

The GitHub Actions deploy identity (OIDC role **or** IAM user) requires the
following least-privilege policy.  Replace `<account-id>` and `<region>` with
your values.

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
        "ecr:PutImage"
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
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:RegisterTaskDefinition"
      ],
      "Resource": "*"
    },
    {
      "Sid": "PassTaskExecutionRole",
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole"
    }
  ]
}
```

> **OIDC adjustment**: attach this policy to the **assumed role** instead of an
> IAM user.  No additional permissions are needed; the OIDC trust relationship
> (see below) handles authentication.

---

## OIDC Setup

1. **Create an OIDC identity provider** in the AWS IAM console:
   - Provider URL: `https://token.actions.githubusercontent.com`
   - Audience: `sts.amazonaws.com`

2. **Create an IAM role** (`github-actions-valor-deploy`) with the following
   trust policy (replace `<org>/<repo>`):

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

4. **Add the GitHub secret** `AWS_ROLE_TO_ASSUME` with the role ARN.

---

## Dockerfile Reference

The backend Dockerfile is located at the repository root (`Dockerfile`).  Key
details relevant to ECS:

- **Base image**: `python:3.11-slim`
- **Exposed port**: `8000`
- **Start command**: `uvicorn app.server:app --host 0.0.0.0 --port 8000 --workers 2`
- **Health check**: `GET http://localhost:8000/health` (30 s interval, 5 s timeout)
- **Non-root user**: runs as `valoruser` (UID created at build time)

The ECS task definition's container port mapping must be `8000 → 8000`.

---

## Verification Steps

### 1 — Confirm the image was pushed to ECR

```bash
aws ecr list-images \
  --repository-name valor-assist-backend \
  --region us-east-1 \
  --query 'imageIds[*].imageTag' \
  --output table
```

You should see both the `latest` tag and the commit SHA tag (40-character hex).

### 2 — Check ECS service deployment status

```bash
aws ecs describe-services \
  --cluster valor-assist-cluster \
  --services valor-assist-backend \
  --region us-east-1 \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}'
```

`runningCount` should equal `desiredCount` once the deployment completes.
`update-service --force-new-deployment` triggers a rolling replacement of tasks.

### 3 — Wait for service stability (CI step mirrors this)

```bash
aws ecs wait services-stable \
  --cluster valor-assist-cluster \
  --services valor-assist-backend \
  --region us-east-1
```

This command blocks until all desired tasks are healthy or returns a non-zero
exit code on timeout (≈ 10 minutes).

### 4 — Verify task health

```bash
# Get the task ARN
TASK_ARN=$(aws ecs list-tasks \
  --cluster valor-assist-cluster \
  --service-name valor-assist-backend \
  --region us-east-1 \
  --query 'taskArns[0]' --output text)

# Describe the task
aws ecs describe-tasks \
  --cluster valor-assist-cluster \
  --tasks "$TASK_ARN" \
  --region us-east-1 \
  --query 'tasks[0].{LastStatus:lastStatus,Health:healthStatus,StopCode:stopCode}'
```

Expected output: `lastStatus: RUNNING`, `healthStatus: HEALTHY`.

### 5 — Hit the health endpoint directly (if public IP assigned)

```bash
# Get the public IP from the task's ENI
PUBLIC_IP=$(aws ec2 describe-network-interfaces \
  --filters Name=description,Values="*valor-assist-backend*" \
  --query 'NetworkInterfaces[0].Association.PublicIp' --output text)

curl http://$PUBLIC_IP:8000/health
# Expected: {"status":"healthy","service":"valor-assist"}
```

---

## Related Documents

- [`infrastructure/aws-architecture.md`](../infrastructure/aws-architecture.md) — full production architecture (VPC, DynamoDB, S3, Secrets Manager)
- [`.github/workflows/ci-cd.yml`](../.github/workflows/ci-cd.yml) — CI/CD pipeline (lint → build → push → deploy)
