import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { getCurrentUser, fetchUserAttributes } from "aws-amplify/auth";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { BulkUpload } from "@/components/BulkUpload";
import { VetGreeting } from "@/components/VetGreeting";
import { getSessionFromStorage } from "@/lib/claimsApi";
import { FileText, Heart, MessageCircle, Upload, Loader2 } from "lucide-react";

type Tab = "claims" | "benefits" | "documents" | "chat";

export function SecureDashboard() {
  const [, setLocation] = useLocation();
  const [tab, setTab] = useState<Tab>("claims");
  const [userName, setUserName] = useState("");
  const [loading, setLoading] = useState(true);
  const [extractedData, setExtractedData] = useState<Record<string, unknown>>({});
  const [docsProcessed, setDocsProcessed] = useState(0);
  const sessionId = getSessionFromStorage();

  useEffect(() => {
    // Parse ?tab= from URL
    const params = new URLSearchParams(window.location.search);
    const t = params.get("tab") as Tab | null;
    if (t) setTab(t);
  }, []);

  useEffect(() => {
    getCurrentUser()
      .then(async (u) => {
        const attrs = await fetchUserAttributes();
        const name = attrs.name
          || (u as any).signInDetails?.loginId?.split("@")[0]
          || u.username;
        setUserName(name ?? "Veteran");
      })
      .catch(() => setLocation("/"))
      .finally(() => setLoading(false));
  }, []);

  const handleDocProcessed = (result: Record<string, unknown>) => {
    setDocsProcessed((n) => n + 1);
    // Merge extracted data (first doc wins for each field)
    setExtractedData((prev) => ({ ...result, ...prev }));
    // Auto-switch to chat after first doc processed
    if (docsProcessed === 0) setTab("chat");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-10 w-10 animate-spin text-navy" />
      </div>
    );
  }

  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "claims",    label: "My Claims",    icon: <FileText size={16} /> },
    { id: "benefits",  label: "Benefits",     icon: <Heart size={16} /> },
    { id: "documents", label: "Documents",    icon: <Upload size={16} /> },
    { id: "chat",      label: "Battle Buddy", icon: <MessageCircle size={16} /> },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <Header />
      <main className="flex-1 max-w-6xl mx-auto w-full px-4 py-8">
        {/* Welcome bar */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">
            Welcome back, <span className="gradient-text">{userName}</span>
          </h1>
          <p className="text-gray-500 text-sm mt-1">Your secure VA claims workspace</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-white border border-gray-200 rounded-xl p-1 mb-6 w-fit">
          {TABS.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t.id
                  ? "bg-navy text-white shadow-sm"
                  : "text-gray-600 hover:text-navy hover:bg-gray-50"
              }`}
            >
              {t.icon}{t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        <div className="bg-white rounded-2xl border border-gray-200 p-6 shadow-sm">
          {tab === "claims" && (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-4">Active Claims</h2>
              {sessionId ? (
                <p className="text-sm text-gray-600">
                  Claim session active. Upload your documents in the Documents tab to begin AI analysis.
                </p>
              ) : (
                <div className="text-center py-8">
                  <p className="text-gray-500 mb-4">No active claim session found.</p>
                  <button
                    onClick={() => setLocation("/start-claim")}
                    className="bg-navy text-white px-6 py-2 rounded-xl text-sm font-semibold hover:bg-navy-dark transition-colors"
                  >
                    Start a New Claim
                  </button>
                </div>
              )}
            </div>
          )}

          {tab === "benefits" && (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-4">VA Benefits Overview</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[
                  { title: "Disability Compensation", desc: "Monthly tax-free payments for service-connected conditions (38 CFR Part 4)" },
                  { title: "Education (GI Bill)", desc: "Tuition, housing, and book stipends for education and training (38 CFR Part 21)" },
                  { title: "Home Loan Guaranty", desc: "No down payment home loans for eligible veterans (38 CFR Part 36)" },
                  { title: "Healthcare", desc: "VA medical care for service-connected and other conditions (38 CFR Part 17)" },
                  { title: "Life Insurance", desc: "SGLI, VGLI, and other coverage options (38 CFR Parts 6, 8, 9)" },
                  { title: "Appeals", desc: "Supplemental Claim, Higher-Level Review, or Board Appeal (38 CFR Parts 19–20)" },
                ].map((b) => (
                  <div key={b.title} className="p-4 border border-gray-200 rounded-xl hover:border-navy/30 transition-colors">
                    <h3 className="font-semibold text-gray-900 text-sm">{b.title}</h3>
                    <p className="text-xs text-gray-500 mt-1">{b.desc}</p>
                  </div>
                ))}
              </div>
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-lg p-3 mt-4">
                Upload your service documents in the Documents tab and ask Val in Battle Buddy for a personalized benefits assessment.
              </p>
            </div>
          )}

          {tab === "documents" && (
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-1">Upload Service Documents</h2>
              <p className="text-sm text-gray-500 mb-4">
                Upload your DD-214, STRs, medical records, nexus letters, and any other supporting documents.
                Claude AI will analyze each one and auto-fill your claim.
              </p>
              {sessionId ? (
                <BulkUpload sessionId={sessionId} onDocumentProcessed={handleDocProcessed} />
              ) : (
                <p className="text-sm text-gray-500">Start a claim session first to upload documents.</p>
              )}
              {docsProcessed > 0 && (
                <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-800">
                  ✓ {docsProcessed} document{docsProcessed > 1 ? "s" : ""} analyzed. Switch to Battle Buddy for your personalized assessment.
                </div>
              )}
            </div>
          )}

          {tab === "chat" && (
            <VetGreeting
              veteranName={userName}
              extractedData={extractedData}
              sessionId={sessionId ?? undefined}
            />
          )}
        </div>
      </main>
      <Footer />
    </div>
  );
}
