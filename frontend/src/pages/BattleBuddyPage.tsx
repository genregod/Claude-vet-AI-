import { useState } from "react";
import { useLocation } from "wouter";
import { Users, CheckCircle, Shield, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const BRANCHES = ["Army", "Navy", "Marine Corps", "Air Force", "Space Force", "Coast Guard", "National Guard / Reserve"];
const ERAS = ["Vietnam Era", "Gulf War", "OEF/OIF/OND", "Post-9/11", "Other"];
const TOPICS = [
  { id: "claims", label: "VA Claims Navigation" },
  { id: "mst", label: "MST / Trauma Support" },
  { id: "mental_health", label: "Mental Health" },
  { id: "transition", label: "Civilian Transition" },
  { id: "housing", label: "Housing & Homelessness" },
  { id: "employment", label: "Employment" },
];

export function BattleBuddyPage() {
  const [, setLocation] = useLocation();
  const [branch, setBranch] = useState("");
  const [era, setEra] = useState("");
  const [topics, setTopics] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState("");

  const toggleTopic = (id: string) =>
    setTopics((prev) => prev.includes(id) ? prev.filter((t) => t !== id) : [...prev, id]);

  const handleSubmit = async () => {
    if (!branch || !era || topics.length === 0) {
      setError("Please select your branch, era, and at least one support topic.");
      return;
    }
    setError("");
    setLoading(true);
    // Persist preference locally; backend matching can be wired later
    localStorage.setItem("va_battle_buddy_prefs", JSON.stringify({ branch, era, topics }));
    await new Promise((r) => setTimeout(r, 800)); // simulate async
    setLoading(false);
    setConfirmed(true);
  };

  if (confirmed) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-100 px-4 py-12">
          <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 shadow-sm p-8 text-center space-y-4">
            <div className="flex justify-center">
              <div className="bg-green-100 rounded-full p-4">
                <CheckCircle className="h-10 w-10 text-green-600" />
              </div>
            </div>
            <h1 className="text-xl font-black text-navy">You're In</h1>
            <p className="text-gray-500 text-sm">
              We'll match you with a Battle Buddy based on your branch, era, and support needs. You'll hear from us within 48 hours.
            </p>
            <Button
              className="w-full bg-navy text-white hover:bg-navy-dark mt-2"
              onClick={() => setLocation("/dashboard")}
            >
              Go to My Dashboard
            </Button>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 flex items-center justify-center bg-gradient-to-br from-gray-50 via-white to-gray-100 px-4 py-12">
        <div className="w-full max-w-md space-y-6">
          {/* Header card */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 text-center">
            <div className="flex justify-center mb-3">
              <div className="bg-gradient-to-br from-navy to-navy-dark p-3 rounded-xl shadow-lg">
                <Users className="h-7 w-7 text-gold" />
              </div>
            </div>
            <h1 className="text-xl font-black text-navy">Battle Buddy Program</h1>
            <p className="text-gray-500 text-sm mt-1">
              Get matched with a fellow veteran who's been through the same process. Peer support, no judgment.
            </p>
          </div>

          {/* Preferences form */}
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-6 space-y-5">
            <div>
              <Label className="text-sm font-semibold text-gray-700">Branch of Service</Label>
              <Select onValueChange={setBranch}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select branch…" />
                </SelectTrigger>
                <SelectContent>
                  {BRANCHES.map((b) => (
                    <SelectItem key={b} value={b}>{b}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-sm font-semibold text-gray-700">Service Era</Label>
              <Select onValueChange={setEra}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Select era…" />
                </SelectTrigger>
                <SelectContent>
                  {ERAS.map((e) => (
                    <SelectItem key={e} value={e}>{e}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <Label className="text-sm font-semibold text-gray-700 mb-2 block">Support Topics (select all that apply)</Label>
              <div className="space-y-2">
                {TOPICS.map(({ id, label }) => (
                  <div key={id} className="flex items-center gap-2">
                    <Checkbox
                      id={id}
                      checked={topics.includes(id)}
                      onCheckedChange={() => toggleTopic(id)}
                    />
                    <label htmlFor={id} className="text-sm text-gray-700 cursor-pointer">{label}</label>
                  </div>
                ))}
              </div>
            </div>

            {error && (
              <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
            )}

            <Button
              className="w-full bg-navy text-white hover:bg-navy-dark"
              onClick={handleSubmit}
              disabled={loading}
            >
              {loading ? <Loader2 size={15} className="animate-spin mr-2" /> : <Shield size={15} className="mr-2" />}
              Find My Battle Buddy
            </Button>
          </div>

          <button
            className="text-xs text-gray-400 hover:text-navy w-full text-center"
            onClick={() => setLocation("/dashboard")}
          >
            Skip for now
          </button>
        </div>
      </main>
      <Footer />
    </div>
  );
}
