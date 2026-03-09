import { defineAuth } from '@aws-amplify/backend';

export const auth = defineAuth({
  loginWith: {
    email: true,
    externalProviders: {
      oidc: [
        {
          name: 'GitHub',
          clientId: 'your-github-client-id',
          clientSecret: 'your-github-client-secret',
          issuerUrl: 'https://github.com',
          scopes: ['user:email', 'read:user']
        }
      ],
      callbackUrls: [
        'http://localhost:3000/',
        'https://your-production-domain.com/'
      ],
      logoutUrls: [
        'http://localhost:3000/',
        'https://your-production-domain.com/'
      ]
    }
  }
});
