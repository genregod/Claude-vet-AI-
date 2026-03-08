const AWS = require('aws-sdk');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const dynamodb = new AWS.DynamoDB.DocumentClient();
const bedrock = new BedrockRuntimeClient({ region: process.env.AWS_REGION });

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    };

    try {
        const { message, sessionId, userId } = JSON.parse(event.body);

        // Get chat history
        const chatHistory = await getChatHistory(sessionId);

        // Prepare context for battle buddy persona
        const systemPrompt = `You are a helpful battle buddy assistant for veterans completing Federal Disability Questionnaires (FDQ).

Key traits:
- Speak like a supportive military peer, not overly formal
- Use clear, direct language without technical jargon
- Be encouraging and understanding of military experiences
- Focus on practical, actionable guidance
- Keep responses concise but thorough
- Show empathy for service-related challenges

Your role is to help veterans navigate the FDQ process, understand requirements, and organize their documentation effectively.`;

        // Prepare messages for Claude
        const messages = [
            { role: "system", content: systemPrompt },
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
        modelId: 'anthropic.claude-3-sonnet-20240229-v1:0',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({
            anthropic_version: "bedrock-2023-05-31",
            max_tokens: 1000,
            messages: messages.filter(m => m.role !== 'system'),
            system: messages.find(m => m.role === 'system')?.content
        })
    };

    const command = new InvokeModelCommand(params);
    const response = await bedrock.send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));

    return responseBody.content[0].text;
}

async function getChatHistory(sessionId) {
    const params = {
        TableName: process.env.CHAT_HISTORY_TABLE,
        KeyConditionExpression: 'sessionId = :sessionId',
        ExpressionAttributeValues: {
            ':sessionId': sessionId
        },
        ScanIndexForward: true,
        Limit: 10
    };

    const result = await dynamodb.query(params).promise();
    return result.Items.map(item => [
        { role: 'user', content: item.userMessage },
        { role: 'assistant', content: item.botResponse }
    ]).flat();
}

async function saveChatMessage(sessionId, userId, userMessage, botResponse) {
    const params = {
        TableName: process.env.CHAT_HISTORY_TABLE,
        Item: {
            sessionId: sessionId,
            timestamp: Date.now(),
            userId: userId,
            userMessage: userMessage,
            botResponse: botResponse
        }
    };

    await dynamodb.put(params).promise();
}
