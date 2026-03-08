/**
 * Valor Assist — API Client
 *
 * Centralizes all backend calls. Supports two auth modes:
 *   1. Cognito (primary) — uses Amplify Auth JWT tokens
 *   2. Legacy JWT (fallback) — uses custom backend-issued tokens
 *
 * The client auto-detects which mode is active based on whether
 * a Cognito session exists. In ECS, VITE_API_URL is baked in at
 * build time so requests go directly to the backend. In dev, Vite
 * proxy handles /api routing.
 */

import { fetchAuthSession } from 'aws-amplify/auth';

const API_BASE = (import.meta.env.VITE_API_URL || '').trim().replace(/\/+$/, '');
const BASE = API_BASE ? `${API_BASE}/api` : '/api';

/**
 * Try to get the Cognito ID token first; fall back to localStorage.
 */
async function getAuthToken() {
  try {
    const session = await fetchAuthSession();
    const idToken = session.tokens?.idToken?.toString();
    if (idToken) return idToken;
  } catch {
    // No Cognito session — fall through to legacy
  }
  return localStorage.getItem('access_token');
}

async function request(path, options = {}) {
  const token = await getAuthToken();
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    // Cognito handles its own token refresh via fetchAuthSession,
    // so only attempt manual refresh for legacy tokens.
    const isLegacy = localStorage.getItem('access_token');
    if (isLegacy) {
      const refreshed = await refreshToken();
      if (refreshed) return request(path, options);
    }
    localStorage.clear();
    window.location.href = '/login';
    throw new Error('Session expired');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'Request failed');
  }

  return res.json();
}

async function refreshToken() {
  const refresh = localStorage.getItem('refresh_token');
  if (!refresh) return false;
  try {
    const res = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const data = await res.json();
    localStorage.setItem('access_token', data.access_token);
    localStorage.setItem('refresh_token', data.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// ── Auth ────────────────────────────────────────────────────────────

export async function signup(email, password, firstName, lastName) {
  const data = await request('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({
      email, password, first_name: firstName, last_name: lastName,
    }),
  });
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data;
}

export async function getIdmeLoginUrl() {
  return request('/auth/idme/login');
}

export async function idmeCallback(code, state) {
  const data = await request('/auth/idme/callback', {
    method: 'POST',
    body: JSON.stringify({ code, state }),
  });
  localStorage.setItem('access_token', data.access_token);
  localStorage.setItem('refresh_token', data.refresh_token);
  return data;
}

export async function getProfile() {
  return request('/auth/me');
}

export async function getConsentChallenge() {
  return request('/auth/consent/challenge');
}

export async function submitConsent(challengeId, responses) {
  return request('/auth/consent', {
    method: 'POST',
    body: JSON.stringify({ challenge_id: challengeId, responses }),
  });
}

export async function logout() {
  const refresh = localStorage.getItem('refresh_token');
  try {
    await request('/auth/logout', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refresh }),
    });
  } catch { /* ignore */ }
  localStorage.clear();
}

// ── Chat ────────────────────────────────────────────────────────────

export async function createChatSession() {
  return request('/chat/onboarding-chat', {
    method: 'POST',
    body: JSON.stringify({ message: 'start_session' }),
  });
}

export async function sendMessage(message, sessionId) {
  return request('/chat/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      sessionId: sessionId || undefined,
    }),
  });
}

export async function sendQuickAction(action, sessionId) {
  return request('/chat/onboarding-chat', {
    method: 'POST',
    body: JSON.stringify({ message: action, sessionId: sessionId || undefined }),
  });
}

// ── Evaluation ──────────────────────────────────────────────────────

export async function submitEvaluation(data) {
  return request('/evaluate', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Health ──────────────────────────────────────────────────────────

export async function getHealth() {
  return request('/health');
}

export async function getStats() {
  return request('/stats');
}
