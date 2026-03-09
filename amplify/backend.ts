import { defineBackend } from "@aws-amplify/backend";
import { Stack } from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";
import { auth } from "./auth/resource";
import { chatbotFunction } from "./functions/chatbot/resource";
import { documentProcessorFunction } from "./functions/document-processor/resource";

/**
 * Valor Assist — Amplify Gen 2 Backend
 *
 * Defines authentication, Lambda functions, and references existing
 * AWS resources (DynamoDB tables, S3 bucket, API Gateway).
 *
 * Existing backend API:
 *   https://rsf5bpx04c.execute-api.us-east-1.amazonaws.com/prod
 */
const backend = defineBackend({
  auth,
  chatbotFunction,
  documentProcessorFunction,
});

// ---------------------------------------------------------------------------
// Custom resource stack — references existing AWS infrastructure
// ---------------------------------------------------------------------------
const existingResourcesStack = backend.createStack("ExistingResources");
const region = Stack.of(existingResourcesStack).region;
const accountId = Stack.of(existingResourcesStack).account;

// --- Existing DynamoDB Tables ---
const chatSessionsTable = dynamodb.Table.fromTableAttributes(
  existingResourcesStack,
  "ChatSessionsTable",
  {
    tableName: "ValorAssist-ChatSessions",
    globalIndexes: ["userId-index"],
  }
);

const usersTable = dynamodb.Table.fromTableAttributes(
  existingResourcesStack,
  "UsersTable",
  {
    tableName: "ValorAssist-Users",
  }
);

const documentsTable = dynamodb.Table.fromTableAttributes(
  existingResourcesStack,
  "DocumentsTable",
  {
    tableName: "ValorAssist-Documents",
  }
);

const claimsTable = dynamodb.Table.fromTableAttributes(
  existingResourcesStack,
  "ClaimsTable",
  {
    tableName: "ValorAssist-Claims",
  }
);

const vectorStoreTable = dynamodb.Table.fromTableAttributes(
  existingResourcesStack,
  "VectorStoreTable",
  {
    tableName: "ValorAssist-VectorStore",
  }
);

// --- Existing S3 Bucket ---
const docsBucket = s3.Bucket.fromBucketName(
  existingResourcesStack,
  "DocsBucket",
  "valor-assist-docs"
);

// ---------------------------------------------------------------------------
// IAM permissions for Lambda functions
// ---------------------------------------------------------------------------

// Chatbot Lambda — DynamoDB + Bedrock
chatSessionsTable.grantReadWriteData(
  backend.chatbotFunction.resources.lambda
);
backend.chatbotFunction.resources.lambda.addToRolePolicy(
  new iam.PolicyStatement({
    actions: ["bedrock:InvokeModel"],
    resources: [
      `arn:aws:bedrock:${region}::foundation-model/anthropic.claude-sonnet-4-20250514-v1:0`,
    ],
  })
);

// Document Processor Lambda — DynamoDB + S3 + Textract + Bedrock
documentsTable.grantReadWriteData(
  backend.documentProcessorFunction.resources.lambda
);
docsBucket.grantReadWrite(
  backend.documentProcessorFunction.resources.lambda
);
backend.documentProcessorFunction.resources.lambda.addToRolePolicy(
  new iam.PolicyStatement({
    actions: [
      "textract:DetectDocumentText",
      "textract:AnalyzeDocument",
      "bedrock:InvokeModel",
    ],
    resources: ["*"],
  })
);

// ---------------------------------------------------------------------------
// Outputs — surface existing resource info to frontend via amplify_outputs.json
// ---------------------------------------------------------------------------
backend.addOutput({
  custom: {
    API: {
      ValorAssistAPI: {
        endpoint:
          "https://rsf5bpx04c.execute-api.us-east-1.amazonaws.com/prod",
        region: "us-east-1",
        apiName: "ValorAssistAPI",
      },
    },
    DynamoDB: {
      ChatSessions: "ValorAssist-ChatSessions",
      Users: "ValorAssist-Users",
      Documents: "ValorAssist-Documents",
      Claims: "ValorAssist-Claims",
      VectorStore: "ValorAssist-VectorStore",
    },
    S3: {
      DocsBucket: "valor-assist-docs",
    },
  },
});
