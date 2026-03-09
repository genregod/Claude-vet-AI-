# Create the backend deployment scripts
mkdir -p backend

cat > backend/deploy_lambda_functions.py << 'EOF'
import boto3
import json
import zipfile
import os
from io import BytesIO

def deploy_all_lambda_functions():
    """Deploy all Valor Assist Lambda functions"""
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    iam_client = boto3.client('iam', region_name='us-east-1')
    
    # Create IAM role for Lambda functions
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        iam_client.create_role(
            RoleName='ValorAssistLambdaRole',
            AssumeRolePolicyDocument=json.dumps(trust_policy),
            Description='Role for Valor Assist Lambda functions'
        )
        
        # Attach policies
        iam_client.attach_role_policy(
            RoleName='ValorAssistLambdaRole',
            PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
        )
        iam_client.attach_role_policy(
            RoleName='ValorAssistLambdaRole',
            PolicyArn='arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess'
        )
        iam_client.attach_role_policy(
            RoleName='ValorAssistLambdaRole',
            PolicyArn='arn:aws:iam::aws:policy/AmazonS3FullAccess'
        )
        
        print("✅ Created IAM role")
    except Exception as e:
        print(f"IAM role exists or error: {e}")
    
    # Get role ARN
    role_arn = f"arn:aws:iam::{boto3.client('sts').get_caller_identity()['Account']}:role/ValorAssistLambdaRole"
    
    # Deploy each Lambda function
    functions = ['valor-assist-chat', 'valor-assist-auth', 'valor-assist-documents']
    
    for func_name in functions:
        try:
            # Create function code (you'd load your actual code here)
            code_content = get_function_code(func_name)
            
            lambda_client.create_function(
                FunctionName=func_name,
                Runtime='nodejs20.x',
                Role=role_arn,
                Handler='index.handler',
                Code={'ZipFile': code_content},
                Description=f'Valor Assist {func_name} function',
                Timeout=60,
                MemorySize=1024
            )
            print(f"✅ Created {func_name}")
            
        except lambda_client.exceptions.ResourceConflictException:
            # Update existing function
            lambda_client.update_function_code(
                FunctionName=func_name,
                ZipFile=code_content
            )
            print(f"✅ Updated {func_name}")
        except Exception as e:
            print(f"❌ Error with {func_name}: {e}")

def get_function_code(func_name):
    """Get the code for each function"""
    # This would contain your actual Lambda function code
    # For now, return a simple placeholder
    code = '''
exports.handler = async (event) => {
    return {
        statusCode: 200,
        headers: {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            message: 'Function deployed successfully',
            function: '%s'
        })
    };
};
''' % func_name
    
    # Create zip file
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        zip_file.writestr('index.js', code)
    
    return zip_buffer.getvalue()

if __name__ == "__main__":
    deploy_all_lambda_functions()
EOF

cat > backend/setup_api_gateway.py << 'EOF'
import boto3
import json

def setup_api_gateway():
    """Set up API Gateway for Valor Assist"""
    apigateway = boto3.client('apigateway', region_name='us-east-1')
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Create REST API
        api_response = apigateway.create_rest_api(
            name='valor-assist-api',
            description='Valor Assist API Gateway',
            endpointConfiguration={'types': ['REGIONAL']}
        )
        
        api_id = api_response['id']
        print(f"✅ Created API Gateway: {api_id}")
        
        # Get root resource
        resources = apigateway.get_resources(restApiId=api_id)
        root_id = resources['items'][0]['id']
        
        # Create /api resource
        api_resource = apigateway.create_resource(
            restApiId=api_id,
            parentId=root_id,
            pathPart='api'
        )
        
        # Create deployment
        apigateway.create_deployment(
            restApiId=api_id,
            stageName='prod'
        )
        
        # Save API endpoint
        endpoint = f"https://{api_id}.execute-api.us-east-1.amazonaws.com/prod"
        
        with open('api_endpoint.txt', 'w') as f:
            f.write(endpoint)
        
        print(f"✅ API Gateway deployed: {endpoint}")
        return endpoint
        
    except Exception as e:
        print(f"❌ Error setting up API Gateway: {e}")
        return None

if __name__ == "__main__":
    setup_api_gateway()
EOF

cat > backend/get_api_endpoint.py << 'EOF'
import json
import os

def get_api_endpoint():
    """Get the API endpoint for frontend configuration"""
    
    # Try to read from deployment
    if os.path.exists('api_endpoint.txt'):
        with open('api_endpoint.txt', 'r') as f:
            endpoint = f.read().strip()
    else:
        # Fallback to existing endpoint
        endpoint = "https://rsf5bpx04c.execute-api.us-east-1.amazonaws.com/prod"
    
    config = {
        "apiUrl": endpoint,
        "region": "us-east-1",
        "deployedAt": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    }
    
    print(json.dumps(config, indent=2))

if __name__ == "__main__":
    get_api_endpoint()
EOF

echo "✅ Backend deployment scripts created"
