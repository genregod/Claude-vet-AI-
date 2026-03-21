import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { signOut, getCurrentUser } from "aws-amplify/auth";
import { Button } from "@/components/ui/button";
import { Shield, LogOut, LogIn, FileText, Heart, MessageCircle, Home } from "lucide-react";

interface AuthUser { name: string; email: string; }

export function Header() {
  const [, setLocation] = useLocation();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then((u) => {
        const name = (u as any).signInDetails?.loginId ?? u.username ?? "";
        setUser({ name, email: name });
      })
      .catch(() => setUser(null));
  }, []);

  const handleSignOut = async () => {
    await signOut();
    setUser(null);
    setLocation("/");
  };

  const isSecure = !!user;

  return (
    <header className="bg-white sticky top-0 z-50 border-b border-gray-200 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <button onClick={() => setLocation("/")} className="flex items-center space-x-3">
            <div className="bg-gradient-to-br from-navy to-navy-dark p-2 rounded-xl shadow-lg">
              <Shield className="h-6 w-6 text-gold" />
            </div>
            <div>
              <span className="text-xl font-black gradient-text">ValorAssist</span>
              <p className="text-xs text-gray-500 leading-none">Veteran Claims Excellence</p>
            </div>
          </button>

          {/* Desktop Nav */}
          <nav className="hidden md:flex items-center gap-1">
            {isSecure ? (
              <>
                <NavBtn icon={<Home size={15} />} label="Dashboard" onClick={() => setLocation("/dashboard")} />
                <NavBtn icon={<FileText size={15} />} label="My Claims" onClick={() => setLocation("/dashboard?tab=claims")} />
                <NavBtn icon={<Heart size={15} />} label="Benefits" onClick={() => setLocation("/dashboard?tab=benefits")} />
                <NavBtn icon={<MessageCircle size={15} />} label="Battle Buddy" onClick={() => setLocation("/battle-buddy")} />
                <div className="ml-3 flex items-center gap-3 border-l pl-3">
                  <span className="text-sm font-semibold text-navy truncate max-w-[140px]">{user.name}</span>
                  <Button size="sm" variant="outline" onClick={handleSignOut} className="gap-1 text-red-600 border-red-200 hover:bg-red-50">
                    <LogOut size={14} /> Sign Out
                  </Button>
                </div>
              </>
            ) : (
              <>
                {[["#services","Services"],["#how-it-works","How It Works"],["#testimonials","Success Stories"]].map(([href, label]) => (
                  <a key={href} href={href} className="px-3 py-2 text-sm text-gray-700 hover:text-navy font-medium rounded-lg hover:bg-gray-100 transition-all">{label}</a>
                ))}
                <Button size="sm" variant="outline" onClick={() => setLocation("/signin")} className="ml-2 gap-1">
                  <LogIn size={14} /> Sign In
                </Button>
                <Button size="sm" onClick={() => setLocation("/start-claim")} className="bg-navy text-white hover:bg-navy-dark ml-1">
                  Start Claim
                </Button>
              </>
            )}
          </nav>

          {/* Mobile toggle */}
          <button className="md:hidden p-2 rounded-lg hover:bg-gray-100" onClick={() => setMenuOpen(!menuOpen)}>
            <div className="space-y-1">
              <span className={`block h-0.5 w-5 bg-navy transition-all ${menuOpen ? "rotate-45 translate-y-1.5" : ""}`} />
              <span className={`block h-0.5 w-5 bg-navy transition-all ${menuOpen ? "opacity-0" : ""}`} />
              <span className={`block h-0.5 w-5 bg-navy transition-all ${menuOpen ? "-rotate-45 -translate-y-1.5" : ""}`} />
            </div>
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div className="md:hidden py-3 border-t border-gray-100 space-y-1">
            {isSecure ? (
              <>
                <MobileNavBtn label="Dashboard" onClick={() => { setLocation("/dashboard"); setMenuOpen(false); }} />
                <MobileNavBtn label="My Claims" onClick={() => { setLocation("/dashboard?tab=claims"); setMenuOpen(false); }} />
                <MobileNavBtn label="Benefits" onClick={() => { setLocation("/dashboard?tab=benefits"); setMenuOpen(false); }} />
                <MobileNavBtn label="Battle Buddy" onClick={() => { setLocation("/battle-buddy"); setMenuOpen(false); }} />
                <div className="px-4 pt-2 flex items-center justify-between">
                  <span className="text-sm font-semibold text-navy">{user.name}</span>
                  <Button size="sm" variant="outline" onClick={handleSignOut} className="gap-1 text-red-600 border-red-200">
                    <LogOut size={14} /> Sign Out
                  </Button>
                </div>
              </>
            ) : (
              <>
                <MobileNavBtn label="Sign In" onClick={() => { setLocation("/signin"); setMenuOpen(false); }} />
                <MobileNavBtn label="Start Claim" onClick={() => { setLocation("/start-claim"); setMenuOpen(false); }} />
              </>
            )}
          </div>
        )}
      </div>
    </header>
  );
}

function NavBtn({ icon, label, onClick }: { icon: React.ReactNode; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="flex items-center gap-1.5 px-3 py-2 text-sm text-gray-700 hover:text-navy font-medium rounded-lg hover:bg-gray-100 transition-all">
      {icon}{label}
    </button>
  );
}

function MobileNavBtn({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button onClick={onClick} className="block w-full text-left px-4 py-2.5 text-gray-700 hover:text-navy hover:bg-gray-50 font-medium transition-colors">
      {label}
    </button>
  );
}
