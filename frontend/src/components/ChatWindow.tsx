import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { MessageCircle, Send, X, User, Bot } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
// import { useAuth } from "@/hooks/use-auth";

interface Message {
  id: string;
  content: string;
  senderId: string;
  senderDisplayName: string;
  timestamp: Date;
  isUser: boolean;
}

interface ChatWindowProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatWindow({ isOpen, onClose }: ChatWindowProps) {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentThread, setCurrentThread] = useState<string | null>(null);
  const [chatUser, setChatUser] = useState<any>(null);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const { toast } = useToast();
  // const { user } = useAuth();
  const user = { username: "Test User" }; // Temporary fix
  const queryClient = useQueryClient();

  // Create chat user mutation
  const createChatUserMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("POST", "/api/chat/users");
      return await res.json();
    },
    onSuccess: (data) => {
      setChatUser(data);
    },
    onError: (error: Error) => {
      toast({
        title: "Error creating chat user",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Create chat thread mutation
  const createThreadMutation = useMutation({
    mutationFn: async () => {
      if (!chatUser) throw new Error("Chat user not initialized");
      
      const res = await apiRequest("POST", "/api/chat/threads", {
        userDisplayName: user?.username || "Veteran User",
        userCommunicationId: chatUser.communicationUserId,
        supportDisplayName: "VA Support Agent",
        supportCommunicationId: "support-agent-001",
        topic: "Support Chat",
      });
      return await res.json();
    },
    onSuccess: (data) => {
      setCurrentThread(data.threadId);
      toast({
        title: "Connected to Support",
        description: "You're now connected with a VA support agent.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Error creating chat thread",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Send message mutation
  const sendMessageMutation = useMutation({
    mutationFn: async (content: string) => {
      if (!currentThread || !chatUser) throw new Error("Chat not initialized");
      
      const res = await apiRequest("POST", `/api/chat/threads/${currentThread}/messages`, {
        senderCommunicationId: chatUser.communicationUserId,
        senderToken: chatUser.token,
        content,
      });
      return await res.json();
    },
    onSuccess: () => {
      setMessage("");
      // Refetch messages after sending
      queryClient.invalidateQueries({ queryKey: [`/api/chat/threads/${currentThread}/messages`] });
    },
    onError: (error: Error) => {
      toast({
        title: "Error sending message",
        description: error.message,
        variant: "destructive",
      });
    },
  });

  // Fetch messages
  const { data: fetchedMessages } = useQuery({
    queryKey: [`/api/chat/threads/${currentThread}/messages`],
    queryFn: async () => {
      if (!currentThread || !chatUser) return [];
      const res = await apiRequest("GET", `/api/chat/threads/${currentThread}/messages?userToken=${chatUser.token}`);
      return await res.json();
    },
    enabled: !!currentThread && !!chatUser,
    refetchInterval: 2000, // Poll for new messages every 2 seconds
  });

  // Initialize chat when opened
  useEffect(() => {
    if (isOpen && user && !chatUser && !createChatUserMutation.isPending) {
      createChatUserMutation.mutate();
    }
  }, [isOpen, user, chatUser, createChatUserMutation]);

  // Create thread after chat user is created
  useEffect(() => {
    if (chatUser && !currentThread && !createThreadMutation.isPending) {
      createThreadMutation.mutate();
    }
  }, [chatUser, currentThread, createThreadMutation]);

  // Update messages when fetched
  useEffect(() => {
    if (fetchedMessages?.messages) {
      const formattedMessages: Message[] = fetchedMessages.messages.map((msg: any) => ({
        id: msg.id,
        content: msg.content,
        senderId: msg.senderId,
        senderDisplayName: msg.senderDisplayName,
        timestamp: new Date(msg.createdOn),
        isUser: msg.senderId === chatUser?.communicationUserId,
      }));
      setMessages(formattedMessages);
    }
  }, [fetchedMessages, chatUser]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollAreaRef.current) {
      scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !sendMessageMutation.isPending) {
      sendMessageMutation.mutate(message);
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
                        <p className="text-sm">{msg.content}</p>
                        <p className="text-xs opacity-70 mt-1">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </p>
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
              disabled={sendMessageMutation.isPending || !currentThread}
              className="flex-1"
            />
            <Button
              type="submit"
              disabled={sendMessageMutation.isPending || !message.trim() || !currentThread}
              className="bg-navy-700 hover:bg-navy-800 text-white"
            >
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </CardFooter>
      </Card>
    </div>
  );
}