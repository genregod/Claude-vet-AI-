const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, QueryCommand } = require('@aws-sdk/lib-dynamodb');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const ddbClient = new DynamoDBClient({ region: process.env.AWS_REGION });
const dynamodb = DynamoDBDocumentClient.from(ddbClient);
const bedrock = new BedrockRuntimeClient({ region: process.env.AWS_REGION });

const SYSTEM_PROMPT = `You are a helpful battle buddy assistant for veterans completing Federal Disability Questionnaires (FDQ).

Key traits:
- Speak like a supportive military peer, not overly formal
- Use clear, direct language without technical jargon
- Be encouraging and understanding of military experiences
- Focus on practical, actionable guidance
- Keep responses concise but thorough
- Show empathy for service-related challenges

Your role is to help veterans navigate the FDQ process, understand requirements, and organize their documentation effectively.`;

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    };

    // Handle CORS preflight
    if (event.httpMethod === 'OPTIONS') {
        return { statusCode: 200, headers, body: '' };
    }

    try {
        const { message, sessionId, userId } = JSON.parse(event.body);

        if (!message || !sessionId) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'message and sessionId are required' })
            };
        }

        // Get chat history
        const chatHistory = await getChatHistory(sessionId);

        // Build messages array (user/assistant only — system is separate)
        const messages = [
            ...chatHistory,
            { role: "user", content: message }
        ];

        // Call Anthropic Claude via Bedrock
        const response = await callClaude(messages);

        // Save conversation to DynamoDB
        await saveChatMessage(sessionId, userId, message, response);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                response: response,
                sessionId: sessionId
            })
        };

    } catch (error) {
        console.error('Error:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: 'Internal server error' })
        };
    }
};

async function callClaude(messages) {
    const params = {
        modelId: 'anthropic.claude-sonnet-4-20250514-v1:0',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({
            anthropic_version: "bedrock-2023-05-31",
            max_tokens: 1024,
            system: SYSTEM_PROMPT,
            messages: messages
        })
    };

    const command = new InvokeModelCommand(params);
    const response = await bedrock.send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));

    return responseBody.content[0].text;
}

async function getChatHistory(sessionId) {
    const command = new QueryCommand({
        TableName: process.env.CHAT_HISTORY_TABLE,
        KeyConditionExpression: 'sessionId = :sessionId',
        ExpressionAttributeValues: {
            ':sessionId': sessionId
        },
        ScanIndexForward: true,
        Limit: 10
    });

    const result = await dynamodb.send(command);
    return (result.Items || []).map(item => [
        { role: 'user', content: item.userMessage },
        { role: 'assistant', content: item.botResponse }
    ]).flat();
}

async function saveChatMessage(sessionId, userId, userMessage, botResponse) {
    const command = new PutCommand({
        TableName: process.env.CHAT_HISTORY_TABLE,
        Item: {
            sessionId: sessionId,
            timestamp: Date.now(),
            userId: userId || 'anonymous',
            userMessage: userMessage,
            botResponse: botResponse,
            ttl: Math.floor(Date.now() / 1000) + (30 * 24 * 60 * 60) // 30 day TTL
        }
    });

    await dynamodb.send(command);
}
