import { useState } from "react";
import { useLocation } from "wouter";
import {
  updateUserAttributes,
  sendUserAttributeVerificationCode,
  confirmUserAttribute,
  setUpTOTP,
  verifyTOTPSetup,
  updateMFAPreference,
  getCurrentUser,
} from "aws-amplify/auth";
import { Shield, Loader2, CheckCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Step = "profile" | "phone" | "phone-otp" | "totp";

const ONBOARDING_KEY = (uid: string) => `va_ob_${uid}`;

export function OnboardingPage() {
  const [, setLocation] = useLocation();
  const [step, setStep] = useState<Step>("profile");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Step 1 — profile
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");

  // Step 2 — phone
  const [phone, setPhone] = useState("");

  // Step 3 — OTP + TOTP
  const [phoneOtp, setPhoneOtp] = useState("");
  const [totpUri, setTotpUri] = useState("");
  const [totpCode, setTotpCode] = useState("");

  const wrap = async (fn: () => Promise<void>) => {
    setError("");
    setLoading(true);
    try { await fn(); } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "An error occurred.");
    } finally { setLoading(false); }
  };

  // ── Step 1: save name ──────────────────────────────────────────────────────
  const submitProfile = () => wrap(async () => {
    if (!firstName.trim() || !lastName.trim()) throw new Error("First and last name are required.");
    await updateUserAttributes({
      userAttributes: { name: `${firstName.trim()} ${lastName.trim()}` },
    });
    setStep("phone");
  });

  // ── Step 2: send phone OTP ─────────────────────────────────────────────────
  const submitPhone = () => wrap(async () => {
    const e164 = phone.trim().replace(/\D/g, "");
    if (e164.length < 10) throw new Error("Enter a valid US phone number.");
    const formatted = `+1${e164.slice(-10)}`;
    await updateUserAttributes({ userAttributes: { phone_number: formatted } });
    await sendUserAttributeVerificationCode({ userAttributeKey: "phone_number" });
    setStep("phone-otp");
  });

  // ── Step 2b: verify phone OTP ──────────────────────────────────────────────
  const verifyPhone = () => wrap(async () => {
    await confirmUserAttribute({ userAttributeKey: "phone_number", confirmationCode: phoneOtp.trim() });
    // Set up TOTP
    const details = await setUpTOTP();
    const user = await getCurrentUser();
    const email = (user as any).signInDetails?.loginId ?? user.username;
    setTotpUri(details.getSetupUri("ValorAssist", email).toString());
    setStep("totp");
  });

  // ── Step 3: verify TOTP and complete ──────────────────────────────────────
  const verifyTotp = () => wrap(async () => {
    await verifyTOTPSetup({ code: totpCode.trim() });
    await updateMFAPreference({ totp: "PREFERRED" });
    const user = await getCurrentUser();
    localStorage.setItem(ONBOARDING_KEY(user.userId), "1");
    setLocation("/dashboard");
  });

  const qrUrl = totpUri
    ? `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(totpUri)}`
    : "";

  const STEPS: Step[] = ["profile", "phone", "phone-otp", "totp"];
  const stepIndex = STEPS.indexOf(step === "phone-otp" ? "phone-otp" : step);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
        {/* Header */}
        <div className="flex flex-col items-center mb-6">
          <div className="bg-gradient-to-br from-navy to-navy-dark p-3 rounded-xl shadow-lg mb-3">
            <Shield className="h-7 w-7 text-gold" />
          </div>
          <h1 className="text-xl font-black gradient-text">Account Setup</h1>
          <p className="text-sm text-gray-500 mt-1">Complete your profile to continue</p>
        </div>

        {/* Progress */}
        <div className="flex items-center gap-2 mb-8">
          {["Profile", "Phone", "2FA"].map((label, i) => {
            const done = stepIndex > i + (i >= 1 ? 1 : 0);
            const active = stepIndex === i + (i >= 1 ? 1 : 0) || (i === 1 && step === "phone-otp");
            return (
              <div key={label} className="flex-1 flex flex-col items-center gap-1">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                  done ? "bg-green-500 text-white" : active ? "bg-navy text-white" : "bg-gray-100 text-gray-400"
                }`}>
                  {done ? <CheckCircle size={14} /> : i + 1}
                </div>
                <span className={`text-xs ${active ? "text-navy font-semibold" : "text-gray-400"}`}>{label}</span>
              </div>
            );
          })}
        </div>

        {/* ── Step 1: Profile ── */}
        {step === "profile" && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="fn">First Name</Label>
                <Input id="fn" value={firstName} onChange={e => setFirstName(e.target.value)} className="mt-1" />
              </div>
              <div>
                <Label htmlFor="ln">Last Name</Label>
                <Input id="ln" value={lastName} onChange={e => setLastName(e.target.value)} className="mt-1" />
              </div>
            </div>
            {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
            <Button className="w-full bg-navy text-white hover:bg-navy-dark" onClick={submitProfile} disabled={loading}>
              {loading ? <Loader2 size={15} className="animate-spin mr-2" /> : null} Continue
            </Button>
          </div>
        )}

        {/* ── Step 2: Phone ── */}
        {step === "phone" && (
          <div className="space-y-4">
            <div>
              <Label htmlFor="ph">Mobile Phone Number</Label>
              <p className="text-xs text-gray-500 mb-1">US numbers only. No VoIP numbers.</p>
              <Input id="ph" type="tel" placeholder="(555) 555-5555" value={phone} onChange={e => setPhone(e.target.value)} className="mt-1" />
            </div>
            {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
            <Button className="w-full bg-navy text-white hover:bg-navy-dark" onClick={submitPhone} disabled={loading}>
              {loading ? <Loader2 size={15} className="animate-spin mr-2" /> : null} Send Verification Code
            </Button>
          </div>
        )}

        {/* ── Step 2b: Phone OTP ── */}
        {step === "phone-otp" && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">Enter the 6-digit code sent to your phone.</p>
            <div>
              <Label htmlFor="potp">Verification Code</Label>
              <Input id="potp" inputMode="numeric" maxLength={6} value={phoneOtp} onChange={e => setPhoneOtp(e.target.value)} className="mt-1 tracking-widest text-center text-lg" />
            </div>
            {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
            <Button className="w-full bg-navy text-white hover:bg-navy-dark" onClick={verifyPhone} disabled={loading}>
              {loading ? <Loader2 size={15} className="animate-spin mr-2" /> : null} Verify
            </Button>
            <button className="text-xs text-gray-400 hover:text-navy w-full text-center" onClick={() => setStep("phone")}>
              ← Change number
            </button>
          </div>
        )}

        {/* ── Step 3: TOTP ── */}
        {step === "totp" && (
          <div className="space-y-4">
            <p className="text-sm text-gray-600">
              Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.), then enter the 6-digit code.
            </p>
            {qrUrl && (
              <div className="flex justify-center">
                <img src={qrUrl} alt="TOTP QR Code" className="rounded-lg border border-gray-200" width={200} height={200} />
              </div>
            )}
            <div>
              <Label htmlFor="totp">Authenticator Code</Label>
              <Input id="totp" inputMode="numeric" maxLength={6} value={totpCode} onChange={e => setTotpCode(e.target.value)} className="mt-1 tracking-widest text-center text-lg" />
            </div>
            {error && <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
            <Button className="w-full bg-navy text-white hover:bg-navy-dark" onClick={verifyTotp} disabled={loading}>
              {loading ? <Loader2 size={15} className="animate-spin mr-2" /> : null} Complete Setup
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
