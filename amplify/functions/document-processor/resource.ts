import { defineFunction } from "@aws-amplify/backend";

/**
 * Document Processor Lambda — handles /documents/* routes.
 * Uses Textract for OCR, Bedrock for embeddings, S3 for storage,
 * and DynamoDB for document metadata.
 */
export const documentProcessorFunction = defineFunction({
  name: "valor-assist-doc-processor",
  entry: "../../backend/function/documentProcessor/src/index.js",
  runtime: 20, // Node.js 20.x
  timeoutSeconds: 120,
  memoryMB: 1024,
  environment: {
    DOCUMENTS_TABLE: "ValorAssist-Documents",
    STORAGE_BUCKET: "valor-assist-documents-1773005280",
    BEDROCK_MODEL_ID: "anthropic.claude-sonnet-4-20250514-v1:0",
  },
});
