const { S3Client, GetObjectCommand } = require('@aws-sdk/client-s3');
const { TextractClient, DetectDocumentTextCommand } = require('@aws-sdk/client-textract');
const AWS = require('aws-sdk');

const s3 = new S3Client({ region: process.env.AWS_REGION });
const textract = new TextractClient({ region: process.env.AWS_REGION });
const dynamodb = new AWS.DynamoDB.DocumentClient();

exports.handler = async (event) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    };

    // Handle S3 trigger events (auto-processing on upload)
    if (event.Records) {
        return handleS3Trigger(event);
    }

    // Handle API Gateway events (manual processing requests)
    try {
        const { documentId, userId, bucket, key } = JSON.parse(event.body);

        if (!documentId || !userId || !bucket || !key) {
            return {
                statusCode: 400,
                headers,
                body: JSON.stringify({ error: 'Missing required fields: documentId, userId, bucket, key' })
            };
        }

        const result = await processDocument(bucket, key, userId, documentId);

        return {
            statusCode: 200,
            headers,
            body: JSON.stringify(result)
        };
    } catch (error) {
        console.error('Error processing document:', error);
        return {
            statusCode: 500,
            headers,
            body: JSON.stringify({ error: 'Failed to process document' })
        };
    }
};

/**
 * Handle S3 trigger — auto-process documents on upload.
 */
async function handleS3Trigger(event) {
    for (const record of event.Records) {
        const bucket = record.s3.bucket.name;
        const key = decodeURIComponent(record.s3.object.key.replace(/\+/g, ' '));

        // Extract userId from S3 key path: private/{userId}/{documentId}/{filename}
        const keyParts = key.split('/');
        if (keyParts.length < 4 || keyParts[0] !== 'private') {
            console.log('Skipping non-user upload:', key);
            continue;
        }

        const userId = keyParts[1];
        const documentId = keyParts[2];

        try {
            await processDocument(bucket, key, userId, documentId);
            console.log(`Processed document: ${key}`);
        } catch (error) {
            console.error(`Failed to process ${key}:`, error);
        }
    }

    return { statusCode: 200, body: 'Processing complete' };
}

/**
 * Process a document: extract text via Textract, store metadata in DynamoDB.
 */
async function processDocument(bucket, key, userId, documentId) {
    // Extract text from the document using Textract
    const extractedText = await extractText(bucket, key);

    // Classify the document type based on content
    const documentType = classifyDocument(extractedText);

    // Store document metadata in DynamoDB
    const metadata = {
        userId,
        documentId,
        s3Bucket: bucket,
        s3Key: key,
        documentType,
        extractedTextPreview: extractedText.substring(0, 500),
        textLength: extractedText.length,
        status: 'processed',
        processedAt: Date.now(),
        createdAt: Date.now()
    };

    await dynamodb.put({
        TableName: process.env.DOCUMENTS_TABLE,
        Item: metadata
    }).promise();

    return {
        documentId,
        documentType,
        status: 'processed',
        textLength: extractedText.length
    };
}

/**
 * Extract text from a document stored in S3 using Textract.
 */
async function extractText(bucket, key) {
    try {
        const command = new DetectDocumentTextCommand({
            Document: {
                S3Object: {
                    Bucket: bucket,
                    Name: key
                }
            }
        });

        const response = await textract.send(command);

        return response.Blocks
            .filter(block => block.BlockType === 'LINE')
            .map(block => block.Text)
            .join('\n');
    } catch (error) {
        console.error('Textract extraction failed:', error);
        // Return empty string on failure — document is still stored in S3
        return '';
    }
}

/**
 * Simple heuristic classifier for common veteran document types.
 */
function classifyDocument(text) {
    const lowerText = text.toLowerCase();

    if (lowerText.includes('disability benefits questionnaire') || lowerText.includes('dbq')) {
        return 'DBQ';
    }
    if (lowerText.includes('dd-214') || lowerText.includes('dd form 214') || lowerText.includes('certificate of release')) {
        return 'DD214';
    }
    if (lowerText.includes('service treatment record') || lowerText.includes('medical record')) {
        return 'MEDICAL_RECORD';
    }
    if (lowerText.includes('rating decision') || lowerText.includes('compensation and pension')) {
        return 'RATING_DECISION';
    }
    if (lowerText.includes('nexus letter') || lowerText.includes('medical opinion')) {
        return 'NEXUS_LETTER';
    }
    if (lowerText.includes('buddy statement') || lowerText.includes('lay statement')) {
        return 'BUDDY_STATEMENT';
    }

    return 'OTHER';
}
