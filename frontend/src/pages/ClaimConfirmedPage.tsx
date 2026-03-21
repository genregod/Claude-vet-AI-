import { useLocation } from "wouter";
import { CheckCircle, FileText, Clock, Users, ArrowRight, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const NEXT_STEPS = [
  {
    icon: <FileText size={18} />,
    title: "FDC Package Generated",
    desc: "Your Fully Developed Claim package has been compiled and is ready for VA submission.",
  },
  {
    icon: <Clock size={18} />,
    title: "VA Review (90–125 days)",
    desc: "The VA will review your claim. You can track status at va.gov or through your dashboard.",
  },
  {
    icon: <Shield size={18} />,
    title: "C&P Exam Possible",
    desc: "The VA may schedule a Compensation & Pension exam to evaluate your conditions.",
  },
];

export function ClaimConfirmedPage() {
  const [, setLocation] = useLocation();

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-100 px-4 py-12">
        <div className="w-full max-w-lg space-y-8">
          {/* Confirmation card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8 text-center">
            <div className="flex justify-center mb-4">
              <div className="bg-green-100 rounded-full p-4">
                <CheckCircle className="h-10 w-10 text-green-600" />
              </div>
            </div>
            <h1 className="text-2xl font-black text-navy mb-2">Claim Submitted</h1>
            <p className="text-gray-500 text-sm">
              Your claim session has been recorded and your FDC package is ready. Keep your dashboard bookmarked to track progress.
            </p>
          </div>

          {/* Next steps */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
            <h2 className="font-bold text-navy text-sm uppercase tracking-wide">What Happens Next</h2>
            {NEXT_STEPS.map(({ icon, title, desc }) => (
              <div key={title} className="flex gap-3">
                <div className="mt-0.5 text-gold shrink-0">{icon}</div>
                <div>
                  <p className="font-semibold text-gray-800 text-sm">{title}</p>
                  <p className="text-gray-500 text-xs mt-0.5">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div className="space-y-3">
            <Button
              className="w-full bg-navy text-white hover:bg-navy-dark flex items-center justify-center gap-2"
              onClick={() => setLocation("/battle-buddy")}
            >
              <Users size={16} />
              Connect with a Battle Buddy
              <ArrowRight size={14} />
            </Button>
            <Button
              variant="outline"
              className="w-full border-navy text-navy hover:bg-navy/5"
              onClick={() => setLocation("/dashboard")}
            >
              Go to My Dashboard
            </Button>
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
