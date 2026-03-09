import { useState, useEffect, useRef } from "react";
import { apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { MessageCircle, Send, X, User, Bot, Loader2 } from "lucide-react";

interface Message {
  id: string;
  content: string;
  timestamp: Date;
  isUser: boolean;
  isLoading?: boolean;
}

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatWindow({ isOpen, onClose }: ChatWindowProps) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      content: "Hello! I'm Valor Assist. How can I help with your VA claim today?",
      timestamp: new Date(),
      isUser: false,
    },
  ]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Create session on mount
  useEffect(() => {
    if (isOpen && !sessionId) {
      const createSession = async () => {
        try {
          const res = await apiRequest("POST", "/chat/onboarding-chat", {
            message: "start_session",
          });
          const data = await res.json();
          setSessionId(data.session_id || `session_${Date.now()}`);
        } catch {
          setSessionId(`local_${Date.now()}`);
        }
      };
      createSession();
    }
  }, [isOpen, sessionId]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || isProcessing || !sessionId) return;

    setIsProcessing(true);

    const userMsg: Message = {
      id: Date.now().toString(),
      content: message,
      timestamp: new Date(),
      isUser: true,
    };
    const loadingMsg: Message = {
      id: (Date.now() + 1).toString(),
      content: "",
      timestamp: new Date(),
      isUser: false,
      isLoading: true,
    };

    setMessages((prev) => [...prev, userMsg, loadingMsg]);
    setMessage("");

    try {
      const res = await apiRequest("POST", "/chat/chat", {
        message: userMsg.content,
        sessionId,
      });
      const data = await res.json();
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? { ...m, content: data.response || data.answer || "No response", isLoading: false }
            : m
        )
      );
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === loadingMsg.id
            ? { ...m, content: "Sorry, something went wrong. Please try again.", isLoading: false }
            : m
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 h-[600px] animate-fadeIn">
      <Card className="h-full flex flex-col shadow-2xl border-2 border-navy-700">
        <CardHeader className="bg-gradient-to-r from-navy-700 to-navy-800 text-white p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              <CardTitle className="text-lg font-semibold">VA Support Chat</CardTitle>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="text-white hover:bg-navy-600 rounded-full"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </CardHeader>
        
        <CardContent className="flex-1 p-0 overflow-hidden">
          <ScrollArea className="h-full p-4" ref={scrollAreaRef}>
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-8">
                <MessageCircle className="h-12 w-12 mx-auto mb-2 text-gray-300" />
                <p>Start a conversation with our VA support team</p>
              </div>
            ) : (
              <div className="space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex gap-2 ${msg.isUser ? "justify-end" : "justify-start"}`}
                  >
                    <div className={`flex gap-2 max-w-[80%] ${msg.isUser ? "flex-row-reverse" : ""}`}>
                      <div
                        className={`p-2 rounded-full ${
                          msg.isUser ? "bg-navy-700" : "bg-gold-500"
                        }`}
                      >
                        {msg.isUser ? (
                          <User className="h-4 w-4 text-white" />
                        ) : (
                          <Bot className="h-4 w-4 text-white" />
                        )}
                      </div>
                      <div
                        className={`px-4 py-2 rounded-2xl ${
                          msg.isUser
                            ? "bg-navy-700 text-white rounded-br-none"
                            : "bg-gray-100 text-gray-800 rounded-bl-none"
                        }`}
                      >
                        {msg.isLoading ? (
                          <div className="flex items-center gap-2">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span className="text-sm">Thinking...</span>
                          </div>
                        ) : (
                          <>
                            <p className="text-sm">{msg.content}</p>
                            <p className="text-xs opacity-70 mt-1">
                              {new Date(msg.timestamp).toLocaleTimeString()}
                            </p>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </CardContent>
        
        <CardFooter className="p-4 border-t">
          <form onSubmit={handleSendMessage} className="flex gap-2 w-full">
            <Input
              type="text"
              placeholder="Type your message..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              disabled={isProcessing}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={isProcessing || !message.trim()}
              className="bg-navy-700 hover:bg-navy-800 text-white"
            >
              {isProcessing ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  );
}