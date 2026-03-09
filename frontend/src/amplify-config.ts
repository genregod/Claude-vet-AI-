/**
 * Valor Assist — AWS Amplify Configuration
 *
 * Configures Amplify with Cognito Auth, API Gateway, and S3 Storage.
 * Values are injected via environment variables at build time.
 *
 * Required env vars (set in Amplify Console or .env):
 *
 *   VITE_AWS_REGION
 *   VITE_COGNITO_USER_POOL_ID
 *   VITE_COGNITO_USER_POOL_CLIENT_ID
 *   VITE_COGNITO_IDENTITY_POOL_ID
 *   VITE_API_GATEWAY_URL
 *   VITE_S3_BUCKET
 */

import { type ResourcesConfig } from 'aws-amplify';

const region = import.meta.env.VITE_AWS_REGION || 'us-east-1';

const amplifyConfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
      userPoolClientId: import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID || '',
      identityPoolId: import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID || '',
      loginWith: {
        email: true,
      },
      signUpVerificationMethod: 'code',
      userAttributes: {
        email: { required: true },
      },
      passwordFormat: {
        minLength: 8,
        requireLowercase: false,
        requireUppercase: false,
        requireNumbers: false,
        requireSpecialCharacters: false,
      },
    },
  },
  API: {
    REST: {
      claudevetaiapi: {
        endpoint: import.meta.env.VITE_API_GATEWAY_URL || '',
        region,
      },
    },
  },
  Storage: {
    S3: {
      bucket: import.meta.env.VITE_S3_BUCKET || '',
      region,
    },
  },
};

export default amplifyConfig;
