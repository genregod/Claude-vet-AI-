import { Header } from "@/components/Header";
import { Footer } from "@/components/Footer";
import { ClaimForm } from "@/components/ClaimForm";

export function EvaluatePage() {
  return (
    <div className="flex flex-col min-h-screen">
      <Header />
      <main className="flex-1 bg-gray-50 py-12">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-8">
              <h1 className="text-4xl font-bold text-navy mb-4">
                Free Case Evaluation
              </h1>
              <p className="text-lg text-gray-600">
                Get a personalized assessment of your VA disability claim powered by AI
              </p>
            </div>
            <ClaimForm />
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
