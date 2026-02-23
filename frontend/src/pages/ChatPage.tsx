import { useState } from "react";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { SimpleChatWindow } from "@/components/SimpleChatWindow";

export function ChatPage() {
  const [isChatOpen] = useState(true);

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl font-bold text-navy mb-4">
            Chat with Valor Assist
          </h1>
          <p className="text-lg text-gray-600 mb-8">
            Get instant answers to your VA claims questions powered by AI.
          </p>
          <SimpleChatWindow isOpen={isChatOpen} onClose={() => {}} />
        </div>
      </main>
      <Footer />
    </div>
  );
}
