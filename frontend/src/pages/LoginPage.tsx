import { useState } from "react";
import { useLocation } from "wouter";
import { signInWithRedirect } from "aws-amplify/auth";
import { cognitoSignIn } from "@/lib/cognitoAuth";
import { Shield, Github, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function LoginPage() {
  const [, setLocation] = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await cognitoSignIn(email, password);
      if (result.isSignedIn) {
        setLocation("/dashboard");
      } else {
        setError("Sign-in step required: " + result.nextStep.signInStep);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleGitHub = () =>
    signInWithRedirect({ provider: { custom: "GitHub" } });

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div className="bg-gradient-to-br from-navy to-navy-dark p-3 rounded-xl shadow-lg mb-3">
            <Shield className="h-7 w-7 text-gold" />
          </div>
          <h1 className="text-2xl font-black gradient-text">ValorAssist</h1>
          <p className="text-sm text-gray-500 mt-1">Sign in to your account</p>
        </div>

        {/* GitHub OAuth */}
        <Button
          type="button"
          variant="outline"
          className="w-full gap-2 mb-6"
          onClick={handleGitHub}
        >
          <Github size={16} />
          Continue with GitHub
        </Button>

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-gray-200" />
          </div>
          <div className="relative flex justify-center text-xs text-gray-400 bg-white px-2">
            or sign in with email
          </div>
        </div>

        {/* Email / Password form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1"
            />
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <Button
            type="submit"
            className="w-full bg-navy text-white hover:bg-navy-dark"
            disabled={loading}
          >
            {loading ? <Loader2 size={16} className="animate-spin mr-2" /> : null}
            Sign In
          </Button>
        </form>
      </div>
    </div>
  );
}
