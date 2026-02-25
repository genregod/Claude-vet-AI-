# Frontend ECS Service Setup

The CI/CD pipeline deploys to `valor-assist-prod-frontend-svc` on the `valor-assist-prod-cluster`
ECS cluster. This service does **not yet exist** and must be created in AWS before the frontend
deploy step in the pipeline will succeed.

## Prerequisites

- AWS CLI configured with appropriate IAM permissions
- The `valor-assist-frontend` ECR repository must exist and have at least one image pushed
  (the CI/CD pipeline will push one on the next `main` push after this PR merges)
- A VPC, subnets, and security group already used by the backend service
  (reuse the same ones from `valor-assist-prod-backend-svc`)

## Step 1: Register the Frontend Task Definition

```bash
aws ecs register-task-definition \
  --family valor-assist-prod-frontend \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu 512 \
  --memory 1024 \
  --execution-role-arn arn:aws:iam::973028704465:role/ecsTaskExecutionRole \
  --container-definitions '[
    {
      "name": "valor-assist-frontend",
      "image": "973028704465.dkr.ecr.us-east-1.amazonaws.com/valor-assist-frontend:latest",
      "portMappings": [
        {
          "containerPort": 80,
          "protocol": "tcp"
        }
      ],
      "essential": true,
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/valor-assist-prod-frontend",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]' \
  --region us-east-1
```

## Step 2: Create the CloudWatch Log Group

```bash
aws logs create-log-group \
  --log-group-name /ecs/valor-assist-prod-frontend \
  --region us-east-1
```

## Step 3: Create the ECS Service

Replace `<SUBNET_ID_1>`, `<SUBNET_ID_2>`, and `<SECURITY_GROUP_ID>` with the values
used by your existing `valor-assist-prod-backend-svc` service. You can find these in
the AWS Console under ECS → Clusters → valor-assist-prod-cluster → valor-assist-prod-backend-svc → Configuration.

```bash
aws ecs create-service \
  --cluster valor-assist-prod-cluster \
  --service-name valor-assist-prod-frontend-svc \
  --task-definition valor-assist-prod-frontend \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<SUBNET_ID_1>,<SUBNET_ID_2>],securityGroups=[<SECURITY_GROUP_ID>],assignPublicIp=ENABLED}" \
  --region us-east-1
```

## Step 4: Verify the Service

```bash
aws ecs describe-services \
  --cluster valor-assist-prod-cluster \
  --services valor-assist-prod-frontend-svc \
  --region us-east-1
```

Once the service shows `status: ACTIVE` and `runningCount: 1`, the CI/CD pipeline's
frontend deploy step will succeed on the next push to `main`.
