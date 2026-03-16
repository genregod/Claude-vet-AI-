import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { MessageCircle, Send, X, User, Bot, Loader2 } from "lucide-react";
import { apiRequest } from "@/lib/queryClient";

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  timestamp: Date;
  isLoading?: boolean;
}

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatWindow({ isOpen, onClose }: ChatWindowProps) {
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Welcome! I'm here to guide you through your VA benefits onboarding. What questions do you have?",
      isUser: false,
      timestamp: new Date(),
    },
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen && !sessionId) {
      apiRequest("POST", "/chat/session", {})
        .then((r) => r.json())
        .then((d) => setSessionId(d.session_id))
        .catch(console.error);
    }
  }, [isOpen, sessionId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || isProcessing || !sessionId) return;
    setIsProcessing(true);

    const userMsg: Message = { id: Date.now().toString(), content: text, isUser: true, timestamp: new Date() };
    const loadingMsg: Message = { id: `${Date.now() + 1}`, content: "", isUser: false, timestamp: new Date(), isLoading: true };
    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setMessage("");

    try {
      const res = await apiRequest("POST", "/chat", { question: text, session_id: sessionId });
      const data = await res.json();
      setMessages((prev) =>
        prev.map((m) => (m.id === loadingMsg.id ? { ...m, content: data.answer, isLoading: false } : m))
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id ? { ...m, content: "Sorry, I couldn't process that. Please try again.", isLoading: false } : m
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-28 right-4 z-50 w-96 h-[600px]">
      <Card className="h-full flex flex-col shadow-2xl border-2 border-navy-700">
        <CardHeader className="bg-gradient-to-r from-navy-700 to-navy-800 text-white p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              <CardTitle className="text-lg font-semibold">VA Onboarding Assistant</CardTitle>
            </div>
            <Button variant="ghost" size="icon" onClick={onClose} className="text-white hover:bg-navy-600 rounded-full">
              <X className="h-5 w-5" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex-1 p-0 overflow-hidden">
          <div className="h-full p-4 overflow-y-auto">
            <div className="space-y-4">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-2 ${msg.isUser ? "justify-end" : "justify-start"}`}>
                  <div className={`flex gap-2 max-w-[80%] ${msg.isUser ? "flex-row-reverse" : ""}`}>
                    <div className={`p-2 rounded-full ${msg.isUser ? "bg-navy-700" : "bg-gold-500"}`}>
                      {msg.isUser ? <User className="h-4 w-4 text-white" /> : <Bot className="h-4 w-4 text-white" />}
                    </div>
                    <div className={`px-4 py-2 rounded-2xl ${msg.isUser ? "bg-navy-700 text-white rounded-br-none" : "bg-gray-100 text-gray-800 rounded-bl-none"}`}>
                      {msg.isLoading ? (
                        <div className="flex items-center gap-2">
                          <Loader2 className="h-4 w-4 animate-spin" />
                          <span className="text-sm">Thinking...</span>
                        </div>
                      ) : (
                        <>
                          <p className="text-sm">{msg.content}</p>
                          <p className="text-xs opacity-70 mt-1">{msg.timestamp.toLocaleTimeString()}</p>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </CardContent>

        <CardFooter className="p-4 border-t">
          <form onSubmit={(e) => { e.preventDefault(); send(message); }} className="flex gap-2 w-full">
            <Input
              type="text"
              placeholder="Ask about your VA benefits..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={!message.trim() || isProcessing} className="bg-navy-700 hover:bg-navy-800 text-white">
              {isProcessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  );
}
