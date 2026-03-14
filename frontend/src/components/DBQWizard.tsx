import { useState } from "react";
import { apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2, AlertTriangle, CheckCircle } from "lucide-react";

const DISCLAIMER = `IMPORTANT LEGAL DISCLAIMER: This tool provides estimates based on 38 CFR regulations and publicly available VA rating criteria. It does NOT constitute official legal, medical, or VA-accredited claims advice. Results are for informational purposes only and do not guarantee any specific VA rating or benefit outcome. Always consult a VA-accredited claims agent, attorney, or Veterans Service Organization (VSO) representative for official guidance.`;

interface Question {
  id: string;
  text: string;
  type: "select" | "multiselect" | "textarea";
  options?: string[];
}

interface Condition {
  id: string;
  label: string;
  questions: Question[];
}

interface EvalResult {
  claim_id: string;
  estimated_rating: number;
  rationale: string;
  supporting_factors: string[];
  limiting_factors: string[];
  cfr_citations: string[];
}

type Step = "select" | "questions" | "processing" | "results";

export function DBQWizard() {
  const [step, setStep] = useState<Step>("select");
  const [conditions, setConditions] = useState<Condition[]>([]);
  const [selected, setSelected] = useState<Condition | null>(null);
  const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
  const [result, setResult] = useState<EvalResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingConditions, setLoadingConditions] = useState(false);

  const loadConditions = async () => {
    setLoadingConditions(true);
    try {
      const res = await apiRequest("GET", "/dbq/conditions");
      setConditions(await res.json());
      setStep("select");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoadingConditions(false);
    }
  };

  const selectCondition = (c: Condition) => {
    setSelected(c);
    setAnswers({});
    setStep("questions");
  };

  const setAnswer = (id: string, value: string | string[]) => {
    setAnswers((prev) => ({ ...prev, [id]: value }));
  };

  const toggleMulti = (id: string, option: string) => {
    const current = (answers[id] as string[]) || [];
    setAnswer(id, current.includes(option) ? current.filter((o) => o !== option) : [...current, option]);
  };

  const submit = async () => {
    if (!selected) return;
    setStep("processing");
    setError(null);
    try {
      const res = await apiRequest("POST", "/dbq/evaluate", {
        condition: selected.id,
        answers,
      });
      setResult(await res.json());
      setStep("results");
    } catch (e: any) {
      setError(e.message);
      setStep("questions");
    }
  };

  const reset = () => {
    setStep("select");
    setSelected(null);
    setAnswers({});
    setResult(null);
    setError(null);
  };

  // ── Disclaimer banner (always visible) ──────────────────────────
  const DisclaimerBanner = () => (
    <div className="bg-amber-50 border border-amber-400 rounded-lg p-4 mb-6 flex gap-3">
      <AlertTriangle className="h-5 w-5 text-amber-600 flex-shrink-0 mt-0.5" />
      <p className="text-sm text-amber-800">{DISCLAIMER}</p>
    </div>
  );

  // ── Step: Select condition ───────────────────────────────────────
  if (step === "select") {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <DisclaimerBanner />
        <h2 className="text-2xl font-bold text-gray-900 mb-2">DBQ Assessment</h2>
        <p className="text-gray-600 mb-6">Select the condition you want to assess for VA disability rating.</p>
        {conditions.length === 0 ? (
          <Button onClick={loadConditions} disabled={loadingConditions} className="bg-navy-700 hover:bg-navy-800 text-white">
            {loadingConditions ? <><Loader2 className="h-4 w-4 animate-spin mr-2" />Loading...</> : "Start Assessment"}
          </Button>
        ) : (
          <div className="grid gap-3">
            {conditions.map((c) => (
              <button key={c.id} onClick={() => selectCondition(c)}
                className="text-left p-4 border-2 border-gray-200 rounded-lg hover:border-navy-700 hover:bg-navy-50 transition-colors">
                <span className="font-semibold text-gray-900">{c.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    );
  }

  // ── Step: Questions ──────────────────────────────────────────────
  if (step === "questions" && selected) {
    const allAnswered = selected.questions.every((q) => {
      const a = answers[q.id];
      return q.type === "multiselect" ? (a as string[])?.length > 0 : !!a;
    });

    return (
      <div className="max-w-2xl mx-auto p-6">
        <DisclaimerBanner />
        <h2 className="text-2xl font-bold text-gray-900 mb-1">{selected.label}</h2>
        <p className="text-gray-500 text-sm mb-6">Answer all questions based on your current symptoms.</p>
        {error && <p className="text-red-600 text-sm mb-4">{error}</p>}
        <div className="space-y-6">
          {selected.questions.map((q) => (
            <div key={q.id}>
              <label className="block text-sm font-medium text-gray-800 mb-2">{q.text}</label>
              {q.type === "select" && (
                <select value={(answers[q.id] as string) || ""}
                  onChange={(e) => setAnswer(q.id, e.target.value)}
                  className="w-full border border-gray-300 rounded-md p-2 text-sm focus:ring-2 focus:ring-navy-700">
                  <option value="">Select an option...</option>
                  {q.options?.map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              )}
              {q.type === "multiselect" && (
                <div className="space-y-2">
                  {q.options?.map((o) => (
                    <label key={o} className="flex items-center gap-2 cursor-pointer">
                      <input type="checkbox" checked={((answers[q.id] as string[]) || []).includes(o)}
                        onChange={() => toggleMulti(q.id, o)} className="rounded" />
                      <span className="text-sm text-gray-700">{o}</span>
                    </label>
                  ))}
                </div>
              )}
              {q.type === "textarea" && (
                <textarea value={(answers[q.id] as string) || ""}
                  onChange={(e) => setAnswer(q.id, e.target.value)}
                  rows={3} placeholder="Describe your experience..."
                  className="w-full border border-gray-300 rounded-md p-2 text-sm focus:ring-2 focus:ring-navy-700" />
              )}
            </div>
          ))}
        </div>
        <div className="flex gap-3 mt-8">
          <Button variant="outline" onClick={reset}>Back</Button>
          <Button onClick={submit} disabled={!allAnswered} className="bg-navy-700 hover:bg-navy-800 text-white">
            Submit for Evaluation
          </Button>
        </div>
      </div>
    );
  }

  // ── Step: Processing ─────────────────────────────────────────────
  if (step === "processing") {
    return (
      <div className="max-w-2xl mx-auto p-6 text-center">
        <DisclaimerBanner />
        <Loader2 className="h-12 w-12 animate-spin mx-auto text-navy-700 mb-4" />
        <h3 className="text-lg font-semibold text-gray-900">Retrieving 38 CFR criteria and evaluating...</h3>
        <p className="text-gray-500 text-sm mt-2">This may take a few seconds.</p>
      </div>
    );
  }

  // ── Step: Results ────────────────────────────────────────────────
  if (step === "results" && result) {
    return (
      <div className="max-w-2xl mx-auto p-6">
        <DisclaimerBanner />
        <div className="flex items-center gap-3 mb-6">
          <CheckCircle className="h-8 w-8 text-green-600" />
          <h2 className="text-2xl font-bold text-gray-900">Evaluation Complete</h2>
        </div>

        <Card className="mb-4 border-2 border-navy-700">
          <CardHeader className="pb-2">
            <CardTitle className="text-gray-600 text-sm font-medium uppercase tracking-wide">Estimated Rating</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-5xl font-bold text-navy-700">{result.estimated_rating}%</p>
            <p className="text-xs text-gray-500 mt-1">Based on retrieved 38 CFR criteria only — not an official VA determination</p>
          </CardContent>
        </Card>

        <Card className="mb-4">
          <CardHeader className="pb-2"><CardTitle className="text-sm">Rationale</CardTitle></CardHeader>
          <CardContent><p className="text-sm text-gray-700">{result.rationale}</p></CardContent>
        </Card>

        {result.cfr_citations.length > 0 && (
          <Card className="mb-4">
            <CardHeader className="pb-2"><CardTitle className="text-sm">38 CFR Citations</CardTitle></CardHeader>
            <CardContent>
              <ul className="list-disc list-inside space-y-1">
                {result.cfr_citations.map((c, i) => <li key={i} className="text-sm text-gray-700">{c}</li>)}
              </ul>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-2 gap-4 mb-6">
          {result.supporting_factors.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-green-700">Supporting Factors</CardTitle></CardHeader>
              <CardContent>
                <ul className="list-disc list-inside space-y-1">
                  {result.supporting_factors.map((f, i) => <li key={i} className="text-xs text-gray-700">{f}</li>)}
                </ul>
              </CardContent>
            </Card>
          )}
          {result.limiting_factors.length > 0 && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm text-red-700">Limiting Factors</CardTitle></CardHeader>
              <CardContent>
                <ul className="list-disc list-inside space-y-1">
                  {result.limiting_factors.map((f, i) => <li key={i} className="text-xs text-gray-700">{f}</li>)}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>

        <div className="bg-amber-50 border border-amber-400 rounded-lg p-4 mb-6">
          <p className="text-xs text-amber-800 font-medium">Next Steps: Contact a VA-accredited VSO or claims agent to file an official claim. This estimate is not binding and does not replace a formal VA rating decision.</p>
        </div>

        <Button onClick={reset} className="bg-navy-700 hover:bg-navy-800 text-white">Start New Assessment</Button>
      </div>
    );
  }

  return null;
}
