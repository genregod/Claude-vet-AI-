/**
 * Valor Assist — Claims API Client
 * 
 * Handles all claim questionnaire API interactions:
 * - Session creation (signup)
 * - Page save/retrieve
 * - AI estimates polling
 * - Claim submission
 * - Claimable conditions lookup
 */

import { apiRequest } from "@/lib/queryClient";

// ── Types ───────────────────────────────────────────────────────────

export interface AIEstimates {
  estimated_rating_percent: number;
  estimated_combined_rating: number;
  estimated_monthly_compensation: number;
  estimated_backpay: number;
  estimated_decision_timeline_days: number;
  confidence_level: string;
  individual_ratings: IndividualRating[];
  notes: string[];
  last_updated: number;
}

export interface IndividualRating {
  condition: string;
  estimated_rating: number;
  rationale: string;
  service_connection_strength: string;
  applicable_cfr?: string;
}

export interface AgentInfo {
  claims_agent_id: string;
  supervisor_id: string;
  claims_assistant_id: string;
  current_handler: string;
  assignment_time: number;
  notes: string[];
}

export interface ClaimSessionStatus {
  session_id: string;
  status: string;
  current_page: string;
  current_page_index: number;
  completed_pages: string[];
  progress_percent: number;
  total_pages: number;
  ai_estimates: AIEstimates;
  agent: AgentInfo;
  created_at: number;
  last_active: number;
}

export interface SavePageResponse {
  session_id: string;
  page_saved: string;
  next_page: string | null;
  progress_percent: number;
  ai_estimates: AIEstimates;
  completed_pages: string[];
}

export interface ConditionsData {
  categories: Record<string, string[]>;
  all_conditions: string[];
  total_count: number;
}

export interface FDCPackage {
  claim_type: string;
  primary_form: string;
  conditions_claimed: string[];
  estimated_combined_rating: number;
  required_forms: string[];
  evidence_checklist: string[];
  status: string;
  prepared_at: number;
}

export interface SubmitClaimResponse {
  session_id: string;
  status: string;
  fdc_package: FDCPackage;
  supervisor_review: Record<string, unknown>;
  message: string;
}

export interface UploadRecordsResponse {
  session_id: string;
  filename: string;
  document_type: string;
  document_description: string;
  confidence: string;
  auto_fill_pages: Record<string, Record<string, unknown>>;
  pages_affected: string[];
  merged_pages: string[];
  raw_findings: string;
  ai_estimates: AIEstimates;
  message: string;
}

export interface UploadedFile {
  filename: string;
  saved_as: string;
  size_bytes: number;
  document_type: string;
  confidence: string;
  pages_affected: string[];
}

// ── Questionnaire page definitions ──────────────────────────────────

export const CLAIM_PAGES = [
  { key: "signup", label: "Sign Up", icon: "UserPlus" },
  { key: "personal_info", label: "Personal Info", icon: "User" },
  { key: "military_service", label: "Military Service", icon: "Shield" },
  { key: "service_history", label: "Service History", icon: "Clock" },
  { key: "disabilities", label: "Disabilities", icon: "HeartPulse" },
  { key: "mental_health", label: "Mental Health", icon: "Brain" },
  { key: "medical_evidence", label: "Medical Evidence", icon: "FileText" },
  { key: "exposures", label: "Exposures", icon: "AlertTriangle" },
  { key: "additional_claims", label: "Additional Claims", icon: "Plus" },
  { key: "review", label: "Review & Submit", icon: "CheckCircle" },
] as const;

export type ClaimPageKey = (typeof CLAIM_PAGES)[number]["key"];

// ── Session storage for persistence across reloads ──────────────────

const STORAGE_KEY = "valor_claim_session";

export function saveSessionToStorage(sessionId: string): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      sessionId,
      timestamp: Date.now(),
    }));
  } catch {
    // localStorage not available
  }
}

export function getSessionFromStorage(): string | null {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    const data = JSON.parse(stored);
    // Expire after 24 hours
    if (Date.now() - data.timestamp > 86400000) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return data.sessionId;
  } catch {
    return null;
  }
}

export function clearSessionStorage(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // noop
  }
}

// Save page answers to localStorage for offline recovery
export function savePageLocally(page: string, answers: Record<string, unknown>): void {
  try {
    const key = `valor_page_${page}`;
    localStorage.setItem(key, JSON.stringify(answers));
  } catch {
    // noop
  }
}

export function getPageLocally(page: string): Record<string, unknown> | null {
  try {
    const key = `valor_page_${page}`;
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function clearAllLocalPages(): void {
  try {
    CLAIM_PAGES.forEach(p => {
      localStorage.removeItem(`valor_page_${p.key}`);
    });
  } catch {
    // noop
  }
}

// ── API Functions ───────────────────────────────────────────────────

export async function createClaimSession(data: {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}): Promise<{ session_id: string; current_page: string; total_pages: number }> {
  const res = await apiRequest("POST", "/claims/session", data);
  const json = await res.json();
  saveSessionToStorage(json.session_id);
  return json;
}

export async function getClaimSession(sessionId: string): Promise<ClaimSessionStatus> {
  const res = await apiRequest("GET", `/claims/session/${sessionId}`);
  return res.json();
}

export async function savePageAnswers(
  sessionId: string,
  page: string,
  answers: Record<string, unknown>,
): Promise<SavePageResponse> {
  // Save locally first for crash recovery
  savePageLocally(page, answers);
  
  const res = await apiRequest("POST", `/claims/session/${sessionId}/page`, {
    page,
    answers,
  });
  return res.json();
}

export async function getPageAnswers(
  sessionId: string,
  page: string,
): Promise<{ answers: Record<string, unknown>; is_completed: boolean }> {
  const res = await apiRequest("GET", `/claims/session/${sessionId}/page/${page}`);
  return res.json();
}

export async function getAIEstimates(sessionId: string): Promise<AIEstimates> {
  const res = await apiRequest("GET", `/claims/session/${sessionId}/estimates`);
  return res.json();
}

export async function triggerEvaluation(
  sessionId: string,
): Promise<{ estimates: AIEstimates }> {
  const res = await apiRequest("POST", `/claims/session/${sessionId}/evaluate`);
  return res.json();
}

export async function submitClaim(sessionId: string): Promise<SubmitClaimResponse> {
  const res = await apiRequest("POST", `/claims/session/${sessionId}/submit`);
  return res.json();
}

export async function getClaimableConditions(): Promise<ConditionsData> {
  const res = await apiRequest("GET", "/claims/conditions");
  return res.json();
}

export async function deleteClaimSession(sessionId: string): Promise<void> {
  await apiRequest("DELETE", `/claims/session/${sessionId}`);
  clearSessionStorage();
  clearAllLocalPages();
}

// ── Records Upload ──────────────────────────────────────────────────

export async function uploadMilitaryRecords(
  sessionId: string,
  file: File,
): Promise<UploadRecordsResponse> {
  const formData = new FormData();
  formData.append("file", file);

  // Use fetch directly for multipart/form-data (apiRequest sends JSON)
  const res = await fetch(`/api/claims/session/${sessionId}/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  if (!res.ok) {
    const errorBody = await res.text();
    let detail = `Upload failed (${res.status})`;
    try {
      const errJson = JSON.parse(errorBody);
      detail = errJson.detail || detail;
    } catch {
      // use default detail
    }
    throw new Error(detail);
  }

  return res.json();
}

export async function getUploadedFiles(
  sessionId: string,
): Promise<{ files: UploadedFile[]; total: number }> {
  const res = await apiRequest("GET", `/claims/session/${sessionId}/uploads`);
  return res.json();
}
