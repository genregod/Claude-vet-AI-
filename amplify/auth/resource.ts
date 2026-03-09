import { defineAuth } from "@aws-amplify/backend";

/**
 * Valor Assist — Cognito Authentication
 *
 * Email-based sign-up/sign-in with verification code.
 * MFA is disabled. Password policy uses Cognito defaults (min 8 chars).
 */
export const auth = defineAuth({
  loginWith: {
    email: {
      verificationEmailSubject: "Your Valor Assist verification code",
      verificationEmailBody: (createCode) =>
        `Your verification code is ${createCode()}`,
      verificationEmailStyle: "CODE",
    },
  },
  userAttributes: {
    email: { required: true, mutable: true },
  },
});
