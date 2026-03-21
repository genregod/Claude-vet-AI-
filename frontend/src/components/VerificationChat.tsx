/**
 * VerificationChat — Human-in-the-loop profile verification.
 *
 * After documents are processed, this component drives a structured
 * conversation where the AI presents each extracted data point to the
 * veteran for confirmation or correction, section by section.
 *
 * Features:
 *  - Progress bar with section indicators (Personal → Service → Claims → Appeals → Benefits)
 *  - Quick-reply buttons (Correct / Not right / More detail / Skip)
 *  - Free-text input for corrections and elaborations
 *  - Live profile sidebar showing confirmed/pending/corrected fields
 *  - Real-time profile updates as corrections are applied
 *  - Auto-starts on mount; resumes from existing conversation history
 */

import { useState, useRef, useEffect, useCallback } from "react";
import {
  CheckCircle, XCircle, AlertCircle, ChevronRight,
  Loader2, Send, User, Bot, Shield, FileText,
  Heart, Star, SkipForward,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";

const API = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");

// ── Types ────────────────────────────────────────────────────────────

interface VerifyResult {
  message: string;
  section: string;
  field_path: string;
  progress: number;
  quick_replies: string[];
  profile_update: Record<string, unknown> | null;
  confirmed_fields: string[];
  skipped_fields: string[];
  done: boolean;
  _usage?: { input_tokens: number; output_tokens: number };
}

interface ChatMessage {
  id: string;
  role: "ai" | "user";
  content: string;
  quick_replies?: string[];
  field_path?: string;
  section?: string;
  status?: "confirmed" | "corrected" | "skipped" | "pending";
}

interface VerificationChatProps {
  userId: string;
  profile: Record<string, unknown>;
  onProfileUpdate: (updated: Record<string, unknown>) => void;
  onComplete: () => void;
}

// ── Section metadata ─────────────────────────────────────────────────

const SECTIONS = [
  { id: "personal",  label: "Personal",  icon: <User size={13} /> },
  { id: "service",   label: "Service",   icon: <Shield size={13} /> },
  { id: "claims",    label: "Claims",    icon: <FileText size={13} /> },
  { id: "appeals",   label: "Appeals",   icon: <AlertCircle size={13} /> },
  { id: "benefits",  label: "Benefits",  icon: <Heart size={13} /> },
  { id: "notes",     label: "Notes",     icon: <Star size={13} /> },
  { id: "complete",  label: "Done",      icon: <CheckCircle size={13} /> },
];

// ── Polling helper ───────────────────────────────────────────────────

async function pollVerifyResult(jobId: string, signal: AbortSignal): Promise<VerifyResult> {
  for (let i = 0; i < 120; i++) {
    if (signal.aborted) throw new Error("aborted");
    await new Promise(r => setTimeout(r, 2000));
    const res = await fetch(`${API}/api/battle-buddy/result/${jobId}`, { signal });
    if (!res.ok) throw new Error(`Poll failed: ${res.status}`);
    const data = await res.json();
    if (data.status === "done" && data.verify_result) {
      const parsed = typeof data.verify_result === "string"
        ? JSON.parse(data.verify_result)
        : data.verify_result;
      return parsed as VerifyResult;
    }
    if (data.status === "error") throw new Error(data.error || "Verification job failed");
  }
  throw new Error("Verification timed out.");
}

// ── Main component ───────────────────────────────────────────────────

export function VerificationChat({
  userId,
  profile,
  onProfileUpdate,
  onComplete,
}: VerificationChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationHistory, setConversationHistory] = useState<{ role: string; content: string }[]>([]);
  const [confirmedFields, setConfirmedFields] = useState<string[]>([]);
  const [skippedFields, setSkippedFields] = useState<string[]>([]);
  const [corrections, setCorrections] = useState<Record<string, unknown>>({});
  const [currentSection, setCurrentSection] = useState("personal");
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [freeInput, setFreeInput] = useState("");
  const [awaitingCorrection, setAwaitingCorrection] = useState(false);
  const [lastFieldPath, setLastFieldPath] = useState("");

  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const startedRef = useRef(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Auto-start on mount
  useEffect(() => {
    if (!startedRef.current && userId) {
      startedRef.current = true;
      runVerifyTurn([]);
    }
  }, [userId]);

  // ── Core: send a turn to the verification AI ─────────────────────

  const runVerifyTurn = useCallback(async (
    updatedHistory: { role: string; content: string }[],
    updatedConfirmed?: string[],
    updatedSkipped?: string[],
    updatedCorrections?: Record<string, unknown>,
  ) => {
    setLoading(true);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    const confirmed = updatedConfirmed ?? confirmedFields;
    const skipped = updatedSkipped ?? skippedFields;
    const corr = updatedCorrections ?? corrections;

    try {
      const postRes = await fetch(`${API}/api/battle-buddy/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          conversation_history: updatedHistory,
          confirmed_fields: confirmed,
          skipped_fields: skipped,
          corrections: corr,
        }),
        signal: abortRef.current.signal,
      });
      if (!postRes.ok) throw new Error(`Verify POST failed: ${postRes.status}`);
      const { job_id } = await postRes.json();

      const result = await pollVerifyResult(job_id, abortRef.current.signal);

      // Update state from result
      setProgress(result.progress ?? 0);
      setCurrentSection(result.section ?? "personal");
      setConfirmedFields(result.confirmed_fields ?? confirmed);
      setSkippedFields(result.skipped_fields ?? skipped);
      setLastFieldPath(result.field_path ?? "");

      if (result.done) {
        setDone(true);
      }

      // Add AI message to chat
      const aiMsg: ChatMessage = {
        id: `ai-${Date.now()}`,
        role: "ai",
        content: result.message,
        quick_replies: result.done ? [] : result.quick_replies,
        field_path: result.field_path,
        section: result.section,
        status: "pending",
      };
      setMessages(prev => [...prev, aiMsg]);

      // Update conversation history with AI response
      setConversationHistory([...updatedHistory, { role: "assistant", content: result.message }]);

    } catch (err: unknown) {
      if ((err as Error).message === "aborted") return;
      const errMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        role: "ai",
        content: "I had a connection issue. Please try again.",
        quick_replies: ["Try again"],
        status: "pending",
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setLoading(false);
    }
  }, [userId, confirmedFields, skippedFields, corrections]);

  // ── Handle quick-reply button click ──────────────────────────────

  const handleQuickReply = async (reply: string) => {
    if (loading) return;

    // Mark last AI message as no longer showing quick replies
    setMessages(prev => prev.map((m, i) =>
      i === prev.length - 1 && m.role === "ai"
        ? { ...m, quick_replies: [] }
        : m
    ));

    // Add user message
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: reply,
    };
    setMessages(prev => [...prev, userMsg]);

    const newHistory = [...conversationHistory, { role: "user", content: reply }];
    setConversationHistory(newHistory);

    const replyLower = reply.toLowerCase();

    if (replyLower.includes("not right") || replyLower === "no") {
      // Veteran wants to correct — open free-text input
      setAwaitingCorrection(true);
      setLoading(false);
      return;
    }

    if (replyLower.includes("correct") || replyLower === "yes") {
      // Confirm the current field
      const newConfirmed = lastFieldPath
        ? [...confirmedFields, lastFieldPath].filter((v, i, a) => a.indexOf(v) === i)
        : confirmedFields;
      setConfirmedFields(newConfirmed);
      await runVerifyTurn(newHistory, newConfirmed, skippedFields, corrections);
      return;
    }

    if (replyLower.includes("skip")) {
      // Skip the current field
      const newSkipped = lastFieldPath
        ? [...skippedFields, lastFieldPath].filter((v, i, a) => a.indexOf(v) === i)
        : skippedFields;
      setSkippedFields(newSkipped);
      await runVerifyTurn(newHistory, confirmedFields, newSkipped, corrections);
      return;
    }

    // "More detail" or "Try again" or anything else — just continue the conversation
    await runVerifyTurn(newHistory);
  };

  // ── Handle free-text submission (corrections or elaborations) ────

  const handleFreeText = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!freeInput.trim() || loading) return;

    const text = freeInput.trim();
    setFreeInput("");
    setAwaitingCorrection(false);

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
    };
    setMessages(prev => [...prev, userMsg]);

    const newHistory = [...conversationHistory, { role: "user", content: text }];
    setConversationHistory(newHistory);

    // If we were awaiting a correction, record it
    let newCorrections = corrections;
    if (awaitingCorrection && lastFieldPath) {
      newCorrections = { ...corrections, [lastFieldPath]: text };
      setCorrections(newCorrections);

      // Apply the correction to the profile via API (fire and forget)
      fetch(`${API}/api/battle-buddy/profile/${userId}/update`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ field_path: lastFieldPath, value: text }),
      })
        .then(r => r.json())
        .then(data => { if (data.profile) onProfileUpdate(data.profile); })
        .catch(() => {});
    }

    await runVerifyTurn(newHistory, confirmedFields, skippedFields, newCorrections);
  };

  // ── Section status helper ─────────────────────────────────────────

  const getSectionStatus = (sectionId: string): "done" | "active" | "pending" => {
    const order = SECTIONS.map(s => s.id);
    const currentIdx = order.indexOf(currentSection);
    const sectionIdx = order.indexOf(sectionId);
    if (sectionId === "complete" && done) return "done";
    if (sectionIdx < currentIdx) return "done";
    if (sectionIdx === currentIdx) return "active";
    return "pending";
  };

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className="flex flex-col lg:flex-row gap-4 h-full">

      {/* ── Main chat panel ── */}
      <div className="flex-1 flex flex-col gap-3 min-w-0">

        {/* Progress bar + section indicators */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 space-y-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-bold text-navy uppercase tracking-wide">
              Profile Verification
            </span>
            <span className="text-xs font-bold text-navy">{progress}%</span>
          </div>
          <Progress value={progress} className="h-2.5" />
          <div className="flex gap-1 flex-wrap">
            {SECTIONS.filter(s => s.id !== "complete").map(s => {
              const status = getSectionStatus(s.id);
              return (
                <div
                  key={s.id}
                  className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold transition-all ${
                    status === "done"
                      ? "bg-green-100 text-green-700"
                      : status === "active"
                      ? "bg-navy text-white shadow-sm"
                      : "bg-gray-100 text-gray-400"
                  }`}
                >
                  {status === "done" ? <CheckCircle size={11} /> : s.icon}
                  {s.label}
                </div>
              );
            })}
          </div>
        </div>

        {/* Chat messages */}
        <div className="flex-1 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-y-auto p-4 space-y-4 min-h-[380px] max-h-[520px]">

          {messages.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 space-y-2">
              <Bot size={32} className="opacity-30" />
              <p className="text-sm">Starting verification…</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"} gap-2`}>

              {/* Message bubble */}
              <div className={`flex items-start gap-2 max-w-[88%] ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
                <div className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                  msg.role === "ai" ? "bg-navy text-gold" : "bg-gray-200 text-gray-600"
                }`}>
                  {msg.role === "ai" ? <Bot size={14} /> : <User size={14} />}
                </div>
                <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                  msg.role === "ai"
                    ? "bg-gray-50 border border-gray-200 text-gray-800 rounded-tl-sm"
                    : "bg-navy text-white rounded-tr-sm"
                }`}>
                  {msg.content}
                  {msg.section && msg.section !== "complete" && msg.role === "ai" && (
                    <div className="mt-1.5">
                      <Badge variant="outline" className="text-xs border-gray-300 text-gray-400 font-normal">
                        {SECTIONS.find(s => s.id === msg.section)?.label ?? msg.section}
                        {msg.field_path && ` · ${msg.field_path}`}
                      </Badge>
                    </div>
                  )}
                </div>
              </div>

              {/* Quick reply buttons (only on last AI message when not loading) */}
              {msg.role === "ai" && msg.quick_replies && msg.quick_replies.length > 0 && !loading && (
                <div className="flex flex-wrap gap-2 ml-9">
                  {msg.quick_replies.map((qr) => (
                    <button
                      key={qr}
                      onClick={() => handleQuickReply(qr)}
                      disabled={loading}
                      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all hover:shadow-sm active:scale-95 ${
                        qr.toLowerCase().includes("correct") || qr === "Yes"
                          ? "border-green-300 text-green-700 bg-green-50 hover:bg-green-100"
                          : qr.toLowerCase().includes("not right") || qr === "No"
                          ? "border-red-300 text-red-700 bg-red-50 hover:bg-red-100"
                          : qr.toLowerCase().includes("skip")
                          ? "border-gray-300 text-gray-500 bg-gray-50 hover:bg-gray-100"
                          : "border-navy/30 text-navy bg-navy/5 hover:bg-navy/10"
                      }`}
                    >
                      {qr.toLowerCase().includes("correct") || qr === "Yes" ? <CheckCircle size={11} /> :
                       qr.toLowerCase().includes("not right") || qr === "No" ? <XCircle size={11} /> :
                       qr.toLowerCase().includes("skip") ? <SkipForward size={11} /> :
                       <ChevronRight size={11} />}
                      {qr}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          {/* Thinking indicator */}
          {loading && (
            <div className="flex items-start gap-2">
              <div className="shrink-0 w-7 h-7 rounded-full bg-navy flex items-center justify-center">
                <Bot size={14} className="text-gold" />
              </div>
              <div className="bg-gray-50 border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2 text-sm text-gray-500">
                <Loader2 size={14} className="animate-spin" />
                Analyzing your profile…
              </div>
            </div>
          )}

          {/* Completion banner */}
          {done && (
            <div className="bg-gradient-to-r from-green-50 to-emerald-50 border border-green-200 rounded-2xl p-4 flex items-start gap-3">
              <CheckCircle className="text-green-600 shrink-0 mt-0.5" size={20} />
              <div>
                <p className="font-bold text-green-800 text-sm">Verification Complete</p>
                <p className="text-xs text-green-700 mt-0.5">
                  {confirmedFields.length} fields confirmed · {Object.keys(corrections).length} corrections applied · {skippedFields.length} skipped
                </p>
                <button
                  onClick={onComplete}
                  className="mt-2 text-xs font-semibold text-green-700 underline hover:text-green-900"
                >
                  View your completed profile →
                </button>
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input area */}
        {!done && (
          <form onSubmit={handleFreeText} className="flex gap-2">
            <Input
              value={freeInput}
              onChange={e => setFreeInput(e.target.value)}
              placeholder={
                awaitingCorrection
                  ? "Type the correct information…"
                  : "Type a response or use the buttons above…"
              }
              disabled={loading}
              className={`flex-1 transition-all ${awaitingCorrection ? "border-orange-400 ring-1 ring-orange-300" : ""}`}
            />
            <Button
              type="submit"
              disabled={loading || !freeInput.trim()}
              className="bg-navy text-white hover:bg-navy-dark px-4 shrink-0"
            >
              {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            </Button>
          </form>
        )}

        {awaitingCorrection && !loading && (
          <p className="text-xs text-orange-600 -mt-1 ml-1">
            ✏️ Please type the correct value above and press Send.
          </p>
        )}
      </div>

      {/* ── Live profile sidebar ── */}
      <div className="lg:w-64 xl:w-72 shrink-0 space-y-3">
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 space-y-4">
          <h3 className="text-xs font-bold text-navy uppercase tracking-wide">Live Profile</h3>

          {/* Personal */}
          <ProfileSection
            title="Personal"
            icon={<User size={13} />}
            status={getSectionStatus("personal")}
            fields={[
              { label: "Name", value: (profile.personal as any)?.name },
              { label: "DOB", value: (profile.personal as any)?.dob },
              { label: "Phone", value: (profile.personal as any)?.phone },
            ]}
            confirmedFields={confirmedFields}
            corrections={corrections}
          />

          {/* Service */}
          <ProfileSection
            title="Service"
            icon={<Shield size={13} />}
            status={getSectionStatus("service")}
            fields={((profile.service as any[]) ?? []).flatMap((s: any, i: number) => [
              { label: `${s.branch || "Branch"}`, value: `${s.entry_date || "?"} – ${s.sep_date || "?"}`, path: `service[${i}]` },
              ...(s.mos ? [{ label: "MOS", value: s.mos, path: `service[${i}].mos` }] : []),
            ])}
            confirmedFields={confirmedFields}
            corrections={corrections}
          />

          {/* Claims */}
          <ProfileSection
            title="Claims"
            icon={<FileText size={13} />}
            status={getSectionStatus("claims")}
            fields={((profile.claims as any[]) ?? []).map((c: any, i: number) => ({
              label: `#${c.claim_number || i + 1}`,
              value: c.status || "pending",
              path: `claims[${i}]`,
              badge: c.status,
            }))}
            confirmedFields={confirmedFields}
            corrections={corrections}
          />

          {/* Appeals */}
          <ProfileSection
            title="Appeals"
            icon={<AlertCircle size={13} />}
            status={getSectionStatus("appeals")}
            fields={((profile.appeals as any[]) ?? []).map((a: any, i: number) => ({
              label: `Claim #${a.claim_number || i + 1}`,
              value: a.deadline ? `Deadline: ${a.deadline}` : "No deadline set",
              path: `appeals[${i}]`,
            }))}
            confirmedFields={confirmedFields}
            corrections={corrections}
          />

          {/* Benefits */}
          <ProfileSection
            title="Benefits"
            icon={<Heart size={13} />}
            status={getSectionStatus("benefits")}
            fields={[
              ...((profile.benefits as any)?.awarded ?? []).map((b: any, i: number) => ({
                label: b.name || `Benefit ${i + 1}`,
                value: b.amount || "awarded",
                path: `benefits.awarded[${i}]`,
              })),
              ...((profile.benefits as any)?.available ?? []).slice(0, 3).map((b: any, i: number) => ({
                label: b.name || `Available ${i + 1}`,
                value: "available",
                path: `benefits.available[${i}]`,
              })),
            ]}
            confirmedFields={confirmedFields}
            corrections={corrections}
          />
        </div>

        {/* Stats */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 space-y-2">
          <h3 className="text-xs font-bold text-navy uppercase tracking-wide">Verification Stats</h3>
          <StatRow icon={<CheckCircle size={13} className="text-green-500" />} label="Confirmed" value={confirmedFields.length} />
          <StatRow icon={<XCircle size={13} className="text-orange-500" />} label="Corrected" value={Object.keys(corrections).length} />
          <StatRow icon={<SkipForward size={13} className="text-gray-400" />} label="Skipped" value={skippedFields.length} />
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────

interface ProfileField {
  label: string;
  value?: string;
  path?: string;
  badge?: string;
}

function ProfileSection({
  title, icon, status, fields, confirmedFields, corrections,
}: {
  title: string;
  icon: React.ReactNode;
  status: "done" | "active" | "pending";
  fields: ProfileField[];
  confirmedFields: string[];
  corrections: Record<string, unknown>;
}) {
  if (fields.length === 0 && status === "pending") return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5">
        <span className={`${status === "done" ? "text-green-600" : status === "active" ? "text-navy" : "text-gray-400"}`}>
          {status === "done" ? <CheckCircle size={13} /> : icon}
        </span>
        <span className={`text-xs font-bold uppercase tracking-wide ${
          status === "done" ? "text-green-700" : status === "active" ? "text-navy" : "text-gray-400"
        }`}>
          {title}
        </span>
      </div>
      {fields.length > 0 && (
        <div className="ml-4 space-y-1">
          {fields.map((f, i) => {
            const isConfirmed = f.path ? confirmedFields.some(cf => cf.startsWith(f.path!)) : false;
            const isCorrected = f.path ? Object.keys(corrections).some(k => k.startsWith(f.path!)) : false;
            return (
              <div key={i} className="flex items-center justify-between gap-2">
                <span className="text-xs text-gray-500 truncate">{f.label}</span>
                <div className="flex items-center gap-1 shrink-0">
                  {f.value && (
                    <span className={`text-xs truncate max-w-[80px] ${
                      isCorrected ? "text-orange-600 font-medium" :
                      isConfirmed ? "text-green-700 font-medium" :
                      "text-gray-600"
                    }`}>
                      {String(corrections[f.path!] ?? f.value)}
                    </span>
                  )}
                  {isConfirmed && !isCorrected && <CheckCircle size={10} className="text-green-500 shrink-0" />}
                  {isCorrected && <XCircle size={10} className="text-orange-500 shrink-0" />}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function StatRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-1.5 text-xs text-gray-600">
        {icon}{label}
      </div>
      <span className="text-xs font-bold text-gray-800">{value}</span>
    </div>
  );
}
