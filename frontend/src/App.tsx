import { Route, Switch } from "wouter";
import { QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "@/lib/queryClient";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Toaster } from "@/components/ui/toaster";
import { HomePage } from "@/pages/HomePage.tsx";
import { ChatPage } from "@/pages/ChatPage.tsx";
import { EvaluatePage } from "@/pages/EvaluatePage.tsx";
import { StartClaimPage } from "@/pages/StartClaimPage.tsx";
import { DBQPage } from "@/pages/DBQPage.tsx";
import { SecureDashboard } from "@/pages/SecureDashboard.tsx";
import { HealthCheckPage } from "@/pages/HealthCheck.tsx";
import { LoginPage } from "@/pages/LoginPage.tsx";
import { AuthCallback } from "@/pages/AuthCallback.tsx";
import { OnboardingPage } from "@/pages/OnboardingPage.tsx";
import { NotFoundPage } from "@/pages/NotFound.tsx";
import { ErrorBoundary, FallbackProps } from "react-error-boundary";

function ErrorFallback({ error }: FallbackProps) {
  const errorMessage = error instanceof Error ? error.message : String(error);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="text-center p-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Something went wrong
        </h2>
        <p className="text-gray-600 mb-4">{errorMessage}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Reload Page
        </button>
      </div>
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <QueryClientProvider client={queryClient}>
        <TooltipProvider>
          <div className="flex flex-col min-h-screen">
            <Switch>
              <Route path="/" component={HomePage} />
              <Route path="/chat" component={ChatPage} />
              <Route path="/evaluate" component={EvaluatePage} />
              <Route path="/start-claim" component={StartClaimPage} />
              <Route path="/dbq" component={DBQPage} />
              <Route path="/dashboard" component={SecureDashboard} />
              <Route path="/health" component={HealthCheckPage} />
              <Route path="/login" component={LoginPage} />
              <Route path="/callback" component={AuthCallback} />
              <Route path="/onboarding" component={OnboardingPage} />
              <Route component={NotFoundPage} />
            </Switch>
          </div>
          <Toaster />
        </TooltipProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
