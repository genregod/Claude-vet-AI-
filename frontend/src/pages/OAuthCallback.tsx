import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { getCurrentUser } from "aws-amplify/auth";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";

const ERROR_REDIRECT_DELAY_MS = 3000;

export function OAuthCallback() {
  const [, setLocation] = useLocation();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        const user = await getCurrentUser();
        if (user) {
          // User successfully signed up/in with GitHub
          setLocation("/chat");
        }
      } catch (err) {
        console.error("OAuth callback error:", err);
        setError(
          err instanceof Error ? err.message : "Authentication failed."
        );
        // Redirect to signup with error indicator after a short delay
        setTimeout(() => {
          setLocation("/signup?error=oauth_failed");
        }, ERROR_REDIRECT_DELAY_MS);
      }
    };

    handleOAuthCallback();
  }, [setLocation]);

  if (error) {
    return (
      <div className="flex flex-col min-h-screen">
        <Header />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center p-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Authentication Failed
            </h2>
            <p className="text-gray-600 mb-4">{error}</p>
            <p className="text-sm text-gray-400">
              Redirecting to sign-up page…
            </p>
          </div>
        </main>
        <Footer />
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 flex items-center justify-center">
        <div className="text-center p-8">
          <div className="animate-spin h-10 w-10 border-4 border-navy border-t-transparent rounded-full mx-auto mb-4" />
          <p className="text-lg text-gray-600">Completing sign-in…</p>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default OAuthCallback;
