const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, QueryCommand, PutCommand } = require('@aws-sdk/lib-dynamodb');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const dynamo = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const bedrock = new BedrockRuntimeClient({ region: process.env.AWS_REGION });

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    };

    try {
        const { message, sessionId, userId } = JSON.parse(event.body);

        const chatHistory = await getChatHistory(sessionId);

        const systemPrompt = `You are a helpful battle buddy assistant for veterans completing Federal Disability Questionnaires (FDQ).

Key traits:
- Speak like a supportive military peer, not overly formal
- Use clear, direct language without technical jargon
- Be encouraging and understanding of military experiences
- Focus on practical, actionable guidance
- Keep responses concise but thorough
- Show empathy for service-related challenges

Your role is to help veterans navigate the FDQ process, understand requirements, and organize their documentation effectively.`;

        const messages = [
            { role: "system", content: systemPrompt },
            ...chatHistory,
            { role: "user", content: message }
        ];

        const response = await callClaude(messages);
        await saveChatMessage(sessionId, userId, message, response);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({ response, sessionId })
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
    const command = new InvokeModelCommand({
        modelId: 'anthropic.claude-3-sonnet-20240229-v1:0',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({
            anthropic_version: "bedrock-2023-05-31",
            max_tokens: 1000,
            messages: messages.filter(m => m.role !== 'system'),
            system: messages.find(m => m.role === 'system')?.content
        })
    });
    const response = await bedrock.send(command);
    return JSON.parse(new TextDecoder().decode(response.body)).content[0].text;
}

async function getChatHistory(sessionId) {
    const result = await dynamo.send(new QueryCommand({
        TableName: process.env.CHAT_HISTORY_TABLE,
        KeyConditionExpression: 'sessionId = :sessionId',
        ExpressionAttributeValues: { ':sessionId': sessionId },
        ScanIndexForward: true,
        Limit: 10
    }));
    return result.Items.flatMap(item => [
        { role: 'user', content: item.userMessage },
        { role: 'assistant', content: item.botResponse }
    ]);
}

async function saveChatMessage(sessionId, userId, userMessage, botResponse) {
    await dynamo.send(new PutCommand({
        TableName: process.env.CHAT_HISTORY_TABLE,
        Item: { sessionId, timestamp: Date.now(), userId, userMessage, botResponse }
    }));
}
