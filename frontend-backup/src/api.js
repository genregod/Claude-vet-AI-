/**
 * Valor Assist — API Client
 *
 * Centralizes all backend calls. In Docker, requests go through the
 * nginx proxy (/api → backend:8000). In dev, Vite proxy handles it.
 */

const BASE = '/api';

async function request(path, options = {}) {
  const token = localStorage.getItem('access_token');
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    // Try refresh
    const refreshed = await refreshToken();
    if (refreshed) return request(path, options);
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
  return request('/chat/session', { method: 'POST' });
}

export async function sendMessage(question, sessionId, sourceTypeFilter) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({
      question,
      session_id: sessionId || undefined,
      source_type_filter: sourceTypeFilter || undefined,
    }),
  });
}

export async function sendQuickAction(action, sessionId) {
  return request('/chat/quick-action', {
    method: 'POST',
    body: JSON.stringify({ action, session_id: sessionId || undefined }),
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
