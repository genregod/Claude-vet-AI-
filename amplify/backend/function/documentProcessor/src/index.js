const AWS = require('aws-sdk');
const { BedrockRuntimeClient, InvokeModelCommand } = require('@aws-sdk/client-bedrock-runtime');

const s3 = new AWS.S3();
const dynamodb = new AWS.DynamoDB.DocumentClient();
const textract = new AWS.Textract();
const bedrock = new BedrockRuntimeClient({ region: process.env.AWS_REGION });

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    };

    try {
        const { fileName, userId, documentType } = JSON.parse(event.body);

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
    const params = {
        Document: {
            S3Object: {
                Bucket: process.env.STORAGE_BUCKET,
                Name: `public/${userId}/${fileName}`
            }
        }
    };

    const result = await textract.detectDocumentText(params).promise();
    return result.Blocks
        .filter(block => block.BlockType === 'LINE')
        .map(block => block.Text)
        .join('\n');
}

async function generateEmbeddings(text) {
    const params = {
        modelId: 'amazon.titan-embed-text-v1',
        contentType: 'application/json',
        accept: 'application/json',
        body: JSON.stringify({
            inputText: text
        })
    };

    const command = new InvokeModelCommand(params);
    const response = await bedrock.send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.body));

    return responseBody.embedding;
}

async function storeDocumentMetadata(userId, fileName, documentType, extractedText, embeddings) {
    const params = {
        TableName: process.env.DOCUMENTS_TABLE,
        Item: {
            userId: userId,
            documentId: `${userId}/${fileName}`,
            fileName: fileName,
            documentType: documentType,
            extractedText: extractedText,
            embeddings: embeddings,
            uploadDate: new Date().toISOString(),
            processed: true
        }
    };

    await dynamodb.put(params).promise();
}
