import { useEffect } from "react";
import { useLocation } from "wouter";
import { getCurrentUser, fetchUserAttributes } from "aws-amplify/auth";
import { Hub } from "aws-amplify/utils";
import { Loader2 } from "lucide-react";

const ONBOARDING_KEY = (uid: string) => `va_ob_${uid}`;

async function resolveDestination(): Promise<"/dashboard" | "/onboarding"> {
  const user = await getCurrentUser();
  if (localStorage.getItem(ONBOARDING_KEY(user.userId))) return "/dashboard";
  const attrs = await fetchUserAttributes();
  const name = attrs.name ?? "";
  const onboarded = name.length > 0 && !name.startsWith("GitHub_");
  if (onboarded) {
    localStorage.setItem(ONBOARDING_KEY(user.userId), "1");
    return "/dashboard";
  }
  return "/onboarding";
}

export function AuthCallback() {
  const [, setLocation] = useLocation();

  useEffect(() => {
    let navigated = false;

    const doNavigate = async () => {
      if (navigated) return;
      navigated = true;
      try {
        setLocation(await resolveDestination());
      } catch {
        setLocation("/login");
      }
    };

    // OAuth path: Amplify fires 'signedIn' once the code exchange completes
    const unsubscribe = Hub.listen("auth", ({ payload }) => {
      if (payload.event === "signedIn") {
        unsubscribe();
        doNavigate();
      } else if (payload.event === "signInWithRedirect_failure") {
        unsubscribe();
        navigated = true;
        setLocation("/login");
      }
    });

    // Email/password path: user is already signed in when they hit /callback
    // IMPORTANT: failure here is silent — OAuth exchange may still be in progress
    getCurrentUser()
      .then(() => { unsubscribe(); doNavigate(); })
      .catch(() => { /* OAuth in progress — Hub listener above will fire */ });

    return () => unsubscribe();
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-gray-50">
      <Loader2 className="h-10 w-10 animate-spin text-navy" />
      <p className="text-sm text-gray-500">Completing sign-in…</p>
    </div>
  );
}
