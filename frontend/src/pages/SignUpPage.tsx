import { useState } from "react";
import { useLocation } from "wouter";
import { signInWithRedirect } from "aws-amplify/auth";
import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { Button } from "@/components/ui/button";
import { Shield } from "lucide-react";

export function SignUpPage() {
  const [, setLocation] = useLocation();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Check for OAuth error in URL search params
  const params = new URLSearchParams(window.location.search);
  const oauthError = params.get("error");

  const handleGitHubSignUp = async () => {
    setIsLoading(true);
    setError(null);
    try {
      await signInWithRedirect({
        provider: { custom: "GitHub" },
      });
    } catch (err) {
      console.error("Error signing up with GitHub:", err);
      setError(
        err instanceof Error ? err.message : "Failed to sign in with GitHub."
      );
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 flex items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center bg-gradient-to-br from-navy to-navy-dark p-4 rounded-2xl shadow-lg mb-4">
              <Shield className="h-10 w-10 text-gold" />
            </div>
            <h1 className="text-3xl font-bold text-navy mb-2">
              Sign Up for ValorAssist
            </h1>
            <p className="text-gray-600">
              Create your account to access AI-powered VA claims assistance.
            </p>
          </div>

          <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-8">
            {(error || oauthError) && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">
                  {error ||
                    "OAuth sign-in failed. Please try again."}
                </p>
              </div>
            )}

            <Button
              onClick={handleGitHubSignUp}
              disabled={isLoading}
              className="w-full bg-gray-900 hover:bg-gray-800 text-white font-semibold py-3 rounded-xl flex items-center justify-center gap-3 transition-all"
            >
              {isLoading ? (
                <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
              ) : (
                <svg
                  className="h-5 w-5"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    fillRule="evenodd"
                    d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
              {isLoading ? "Redirecting…" : "Sign up with GitHub"}
            </Button>

            <div className="mt-6 text-center">
              <p className="text-sm text-gray-500">
                Already have an account?{" "}
                <button
                  onClick={() => setLocation("/signup")}
                  className="text-navy font-medium hover:underline"
                >
                  Sign in
                </button>
              </p>
            </div>
          </div>

          <p className="mt-6 text-center text-xs text-gray-400">
            By signing up, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default SignUpPage;
