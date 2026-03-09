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

import { apiRequest, buildApiUrl } from "@/lib/queryClient";

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
  const res = await apiRequest("POST", "/auth/signup", data);
  const json = await res.json();
  // Backend returns session info — store tokens if provided
  if (json.access_token) {
    localStorage.setItem("access_token", json.access_token);
  }
  if (json.refresh_token) {
    localStorage.setItem("refresh_token", json.refresh_token);
  }
  const sessionId = json.session_id || json.user_id || `session_${Date.now()}`;
  saveSessionToStorage(sessionId);
  return { session_id: sessionId, current_page: "personal_info", total_pages: 10, ...json };
}

export async function getClaimSession(sessionId: string): Promise<ClaimSessionStatus> {
  // Claims session management is handled locally until backend adds support.
  // Return a synthetic session status from localStorage.
  const storedId = getSessionFromStorage();
  if (!storedId || storedId !== sessionId) {
    throw new Error("Session not found");
  }
  return {
    session_id: sessionId,
    status: "active",
    current_page: "personal_info",
    current_page_index: 1,
    completed_pages: [],
    progress_percent: 0,
    total_pages: 10,
    ai_estimates: {
      estimated_rating_percent: 0,
      estimated_combined_rating: 0,
      estimated_monthly_compensation: 0,
      estimated_backpay: 0,
      estimated_decision_timeline_days: 0,
      confidence_level: "pending",
      individual_ratings: [],
      notes: [],
      last_updated: 0,
    },
    agent: {
      claims_agent_id: "",
      supervisor_id: "",
      claims_assistant_id: "",
      current_handler: "",
      assignment_time: 0,
      notes: [],
    },
    created_at: Date.now(),
    last_active: Date.now(),
  };
}

export async function savePageAnswers(
  sessionId: string,
  page: string,
  answers: Record<string, unknown>,
): Promise<SavePageResponse> {
  // Save locally for persistence (backend claims session routes pending)
  savePageLocally(page, answers);

  return {
    session_id: sessionId,
    page_saved: page,
    next_page: null,
    progress_percent: 0,
    ai_estimates: {
      estimated_rating_percent: 0,
      estimated_combined_rating: 0,
      estimated_monthly_compensation: 0,
      estimated_backpay: 0,
      estimated_decision_timeline_days: 0,
      confidence_level: "pending",
      individual_ratings: [],
      notes: [],
      last_updated: 0,
    },
    completed_pages: [],
  };
}

export async function getPageAnswers(
  _sessionId: string,
  page: string,
): Promise<{ answers: Record<string, unknown>; is_completed: boolean }> {
  // Retrieve from localStorage (backend claims session routes pending)
  const answers = getPageLocally(page);
  return {
    answers: answers || {},
    is_completed: answers !== null,
  };
}

export async function getAIEstimates(_sessionId: string): Promise<AIEstimates> {
  // AI estimates will come from the backend once the evaluation pipeline is connected.
  return {
    estimated_rating_percent: 0,
    estimated_combined_rating: 0,
    estimated_monthly_compensation: 0,
    estimated_backpay: 0,
    estimated_decision_timeline_days: 0,
    confidence_level: "pending",
    individual_ratings: [],
    notes: ["AI evaluation pending — complete the questionnaire for estimates."],
    last_updated: Date.now(),
  };
}

export async function triggerEvaluation(
  _sessionId: string,
): Promise<{ estimates: AIEstimates }> {
  // Evaluation pipeline pending backend integration
  return {
    estimates: await getAIEstimates(_sessionId),
  };
}

export async function submitClaim(_sessionId: string): Promise<SubmitClaimResponse> {
  // Gather all locally saved pages for a basic submission
  return {
    session_id: _sessionId,
    status: "submitted",
    fdc_package: {
      claim_type: "disability",
      primary_form: "VA-21-526EZ",
      conditions_claimed: [],
      estimated_combined_rating: 0,
      required_forms: [],
      evidence_checklist: [],
      status: "draft",
      prepared_at: Date.now(),
    },
    supervisor_review: {},
    message: "Your claim information has been saved. Full submission pipeline coming soon.",
  };
}

export async function getClaimableConditions(): Promise<ConditionsData> {
  // Static conditions list until backend endpoint is connected
  return {
    categories: {
      "Mental Health": ["PTSD", "Depression", "Anxiety", "Insomnia", "Adjustment Disorder"],
      "Musculoskeletal": ["Back Pain", "Knee Condition", "Shoulder Injury", "Neck Pain", "Plantar Fasciitis"],
      "Hearing": ["Tinnitus", "Hearing Loss"],
      "Respiratory": ["Asthma", "Sleep Apnea", "Sinusitis"],
      "Skin": ["Eczema", "Scars", "Skin Cancer"],
      "Cardiovascular": ["Hypertension", "Heart Disease"],
      "Neurological": ["Migraines", "TBI", "Radiculopathy"],
    },
    all_conditions: [],
    total_count: 0,
  };
}

export async function deleteClaimSession(_sessionId: string): Promise<void> {
  clearSessionStorage();
  clearAllLocalPages();
}

// ── Records Upload ──────────────────────────────────────────────────

export async function uploadMilitaryRecords(
  _sessionId: string,
  file: File,
): Promise<UploadRecordsResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("source_type", "General");

  // Use fetch directly for multipart/form-data (apiRequest sends JSON)
  const res = await fetch(buildApiUrl("/upload"), {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  if (!res.ok) {
    const errorBody = await res.text();
    let detail = `Upload failed (${res.status})`;
    try {
      const errJson = JSON.parse(errorBody);
      detail = errJson.detail || errJson.error || detail;
    } catch {
      // use default detail
    }
    throw new Error(detail);
  }

  return res.json();
}

export async function getUploadedFiles(
  _sessionId: string,
): Promise<{ files: UploadedFile[]; total: number }> {
  // The backend does not expose a file-listing endpoint yet.
  // Return an empty list so callers can render gracefully.
  return { files: [], total: 0 };
}
