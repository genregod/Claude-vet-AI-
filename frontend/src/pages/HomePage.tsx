import { useState } from "react";
import { Header } from "@/components/Header";
import { Hero } from "@/components/Hero";
import { Services } from "@/components/Services";
import { HowItWorks } from "@/components/HowItWorks";
import { Testimonials } from "@/components/Testimonials";
import { Demo } from "@/components/Demo";
import { CTA } from "@/components/CTA";
import { Footer } from "@/components/Footer";
import { SimpleChatWindow } from "@/components/SimpleChatWindow";
import { MessageCircle } from "lucide-react";

export function HomePage() {
  const [isChatOpen, setIsChatOpen] = useState(false);

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1">
        <Hero />
        <Services />
        <HowItWorks />
        <Testimonials />
        <Demo />
        <CTA />
      </main>
      <Footer />
      
      {/* Floating Chat Button */}
      <div
        onClick={() => setIsChatOpen(!isChatOpen)}
        style={{
          position: "fixed",
          bottom: "30px",
          right: "30px",
          width: "70px",
          height: "70px",
          backgroundColor: "#001c3d",
          color: "white",
          borderRadius: "50%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          cursor: "pointer",
          zIndex: 99999,
          boxShadow: "0 10px 30px rgba(0, 0, 0, 0.5)",
        }}
        className="hover:scale-110 transition-transform"
      >
        <MessageCircle size={32} color="white" strokeWidth={2} />
      </div>
      
      {/* Chat Window */}
      {isChatOpen && (
        <SimpleChatWindow
          isOpen={isChatOpen}
          onClose={() => setIsChatOpen(false)}
        />
      )}
    </div>
  );
}
