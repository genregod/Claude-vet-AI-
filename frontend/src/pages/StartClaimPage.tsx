/**
 * StartClaimPage — Signup Splash + Multi-page Claim Questionnaire
 *
 * Flow:
 * 1. Veteran clicks "Start Your Claim" → lands here
 * 2. Sees splash signup page (email, name, password)
 * 3. On signup → claim session created → questionnaire begins
 * 4. Questionnaire auto-saves, AI evaluates in background
 * 5. On completion → agent pipeline processes claim → FDC package
 *
 * Session persists across reloads via localStorage + server session.
 */

import { useState, useEffect } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ClaimQuestionnaire } from "@/components/ClaimQuestionnaire";
import {
  createClaimSession,
  getClaimSession,
  getSessionFromStorage,
  clearSessionStorage,
} from "@/lib/claimsApi";
import {
  Shield,
  Lock,
  Star,
  ArrowRight,
  CheckCircle,
  Eye,
  EyeOff,
  Bot,
  Users,
  FileCheck,
  Loader2,
} from "lucide-react";

export function StartClaimPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const { toast } = useToast();

  // Check for existing session on mount
  useEffect(() => {
    async function checkExisting() {
      const storedId = getSessionFromStorage();
      if (storedId) {
        try {
          const session = await getClaimSession(storedId);
          if (session) {
            setSessionId(storedId);
          }
        } catch {
          clearSessionStorage();
        }
      }
      setIsLoading(false);
    }
    checkExisting();
  }, []);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <Loader2 className="h-10 w-10 animate-spin text-navy" />
      </div>
    );
  }

  // If we have an active session, go straight to questionnaire
  if (sessionId) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-1">
          <ClaimQuestionnaire
            sessionId={sessionId}
            onComplete={() => {
              toast({
                title: "Claim Complete",
                description: "Your FDC package is ready for review.",
              });
            }}
          />
        </main>
        <Footer />
      </div>
    );
  }

  // Otherwise, show the splash signup page
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1">
        <SignupSplash onSessionCreated={setSessionId} />
      </main>
      <Footer />
    </div>
  );
}

// ── Signup Splash Section ───────────────────────────────────────────

interface SignupSplashProps {
  onSessionCreated: (sessionId: string) => void;
}

function SignupSplash({ onSessionCreated }: SignupSplashProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const { toast } = useToast();

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation
    if (!email || !password || !firstName || !lastName) {
      toast({
        title: "Required Fields",
        description: "Please fill out all required fields.",
        variant: "destructive",
      });
      return;
    }
    if (password.length < 6) {
      toast({
        title: "Password Too Short",
        description: "Password must be at least 6 characters.",
        variant: "destructive",
      });
      return;
    }
    if (password !== confirmPassword) {
      toast({
        title: "Passwords Don't Match",
        description: "Please make sure your passwords match.",
        variant: "destructive",
      });
      return;
    }
    if (!acceptedTerms) {
      toast({
        title: "Terms Required",
        description: "Please accept the terms and privacy policy.",
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await createClaimSession({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
      });
      toast({
        title: "Account Created",
        description: "Your secure claim session has been started.",
      });
      onSessionCreated(result.session_id);
    } catch (err) {
      toast({
        title: "Signup Failed",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "destructive",
      });
    }
    setIsSubmitting(false);
  };

  return (
    <section className="relative min-h-[calc(100vh-80px)] flex items-center bg-gradient-to-br from-gray-50 via-white to-gray-100 overflow-hidden">
      {/* Background decoration */}
      <div className="absolute top-10 left-10 w-72 h-72 bg-gold/8 rounded-full blur-3xl" />
      <div className="absolute bottom-10 right-10 w-96 h-96 bg-navy/8 rounded-full blur-3xl" />

      <div className="relative max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12 w-full">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: Value Proposition */}
          <div className="space-y-8">
            <div className="inline-flex items-center bg-navy/5 rounded-full px-5 py-2.5">
              <Star className="h-4 w-4 text-gold mr-2" />
              <span className="text-navy font-bold text-sm">
                FREE AI-POWERED CLAIM ASSESSMENT
              </span>
            </div>

            <h1 className="text-4xl lg:text-5xl font-black text-navy leading-tight">
              Start Your VA
              <span className="block text-gold">Disability Claim</span>
            </h1>

            <p className="text-lg text-gray-600 leading-relaxed max-w-lg">
              Our AI-powered questionnaire evaluates your service history,
              conditions, and evidence to estimate your disability rating
              and build a Fully Developed Claim — in minutes, not months.
            </p>

            {/* Process Steps */}
            <div className="space-y-4">
              {[
                {
                  icon: <Shield className="h-5 w-5 text-navy" />,
                  title: "Secure Signup",
                  desc: "Your PII is encrypted with military-grade AES-256 encryption",
                },
                {
                  icon: <Bot className="h-5 w-5 text-navy" />,
                  title: "AI Analysis",
                  desc: "Real-time disability rating estimates as you answer",
                },
                {
                  icon: <Users className="h-5 w-5 text-navy" />,
                  title: "Agent Pipeline",
                  desc: "Claims Agent → Supervisor → Assistant → FDC package",
                },
                {
                  icon: <FileCheck className="h-5 w-5 text-navy" />,
                  title: "FDC Ready",
                  desc: "Your Fully Developed Claim package, ready for submission",
                },
              ].map((step, idx) => (
                <div key={idx} className="flex items-start gap-4">
                  <div className="bg-navy/5 p-2.5 rounded-xl flex-shrink-0">
                    {step.icon}
                  </div>
                  <div>
                    <p className="font-bold text-navy text-sm">{step.title}</p>
                    <p className="text-gray-500 text-sm">{step.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Right: Signup Form */}
          <Card className="shadow-2xl border-0 bg-white/90 backdrop-blur-sm">
            <CardContent className="p-8">
              <div className="text-center mb-6">
                <div className="bg-navy p-3 rounded-2xl w-fit mx-auto mb-3">
                  <Lock className="h-7 w-7 text-gold" />
                </div>
                <h2 className="text-2xl font-bold text-navy">Create Your Account</h2>
                <p className="text-gray-500 text-sm mt-1">
                  All data encrypted and secure
                </p>
              </div>

              <form onSubmit={handleSignup} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="signup_first">First Name *</Label>
                    <Input
                      id="signup_first"
                      value={firstName}
                      onChange={(e) => setFirstName(e.target.value)}
                      placeholder="John"
                      required
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="signup_last">Last Name *</Label>
                    <Input
                      id="signup_last"
                      value={lastName}
                      onChange={(e) => setLastName(e.target.value)}
                      placeholder="Doe"
                      required
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="signup_email">Email Address *</Label>
                  <Input
                    id="signup_email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="veteran@email.com"
                    required
                  />
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="signup_password">Password *</Label>
                  <div className="relative">
                    <Input
                      id="signup_password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Min 6 characters"
                      required
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="signup_confirm">Confirm Password *</Label>
                  <Input
                    id="signup_confirm"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Re-enter password"
                    required
                  />
                </div>

                <Separator />

                <label className="flex items-start gap-3 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={acceptedTerms}
                    onChange={(e) => setAcceptedTerms(e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-gray-300"
                  />
                  <span className="text-xs text-gray-500 leading-relaxed">
                    I understand that my personal information will be encrypted
                    and stored securely. I consent to AI analysis of my claim
                    data for disability rating estimation. This is not legal
                    advice and does not file a claim with the VA.
                  </span>
                </label>

                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-gradient-to-r from-navy to-navy-light text-white font-bold text-lg py-6 rounded-2xl shadow-lg hover:scale-[1.02] transition-all"
                >
                  {isSubmitting ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin" />
                      Creating Secure Session...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Begin Claim Assessment
                      <ArrowRight className="h-5 w-5" />
                    </span>
                  )}
                </Button>
              </form>

              {/* Trust badges */}
              <div className="flex items-center justify-center gap-6 mt-6 pt-4 border-t">
                {[
                  { icon: <Lock className="h-3.5 w-3.5" />, text: "AES-256" },
                  { icon: <Shield className="h-3.5 w-3.5" />, text: "HIPAA Ready" },
                  { icon: <CheckCircle className="h-3.5 w-3.5" />, text: "PII Protected" },
                ].map((badge, idx) => (
                  <div key={idx} className="flex items-center gap-1.5 text-gray-400">
                    {badge.icon}
                    <span className="text-xs font-medium">{badge.text}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
