import { defineAuth, secret } from '@aws-amplify/backend';

export const auth = defineAuth({
  loginWith: {
    email: true,
    externalProviders: {
      oidc: [
        {
          name: 'GitHub',
          clientId: secret('GITHUB_CLIENT_ID'),
          clientSecret: secret('GITHUB_CLIENT_SECRET'),
          issuerUrl: 'https://github.com',
          scopes: ['user:email', 'read:user'],
        },
      ],
      callbackUrls: [
        'http://localhost:3000/',
        'https://your-production-domain.com/',
      ],
      logoutUrls: [
        'http://localhost:3000/',
        'https://your-production-domain.com/',
      ],
    },
  },
});
