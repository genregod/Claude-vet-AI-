/**
 * Valor Assist — Cognito Authentication Service
 *
 * Wraps AWS Amplify Auth operations for sign-up, sign-in, sign-out,
 * token management, and session handling. This module works alongside
 * the existing api.js auth functions — Cognito handles identity while
 * the backend still manages veteran verification (ID.me) and VA access.
 *
 * Flow:
 *   1. User signs up / signs in via Cognito (email + password)
 *   2. Cognito JWT is sent to backend on every API call
 *   3. Backend verifies Cognito JWT and maps to UserProfile
 *   4. Veteran identity proofing still goes through ID.me
 */

import {
  signUp,
  signIn,
  signOut,
  signInWithRedirect,
  confirmSignUp,
  resetPassword,
  confirmResetPassword,
  fetchAuthSession,
  fetchUserAttributes,
  getCurrentUser,
  type SignUpOutput,
  type SignInOutput,
} from 'aws-amplify/auth';

export interface CognitoUser {
  userId: string;
  email: string;
  emailVerified: boolean;
}

/**
 * Register a new user with Cognito.
 * After signup, user must verify email with the confirmation code.
 */
export async function cognitoSignUp(
  email: string,
  password: string
): Promise<SignUpOutput> {
  return signUp({
    username: email,
    password,
    options: {
      userAttributes: { email },
    },
  });
}

/**
 * Confirm signup with the verification code sent to email.
 */
export async function cognitoConfirmSignUp(
  email: string,
  code: string
): Promise<void> {
  await confirmSignUp({ username: email, confirmationCode: code });
}

/**
 * Sign in with email and password.
 */
export async function cognitoSignIn(
  email: string,
  password: string
): Promise<SignInOutput> {
  return signIn({ username: email, password });
}

/**
 * Sign out the current user (clears local tokens).
 */
export async function cognitoSignOut(): Promise<void> {
  await signOut();
}

/**
 * Get the current Cognito JWT access token.
 * Returns null if no active session.
 */
export async function getCognitoAccessToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.accessToken?.toString() ?? null;
  } catch {
    return null;
  }
}

/**
 * Get the current Cognito ID token (contains user attributes).
 * This is the token sent to the backend for verification.
 */
export async function getCognitoIdToken(): Promise<string | null> {
  try {
    const session = await fetchAuthSession();
    return session.tokens?.idToken?.toString() ?? null;
  } catch {
    return null;
  }
}

/**
 * Get the current authenticated user info.
 * Returns null if not authenticated.
 */
export async function getCognitoUser(): Promise<CognitoUser | null> {
  try {
    const user = await getCurrentUser();
    const attributes = await fetchUserAttributes();
    return {
      userId: user.userId,
      email: attributes.email ?? '',
      emailVerified: attributes.email_verified === 'true',
    };
  } catch {
    return null;
  }
}

/**
 * Sign in (or sign up) via GitHub OAuth using Cognito hosted UI.
 * Redirects the user to GitHub for authorization.
 */
export async function signInWithGitHub(): Promise<void> {
  await signInWithRedirect({ provider: { custom: 'GitHub' } });
}

/**
 * Check if there is an active Cognito session.
 */
export async function isAuthenticated(): Promise<boolean> {
  try {
    await getCurrentUser();
    return true;
  } catch {
    return false;
  }
}

/**
 * Initiate forgot password flow — sends reset code to email.
 */
export async function cognitoForgotPassword(email: string): Promise<void> {
  await resetPassword({ username: email });
}

/**
 * Confirm password reset with the code and new password.
 */
export async function cognitoConfirmResetPassword(
  email: string,
  code: string,
  newPassword: string
): Promise<void> {
  await confirmResetPassword({
    username: email,
    confirmationCode: code,
    newPassword,
  });
}
