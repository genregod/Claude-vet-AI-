import { useState, useRef, useEffect } from "react";
import { useLocation } from "wouter";
import { Users, Send, Loader2, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

interface Message {
  id: string;
  content: string;
  isUser: boolean;
}

const API_BASE = (import.meta.env.VITE_API_URL || "").trim().replace(/\/+$/, "");

const STARTERS = [
  "How do I appeal a VA denial?",
  "What evidence do I need for PTSD?",
  "Explain the AMA appeal lanes",
  "How does combined rating work?",
];

async function pollResult(jobId: string, signal: AbortSignal): Promise<string> {
  for (let i = 0; i < 90; i++) {
    if (signal.aborted) throw new Error("aborted");
    await new Promise((r) => setTimeout(r, 2000));
    const res = await fetch(`${API_BASE}/api/battle-buddy/result/${jobId}`, { signal });
    const data = await res.json();
    if (data.status === "done") return data.answer;
    if (data.status === "error") throw new Error(data.error || "Job failed");
  }
  throw new Error("Timed out waiting for response.");
}

export function BattleBuddyPage() {
  const [, setLocation] = useLocation();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "0",
      content:
        "Hey — I'm your Battle Buddy. I've been through the VA system and I'm here to help you navigate it. What's going on with your claim?",
      isUser: false,
    },
  ]);
  const [history, setHistory] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: Message = { id: Date.now().toString(), content: text, isUser: true };
    setMessages((prev) => [...prev, userMsg, { id: "thinking", content: "", isUser: false }]);
    setInput("");
    setLoading(true);

    abortRef.current = new AbortController();

    try {
      // POST → get job_id immediately
      const postRes = await fetch(`${API_BASE}/api/battle-buddy/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: text, conversation_history: history }),
        signal: abortRef.current.signal,
      });
      const { job_id } = await postRes.json();

      // Poll until done
      const answer = await pollResult(job_id, abortRef.current.signal);

      setMessages((prev) => [
        ...prev.filter((m) => m.id !== "thinking"),
        { id: Date.now().toString(), content: answer, isUser: false },
      ]);
      setHistory((h) => [...h, { role: "user", content: text }, { role: "assistant", content: answer }]);
    } catch (err: unknown) {
      if ((err as Error).message === "aborted") return;
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== "thinking"),
        {
          id: Date.now().toString(),
          content: (err as Error).message || "Something went wrong — try again.",
          isUser: false,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 flex flex-col max-w-2xl mx-auto w-full px-4 py-6 gap-4">
        {/* Title bar */}
        <div className="flex items-center gap-3">
          <button onClick={() => setLocation("/dashboard")} className="text-gray-400 hover:text-navy">
            <ArrowLeft size={18} />
          </button>
          <div className="bg-gradient-to-br from-navy to-navy-dark p-2 rounded-xl shadow">
            <Users className="h-5 w-5 text-gold" />
          </div>
          <div>
            <h1 className="font-black text-navy text-base leading-none">Battle Buddy</h1>
            <p className="text-xs text-gray-400">Powered by Claude claude-opus-4-5 · Extended Reasoning</p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 bg-white rounded-2xl border border-gray-200 shadow-sm overflow-y-auto p-4 space-y-3 min-h-[400px]">
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.isUser ? "justify-end" : "justify-start"}`}>
              {m.id === "thinking" ? (
                <div className="flex items-center gap-2 bg-gray-100 rounded-2xl px-4 py-2.5 text-sm text-gray-500">
                  <Loader2 size={14} className="animate-spin" />
                  Thinking deeply…
                </div>
              ) : (
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
                    m.isUser
                      ? "bg-navy text-white rounded-br-sm"
                      : "bg-gray-100 text-gray-800 rounded-bl-sm"
                  }`}
                >
                  {m.content}
                </div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Starters */}
        {messages.filter((m) => m.isUser).length === 0 && (
          <div className="grid grid-cols-2 gap-2">
            {STARTERS.map((s) => (
              <button
                key={s}
                onClick={() => send(s)}
                className="text-xs text-left px-3 py-2 rounded-xl border border-gray-200 hover:border-navy hover:text-navy text-gray-600 transition-colors bg-white"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your Battle Buddy…"
            disabled={loading}
            className="flex-1"
          />
          <Button type="submit" disabled={loading || !input.trim()} className="bg-navy text-white hover:bg-navy-dark px-4">
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          </Button>
        </form>
      </main>
      <Footer />
    </div>
  );
}
