import { useEffect } from "react";
import { useLocation } from "wouter";
import { getCurrentUser, fetchUserAttributes } from "aws-amplify/auth";
import { Loader2 } from "lucide-react";

const ONBOARDING_KEY = (uid: string) => `va_ob_${uid}`;

export function AuthCallback() {
  const [, setLocation] = useLocation();

  useEffect(() => {
    (async () => {
      try {
        const user = await getCurrentUser();
        // Check localStorage first (fast path)
        if (localStorage.getItem(ONBOARDING_KEY(user.userId))) {
          setLocation("/dashboard");
          return;
        }
        // Fallback: check if name attribute is already a real name (cross-device)
        const attrs = await fetchUserAttributes();
        const name = attrs.name ?? "";
        const isOnboarded = name.length > 0 && !name.startsWith("GitHub_");
        if (isOnboarded) {
          localStorage.setItem(ONBOARDING_KEY(user.userId), "1");
          setLocation("/dashboard");
        } else {
          setLocation("/onboarding");
        }
      } catch {
        setLocation("/login");
      }
    })();
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-gray-50">
      <Loader2 className="h-10 w-10 animate-spin text-navy" />
      <p className="text-sm text-gray-500">Completing sign-in…</p>
    </div>
  );
}
