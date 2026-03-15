import { useEffect } from "react";
import { useLocation } from "wouter";
import { getCurrentUser } from "aws-amplify/auth";
import { Loader2 } from "lucide-react";

/**
 * Handles the OAuth redirect from Cognito (GitHub, future ID.me, etc.).
 * Amplify automatically exchanges the ?code= param for tokens on mount.
 * We just wait for getCurrentUser() to resolve, then navigate.
 */
export function AuthCallback() {
  const [, setLocation] = useLocation();

  useEffect(() => {
    getCurrentUser()
      .then(() => setLocation("/dashboard"))
      .catch(() => setLocation("/login"));
  }, []);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-3 bg-gray-50">
      <Loader2 className="h-10 w-10 animate-spin text-navy" />
      <p className="text-sm text-gray-500">Completing sign-in…</p>
    </div>
  );
}
