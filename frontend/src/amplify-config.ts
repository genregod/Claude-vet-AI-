/**
 * Valor Assist — AWS Amplify Configuration
 *
 * Configures Amplify with Cognito User Pool and Identity Pool settings.
 * Values are injected via environment variables at build time.
 *
 * After provisioning Cognito (via Amplify CLI or AWS Console), set these
 * in your .env or Amplify environment variables:
 *
 *   VITE_AWS_REGION
 *   VITE_COGNITO_USER_POOL_ID
 *   VITE_COGNITO_USER_POOL_CLIENT_ID
 *   VITE_COGNITO_IDENTITY_POOL_ID
 */

import { type ResourcesConfig } from 'aws-amplify';

const amplifyConfig: ResourcesConfig = {
  Auth: {
    Cognito: {
      userPoolId: import.meta.env.VITE_COGNITO_USER_POOL_ID || '',
      userPoolClientId: import.meta.env.VITE_COGNITO_USER_POOL_CLIENT_ID || '',
      identityPoolId: import.meta.env.VITE_COGNITO_IDENTITY_POOL_ID || '',
      loginWith: {
        email: true,
        oauth: {
          domain: 'valor-assist.auth.us-east-1.amazoncognito.com',
          scopes: ['openid', 'email', 'profile'],
          redirectSignIn: ['https://main.dnfalf4ttkc7b.amplifyapp.com/callback'],
          redirectSignOut: ['https://main.dnfalf4ttkc7b.amplifyapp.com/'],
          responseType: 'code',
        },
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
};

export default amplifyConfig;
