#!/usr/bin/env bash
# ── Valor Assist — AWS Infrastructure Setup ──────────────────────────
# One-time script to provision the AWS infrastructure for Valor Assist.
# Based on the valor-assist-final branch architecture.
#
# Prerequisites:
#   - AWS CLI v2 installed and configured (aws configure)
#   - Sufficient IAM permissions (VPC, ECS, ECR, ALB, Secrets Manager, IAM, CloudWatch)
#   - Copy scripts/aws_config.env.example → scripts/aws_config.env and fill in values
#
# Usage:
#   chmod +x scripts/setup_aws_infrastructure.sh
#   ./scripts/setup_aws_infrastructure.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/aws_config.env"

# ── Load configuration ───────────────────────────────────────────────
if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "ERROR: Config file not found: $CONFIG_FILE"
    echo "Copy scripts/aws_config.env.example → scripts/aws_config.env and fill in values."
    exit 1
fi
# shellcheck source=/dev/null
source "$CONFIG_FILE"

if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
    echo "ERROR: AWS_ACCOUNT_ID is not set in $CONFIG_FILE"
    exit 1
fi

TAG_ARGS="Key=Project,Value=${PROJECT_TAG} Key=Environment,Value=${ENVIRONMENT_TAG}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Valor Assist — AWS Infrastructure Setup                    ║"
echo "║  Region: ${AWS_REGION}                                      ║"
echo "║  Account: ${AWS_ACCOUNT_ID}                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# ── 1. ECR Repositories ──────────────────────────────────────────────
echo ""
echo "── Step 1/8: Creating ECR repositories ──"
for repo in "$ECR_REPOSITORY_BACKEND" "$ECR_REPOSITORY_FRONTEND"; do
    if aws ecr describe-repositories --repository-names "$repo" --region "$AWS_REGION" >/dev/null 2>&1; then
        echo "  ✓ ECR repository '$repo' already exists"
    else
        aws ecr create-repository \
            --repository-name "$repo" \
            --region "$AWS_REGION" \
            --image-scanning-configuration scanOnPush=true \
            --encryption-configuration encryptionType=AES256 \
            --tags Key=Project,Value="${PROJECT_TAG}" Key=Environment,Value="${ENVIRONMENT_TAG}" \
            >/dev/null
        echo "  ✓ Created ECR repository: $repo"
    fi

    # Set lifecycle policy to keep only last 10 images
    aws ecr put-lifecycle-policy \
        --repository-name "$repo" \
        --region "$AWS_REGION" \
        --lifecycle-policy-text '{
            "rules": [{
                "rulePriority": 1,
                "description": "Keep only last 10 images",
                "selection": {
                    "tagStatus": "any",
                    "countType": "imageCountMoreThan",
                    "countNumber": 10
                },
                "action": { "type": "expire" }
            }]
        }' >/dev/null
    echo "  ✓ Set lifecycle policy for $repo (keep last 10 images)"
done

# ── 2. VPC & Networking ──────────────────────────────────────────────
echo ""
echo "── Step 2/8: Creating VPC and networking ──"

VPC_ID=$(aws ec2 create-vpc \
    --cidr-block "$VPC_CIDR" \
    --region "$AWS_REGION" \
    --tag-specifications "ResourceType=vpc,Tags=[{Key=Name,Value=valor-assist-vpc},{${TAG_ARGS// /,}}]" \
    --query 'Vpc.VpcId' --output text)
echo "  ✓ Created VPC: $VPC_ID"

aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-support '{"Value":true}' --region "$AWS_REGION"
aws ec2 modify-vpc-attribute --vpc-id "$VPC_ID" --enable-dns-hostnames '{"Value":true}' --region "$AWS_REGION"

# Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
    --region "$AWS_REGION" \
    --tag-specifications "ResourceType=internet-gateway,Tags=[{Key=Name,Value=valor-assist-igw},{${TAG_ARGS// /,}}]" \
    --query 'InternetGateway.InternetGatewayId' --output text)
aws ec2 attach-internet-gateway --internet-gateway-id "$IGW_ID" --vpc-id "$VPC_ID" --region "$AWS_REGION"
echo "  ✓ Created and attached Internet Gateway: $IGW_ID"

# Get AZs
AZ1=$(aws ec2 describe-availability-zones --region "$AWS_REGION" --query 'AvailabilityZones[0].ZoneName' --output text)
AZ2=$(aws ec2 describe-availability-zones --region "$AWS_REGION" --query 'AvailabilityZones[1].ZoneName' --output text)

# Public subnets
PUB_SUBNET_1=$(aws ec2 create-subnet --vpc-id "$VPC_ID" --cidr-block "$SUBNET_PUBLIC_1_CIDR" \
    --availability-zone "$AZ1" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=valor-assist-public-1},{${TAG_ARGS// /,}}]" \
    --query 'Subnet.SubnetId' --output text)
PUB_SUBNET_2=$(aws ec2 create-subnet --vpc-id "$VPC_ID" --cidr-block "$SUBNET_PUBLIC_2_CIDR" \
    --availability-zone "$AZ2" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=valor-assist-public-2},{${TAG_ARGS// /,}}]" \
    --query 'Subnet.SubnetId' --output text)
echo "  ✓ Created public subnets: $PUB_SUBNET_1, $PUB_SUBNET_2"

# Private subnets
PRIV_SUBNET_1=$(aws ec2 create-subnet --vpc-id "$VPC_ID" --cidr-block "$SUBNET_PRIVATE_1_CIDR" \
    --availability-zone "$AZ1" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=valor-assist-private-1},{${TAG_ARGS// /,}}]" \
    --query 'Subnet.SubnetId' --output text)
PRIV_SUBNET_2=$(aws ec2 create-subnet --vpc-id "$VPC_ID" --cidr-block "$SUBNET_PRIVATE_2_CIDR" \
    --availability-zone "$AZ2" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=subnet,Tags=[{Key=Name,Value=valor-assist-private-2},{${TAG_ARGS// /,}}]" \
    --query 'Subnet.SubnetId' --output text)
echo "  ✓ Created private subnets: $PRIV_SUBNET_1, $PRIV_SUBNET_2"

# Route table for public subnets
PUB_RT=$(aws ec2 create-route-table --vpc-id "$VPC_ID" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=valor-assist-public-rt},{${TAG_ARGS// /,}}]" \
    --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id "$PUB_RT" --destination-cidr-block 0.0.0.0/0 --gateway-id "$IGW_ID" --region "$AWS_REGION" >/dev/null
aws ec2 associate-route-table --route-table-id "$PUB_RT" --subnet-id "$PUB_SUBNET_1" --region "$AWS_REGION" >/dev/null
aws ec2 associate-route-table --route-table-id "$PUB_RT" --subnet-id "$PUB_SUBNET_2" --region "$AWS_REGION" >/dev/null
echo "  ✓ Created public route table with internet gateway route"

# NAT Gateway for private subnets (outbound API calls)
EIP_ALLOC=$(aws ec2 allocate-address --domain vpc --region "$AWS_REGION" \
    --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=valor-assist-nat-eip},{${TAG_ARGS// /,}}]" \
    --query 'AllocationId' --output text)
NAT_GW=$(aws ec2 create-nat-gateway --subnet-id "$PUB_SUBNET_1" --allocation-id "$EIP_ALLOC" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=natgateway,Tags=[{Key=Name,Value=valor-assist-nat},{${TAG_ARGS// /,}}]" \
    --query 'NatGateway.NatGatewayId' --output text)
echo "  ✓ Created NAT Gateway: $NAT_GW (waiting for it to become available...)"
aws ec2 wait nat-gateway-available --nat-gateway-ids "$NAT_GW" --region "$AWS_REGION"

PRIV_RT=$(aws ec2 create-route-table --vpc-id "$VPC_ID" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=route-table,Tags=[{Key=Name,Value=valor-assist-private-rt},{${TAG_ARGS// /,}}]" \
    --query 'RouteTable.RouteTableId' --output text)
aws ec2 create-route --route-table-id "$PRIV_RT" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$NAT_GW" --region "$AWS_REGION" >/dev/null
aws ec2 associate-route-table --route-table-id "$PRIV_RT" --subnet-id "$PRIV_SUBNET_1" --region "$AWS_REGION" >/dev/null
aws ec2 associate-route-table --route-table-id "$PRIV_RT" --subnet-id "$PRIV_SUBNET_2" --region "$AWS_REGION" >/dev/null
echo "  ✓ Created private route table with NAT gateway route"

# ── 3. Security Groups ───────────────────────────────────────────────
echo ""
echo "── Step 3/8: Creating security groups ──"

ALB_SG=$(aws ec2 create-security-group \
    --group-name valor-assist-alb-sg \
    --description "ALB security group - allows HTTP/HTTPS inbound" \
    --vpc-id "$VPC_ID" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=valor-assist-alb-sg},{${TAG_ARGS// /,}}]" \
    --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id "$ALB_SG" --protocol tcp --port 80 --cidr 0.0.0.0/0 --region "$AWS_REGION" >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$ALB_SG" --protocol tcp --port 443 --cidr 0.0.0.0/0 --region "$AWS_REGION" >/dev/null
echo "  ✓ Created ALB security group: $ALB_SG (ports 80, 443)"

ECS_SG=$(aws ec2 create-security-group \
    --group-name valor-assist-ecs-sg \
    --description "ECS tasks security group - allows traffic from ALB only" \
    --vpc-id "$VPC_ID" --region "$AWS_REGION" \
    --tag-specifications "ResourceType=security-group,Tags=[{Key=Name,Value=valor-assist-ecs-sg},{${TAG_ARGS// /,}}]" \
    --query 'GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id "$ECS_SG" --protocol tcp --port 8000 --source-group "$ALB_SG" --region "$AWS_REGION" >/dev/null
aws ec2 authorize-security-group-ingress --group-id "$ECS_SG" --protocol tcp --port 80 --source-group "$ALB_SG" --region "$AWS_REGION" >/dev/null
echo "  ✓ Created ECS security group: $ECS_SG (ports 8000, 80 from ALB only)"

# ── 4. Application Load Balancer ──────────────────────────────────────
echo ""
echo "── Step 4/8: Creating Application Load Balancer ──"

ALB_ARN=$(aws elbv2 create-load-balancer \
    --name valor-assist-alb \
    --subnets "$PUB_SUBNET_1" "$PUB_SUBNET_2" \
    --security-groups "$ALB_SG" \
    --scheme internet-facing \
    --type application \
    --region "$AWS_REGION" \
    --tags Key=Project,Value="${PROJECT_TAG}" Key=Environment,Value="${ENVIRONMENT_TAG}" \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text)
echo "  ✓ Created ALB: $ALB_ARN"

# Backend target group (port 8000)
BACKEND_TG=$(aws elbv2 create-target-group \
    --name valor-assist-backend-tg \
    --protocol HTTP --port 8000 \
    --vpc-id "$VPC_ID" \
    --target-type ip \
    --health-check-path /health \
    --health-check-interval-seconds 30 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region "$AWS_REGION" \
    --tags Key=Project,Value="${PROJECT_TAG}" Key=Environment,Value="${ENVIRONMENT_TAG}" \
    --query 'TargetGroups[0].TargetGroupArn' --output text)
echo "  ✓ Created backend target group: $BACKEND_TG"

# Frontend target group (port 80)
FRONTEND_TG=$(aws elbv2 create-target-group \
    --name valor-assist-frontend-tg \
    --protocol HTTP --port 80 \
    --vpc-id "$VPC_ID" \
    --target-type ip \
    --health-check-path / \
    --health-check-interval-seconds 30 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region "$AWS_REGION" \
    --tags Key=Project,Value="${PROJECT_TAG}" Key=Environment,Value="${ENVIRONMENT_TAG}" \
    --query 'TargetGroups[0].TargetGroupArn' --output text)
echo "  ✓ Created frontend target group: $FRONTEND_TG"

# HTTP listener — default to frontend, /api/* to backend
aws elbv2 create-listener \
    --load-balancer-arn "$ALB_ARN" \
    --protocol HTTP --port 80 \
    --default-actions "Type=forward,TargetGroupArn=$FRONTEND_TG" \
    --region "$AWS_REGION" >/dev/null
echo "  ✓ Created HTTP listener (default → frontend)"

# Path-based routing: /api/* → backend
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" --region "$AWS_REGION" \
    --query 'Listeners[0].ListenerArn' --output text)
aws elbv2 create-rule \
    --listener-arn "$LISTENER_ARN" \
    --conditions "Field=path-pattern,Values=/api/*" \
    --priority 10 \
    --actions "Type=forward,TargetGroupArn=$BACKEND_TG" \
    --region "$AWS_REGION" >/dev/null
echo "  ✓ Added path-based rule: /api/* → backend target group"

# ── 5. Secrets Manager ───────────────────────────────────────────────
echo ""
echo "── Step 5/8: Setting up Secrets Manager ──"

SECRET_NAME="valor-assist/production"
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --region "$AWS_REGION" >/dev/null 2>&1; then
    echo "  ✓ Secret '$SECRET_NAME' already exists (update manually via AWS Console or CLI)"
else
    aws secretsmanager create-secret \
        --name "$SECRET_NAME" \
        --description "Valor Assist production secrets" \
        --secret-string '{
            "ANTHROPIC_API_KEY": "REPLACE_ME",
            "VOYAGE_API_KEY": "REPLACE_ME",
            "ENCRYPTION_KEY": "REPLACE_ME",
            "JWT_SECRET_KEY": "REPLACE_ME"
        }' \
        --region "$AWS_REGION" \
        --tags Key=Project,Value="${PROJECT_TAG}" Key=Environment,Value="${ENVIRONMENT_TAG}" \
        >/dev/null
    echo "  ✓ Created secret: $SECRET_NAME"
    echo "    ⚠  Update the secret values: aws secretsmanager update-secret --secret-id $SECRET_NAME --secret-string '...'"
fi

# ── 6. IAM Roles ─────────────────────────────────────────────────────
echo ""
echo "── Step 6/8: Creating IAM roles ──"

# ECS Task Execution Role (for pulling images, logging)
EXEC_ROLE_NAME="valorAssistEcsTaskExecutionRole"
if aws iam get-role --role-name "$EXEC_ROLE_NAME" >/dev/null 2>&1; then
    echo "  ✓ Execution role '$EXEC_ROLE_NAME' already exists"
else
    aws iam create-role \
        --role-name "$EXEC_ROLE_NAME" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' \
        --tags Key=Project,Value="${PROJECT_TAG}" Key=Environment,Value="${ENVIRONMENT_TAG}" \
        >/dev/null
    aws iam attach-role-policy --role-name "$EXEC_ROLE_NAME" \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    echo "  ✓ Created ECS task execution role: $EXEC_ROLE_NAME"
fi

# ECS Task Role (for app-level permissions: S3, DynamoDB, Secrets Manager)
TASK_ROLE_NAME="valorAssistEcsTaskRole"
if aws iam get-role --role-name "$TASK_ROLE_NAME" >/dev/null 2>&1; then
    echo "  ✓ Task role '$TASK_ROLE_NAME' already exists"
else
    aws iam create-role \
        --role-name "$TASK_ROLE_NAME" \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' \
        --tags Key=Project,Value="${PROJECT_TAG}" Key=Environment,Value="${ENVIRONMENT_TAG}" \
        >/dev/null

    # Inline policy: least-privilege access to Secrets Manager
    aws iam put-role-policy \
        --role-name "$TASK_ROLE_NAME" \
        --policy-name "ValorAssistSecretsAccess" \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [{
                \"Effect\": \"Allow\",
                \"Action\": [\"secretsmanager:GetSecretValue\"],
                \"Resource\": \"arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:${SECRET_NAME}*\"
            }]
        }"
    echo "  ✓ Created ECS task role: $TASK_ROLE_NAME"
fi

# ── 7. ECS Cluster ───────────────────────────────────────────────────
echo ""
echo "── Step 7/8: Creating ECS cluster ──"

if aws ecs describe-clusters --clusters "$ECS_CLUSTER_NAME" --region "$AWS_REGION" \
    --query 'clusters[?status==`ACTIVE`].clusterName' --output text | grep -q "$ECS_CLUSTER_NAME"; then
    echo "  ✓ ECS cluster '$ECS_CLUSTER_NAME' already exists"
else
    aws ecs create-cluster \
        --cluster-name "$ECS_CLUSTER_NAME" \
        --capacity-providers FARGATE \
        --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
        --setting name=containerInsights,value=enabled \
        --region "$AWS_REGION" \
        --tags key=Project,value="${PROJECT_TAG}" key=Environment,value="${ENVIRONMENT_TAG}" \
        >/dev/null
    echo "  ✓ Created ECS cluster: $ECS_CLUSTER_NAME"
fi

# ── 8. CloudWatch Log Groups ─────────────────────────────────────────
echo ""
echo "── Step 8/8: Creating CloudWatch log groups ──"

for log_group in "/ecs/valor-assist-backend" "/ecs/valor-assist-frontend"; do
    if aws logs describe-log-groups --log-group-name-prefix "$log_group" --region "$AWS_REGION" \
        --query 'logGroups[?logGroupName==`'"$log_group"'`].logGroupName' --output text | grep -q "$log_group"; then
        echo "  ✓ Log group '$log_group' already exists"
    else
        aws logs create-log-group --log-group-name "$log_group" --region "$AWS_REGION"
        aws logs put-retention-policy --log-group-name "$log_group" --retention-in-days 30 --region "$AWS_REGION"
        echo "  ✓ Created log group: $log_group (30-day retention)"
    fi
done

# ── Summary ───────────────────────────────────────────────────────────
ALB_DNS=$(aws elbv2 describe-load-balancers --names valor-assist-alb --region "$AWS_REGION" \
    --query 'LoadBalancers[0].DNSName' --output text 2>/dev/null || echo "PENDING")

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  Infrastructure setup complete!                             ║"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  VPC:           $VPC_ID"
echo "║  ALB:           $ALB_DNS"
echo "║  ECS Cluster:   $ECS_CLUSTER_NAME"
echo "║  ECR Backend:   $ECR_REGISTRY/$ECR_REPOSITORY_BACKEND"
echo "║  ECR Frontend:  $ECR_REGISTRY/$ECR_REPOSITORY_FRONTEND"
echo "║  Secrets:       $SECRET_NAME"
echo "╠══════════════════════════════════════════════════════════════╣"
echo "║  Next steps:                                                ║"
echo "║  1. Update secrets: aws secretsmanager update-secret ...    ║"
echo "║  2. Deploy: ./scripts/deploy_aws.sh                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"

# Save resource IDs for deploy script
cat > "${SCRIPT_DIR}/aws_resources.env" << EOF
# Auto-generated by setup_aws_infrastructure.sh — do not edit manually
VPC_ID=$VPC_ID
PUB_SUBNET_1=$PUB_SUBNET_1
PUB_SUBNET_2=$PUB_SUBNET_2
PRIV_SUBNET_1=$PRIV_SUBNET_1
PRIV_SUBNET_2=$PRIV_SUBNET_2
ALB_SG=$ALB_SG
ECS_SG=$ECS_SG
ALB_ARN=$ALB_ARN
BACKEND_TG=$BACKEND_TG
FRONTEND_TG=$FRONTEND_TG
EXEC_ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/${EXEC_ROLE_NAME}
TASK_ROLE_ARN=arn:aws:iam::${AWS_ACCOUNT_ID}:role/${TASK_ROLE_NAME}
SECRET_NAME=$SECRET_NAME
EOF
echo ""
echo "Resource IDs saved to: ${SCRIPT_DIR}/aws_resources.env"
