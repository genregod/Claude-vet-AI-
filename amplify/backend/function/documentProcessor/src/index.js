const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand, ScanCommand } = require('@aws-sdk/lib-dynamodb');
const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');
const { TextractClient, DetectDocumentTextCommand } = require('@aws-sdk/client-textract');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const dynamo = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const s3 = new S3Client({});
const textract = new TextractClient({});
const bedrock = new BedrockRuntimeClient({ region: process.env.AWS_REGION });

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    };

    try {
        const body = JSON.parse(event.body);

        // Route by action
        if (event.httpMethod === 'GET' || body.action === 'list') {
            return await handleListDocuments(event, headers);
        }

        const { fileName, userId, documentType } = body;
        const extractedText = await extractTextFromDocument(fileName, userId);
        const embeddings = await generateEmbeddings(extractedText);
        await storeDocumentMetadata(userId, fileName, documentType, extractedText, embeddings);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({ message: 'Document processed successfully', documentId: `${userId}/${fileName}` })
        };

    } catch (error) {
        console.error('Error processing document:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: 'Document processing failed' })
        };
    }
};

async function handleListDocuments(event, headers) {
    const userId = event.queryStringParameters?.userId;
    const result = await dynamo.send(new ScanCommand({
        TableName: process.env.DOCUMENTS_TABLE,
        FilterExpression: 'userId = :uid',
        ExpressionAttributeValues: { ':uid': userId }
    }));
    return { statusCode: 200, headers, body: JSON.stringify({ documents: result.Items }) };
}

async function extractTextFromDocument(fileName, userId) {
    const result = await textract.send(new DetectDocumentTextCommand({
        Document: {
            S3Object: { Bucket: process.env.STORAGE_BUCKET, Name: `public/${userId}/${fileName}` }
        }
    }));
    return result.Blocks
        .filter(block => block.BlockType === 'LINE')
        .map(block => block.Text)
        .join('\n');
}

async function generateEmbeddings(text) {
    const command = new InvokeModelCommand({
        modelId: 'amazon.titan-embed-text-v1',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({ inputText: text })
    });
    const response = await bedrock.send(command);
    return JSON.parse(new TextDecoder().decode(response.body)).embedding;
}

async function storeDocumentMetadata(userId, fileName, documentType, extractedText, embeddings) {
    await dynamo.send(new PutCommand({
        TableName: process.env.DOCUMENTS_TABLE,
        Item: {
            userId, documentId: `${userId}/${fileName}`, fileName,
            documentType, extractedText, embeddings,
            uploadDate: new Date().toISOString(), processed: true
        }
    }));
}
