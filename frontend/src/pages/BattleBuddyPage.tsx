import { useState, useRef, useEffect, useCallback } from "react";
import { useLocation } from "wouter";
import {
  Users, Send, Loader2, ArrowLeft, Upload, FileText,
  Shield, Heart, Clock, AlertTriangle, CheckCircle, ChevronRight,
  ClipboardCheck,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { VerificationChat } from "@/components/VerificationChat";
import { getCurrentUser } from "aws-amplify/auth";

const API = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");
const MAX_FILES = 30;

type Tab = "upload" | "verify" | "profile" | "benefits" | "chat";

interface UploadedFile {
  file: File;
  s3_key: string;
  status: "pending" | "uploading" | "done" | "error";
  progress: number;
}

interface ChatMsg { id: string; content: string; isUser: boolean; }

interface Profile {
  personal: Record<string, string>;
  service: any[];
  claims: any[];
  appeals: any[];
  benefits: { awarded: any[]; available: any[] };
  documents: any[];
  notes: string;
}

async function pollResult(jobId: string, signal: AbortSignal): Promise<string> {
  for (let i = 0; i < 90; i++) {
    if (signal.aborted) throw new Error("aborted");
    await new Promise(r => setTimeout(r, 2000));
    const r = await fetch(`${API}/api/battle-buddy/result/${jobId}`, { signal });
    const d = await r.json();
    if (d.status === "done") return d.answer;
    if (d.status === "error") throw new Error(d.error || "Job failed");
  }
  throw new Error("Timed out.");
}

export function BattleBuddyPage() {
  const [, setLocation] = useLocation();
  const [tab, setTab] = useState<Tab>("upload");
  const [userId, setUserId] = useState("");

  // Upload state
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [processJobIds, setProcessJobIds] = useState<string[]>([]);
  const [processedCount, setProcessedCount] = useState(0);
  const [allProcessed, setAllProcessed] = useState(false);

  // Profile state
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);

  // Chat state
  const [messages, setMessages] = useState<ChatMsg[]>([{
    id: "0",
    content: "Hey — I'm your Battle Buddy. Upload your claim documents first and I'll know your case inside and out. Or just ask me anything.",
    isUser: false,
  }]);
  const [chatHistory, setChatHistory] = useState<{ role: string; content: string }[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    getCurrentUser().then(u => setUserId(u.userId)).catch(() => setUserId("anonymous"));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── File upload ──────────────────────────────────────────────────

  const addFiles = (incoming: FileList | File[]) => {
    const arr = Array.from(incoming).slice(0, MAX_FILES - files.length);
    setFiles(prev => [
      ...prev,
      ...arr.map(f => ({ file: f, s3_key: "", status: "pending" as const, progress: 0 })),
    ]);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    addFiles(e.dataTransfer.files);
  };

  const uploadAll = async () => {
    if (!userId || files.length === 0) return;
    setUploading(true);

    const uploaded: { s3_key: string; filename: string }[] = [];

    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      if (f.status === "done") {
        uploaded.push({ s3_key: f.s3_key, filename: f.file.name });
        continue;
      }

      setFiles(prev => prev.map((x, idx) => idx === i ? { ...x, status: "uploading" } : x));

      try {
        const pr = await fetch(`${API}/api/battle-buddy/upload-url`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            filename: f.file.name,
            content_type: f.file.type || "application/octet-stream",
            user_id: userId,
          }),
        });
        const { upload_url, s3_key } = await pr.json();

        await fetch(upload_url, {
          method: "PUT",
          headers: { "Content-Type": f.file.type || "application/octet-stream" },
          body: f.file,
        });

        uploaded.push({ s3_key, filename: f.file.name });
        setFiles(prev => prev.map((x, idx) =>
          idx === i ? { ...x, status: "done", s3_key, progress: 100 } : x
        ));
      } catch {
        setFiles(prev => prev.map((x, idx) =>
          idx === i ? { ...x, status: "error" } : x
        ));
      }
    }

    if (uploaded.length > 0) {
      const res = await fetch(`${API}/api/battle-buddy/process-docs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: userId, files: uploaded }),
      });
      const { job_ids } = await res.json();
      setProcessJobIds(job_ids);
      pollProcessingJobs(job_ids);
    }

    setUploading(false);
  };

  const pollProcessingJobs = async (jobIds: string[]) => {
    let done = 0;
    const poll = async (jobId: string) => {
      for (let i = 0; i < 90; i++) {
        await new Promise(r => setTimeout(r, 3000));
        const r = await fetch(`${API}/api/battle-buddy/result/${jobId}`);
        const d = await r.json();
        if (d.status === "done" || d.status === "error") {
          done++;
          setProcessedCount(done);
          if (done === jobIds.length) {
            setAllProcessed(true);
            loadProfile();
            // Auto-switch to verification tab
            setTab("verify");
          }
          return;
        }
      }
    };
    await Promise.all(jobIds.map(poll));
  };

  const loadProfile = useCallback(async () => {
    if (!userId) return;
    setProfileLoading(true);
    try {
      const r = await fetch(`${API}/api/battle-buddy/profile/${userId}`);
      setProfile(await r.json());
    } finally {
      setProfileLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (userId) loadProfile();
  }, [userId, loadProfile]);

  // ── Chat ─────────────────────────────────────────────────────────

  const sendChat = async (text: string) => {
    if (!text.trim() || chatLoading) return;
    setMessages(prev => [
      ...prev,
      { id: Date.now().toString(), content: text, isUser: true },
      { id: "thinking", content: "", isUser: false },
    ]);
    setChatInput("");
    setChatLoading(true);
    abortRef.current = new AbortController();
    try {
      const pr = await fetch(`${API}/api/battle-buddy/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, conversation_history: chatHistory, user_id: userId }),
        signal: abortRef.current.signal,
      });
      const { job_id } = await pr.json();
      const answer = await pollResult(job_id, abortRef.current.signal);
      setMessages(prev => [
        ...prev.filter(m => m.id !== "thinking"),
        { id: Date.now().toString(), content: answer, isUser: false },
      ]);
      setChatHistory(h => [
        ...h,
        { role: "user", content: text },
        { role: "assistant", content: answer },
      ]);
    } catch (err: unknown) {
      if ((err as Error).message === "aborted") return;
      setMessages(prev => [
        ...prev.filter(m => m.id !== "thinking"),
        { id: Date.now().toString(), content: "Something went wrong — try again.", isUser: false },
      ]);
    } finally {
      setChatLoading(false); }
  };

  // ── Tabs ─────────────────────────────────────────────────────────

  const TABS: { id: Tab; label: string; icon: React.ReactNode; badge?: string }[] = [
    { id: "upload",   label: "Documents",    icon: <Upload size={14} /> },
    { id: "verify",   label: "Verify",       icon: <ClipboardCheck size={14} />, badge: allProcessed ? "Ready" : undefined },
    { id: "profile",  label: "Profile",      icon: <FileText size={14} /> },
    { id: "benefits", label: "Benefits",     icon: <Heart size={14} /> },
    { id: "chat",     label: "Chat",         icon: <Users size={14} /> },
  ];

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 max-w-5xl mx-auto w-full px-4 py-6 space-y-4">

        {/* Header */}
        <div className="flex items-center gap-3">
          <button onClick={() => setLocation("/dashboard")} className="text-gray-400 hover:text-navy">
            <ArrowLeft size={18} />
          </button>
          <div className="bg-gradient-to-br from-navy to-navy-dark p-2 rounded-xl shadow">
            <Users className="h-5 w-5 text-gold" />
          </div>
          <div>
            <h1 className="font-black text-navy text-base leading-none">Battle Buddy</h1>
            <p className="text-xs text-gray-400">claude-opus-4-5 · Extended Reasoning · Claimant Profile</p>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 overflow-x-auto">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex-1 min-w-fit flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-semibold transition-all whitespace-nowrap ${
                tab === t.id ? "bg-white text-navy shadow-sm" : "text-gray-500 hover:text-navy"
              }`}
            >
              {t.icon}
              {t.label}
              {t.badge && (
                <span className="ml-1 bg-gold text-navy text-[10px] font-bold px-1.5 py-0.5 rounded-full">
                  {t.badge}
                </span>
              )}
            </button>
          ))}
        </div>

        {/* ── Upload Tab ── */}
        {tab === "upload" && (
          <div className="space-y-4">
            <div
              onDrop={onDrop}
              onDragOver={e => e.preventDefault()}
              className="border-2 border-dashed border-gray-300 hover:border-navy rounded-2xl p-10 text-center cursor-pointer transition-colors"
              onClick={() => document.getElementById("file-input")?.click()}
            >
              <Upload className="mx-auto h-10 w-10 text-gray-300 mb-3" />
              <p className="font-semibold text-gray-600">Drop up to {MAX_FILES} files here</p>
              <p className="text-xs text-gray-400 mt-1">
                DD-214, rating decisions, medical records, claim letters — PDF, images, text · Up to 5 GB per file
              </p>
              <input
                id="file-input"
                type="file"
                multiple
                accept=".pdf,.txt,.md,.jpg,.jpeg,.png,.webp"
                className="hidden"
                onChange={e => e.target.files && addFiles(e.target.files)}
              />
            </div>

            {files.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm divide-y divide-gray-100">
                {files.map((f, i) => (
                  <div key={i} className="flex items-center gap-3 px-4 py-3">
                    <FileText size={16} className="text-gray-400 shrink-0" />
                    <span className="flex-1 text-sm text-gray-700 truncate">{f.file.name}</span>
                    <span className="text-xs text-gray-400">{(f.file.size / 1024 / 1024).toFixed(1)} MB</span>
                    {f.status === "done" && <CheckCircle size={15} className="text-green-500" />}
                    {f.status === "error" && <AlertTriangle size={15} className="text-red-500" />}
                    {f.status === "uploading" && <Loader2 size={15} className="animate-spin text-navy" />}
                  </div>
                ))}
              </div>
            )}

            {processJobIds.length > 0 && processedCount < processJobIds.length && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-4 space-y-2">
                <p className="text-sm font-semibold text-navy">Analyzing documents with claude-opus-4-5…</p>
                <Progress value={(processedCount / processJobIds.length) * 100} className="h-2" />
                <p className="text-xs text-gray-400">{processedCount} / {processJobIds.length} complete</p>
              </div>
            )}

            {allProcessed && (
              <div className="bg-green-50 border border-green-200 rounded-2xl p-4 flex items-center gap-3">
                <CheckCircle className="text-green-600 shrink-0" size={20} />
                <div>
                  <p className="font-semibold text-green-800 text-sm">
                    {processedCount} document{processedCount > 1 ? "s" : ""} analyzed — profile ready for verification
                  </p>
                  <button
                    className="text-xs text-green-700 underline mt-0.5"
                    onClick={() => setTab("verify")}
                  >
                    Start verification →
                  </button>
                </div>
              </div>
            )}

            <Button
              className="w-full bg-navy text-white hover:bg-navy-dark"
              onClick={uploadAll}
              disabled={uploading || files.length === 0 || files.every(f => f.status === "done")}
            >
              {uploading
                ? <><Loader2 size={15} className="animate-spin mr-2" />Uploading…</>
                : `Upload & Analyze ${files.length} File${files.length !== 1 ? "s" : ""}`}
            </Button>
          </div>
        )}

        {/* ── Verify Tab ── */}
        {tab === "verify" && (
          <div>
            {!allProcessed && !profile && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 text-center text-gray-400">
                <ClipboardCheck className="mx-auto h-10 w-10 mb-3 opacity-30" />
                <p className="font-semibold">No documents processed yet</p>
                <p className="text-sm mt-1">Upload your documents first, then come back here to verify the extracted data.</p>
                <Button variant="outline" className="mt-4 border-navy text-navy" onClick={() => setTab("upload")}>
                  Upload Documents
                </Button>
              </div>
            )}
            {(allProcessed || profile) && userId && (
              <VerificationChat
                userId={userId}
                profile={(profile ?? {}) as Record<string, unknown>}
                onProfileUpdate={updated => setProfile(updated as unknown as Profile)}
                onComplete={() => { loadProfile(); setTab("profile"); }}
              />
            )}
          </div>
        )}

        {/* ── Profile Tab ── */}
        {tab === "profile" && (
          <div className="space-y-4">
            {profileLoading && (
              <div className="flex justify-center py-12">
                <Loader2 className="animate-spin text-navy h-8 w-8" />
              </div>
            )}
            {!profileLoading && !profile?.service?.length && !profile?.claims?.length && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 text-center text-gray-400">
                <FileText className="mx-auto h-10 w-10 mb-3 opacity-30" />
                <p className="font-semibold">No profile data yet</p>
                <p className="text-sm mt-1">Upload your documents to build your claimant profile.</p>
                <Button variant="outline" className="mt-4 border-navy text-navy" onClick={() => setTab("upload")}>
                  Upload Documents
                </Button>
              </div>
            )}
            {!profileLoading && profile && (
              <>
                {Object.keys(profile.personal || {}).length > 0 && (
                  <Section title="Personal Information" icon={<Shield size={15} />}>
                    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                      {Object.entries(profile.personal).map(([k, v]) =>
                        v ? (
                          <div key={k}>
                            <dt className="text-gray-400 text-xs capitalize">{k.replace(/_/g, " ")}</dt>
                            <dd className="font-medium text-gray-800">{v}</dd>
                          </div>
                        ) : null
                      )}
                    </dl>
                  </Section>
                )}

                {profile.service?.length > 0 && (
                  <Section title="Service Timeline" icon={<Clock size={15} />}>
                    {profile.service.map((s, i) => (
                      <div key={i} className="border-l-2 border-navy pl-4 pb-4 last:pb-0">
                        <p className="font-bold text-navy text-sm">{s.branch}</p>
                        <p className="text-xs text-gray-500">{s.entry_date} — {s.sep_date} · {s.discharge}</p>
                        {s.mos && <p className="text-xs text-gray-600 mt-0.5">MOS: {s.mos}</p>}
                        {s.deployments?.map((d: any, j: number) => (
                          <p key={j} className="text-xs text-gray-500 mt-0.5">↳ {d.location} {d.dates}</p>
                        ))}
                      </div>
                    ))}
                  </Section>
                )}

                {profile.claims?.length > 0 && (
                  <Section title="Claims History" icon={<FileText size={15} />}>
                    {profile.claims.map((c, i) => (
                      <div key={i} className="rounded-xl border border-gray-100 p-3 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm text-gray-800">#{c.claim_number || "—"}</span>
                          <StatusBadge status={c.status} />
                        </div>
                        <p className="text-xs text-gray-500">
                          Filed: {c.filed_date || "—"} · Decision: {c.decision_date || "pending"}
                        </p>
                        {c.conditions?.length > 0 && (
                          <p className="text-xs text-gray-600">Conditions: {c.conditions.join(", ")}</p>
                        )}
                        {c.rating > 0 && (
                          <p className="text-xs font-semibold text-navy">Rating: {c.rating}%</p>
                        )}
                        {c.denial_reason && (
                          <p className="text-xs text-red-600 bg-red-50 rounded px-2 py-1 mt-1">
                            Denial: {c.denial_reason}
                          </p>
                        )}
                      </div>
                    ))}
                  </Section>
                )}

                {profile.appeals?.length > 0 && (
                  <Section title="Appeals" icon={<AlertTriangle size={15} />}>
                    {profile.appeals.map((a, i) => (
                      <div key={i} className="rounded-xl border border-orange-100 bg-orange-50 p-3 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-sm text-gray-800">Claim #{a.claim_number || "—"}</span>
                          {a.deadline && (
                            <span className="text-xs font-bold text-red-600">Deadline: {a.deadline}</span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500">
                          Denial date: {a.denial_date || "—"} · Status: {a.status || "not filed"}
                        </p>
                        {a.draft && (
                          <div className="mt-2">
                            <p className="text-xs font-semibold text-gray-700 mb-1">Draft Appeal Opening:</p>
                            <p className="text-xs text-gray-600 bg-white rounded p-2 border border-orange-200">
                              {a.draft}
                            </p>
                          </div>
                        )}
                      </div>
                    ))}
                  </Section>
                )}

                {profile.notes && (
                  <Section title="Additional Notes" icon={<FileText size={15} />}>
                    <p className="text-sm text-gray-600 whitespace-pre-wrap">{profile.notes}</p>
                  </Section>
                )}
              </>
            )}
          </div>
        )}

        {/* ── Benefits Tab ── */}
        {tab === "benefits" && (
          <div className="space-y-4">
            {!profile?.benefits?.awarded?.length && !profile?.benefits?.available?.length && (
              <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 text-center text-gray-400">
                <Heart className="mx-auto h-10 w-10 mb-3 opacity-30" />
                <p className="font-semibold">No benefits data yet</p>
                <p className="text-sm mt-1">Upload your documents to discover awarded and available benefits.</p>
                <Button variant="outline" className="mt-4 border-navy text-navy" onClick={() => setTab("upload")}>
                  Upload Documents
                </Button>
              </div>
            )}

            {(profile?.benefits?.awarded?.length ?? 0) > 0 && (
              <Section title="Awarded Benefits" icon={<CheckCircle size={15} />}>
                {profile!.benefits.awarded.map((b, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                    <div>
                      <p className="font-semibold text-sm text-gray-800">{b.name}</p>
                      <p className="text-xs text-gray-400">Effective: {b.effective_date || "—"}</p>
                    </div>
                    {b.amount && <span className="text-sm font-bold text-navy">{b.amount}</span>}
                  </div>
                ))}
              </Section>
            )}

            {(profile?.benefits?.available?.length ?? 0) > 0 && (
              <Section title="Available Benefits You May Not Know About" icon={<Heart size={15} />}>
                {profile!.benefits.available.map((b, i) => (
                  <div key={i} className="rounded-xl border border-gray-100 p-3 space-y-1">
                    <div className="flex items-center justify-between">
                      <p className="font-bold text-sm text-navy">{b.name}</p>
                      {b.cfr_cite && <span className="text-xs text-gray-400">{b.cfr_cite}</span>}
                    </div>
                    <p className="text-xs text-gray-600">{b.eligibility}</p>
                    {b.how_to_claim && (
                      <div className="flex items-start gap-1.5 mt-1">
                        <ChevronRight size={12} className="text-gold mt-0.5 shrink-0" />
                        <p className="text-xs text-gray-500">{b.how_to_claim}</p>
                      </div>
                    )}
                  </div>
                ))}
              </Section>
            )}
          </div>
        )}

        {/* ── Chat Tab ── */}
        {tab === "chat" && (
          <div className="space-y-3">
            <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-y-auto p-4 space-y-3 min-h-[420px] max-h-[520px]">
              {messages.map(m => (
                <div key={m.id} className={`flex ${m.isUser ? "justify-end" : "justify-start"}`}>
                  {m.id === "thinking" ? (
                    <div className="flex items-center gap-2 bg-gray-100 rounded-2xl px-4 py-2.5 text-sm text-gray-500">
                      <Loader2 size={14} className="animate-spin" />Thinking deeply…
                    </div>
                  ) : (
                    <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                      m.isUser
                        ? "bg-navy text-white rounded-br-sm"
                        : "bg-gray-100 text-gray-800 rounded-bl-sm"
                    }`}>
                      {m.content}
                    </div>
                  )}
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
            <form onSubmit={e => { e.preventDefault(); sendChat(chatInput); }} className="flex gap-2">
              <Input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                placeholder="Ask your Battle Buddy…"
                disabled={chatLoading}
                className="flex-1"
              />
              <Button
                type="submit"
                disabled={chatLoading || !chatInput.trim()}
                className="bg-navy text-white hover:bg-navy-dark px-4"
              >
                {chatLoading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
              </Button>
            </form>
          </div>
        )}
      </main>
      <Footer />
    </div>
  );
}

// ── Shared sub-components ─────────────────────────────────────────────

function Section({ title, icon, children }: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-5 space-y-3">
      <h2 className="flex items-center gap-2 font-bold text-navy text-sm uppercase tracking-wide">
        <span className="text-gold">{icon}</span>{title}
      </h2>
      {children}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    approved: "bg-green-100 text-green-700",
    denied: "bg-red-100 text-red-700",
    pending: "bg-yellow-100 text-yellow-700",
  };
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full capitalize ${map[status] || "bg-gray-100 text-gray-600"}`}>
      {status || "unknown"}
    </span>
  );
}
