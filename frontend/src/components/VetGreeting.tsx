import { useEffect, useRef, useState } from "react";
import { Shield, Loader2, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiRequest } from "@/lib/queryClient";

const DISCLAIMER =
  "This assessment is for informational purposes only and does not constitute official VA, legal, or medical advice. Consult a VA-accredited VSO or attorney for your specific situation.";

interface Message { role: "assistant" | "user"; content: string; }

interface Props {
  veteranName: string;
  extractedData?: Record<string, unknown>; // from DD-214 / STR extraction
  sessionId?: string;
}

export function VetGreeting({ veteranName, extractedData, sessionId: _sessionId }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatSessionId, setChatSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Build greeting context from extracted DD-214 data
  const buildGreetingPrompt = () => {
    const rank = (extractedData as any)?.rank ?? (extractedData as any)?.grade ?? "";
    const branch = (extractedData as any)?.branch ?? (extractedData as any)?.service_branch ?? "";
    const conditions = (extractedData as any)?.conditions ?? [];
    const serviceYears = (extractedData as any)?.service_years ?? "";
    const discharge = (extractedData as any)?.discharge_type ?? "Honorable";

    const displayName = rank ? `${rank} ${veteranName}` : veteranName;

    let context = `Veteran profile from uploaded documents:\n`;
    if (rank) context += `- Rank/Grade: ${rank}\n`;
    if (branch) context += `- Branch: ${branch}\n`;
    if (serviceYears) context += `- Service: ${serviceYears}\n`;
    if (discharge) context += `- Discharge: ${discharge}\n`;
    if (conditions?.length) context += `- Noted conditions: ${conditions.join(", ")}\n`;

    return `${context}\nGreet ${displayName} warmly by name and rank. Based on their service record, give a brief personalized assessment of what VA benefits they may qualify for. Be specific, cite 38 CFR where relevant, and end with the most important next step they should take. Keep it under 400 characters.`;
  };

  useEffect(() => {
    const init = async () => {
      setLoading(true);
      try {
        // Create chat session
        const sessRes = await apiRequest("POST", "/chat/session");
        const { session_id } = await sessRes.json();
        setChatSessionId(session_id);

        // Send greeting prompt
        const res = await apiRequest("POST", "/chat", {
          question: buildGreetingPrompt(),
          session_id,
        });
        const data = await res.json();
        setMessages([{ role: "assistant", content: data.answer }]);
      } catch (e) {
        setMessages([{ role: "assistant", content: `Welcome, ${veteranName}. I'm Val, your AI battle buddy. I'm here to help you navigate your VA claim. What would you like to know?` }]);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);
    try {
      const res = await apiRequest("POST", "/chat", { question, session_id: chatSessionId });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.answer }]);
    } catch {
      setMessages((prev) => [...prev, { role: "assistant", content: "Sorry, I hit a snag. Try again in a moment." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-h-[600px] bg-white rounded-2xl shadow-xl border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-navy to-navy-dark px-5 py-4 flex items-center gap-3">
        <div className="bg-gold/20 p-2 rounded-full">
          <Shield className="h-5 w-5 text-gold" />
        </div>
        <div>
          <p className="text-white font-bold text-sm">Val — Your AI Battle Buddy</p>
          <p className="text-white/60 text-xs">Powered by 38 CFR · Not legal advice</p>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-2">
        <p className="text-xs text-amber-700">{DISCLAIMER}</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {loading && messages.length === 0 && (
          <div className="flex items-center gap-2 text-gray-500 text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Analyzing your service record…
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
              m.role === "user"
                ? "bg-navy text-white rounded-br-sm"
                : "bg-gray-100 text-gray-800 rounded-bl-sm"
            }`}>
              {m.content}
            </div>
          </div>
        ))}
        {loading && messages.length > 0 && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-2xl rounded-bl-sm px-4 py-2.5">
              <Loader2 className="h-4 w-4 animate-spin text-gray-500" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t p-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          placeholder="Ask Val anything about your claim…"
          className="flex-1 text-sm border border-gray-200 rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-navy/30"
        />
        <Button size="sm" onClick={send} disabled={loading || !input.trim()} className="bg-navy text-white hover:bg-navy-dark px-3">
          <Send size={15} />
        </Button>
      </div>
    </div>
  );
}
