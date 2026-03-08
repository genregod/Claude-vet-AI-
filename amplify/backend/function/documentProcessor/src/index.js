const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');
const { TextractClient, DetectDocumentTextCommand } = require('@aws-sdk/client-textract');
const { DynamoDBClient } = require('@aws-sdk/client-dynamodb');
const { DynamoDBDocumentClient, PutCommand } = require('@aws-sdk/lib-dynamodb');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const region = process.env.AWS_REGION;
const s3 = new S3Client({ region });
const textract = new TextractClient({ region });
const ddbClient = new DynamoDBClient({ region });
const dynamodb = DynamoDBDocumentClient.from(ddbClient);
const bedrock = new BedrockRuntimeClient({ region });

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
        const { fileName, userId, documentType } = JSON.parse(event.body);

        if (!fileName || !userId) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'fileName and userId are required' })
            };
        }

        // Process document with Textract
        const extractedText = await extractTextFromDocument(fileName, userId);

        // Generate embeddings for RAG
        const embeddings = await generateEmbeddings(extractedText);

        // Store document metadata
        await storeDocumentMetadata(userId, fileName, documentType, extractedText, embeddings);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                message: 'Document processed successfully',
                documentId: `${userId}/${fileName}`
            })
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

async function extractTextFromDocument(fileName, userId) {
    const command = new DetectDocumentTextCommand({
        Document: {
            S3Object: {
                Bucket: process.env.STORAGE_BUCKET,
                Name: `private/${userId}/${fileName}`
            }
        }
    });

    const result = await textract.send(command);
    return (result.Blocks || [])
        .filter(block => block.BlockType === 'LINE')
        .map(block => block.Text)
        .join('\n');
}

async function generateEmbeddings(text) {
    const command = new InvokeModelCommand({
        modelId: 'amazon.titan-embed-text-v1',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({
            inputText: text.substring(0, 8000) // Titan embed limit
        })
    });

    const response = await bedrock.send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));

    return responseBody.embedding;
}

async function storeDocumentMetadata(userId, fileName, documentType, extractedText, embeddings) {
    const command = new PutCommand({
        TableName: process.env.DOCUMENTS_TABLE,
        Item: {
            userId: userId,
            documentId: `${userId}/${fileName}`,
            fileName: fileName,
            documentType: documentType || 'unknown',
            extractedText: extractedText,
            embeddings: embeddings,
            uploadDate: new Date().toISOString(),
            processed: true
        }
    });

    await dynamodb.send(command);
}
