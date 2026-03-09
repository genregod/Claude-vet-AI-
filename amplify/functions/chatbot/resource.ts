import { defineFunction } from "@aws-amplify/backend";

/**
 * Chatbot Lambda — handles /chat/* routes.
 * Uses Bedrock Claude for AI responses and DynamoDB for chat history.
 */
export const chatbotFunction = defineFunction({
  name: "valor-assist-chatbot",
  entry: "../../backend/function/chatbot/src/index.js",
  runtime: 20, // Node.js 20.x
  timeoutSeconds: 30,
  memoryMB: 512,
  environment: {
    CHAT_TABLE_NAME: "ValorAssist-ChatSessions",
    BEDROCK_MODEL_ID: "anthropic.claude-sonnet-4-20250514-v1:0",
  },
});
