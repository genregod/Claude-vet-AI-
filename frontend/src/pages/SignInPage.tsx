import { useState } from "react";
import { useLocation } from "wouter";
import { signInWithRedirect } from "aws-amplify/auth";
import { cognitoSignIn } from "@/lib/cognitoAuth";
import { Shield, Github, Loader2, Eye, EyeOff, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";

export function SignInPage() {
  const [, setLocation] = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const result = await cognitoSignIn(email, password);
      if (result.isSignedIn) {
        setLocation("/dashboard");
      } else {
        setError("Additional sign-in step required: " + result.nextStep.signInStep);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Sign-in failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleGitHub = () => {
    setGithubLoading(true);
    signInWithRedirect({ provider: { custom: "GitHub" } });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 px-4">
      <div className="w-full max-w-sm">
        {/* Card */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-lg p-8 space-y-6">

          {/* Logo + heading */}
          <div className="flex flex-col items-center text-center space-y-2">
            <div className="bg-gradient-to-br from-navy to-navy-dark p-3 rounded-xl shadow-lg">
              <Shield className="h-7 w-7 text-gold" />
            </div>
            <h1 className="text-2xl font-black gradient-text">ValorAssist</h1>
            <p className="text-sm text-gray-500">Sign in to your veteran account</p>
          </div>

          {/* GitHub OAuth */}
          <Button
            type="button"
            variant="outline"
            className="w-full gap-2 h-11 font-semibold border-gray-300 hover:border-gray-400 hover:bg-gray-50"
            onClick={handleGitHub}
            disabled={githubLoading || loading}
          >
            {githubLoading
              ? <Loader2 size={16} className="animate-spin" />
              : <Github size={16} />}
            Continue with GitHub
          </Button>

          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-gray-400 font-medium">or</span>
            <Separator className="flex-1" />
          </div>

          {/* Email / Password */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email" className="text-sm font-semibold text-gray-700">
                Email address
              </Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                disabled={loading}
                className="h-11"
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-sm font-semibold text-gray-700">
                  Password
                </Label>
                <button
                  type="button"
                  className="text-xs text-navy hover:underline"
                  onClick={() => setLocation("/forgot-password")}
                >
                  Forgot password?
                </button>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  required
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  disabled={loading}
                  className="h-11 pr-10"
                />
                <button
                  type="button"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  onClick={() => setShowPassword(v => !v)}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-start gap-2 text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl px-3 py-2.5">
                <AlertCircle size={15} className="shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <Button
              type="submit"
              className="w-full h-11 bg-navy text-white hover:bg-navy-dark font-semibold"
              disabled={loading || githubLoading}
            >
              {loading
                ? <><Loader2 size={16} className="animate-spin mr-2" />Signing in…</>
                : "Sign In"}
            </Button>
          </form>

          {/* Sign up link */}
          <p className="text-center text-sm text-gray-500">
            New to ValorAssist?{" "}
            <button
              className="text-navy font-semibold hover:underline"
              onClick={() => setLocation("/start-claim")}
            >
              Start your free claim
            </button>
          </p>
        </div>

        {/* Legal */}
        <p className="text-center text-xs text-gray-400 mt-4 px-4">
          By signing in you agree to our Terms of Service. ValorAssist is not affiliated with the VA.
        </p>
      </div>
    </div>
  );
}
