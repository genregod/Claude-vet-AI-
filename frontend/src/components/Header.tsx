import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Shield } from "lucide-react";
import { useState } from "react";

export function Header() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [, setLocation] = useLocation();

  return (
    <header className="glass-card sticky top-0 z-50 border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-20">
          {/* Logo with modern design */}
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="bg-gradient-to-br from-navy to-navy-dark p-3 rounded-xl shadow-lg transform hover:scale-105 transition-transform">
                <Shield className="h-8 w-8 text-gold" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-gold rounded-full animate-pulse"></div>
            </div>
            <div>
              <h1 className="text-2xl font-black gradient-text">ValorAssist</h1>
              <p className="text-xs text-gray-600 font-medium">Veteran Claims Excellence</p>
            </div>
          </div>

          {/* Desktop Navigation with modern styling */}
          <nav className="hidden md:flex items-center space-x-1">
            {[
              { href: "#services", label: "Services" },
              { href: "#how-it-works", label: "How It Works" },
              { href: "#testimonials", label: "Success Stories" },
              { href: "#contact", label: "Contact" }
            ].map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="px-4 py-2 text-gray-700 hover:text-navy font-medium rounded-lg hover:bg-gray-100 transition-all duration-200"
              >
                {link.label}
              </a>
            ))}
            <div className="ml-4">
              <Button
                onClick={() => setLocation("/start-claim")}
                className="bg-gradient-to-r from-navy to-navy-light text-white hover:from-navy-light hover:to-navy font-bold px-6 py-2 rounded-xl shadow-lg transform hover:scale-105 transition-all"
              >
                Start Your Claim
              </Button>
            </div>
          </nav>

          {/* Mobile Menu Button with animation */}
          <button
            className="md:hidden relative w-10 h-10 flex items-center justify-center rounded-lg hover:bg-gray-100 transition-colors"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <div className="relative">
              <span className={`absolute block h-0.5 w-5 bg-navy transform transition-all duration-300 ${isMenuOpen ? 'rotate-45' : '-translate-y-1.5'}`}></span>
              <span className={`block h-0.5 w-5 bg-navy transition-all duration-300 ${isMenuOpen ? 'opacity-0' : ''}`}></span>
              <span className={`absolute block h-0.5 w-5 bg-navy transform transition-all duration-300 ${isMenuOpen ? '-rotate-45' : 'translate-y-1.5'}`}></span>
            </div>
          </button>
        </div>

        {/* Mobile Menu with smooth animation */}
        <div className={`md:hidden transition-all duration-300 ease-in-out ${isMenuOpen ? 'max-h-96' : 'max-h-0'} overflow-hidden`}>
          <nav className="py-4 border-t border-gray-100">
            {[
              { href: "#services", label: "Services" },
              { href: "#how-it-works", label: "How It Works" },
              { href: "#testimonials", label: "Success Stories" },
              { href: "#contact", label: "Contact" }
            ].map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="block px-4 py-3 text-gray-700 hover:text-navy hover:bg-gray-50 font-medium transition-colors"
                onClick={() => setIsMenuOpen(false)}
              >
                {link.label}
              </a>
            ))}
            <div className="px-4 pt-4">
              <Button
                onClick={() => { setIsMenuOpen(false); setLocation("/start-claim"); }}
                className="w-full bg-gradient-to-r from-navy to-navy-light text-white font-bold py-3 rounded-xl shadow-lg"
              >
                Start Your Claim
              </Button>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}