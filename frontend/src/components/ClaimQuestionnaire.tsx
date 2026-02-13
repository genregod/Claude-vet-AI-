/**
 * ClaimQuestionnaire — Multi-page interactive claim intake form
 *
 * 10-page questionnaire covering all VA-recognized claimable aspects.
 * Auto-saves answers on each page, triggers AI evaluation in background,
 * and displays real-time estimated disability ratings.
 *
 * Pages:
 *  1. Signup (handled by splash page)
 *  2. Personal Information
 *  3. Military Service
 *  4. Service History (deployments, combat, duties)
 *  5. Disabilities (VA-recognized conditions)
 *  6. Mental Health
 *  7. Medical Evidence
 *  8. Exposures (burn pits, Agent Orange, radiation, etc.)
 *  9. Additional Claims (secondary conditions, dependents)
 * 10. Review & Submit
 */

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { AIEstimatesPanel } from "@/components/AIEstimatesPanel";
import { RecordsUpload } from "@/components/RecordsUpload";
import {
  savePageAnswers,
  getPageAnswers,
  getClaimSession,
  savePageLocally,
  getPageLocally,
  submitClaim,
  CLAIM_PAGES,
  type AIEstimates,
} from "@/lib/claimsApi";
import {
  User,
  Shield,
  Clock,
  HeartPulse,
  Brain,
  FileText,
  AlertTriangle,
  Plus,
  CheckCircle,
  ChevronLeft,
  ChevronRight,
  Save,
  Loader2,
  Upload,
} from "lucide-react";

// ── Page icon mapping ───────────────────────────────────────────────

const PAGE_ICONS: Record<string, React.ReactNode> = {
  personal_info: <User className="h-4 w-4" />,
  military_service: <Shield className="h-4 w-4" />,
  service_history: <Clock className="h-4 w-4" />,
  disabilities: <HeartPulse className="h-4 w-4" />,
  mental_health: <Brain className="h-4 w-4" />,
  medical_evidence: <FileText className="h-4 w-4" />,
  exposures: <AlertTriangle className="h-4 w-4" />,
  additional_claims: <Plus className="h-4 w-4" />,
  review: <CheckCircle className="h-4 w-4" />,
};

// Skip the signup page (index 0) — it's handled by the splash page
const QUESTIONNAIRE_PAGES = CLAIM_PAGES.filter((p) => p.key !== "signup");

// ── VA-recognized conditions for the disabilities page ──────────────

const CONDITION_CATEGORIES: Record<string, string[]> = {
  "Musculoskeletal": [
    "Back conditions (lumbar/thoracic/cervical)",
    "Knee conditions",
    "Shoulder conditions (rotator cuff)",
    "Hip conditions",
    "Ankle/foot conditions (flat feet, plantar fasciitis)",
    "Neck conditions",
    "Wrist/hand conditions (carpal tunnel)",
    "Fibromyalgia",
  ],
  "Neurological": [
    "Tinnitus",
    "Hearing loss",
    "Migraines/headaches",
    "Peripheral neuropathy",
    "Radiculopathy",
    "Sciatica",
    "Vertigo",
    "TBI (Traumatic Brain Injury)",
  ],
  "Mental Health": [
    "PTSD",
    "Major Depressive Disorder",
    "Generalized Anxiety Disorder",
    "Adjustment Disorder",
    "Military Sexual Trauma (MST)",
    "Insomnia/sleep disturbance",
    "Substance Use Disorder (secondary)",
  ],
  "Respiratory": [
    "Sleep apnea",
    "Asthma",
    "Sinusitis/rhinitis",
    "Burn pit exposure conditions",
    "COPD",
  ],
  "Cardiovascular": [
    "Hypertension",
    "Ischemic heart disease",
    "Heart arrhythmia",
    "Varicose veins",
  ],
  "Digestive": [
    "GERD",
    "IBS",
    "Hiatal hernia",
    "Liver conditions",
  ],
  "Skin": [
    "Eczema/dermatitis",
    "Psoriasis",
    "Scarring",
    "Skin cancer",
  ],
  "Endocrine": [
    "Diabetes mellitus",
    "Thyroid conditions",
  ],
  "Genitourinary": [
    "Erectile dysfunction",
    "Kidney conditions",
    "Prostate conditions",
    "Urinary incontinence",
  ],
  "Vision/Dental": [
    "Vision impairment",
    "Glaucoma",
    "TMJ disorder",
    "Dental conditions (trauma-related)",
  ],
  "Cancer": [
    "Service-connected cancer",
    "Agent Orange-related cancer",
    "Burn pit-related cancer",
    "Radiation-exposure cancer",
  ],
  "Presumptive / Toxic Exposure": [
    "Agent Orange presumptives",
    "Gulf War illness",
    "Camp Lejeune water contamination",
    "PACT Act burn pit presumptives",
    "Radiation-risk presumptives",
  ],
};

interface ClaimQuestionnaireProps {
  sessionId: string;
  onComplete?: () => void;
}

export function ClaimQuestionnaire({ sessionId, onComplete }: ClaimQuestionnaireProps) {
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Record<string, unknown>>>({});
  const [completedPages, setCompletedPages] = useState<string[]>([]);
  const [aiEstimates, setAiEstimates] = useState<AIEstimates>({
    estimated_rating_percent: 0,
    estimated_combined_rating: 0,
    estimated_monthly_compensation: 0,
    estimated_backpay: 0,
    estimated_decision_timeline_days: 0,
    confidence_level: "low",
    individual_ratings: [],
    notes: [],
    last_updated: 0,
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingPage, setIsLoadingPage] = useState(false);
  const [showUpload, setShowUpload] = useState(true);
  const { toast } = useToast();

  const currentPage = QUESTIONNAIRE_PAGES[currentPageIndex];
  const progressPercent = ((completedPages.length) / QUESTIONNAIRE_PAGES.length) * 100;

  // ── Load session state on mount ───────────────────────────────────

  useEffect(() => {
    async function loadSession() {
      try {
        const session = await getClaimSession(sessionId);
        if (session.completed_pages) {
          setCompletedPages(session.completed_pages.filter((p) => p !== "signup"));
        }
        if (session.ai_estimates) {
          setAiEstimates(session.ai_estimates);
        }
        // Find current page
        const pageIdx = QUESTIONNAIRE_PAGES.findIndex(
          (p) => p.key === session.current_page
        );
        if (pageIdx >= 0) {
          setCurrentPageIndex(pageIdx);
        }
      } catch (err) {
        console.error("Failed to load session:", err);
      }
    }
    loadSession();
  }, [sessionId]);

  // ── Load page answers when page changes ───────────────────────────

  useEffect(() => {
    async function loadPage() {
      if (!currentPage) return;
      setIsLoadingPage(true);
      try {
        // Try server first
        const data = await getPageAnswers(sessionId, currentPage.key);
        if (data.answers && Object.keys(data.answers).length > 0) {
          setAnswers((prev) => ({ ...prev, [currentPage.key]: data.answers }));
        } else {
          // Fall back to local storage
          const local = getPageLocally(currentPage.key);
          if (local) {
            setAnswers((prev) => ({ ...prev, [currentPage.key]: local }));
          }
        }
      } catch {
        // Try local storage fallback
        const local = getPageLocally(currentPage.key);
        if (local) {
          setAnswers((prev) => ({ ...prev, [currentPage.key]: local }));
        }
      }
      setIsLoadingPage(false);
    }
    loadPage();
  }, [currentPage?.key, sessionId]);

  // ── Answer helpers ────────────────────────────────────────────────

  const getPageAnswers_ = useCallback(
    (page: string): Record<string, unknown> => answers[page] || {},
    [answers]
  );

  const updateAnswer = useCallback(
    (page: string, field: string, value: unknown) => {
      setAnswers((prev) => {
        const updated = {
          ...prev,
          [page]: { ...(prev[page] || {}), [field]: value },
        };
        // Auto-save to localStorage
        savePageLocally(page, updated[page]);
        return updated;
      });
    },
    []
  );

  const toggleArrayItem = useCallback(
    (page: string, field: string, item: string) => {
      setAnswers((prev) => {
        const current = ((prev[page] || {})[field] as string[]) || [];
        const idx = current.indexOf(item);
        const updated = idx === -1
          ? [...current, item]
          : current.filter((_, i) => i !== idx);
        const newAnswers = {
          ...prev,
          [page]: { ...(prev[page] || {}), [field]: updated },
        };
        savePageLocally(page, newAnswers[page]);
        return newAnswers;
      });
    },
    []
  );

  // ── Save current page ─────────────────────────────────────────────

  const handleSavePage = async () => {
    if (!currentPage) return;
    setIsSaving(true);
    try {
      const pageAnswers = getPageAnswers_(currentPage.key);
      const result = await savePageAnswers(sessionId, currentPage.key, pageAnswers);
      
      setCompletedPages(result.completed_pages.filter((p) => p !== "signup"));
      setAiEstimates(result.ai_estimates);
      
      toast({
        title: "Page Saved",
        description: `${currentPage.label} saved successfully.`,
      });
      
      return result;
    } catch (err) {
      toast({
        title: "Save Failed",
        description: "Could not save. Your answers are stored locally.",
        variant: "destructive",
      });
      return null;
    } finally {
      setIsSaving(false);
    }
  };

  // ── Auto-fill from uploaded records ───────────────────────────────

  const handleAutoFill = useCallback(
    (pages: Record<string, Record<string, unknown>>) => {
      setAnswers((prev) => {
        const merged = { ...prev };
        for (const [pageKey, extractedFields] of Object.entries(pages)) {
          // Merge: extracted values fill blanks, don't overwrite user input
          const existing = merged[pageKey] || {};
          const combined: Record<string, unknown> = { ...extractedFields };
          for (const [field, value] of Object.entries(existing)) {
            if (value !== undefined && value !== "" && value !== null) {
              combined[field] = value; // keep user's value
            }
          }
          merged[pageKey] = combined;
          // Persist to localStorage
          savePageLocally(pageKey, combined);
        }
        return merged;
      });

      toast({
        title: "Fields Auto-Filled",
        description: `Updated ${Object.keys(pages).length} page(s) from your uploaded records. Review each page to confirm.`,
      });
    },
    [toast]
  );

  // ── Navigation ────────────────────────────────────────────────────

  const handleNext = async () => {
    const result = await handleSavePage();
    if (result && currentPageIndex < QUESTIONNAIRE_PAGES.length - 1) {
      setCurrentPageIndex((i) => i + 1);
    }
  };

  const handlePrev = () => {
    if (currentPageIndex > 0) {
      setCurrentPageIndex((i) => i - 1);
    }
  };

  const handleGoToPage = (idx: number) => {
    // Allow navigation to completed pages or the next page
    const targetKey = QUESTIONNAIRE_PAGES[idx]?.key;
    if (completedPages.includes(targetKey) || idx <= completedPages.length) {
      setCurrentPageIndex(idx);
    }
  };

  // ── Render ────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top Progress Bar */}
      <div className="bg-white border-b shadow-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 py-3">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-bold text-navy">VA Claim Questionnaire</h2>
            <span className="text-sm text-gray-500">
              {Math.round(progressPercent)}% Complete
            </span>
          </div>
          <Progress value={progressPercent} className="h-2" />
          
          {/* Page indicators */}
          <div className="flex gap-1 mt-3 overflow-x-auto pb-1">
            {QUESTIONNAIRE_PAGES.map((page, idx) => {
              const isCompleted = completedPages.includes(page.key);
              const isCurrent = idx === currentPageIndex;
              return (
                <button
                  key={page.key}
                  onClick={() => handleGoToPage(idx)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-all ${
                    isCurrent
                      ? "bg-navy text-white shadow-md"
                      : isCompleted
                      ? "bg-green-100 text-green-800 hover:bg-green-200"
                      : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                  }`}
                >
                  {PAGE_ICONS[page.key] || null}
                  <span className="hidden sm:inline">{page.label}</span>
                  {isCompleted && <CheckCircle className="h-3 w-3" />}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        {/* Records Upload Section */}
        <div className="mb-6">
          <button
            type="button"
            onClick={() => setShowUpload((v) => !v)}
            className="flex items-center gap-2 text-sm font-medium text-navy hover:text-navy/80 mb-3 transition-colors"
          >
            <Upload className="h-4 w-4" />
            {showUpload ? "Hide" : "Show"} Records Upload
            <Badge variant="secondary" className="text-xs">Speed up your claim</Badge>
          </button>
          {showUpload && (
            <RecordsUpload
              sessionId={sessionId}
              onAutoFill={handleAutoFill}
              onEstimatesUpdate={setAiEstimates}
            />
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Questionnaire Form (left 2/3) */}
          <div className="lg:col-span-2">
            <Card className="shadow-lg">
              <CardContent className="p-6 sm:p-8">
                {isLoadingPage ? (
                  <div className="flex items-center justify-center py-20">
                    <Loader2 className="h-8 w-8 animate-spin text-navy" />
                  </div>
                ) : (
                  <PageRenderer
                    page={currentPage?.key || "personal_info"}
                    answers={getPageAnswers_(currentPage?.key || "")}
                    updateAnswer={(field, value) =>
                      updateAnswer(currentPage?.key || "", field, value)
                    }
                    toggleArrayItem={(field, item) =>
                      toggleArrayItem(currentPage?.key || "", field, item)
                    }
                    allAnswers={answers}
                    aiEstimates={aiEstimates}
                    sessionId={sessionId}
                    onComplete={onComplete}
                  />
                )}

                {/* Navigation Buttons */}
                {currentPage?.key !== "review" && (
                  <div className="flex items-center justify-between mt-8 pt-6 border-t">
                    <Button
                      variant="outline"
                      onClick={handlePrev}
                      disabled={currentPageIndex === 0}
                      className="gap-2"
                    >
                      <ChevronLeft className="h-4 w-4" />
                      Previous
                    </Button>
                    
                    <Button
                      variant="outline"
                      onClick={handleSavePage}
                      disabled={isSaving}
                      className="gap-2"
                    >
                      {isSaving ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Save className="h-4 w-4" />
                      )}
                      Save Progress
                    </Button>
                    
                    <Button
                      onClick={handleNext}
                      disabled={isSaving}
                      className="bg-navy text-white gap-2 hover:bg-navy/90"
                    >
                      Next
                      <ChevronRight className="h-4 w-4" />
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* AI Estimates Sidebar (right 1/3) */}
          <div className="lg:col-span-1">
            <AIEstimatesPanel estimates={aiEstimates} isLoading={isSaving} />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Page Renderer ───────────────────────────────────────────────────

interface PageRendererProps {
  page: string;
  answers: Record<string, unknown>;
  updateAnswer: (field: string, value: unknown) => void;
  toggleArrayItem: (field: string, item: string) => void;
  allAnswers: Record<string, Record<string, unknown>>;
  aiEstimates: AIEstimates;
  sessionId: string;
  onComplete?: () => void;
}

function PageRenderer(props: PageRendererProps) {
  switch (props.page) {
    case "personal_info":
      return <PersonalInfoPage {...props} />;
    case "military_service":
      return <MilitaryServicePage {...props} />;
    case "service_history":
      return <ServiceHistoryPage {...props} />;
    case "disabilities":
      return <DisabilitiesPage {...props} />;
    case "mental_health":
      return <MentalHealthPage {...props} />;
    case "medical_evidence":
      return <MedicalEvidencePage {...props} />;
    case "exposures":
      return <ExposuresPage {...props} />;
    case "additional_claims":
      return <AdditionalClaimsPage {...props} />;
    case "review":
      return <ReviewPage {...props} />;
    default:
      return <PersonalInfoPage {...props} />;
  }
}

// ── Page 1: Personal Information ────────────────────────────────────

function PersonalInfoPage({ answers, updateAnswer }: PageRendererProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Personal Information</h3>
        <p className="text-gray-500">
          This information is encrypted and stored securely.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="first_name">First Name *</Label>
          <Input
            id="first_name"
            value={(answers.first_name as string) || ""}
            onChange={(e) => updateAnswer("first_name", e.target.value)}
            placeholder="John"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="last_name">Last Name *</Label>
          <Input
            id="last_name"
            value={(answers.last_name as string) || ""}
            onChange={(e) => updateAnswer("last_name", e.target.value)}
            placeholder="Doe"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="date_of_birth">Date of Birth *</Label>
          <Input
            id="date_of_birth"
            type="date"
            value={(answers.date_of_birth as string) || ""}
            onChange={(e) => updateAnswer("date_of_birth", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="ssn">Last 4 of SSN</Label>
          <Input
            id="ssn"
            maxLength={4}
            value={(answers.ssn as string) || ""}
            onChange={(e) => updateAnswer("ssn", e.target.value.replace(/\D/g, "").slice(0, 4))}
            placeholder="1234"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="phone">Phone Number *</Label>
          <Input
            id="phone"
            type="tel"
            value={(answers.phone as string) || ""}
            onChange={(e) => updateAnswer("phone", e.target.value)}
            placeholder="(555) 123-4567"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="va_file_number">VA File Number (if known)</Label>
          <Input
            id="va_file_number"
            value={(answers.va_file_number as string) || ""}
            onChange={(e) => updateAnswer("va_file_number", e.target.value)}
            placeholder="C12345678"
          />
        </div>
      </div>

      <Separator />
      <h4 className="font-semibold text-navy">Mailing Address</h4>
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="address_street">Street Address *</Label>
          <Input
            id="address_street"
            value={(answers.address_street as string) || ""}
            onChange={(e) => updateAnswer("address_street", e.target.value)}
          />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="space-y-2">
            <Label htmlFor="address_city">City</Label>
            <Input
              id="address_city"
              value={(answers.address_city as string) || ""}
              onChange={(e) => updateAnswer("address_city", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="address_state">State</Label>
            <Input
              id="address_state"
              value={(answers.address_state as string) || ""}
              onChange={(e) => updateAnswer("address_state", e.target.value)}
              maxLength={2}
              placeholder="TX"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="address_zip">ZIP Code</Label>
            <Input
              id="address_zip"
              value={(answers.address_zip as string) || ""}
              onChange={(e) => updateAnswer("address_zip", e.target.value)}
              maxLength={10}
            />
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Page 2: Military Service ────────────────────────────────────────

function MilitaryServicePage({ answers, updateAnswer }: PageRendererProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Military Service</h3>
        <p className="text-gray-500">Tell us about your military service.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Branch of Service *</Label>
          <Select
            value={(answers.branch as string) || ""}
            onValueChange={(v) => updateAnswer("branch", v)}
          >
            <SelectTrigger><SelectValue placeholder="Select branch" /></SelectTrigger>
            <SelectContent>
              {["Army", "Navy", "Air Force", "Marine Corps", "Coast Guard", "Space Force", "National Guard", "Reserves"].map((b) => (
                <SelectItem key={b} value={b}>{b}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label>Pay Grade / Rank at Discharge</Label>
          <Input
            value={(answers.rank as string) || ""}
            onChange={(e) => updateAnswer("rank", e.target.value)}
            placeholder="e.g., E-5 / SGT"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Service Start Date *</Label>
          <Input
            type="date"
            value={(answers.service_start_date as string) || ""}
            onChange={(e) => updateAnswer("service_start_date", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label>Service End Date *</Label>
          <Input
            type="date"
            value={(answers.service_end_date as string) || ""}
            onChange={(e) => updateAnswer("service_end_date", e.target.value)}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Discharge Type *</Label>
        <Select
          value={(answers.discharge_type as string) || ""}
          onValueChange={(v) => updateAnswer("discharge_type", v)}
        >
          <SelectTrigger><SelectValue placeholder="Select discharge type" /></SelectTrigger>
          <SelectContent>
            {[
              "Honorable",
              "General (Under Honorable Conditions)",
              "Other Than Honorable (OTH)",
              "Bad Conduct Discharge (BCD)",
              "Dishonorable",
              "Uncharacterized",
              "Currently Serving",
            ].map((d) => (
              <SelectItem key={d} value={d}>{d}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>MOS / Rating / AFSC</Label>
        <Input
          value={(answers.mos as string) || ""}
          onChange={(e) => updateAnswer("mos", e.target.value)}
          placeholder="e.g., 11B Infantryman"
        />
      </div>

      <div className="space-y-2">
        <Label>Multiple Periods of Service?</Label>
        <RadioGroup
          value={(answers.multiple_service_periods as string) || ""}
          onValueChange={(v) => updateAnswer("multiple_service_periods", v)}
        >
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="multi_yes" />
              <Label htmlFor="multi_yes">Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="multi_no" />
              <Label htmlFor="multi_no">No</Label>
            </div>
          </div>
        </RadioGroup>
      </div>

      {answers.multiple_service_periods === "yes" && (
        <div className="space-y-2">
          <Label>Additional Service Details</Label>
          <Textarea
            value={(answers.additional_service_details as string) || ""}
            onChange={(e) => updateAnswer("additional_service_details", e.target.value)}
            placeholder="Describe additional periods of service (branch, dates, discharge type)"
            rows={4}
          />
        </div>
      )}
    </div>
  );
}

// ── Page 3: Service History ─────────────────────────────────────────

function ServiceHistoryPage({ answers, updateAnswer }: PageRendererProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Service History Details</h3>
        <p className="text-gray-500">
          Deployments, combat experience, and duty assignments help establish
          service-connection for your conditions.
        </p>
      </div>

      <div className="space-y-2">
        <Label>Combat Deployments</Label>
        <RadioGroup
          value={(answers.combat_deployments as string) || ""}
          onValueChange={(v) => updateAnswer("combat_deployments", v)}
        >
          <div className="flex flex-col gap-2">
            {[
              { value: "none", label: "No combat deployments" },
              { value: "one", label: "One deployment" },
              { value: "multiple", label: "Multiple deployments" },
            ].map((opt) => (
              <div key={opt.value} className="flex items-center gap-2">
                <RadioGroupItem value={opt.value} id={`combat_${opt.value}`} />
                <Label htmlFor={`combat_${opt.value}`}>{opt.label}</Label>
              </div>
            ))}
          </div>
        </RadioGroup>
      </div>

      {answers.combat_deployments !== "none" && (
        <div className="space-y-2">
          <Label>Deployment Locations & Dates</Label>
          <Textarea
            value={(answers.deployment_details as string) || ""}
            onChange={(e) => updateAnswer("deployment_details", e.target.value)}
            placeholder="e.g., Iraq (OIF) 2005-2006, Afghanistan (OEF) 2009-2010"
            rows={3}
          />
        </div>
      )}

      <div className="space-y-2">
        <Label>Were you awarded any combat-related decorations?</Label>
        <RadioGroup
          value={(answers.combat_decorations as string) || ""}
          onValueChange={(v) => updateAnswer("combat_decorations", v)}
        >
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="dec_yes" />
              <Label htmlFor="dec_yes">Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="dec_no" />
              <Label htmlFor="dec_no">No</Label>
            </div>
          </div>
        </RadioGroup>
      </div>

      {answers.combat_decorations === "yes" && (
        <div className="space-y-2">
          <Label>List Decorations</Label>
          <Input
            value={(answers.decorations_list as string) || ""}
            onChange={(e) => updateAnswer("decorations_list", e.target.value)}
            placeholder="e.g., CIB, Purple Heart, Bronze Star"
          />
        </div>
      )}

      <div className="space-y-2">
        <Label>Describe your primary duty assignments</Label>
        <Textarea
          value={(answers.duty_assignments as string) || ""}
          onChange={(e) => updateAnswer("duty_assignments", e.target.value)}
          placeholder="Describe your main duties — this helps establish how your conditions are service-connected"
          rows={4}
        />
      </div>

      <div className="space-y-2">
        <Label>Any in-service injuries, incidents, or events?</Label>
        <Textarea
          value={(answers.in_service_events as string) || ""}
          onChange={(e) => updateAnswer("in_service_events", e.target.value)}
          placeholder="Describe injuries, accidents, exposures, or significant events during service"
          rows={4}
        />
      </div>
    </div>
  );
}

// ── Page 4: Disabilities ────────────────────────────────────────────

function DisabilitiesPage({ answers, toggleArrayItem, updateAnswer }: PageRendererProps) {
  const selectedConditions = (answers.selected_conditions as string[]) || [];
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Claimed Disabilities</h3>
        <p className="text-gray-500">
          Select all conditions you believe are connected to your military
          service. The AI will estimate individual ratings for each.
        </p>
        {selectedConditions.length > 0 && (
          <Badge className="mt-2 bg-navy">
            {selectedConditions.length} condition{selectedConditions.length !== 1 ? "s" : ""} selected
          </Badge>
        )}
      </div>

      <div className="space-y-3">
        {Object.entries(CONDITION_CATEGORIES).map(([category, conditions]) => (
          <div key={category} className="border rounded-xl overflow-hidden">
            <button
              type="button"
              onClick={() =>
                setExpandedCategory(expandedCategory === category ? null : category)
              }
              className={`w-full flex items-center justify-between px-4 py-3 text-left font-semibold transition-colors ${
                expandedCategory === category
                  ? "bg-navy text-white"
                  : "bg-gray-50 text-gray-800 hover:bg-gray-100"
              }`}
            >
              <span>{category}</span>
              <div className="flex items-center gap-2">
                {conditions.filter((c) => selectedConditions.includes(c)).length > 0 && (
                  <Badge variant="secondary" className="text-xs">
                    {conditions.filter((c) => selectedConditions.includes(c)).length}
                  </Badge>
                )}
                <ChevronRight
                  className={`h-4 w-4 transition-transform ${
                    expandedCategory === category ? "rotate-90" : ""
                  }`}
                />
              </div>
            </button>
            {expandedCategory === category && (
              <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-2">
                {conditions.map((condition) => (
                  <label
                    key={condition}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      selectedConditions.includes(condition)
                        ? "bg-navy/5 border-navy"
                        : "hover:bg-gray-50 border-gray-200"
                    }`}
                  >
                    <Checkbox
                      checked={selectedConditions.includes(condition)}
                      onCheckedChange={() =>
                        toggleArrayItem("selected_conditions", condition)
                      }
                    />
                    <span className="text-sm">{condition}</span>
                  </label>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <Separator />

      <div className="space-y-2">
        <Label>Other conditions not listed above</Label>
        <Textarea
          value={(answers.custom_conditions as string) || ""}
          onChange={(e) => updateAnswer("custom_conditions", e.target.value)}
          placeholder="List any additional conditions separated by commas"
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label>Current VA Disability Rating (if any)</Label>
        <Select
          value={(answers.current_rating as string) || ""}
          onValueChange={(v) => updateAnswer("current_rating", v)}
        >
          <SelectTrigger><SelectValue placeholder="Select current rating" /></SelectTrigger>
          <SelectContent>
            {["Not yet rated", "0%", "10%", "20%", "30%", "40%", "50%", "60%", "70%", "80%", "90%", "100%"].map((r) => (
              <SelectItem key={r} value={r}>{r}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}

// ── Page 5: Mental Health ───────────────────────────────────────────

function MentalHealthPage({ answers, updateAnswer, toggleArrayItem }: PageRendererProps) {
  const selectedConditions = (answers.conditions as string[]) || [];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Mental Health Assessment</h3>
        <p className="text-gray-500">
          Your responses here are protected by our PII shield. This section
          helps evaluate mental health-related disability claims.
        </p>
      </div>

      <div className="space-y-3">
        <Label>Do you experience any of the following? (Select all that apply)</Label>
        {[
          "Recurrent nightmares or flashbacks",
          "Difficulty sleeping / insomnia",
          "Hypervigilance or exaggerated startle response",
          "Avoidance of people, places, or situations",
          "Feelings of detachment or emotional numbness",
          "Persistent sadness, depression, or hopelessness",
          "Anxiety or panic attacks",
          "Difficulty concentrating or memory problems",
          "Irritability or angry outbursts",
          "Suicidal thoughts or self-harm",
          "Substance use to cope",
          "Difficulty maintaining relationships",
          "Problems at work due to mental health",
        ].map((symptom) => (
          <label
            key={symptom}
            className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
              selectedConditions.includes(symptom)
                ? "bg-navy/5 border-navy"
                : "hover:bg-gray-50"
            }`}
          >
            <Checkbox
              checked={selectedConditions.includes(symptom)}
              onCheckedChange={() => toggleArrayItem("conditions", symptom)}
            />
            <span className="text-sm">{symptom}</span>
          </label>
        ))}
      </div>

      <Separator />

      <div className="space-y-2">
        <Label>Are you currently receiving mental health treatment?</Label>
        <RadioGroup
          value={(answers.receiving_treatment as string) || ""}
          onValueChange={(v) => updateAnswer("receiving_treatment", v)}
        >
          <div className="flex flex-col gap-2">
            {[
              { value: "yes_va", label: "Yes, through the VA" },
              { value: "yes_private", label: "Yes, private provider" },
              { value: "yes_both", label: "Yes, both VA and private" },
              { value: "no", label: "No, not currently" },
              { value: "past", label: "In the past, but not currently" },
            ].map((opt) => (
              <div key={opt.value} className="flex items-center gap-2">
                <RadioGroupItem value={opt.value} id={`mh_${opt.value}`} />
                <Label htmlFor={`mh_${opt.value}`}>{opt.label}</Label>
              </div>
            ))}
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label>Have you been diagnosed with a mental health condition?</Label>
        <RadioGroup
          value={(answers.diagnosed as string) || ""}
          onValueChange={(v) => updateAnswer("diagnosed", v)}
        >
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="diag_yes" />
              <Label htmlFor="diag_yes">Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="diag_no" />
              <Label htmlFor="diag_no">No</Label>
            </div>
          </div>
        </RadioGroup>
      </div>

      {answers.diagnosed === "yes" && (
        <div className="space-y-2">
          <Label>What diagnosis? (e.g., PTSD, MDD, GAD, TBI)</Label>
          <Input
            value={(answers.diagnosis_details as string) || ""}
            onChange={(e) => updateAnswer("diagnosis_details", e.target.value)}
          />
        </div>
      )}

      <div className="space-y-2">
        <Label>Describe the in-service event(s) related to your mental health</Label>
        <Textarea
          value={(answers.stressor_description as string) || ""}
          onChange={(e) => updateAnswer("stressor_description", e.target.value)}
          placeholder="Describe combat exposure, MST, accident, or other traumatic events"
          rows={4}
        />
      </div>

      <div className="space-y-2">
        <Label>How do these conditions affect your daily life and work?</Label>
        <Textarea
          value={(answers.functional_impact as string) || ""}
          onChange={(e) => updateAnswer("functional_impact", e.target.value)}
          placeholder="Describe how these conditions affect your job, relationships, and daily activities"
          rows={4}
        />
      </div>
    </div>
  );
}

// ── Page 6: Medical Evidence ────────────────────────────────────────

function MedicalEvidencePage({ answers, updateAnswer }: PageRendererProps) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Medical Evidence</h3>
        <p className="text-gray-500">
          Strong medical evidence significantly impacts your claim's success
          and processing speed.
        </p>
      </div>

      <div className="space-y-2">
        <Label>Do you have service treatment records (STRs)?</Label>
        <RadioGroup
          value={(answers.has_strs as string) || ""}
          onValueChange={(v) => updateAnswer("has_strs", v)}
        >
          {[
            { value: "yes", label: "Yes, I have copies" },
            { value: "partial", label: "I have some records" },
            { value: "no", label: "No, I need to request them" },
            { value: "unsure", label: "I'm not sure" },
          ].map((opt) => (
            <div key={opt.value} className="flex items-center gap-2">
              <RadioGroupItem value={opt.value} id={`str_${opt.value}`} />
              <Label htmlFor={`str_${opt.value}`}>{opt.label}</Label>
            </div>
          ))}
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label>Do you have private medical records supporting your conditions?</Label>
        <RadioGroup
          value={(answers.has_medical_records as string) || ""}
          onValueChange={(v) => updateAnswer("has_medical_records", v)}
        >
          <div className="flex flex-col gap-2">
            {[
              { value: "yes", label: "Yes" },
              { value: "some", label: "Some, but not complete" },
              { value: "no", label: "No" },
            ].map((opt) => (
              <div key={opt.value} className="flex items-center gap-2">
                <RadioGroupItem value={opt.value} id={`med_${opt.value}`} />
                <Label htmlFor={`med_${opt.value}`}>{opt.label}</Label>
              </div>
            ))}
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label>Have you had a VA C&P (Compensation & Pension) exam?</Label>
        <RadioGroup
          value={(answers.had_cp_exam as string) || ""}
          onValueChange={(v) => updateAnswer("had_cp_exam", v)}
        >
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="cp_yes" />
              <Label htmlFor="cp_yes">Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="cp_no" />
              <Label htmlFor="cp_no">No</Label>
            </div>
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label>Do you have buddy / lay statements?</Label>
        <RadioGroup
          value={(answers.has_buddy_statements as string) || ""}
          onValueChange={(v) => updateAnswer("has_buddy_statements", v)}
        >
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="buddy_yes" />
              <Label htmlFor="buddy_yes">Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="buddy_no" />
              <Label htmlFor="buddy_no">No</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="planned" id="buddy_planned" />
              <Label htmlFor="buddy_planned">Planning to get</Label>
            </div>
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label>Do you have a nexus letter from a physician?</Label>
        <RadioGroup
          value={(answers.has_nexus_letter as string) || ""}
          onValueChange={(v) => updateAnswer("has_nexus_letter", v)}
        >
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="nexus_yes" />
              <Label htmlFor="nexus_yes">Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="nexus_no" />
              <Label htmlFor="nexus_no">No</Label>
            </div>
          </div>
        </RadioGroup>
      </div>

      <div className="space-y-2">
        <Label>List current medications related to claimed conditions</Label>
        <Textarea
          value={(answers.medications as string) || ""}
          onChange={(e) => updateAnswer("medications", e.target.value)}
          placeholder="List medications and what they're prescribed for"
          rows={3}
        />
      </div>
    </div>
  );
}

// ── Page 7: Exposures ───────────────────────────────────────────────

function ExposuresPage({ answers, updateAnswer, toggleArrayItem }: PageRendererProps) {
  const selectedExposures = (answers.exposures as string[]) || [];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Environmental & Toxic Exposures</h3>
        <p className="text-gray-500">
          The PACT Act expanded VA coverage for toxic exposure conditions.
          Select any exposures you experienced during service.
        </p>
      </div>

      <div className="space-y-2">
        {[
          "Burn pit / airborne hazards",
          "Agent Orange / tactical herbicides",
          "Depleted uranium",
          "Ionizing radiation",
          "Contaminated water (Camp Lejeune)",
          "Asbestos",
          "Industrial solvents / chemicals",
          "JP-8 jet fuel",
          "Noise exposure (weapons, vehicles, aircraft)",
          "Extreme temperatures (heat/cold injuries)",
          "Sand/dust storms",
          "Oil well fires",
          "Mustard gas / chemical weapons testing",
        ].map((exposure) => (
          <label
            key={exposure}
            className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
              selectedExposures.includes(exposure)
                ? "bg-yellow-50 border-yellow-400"
                : "hover:bg-gray-50"
            }`}
          >
            <Checkbox
              checked={selectedExposures.includes(exposure)}
              onCheckedChange={() => toggleArrayItem("exposures", exposure)}
            />
            <span className="text-sm">{exposure}</span>
          </label>
        ))}
      </div>

      <div className="space-y-2">
        <Label>Describe the exposure circumstances</Label>
        <Textarea
          value={(answers.exposure_details as string) || ""}
          onChange={(e) => updateAnswer("exposure_details", e.target.value)}
          placeholder="Where, when, and for how long were you exposed?"
          rows={4}
        />
      </div>

      <div className="space-y-2">
        <Label>Are you enrolled in the Airborne Hazards and Open Burn Pit Registry?</Label>
        <RadioGroup
          value={(answers.burn_pit_registry as string) || ""}
          onValueChange={(v) => updateAnswer("burn_pit_registry", v)}
        >
          <div className="flex gap-6">
            <div className="flex items-center gap-2">
              <RadioGroupItem value="yes" id="bpr_yes" />
              <Label htmlFor="bpr_yes">Yes</Label>
            </div>
            <div className="flex items-center gap-2">
              <RadioGroupItem value="no" id="bpr_no" />
              <Label htmlFor="bpr_no">No</Label>
            </div>
          </div>
        </RadioGroup>
      </div>
    </div>
  );
}

// ── Page 8: Additional Claims ───────────────────────────────────────

function AdditionalClaimsPage({ answers, updateAnswer, toggleArrayItem }: PageRendererProps) {
  const selectedClaims = (answers.additional_claim_types as string[]) || [];

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Additional Claims & Benefits</h3>
        <p className="text-gray-500">
          Beyond disability compensation, you may be eligible for additional benefits.
        </p>
      </div>

      <div className="space-y-3">
        <Label>Are you claiming any of the following? (Select all that apply)</Label>
        {[
          "Individual Unemployability (TDIU)",
          "Special Monthly Compensation (SMC)",
          "Aid and Attendance",
          "Housebound benefits",
          "Dependents' benefits (additional compensation for dependents)",
          "Vocational Rehabilitation & Employment (VR&E / Chapter 31)",
          "Automobile / adaptive equipment allowance",
          "Clothing allowance",
          "Secondary service-connected conditions",
        ].map((claim) => (
          <label
            key={claim}
            className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
              selectedClaims.includes(claim)
                ? "bg-navy/5 border-navy"
                : "hover:bg-gray-50"
            }`}
          >
            <Checkbox
              checked={selectedClaims.includes(claim)}
              onCheckedChange={() => toggleArrayItem("additional_claim_types", claim)}
            />
            <span className="text-sm">{claim}</span>
          </label>
        ))}
      </div>

      <Separator />

      <div className="space-y-2">
        <Label>Have you previously filed a VA disability claim?</Label>
        <RadioGroup
          value={(answers.previous_claim as string) || ""}
          onValueChange={(v) => updateAnswer("previous_claim", v)}
        >
          {[
            { value: "no", label: "No — this is my first claim" },
            { value: "yes_granted", label: "Yes — it was granted" },
            { value: "yes_denied", label: "Yes — it was denied" },
            { value: "yes_pending", label: "Yes — it's pending" },
          ].map((opt) => (
            <div key={opt.value} className="flex items-center gap-2">
              <RadioGroupItem value={opt.value} id={`prev_${opt.value}`} />
              <Label htmlFor={`prev_${opt.value}`}>{opt.label}</Label>
            </div>
          ))}
        </RadioGroup>
      </div>

      {(answers.previous_claim === "yes_denied" || answers.previous_claim === "yes_pending") && (
        <div className="space-y-2">
          <Label>Provide details about your previous claim</Label>
          <Textarea
            value={(answers.previous_claim_details as string) || ""}
            onChange={(e) => updateAnswer("previous_claim_details", e.target.value)}
            placeholder="What conditions were claimed? What was the reason for denial?"
            rows={3}
          />
        </div>
      )}

      <div className="space-y-2">
        <Label>Any additional information you'd like to share?</Label>
        <Textarea
          value={(answers.additional_info as string) || ""}
          onChange={(e) => updateAnswer("additional_info", e.target.value)}
          placeholder="Anything else that might be relevant to your claim"
          rows={4}
        />
      </div>
    </div>
  );
}

// ── Page 9: Review & Submit ─────────────────────────────────────────

function ReviewPage({ allAnswers, aiEstimates, sessionId, onComplete }: PageRendererProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<Record<string, unknown> | null>(null);
  const { toast } = useToast();

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const result = await submitClaim(sessionId);
      setSubmitResult(result as unknown as Record<string, unknown>);
      toast({
        title: "Claim Submitted",
        description: "Your claim has been processed through our AI agent pipeline.",
      });
      onComplete?.();
    } catch (err) {
      toast({
        title: "Submission Failed",
        description: err instanceof Error ? err.message : "Please try again.",
        variant: "destructive",
      });
    }
    setIsSubmitting(false);
  };

  // Display a summary of all answered pages
  const pageSummary = QUESTIONNAIRE_PAGES.filter((p) => p.key !== "review").map((page) => {
    const pageAnswers = allAnswers[page.key] || {};
    const answerCount = Object.keys(pageAnswers).length;
    return { ...page, answerCount, hasAnswers: answerCount > 0 };
  });

  if (submitResult) {
    const fdc = (submitResult as any).fdc_package || {};
    return (
      <div className="space-y-6">
        <div className="text-center py-6">
          <CheckCircle className="h-16 w-16 text-green-600 mx-auto mb-4" />
          <h3 className="text-2xl font-bold text-navy">Claim Submitted Successfully</h3>
          <p className="text-gray-500 mt-2 max-w-md mx-auto">
            {(submitResult as any).message}
          </p>
        </div>

        <Separator />

        <div className="space-y-4">
          <h4 className="font-bold text-navy text-lg">FDC Package Summary</h4>
          
          <div className="bg-green-50 rounded-xl p-4 border border-green-200">
            <p className="text-sm font-semibold text-green-800 mb-2">Required Forms</p>
            <ul className="space-y-1">
              {(fdc.required_forms || []).map((form: string, idx: number) => (
                <li key={idx} className="text-sm text-green-700 flex items-center gap-2">
                  <CheckCircle className="h-3 w-3" /> {form}
                </li>
              ))}
            </ul>
          </div>

          <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
            <p className="text-sm font-semibold text-blue-800 mb-2">Evidence Checklist</p>
            <ul className="space-y-1">
              {(fdc.evidence_checklist || []).map((item: string, idx: number) => (
                <li key={idx} className="text-sm text-blue-700 flex items-center gap-2">
                  <FileText className="h-3 w-3" /> {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-2xl font-bold text-navy mb-1">Review & Submit</h3>
        <p className="text-gray-500">
          Review your answers below. Your claim will be processed by our
          AI agent pipeline: Claims Agent → Supervisor → Claims Assistant → FDC.
        </p>
      </div>

      {/* Page completion summary */}
      <div className="space-y-2">
        {pageSummary.map((page) => (
          <div
            key={page.key}
            className={`flex items-center justify-between p-3 rounded-lg border ${
              page.hasAnswers
                ? "bg-green-50 border-green-200"
                : "bg-yellow-50 border-yellow-200"
            }`}
          >
            <div className="flex items-center gap-3">
              {PAGE_ICONS[page.key]}
              <span className="text-sm font-medium">{page.label}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500">
                {page.answerCount} field{page.answerCount !== 1 ? "s" : ""}
              </span>
              {page.hasAnswers ? (
                <CheckCircle className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              )}
            </div>
          </div>
        ))}
      </div>

      {/* AI Estimates Summary */}
      {aiEstimates.estimated_combined_rating > 0 && (
        <>
          <Separator />
          <div className="bg-navy/5 rounded-xl p-5 border border-navy/10">
            <h4 className="font-bold text-navy mb-3">AI Estimated Outcome</h4>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-2xl font-black text-navy">
                  {aiEstimates.estimated_combined_rating}%
                </p>
                <p className="text-xs text-gray-500">Combined Rating</p>
              </div>
              <div>
                <p className="text-2xl font-black text-green-700">
                  ${Math.round(aiEstimates.estimated_monthly_compensation)}/mo
                </p>
                <p className="text-xs text-gray-500">Monthly Comp</p>
              </div>
              <div>
                <p className="text-2xl font-black text-blue-700">
                  ${Math.round(aiEstimates.estimated_backpay).toLocaleString()}
                </p>
                <p className="text-xs text-gray-500">Est. Backpay</p>
              </div>
            </div>
          </div>
        </>
      )}

      {/* Submit button */}
      <div className="pt-4">
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="w-full bg-gradient-to-r from-navy to-navy-light text-white font-bold text-lg py-6 rounded-2xl shadow-lg hover:scale-[1.02] transition-all"
        >
          {isSubmitting ? (
            <span className="flex items-center gap-2">
              <Loader2 className="h-5 w-5 animate-spin" />
              Processing through AI Agent Pipeline...
            </span>
          ) : (
            "Submit Claim to AI Agent Pipeline"
          )}
        </Button>
        <p className="text-xs text-gray-400 text-center mt-2">
          Your claim will be reviewed by Claims Agent → Supervisor → Claims Assistant
        </p>
      </div>
    </div>
  );
}
