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
  sources?: any[];
}

interface ChatResponse {
  answer: string;
  sources?: any[];
  model?: string;
}

interface SimpleChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SimpleChatWindow({ isOpen, onClose }: SimpleChatWindowProps) {
  const [message, setMessage] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      content: "Hello! I'm Valor Assist, powered by Claude AI. I can help you navigate VA disability claims, appeals, and regulations. How can I assist you today?",
      isUser: false,
      timestamp: new Date(),
    },
  ]);
  const [quickActions] = useState<string[]>([
    "Learn about appeals",
    "PTSD service connection",
    "Check eligibility",
    "Filing instructions"
  ]);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Create session on mount
  useEffect(() => {
    const createSession = async () => {
      try {
        const response = await apiRequest("POST", "/chat/session", {});
        const data = await response.json();
        setSessionId(data.session_id);
      } catch (error) {
        console.error("Failed to create session:", error);
      }
    };
    
    if (isOpen && !sessionId) {
      createSession();
    }
  }, [isOpen, sessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isProcessing && sessionId) {
      setIsProcessing(true);
      
      // Add user message
      const userMessage: Message = {
        id: Date.now().toString(),
        content: message,
        isUser: true,
        timestamp: new Date(),
      };
      
      // Add loading message
      const loadingMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: "",
        isUser: false,
        timestamp: new Date(),
        isLoading: true,
      };
      
      setMessages((prev) => [...prev, userMessage, loadingMessage]);
      setMessage("");
      
      try {
        // Send message to FastAPI backend
        const response = await apiRequest("POST", "/chat", {
          question: userMessage.content,
          session_id: sessionId
        });
        const chatResponse: ChatResponse = await response.json();
        
        // Update loading message with AI response
        setMessages((prev) => 
          prev.map((msg) => 
            msg.id === loadingMessage.id 
              ? { 
                  ...msg, 
                  content: chatResponse.answer, 
                  isLoading: false,
                  sources: chatResponse.sources 
                }
              : msg
          )
        );
      } catch (error) {
        // Update loading message with error
        setMessages((prev) => 
          prev.map((msg) => 
            msg.id === loadingMessage.id 
              ? { 
                  ...msg, 
                  content: "I apologize, but I'm having trouble processing your request. Please try again.", 
                  isLoading: false 
                }
              : msg
          )
        );
      } finally {
        setIsProcessing(false);
      }
    }
  };

  const handleQuickAction = async (action: string) => {
    if (!sessionId || isProcessing) return;
    
    setIsProcessing(true);
    setMessage(action);
    
    // Add user message for the quick action
    const userMessage: Message = {
      id: Date.now().toString(),
      content: action,
      isUser: true,
      timestamp: new Date(),
    };
    
    const loadingMessage: Message = {
      id: (Date.now() + 1).toString(),
      content: "",
      isUser: false,
      timestamp: new Date(),
      isLoading: true,
    };
    
    setMessages((prev) => [...prev, userMessage, loadingMessage]);
    setMessage("");
    
    try {
      const response = await apiRequest("POST", "/chat/quick-action", {
        action: action.toLowerCase().replace(/\s+/g, '_'),
        session_id: sessionId
      });
      const chatResponse: ChatResponse = await response.json();
      
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === loadingMessage.id 
            ? { 
                ...msg, 
                content: chatResponse.answer, 
                isLoading: false,
                sources: chatResponse.sources 
              }
            : msg
        )
      );
    } catch (error) {
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === loadingMessage.id 
            ? { 
                ...msg, 
                content: "I apologize, but I'm having trouble processing your request. Please try again.", 
                isLoading: false 
              }
            : msg
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-96 h-[600px]">
      <Card className="h-full flex flex-col shadow-2xl border-2 border-navy-700">
        <CardHeader className="bg-gradient-to-r from-navy-700 to-navy-800 text-white p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              <CardTitle className="text-lg font-semibold">Valor Assist AI</CardTitle>
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
          <div className="h-full p-4 overflow-y-auto">
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
                            {msg.timestamp.toLocaleTimeString()}
                          </p>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
            
            {/* Quick Actions */}
            {quickActions.length > 0 && (
              <div className="mt-4 p-2 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-600 mb-2">Quick actions:</p>
                <div className="flex flex-wrap gap-2">
                  {quickActions.map((action, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      size="sm"
                      onClick={() => handleQuickAction(action)}
                      disabled={isProcessing}
                      className="text-xs hover:bg-navy-100 hover:text-navy-700 hover:border-navy-700"
                    >
                      {action}
                    </Button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </CardContent>
        
        <CardFooter className="p-4 border-t">
          <form onSubmit={handleSendMessage} className="flex gap-2 w-full">
            <Input
              type="text"
              placeholder="Type your message..."
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={!message.trim() || isProcessing}
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