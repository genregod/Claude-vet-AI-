/**
 * Valor Assist — Amplify Gen 2 Backend Reference Configuration
 *
 * This file documents the existing AWS infrastructure. The backend is
 * deployed independently (Lambda, API Gateway, Cognito, DynamoDB, S3)
 * and is NOT managed by Amplify Gen 2 pipeline-deploy.
 *
 * Amplify Hosting handles frontend CI/CD only.
 *
 * Existing resources:
 *   API Gateway:  https://rsf5bpx04c.execute-api.us-east-1.amazonaws.com/prod
 *   Cognito:      us-east-1_2Ec6BMJsE (client: 4u4gtq8o2cnvgaevh0hqc62cu9)
 *   S3 Bucket:    valor-assist-documents-1773005280
 *   DynamoDB:     ValorAssist-Users, ValorAssist-ChatSessions,
 *                 ValorAssist-Documents, ValorAssist-Claims,
 *                 ValorAssist-VectorStore
 *   Lambdas:      valor-assist-chat, valor-assist-auth, valor-assist-documents
 */

export const existingResources = {
  api: {
    endpoint: "https://rsf5bpx04c.execute-api.us-east-1.amazonaws.com/prod",
    id: "rsf5bpx04c",
    region: "us-east-1",
  },
  cognito: {
    userPoolId: "us-east-1_2Ec6BMJsE",
    userPoolClientId: "4u4gtq8o2cnvgaevh0hqc62cu9",
    identityPoolId: "us-east-1:e787e729-fced-4892-8d7b-a5fe72f53cbd",
  },
  s3: {
    documentsBucket: "valor-assist-documents-1773005280",
  },
  dynamodb: {
    users: "ValorAssist-Users",
    chatSessions: "ValorAssist-ChatSessions",
    documents: "ValorAssist-Documents",
    claims: "ValorAssist-Claims",
    vectorStore: "ValorAssist-VectorStore",
  },
  lambda: {
    chat: "valor-assist-chat",
    auth: "valor-assist-auth",
    documents: "valor-assist-documents",
  },
};
