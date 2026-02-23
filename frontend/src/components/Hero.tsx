
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Shield, Star, CheckCircle } from "lucide-react";

export function Hero() {
  const [, setLocation] = useLocation();

  return (
    <section className="relative min-h-screen flex items-center bg-gradient-to-br from-gray-50 to-gray-100 overflow-hidden">
      {/* Modern geometric background pattern */}
      <div className="absolute inset-0 hero-pattern opacity-5"></div>
      
      {/* Animated background shapes */}
      <div className="absolute top-20 left-10 w-72 h-72 bg-gold/10 rounded-full blur-3xl animate-float"></div>
      <div className="absolute bottom-20 right-10 w-96 h-96 bg-navy/10 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }}></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Content */}
          <div className="space-y-8">
            {/* Badge with modern styling */}
            <div className="inline-flex items-center glass-card rounded-full px-6 py-3 animate-pulse-gold">
              <Star className="h-5 w-5 text-gold mr-2" />
              <span className="text-navy font-bold text-sm tracking-wide">VETERAN-OWNED & OPERATED</span>
            </div>

            {/* Main Headline with blue banner background */}
            <div className="relative bg-navy rounded-2xl p-8 shadow-2xl">
              <h1 className="text-5xl lg:text-6xl font-black leading-none mb-4">
                <span className="text-white">Transform Your</span>
                <span className="block text-gold mt-2">VA Claims Experience</span>
              </h1>
              <p className="text-xl lg:text-2xl text-gold font-medium leading-relaxed mb-4">
                Expert guidance from veterans who understand your journey
              </p>
              
              {/* Subheading inside the banner */}
              <p className="text-lg text-gray-200 leading-relaxed max-w-xl">
                Stop struggling with complex paperwork and endless delays. Our AI-powered platform and veteran experts help you get the benefits you've earned - faster and with less stress.
              </p>
            </div>

            {/* CTA Section with modern buttons */}
            <div className="flex flex-wrap gap-4 pt-4">
              <Button
                onClick={() => setLocation("/start-claim")}
                className="bg-gradient-to-r from-navy to-navy-light text-white font-bold text-lg px-8 py-6 rounded-2xl shadow-navy transform hover:scale-105 transition-all duration-300"
              >
                Start Your Claim
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  const el = document.getElementById('services');
                  el?.scrollIntoView({ behavior: 'smooth' });
                }}
                className="border-2 border-navy text-navy font-bold text-lg px-8 py-6 rounded-2xl hover:bg-navy hover:text-white transition-all duration-300"
              >
                Learn More
              </Button>
            </div>

            {/* Trust Indicators with modern design */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 pt-8">
              {[
                { value: "50K+", label: "Veterans Helped" },
                { value: "98%", label: "Success Rate" },
                { value: "$2.5M", label: "Benefits Secured" },
                { value: "24/7", label: "Support" }
              ].map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="text-2xl font-black text-navy">{stat.value}</div>
                  <div className="text-xs text-gray-600 font-medium">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Visual Element - Modern card design */}
          <div className="relative lg:pl-8">
            <div className="relative glass-card rounded-3xl p-2 shadow-2xl">
              <div className="bg-gradient-to-br from-navy to-navy-dark rounded-2xl p-8 text-white">
                <div className="space-y-6">
                  {/* Icon */}
                  <div className="bg-gold p-4 rounded-2xl w-fit shadow-gold">
                    <Shield className="h-12 w-12 text-navy" />
                  </div>
                  
                  {/* Content */}
                  <div>
                    <h3 className="text-2xl font-bold mb-3">Your Benefits Maximized</h3>
                    <p className="text-gray-300 leading-relaxed mb-6">
                      Our proven system helps veterans navigate the complex VA claims process with confidence and success.
                    </p>
                  </div>

                  {/* Features list */}
                  <div className="space-y-3">
                    {[
                      "AI-powered document analysis",
                      "Expert veteran advocates",
                      "Real-time claim tracking",
                      "Guaranteed results"
                    ].map((feature, index) => (
                      <div key={index} className="flex items-center space-x-3">
                        <CheckCircle className="h-5 w-5 text-gold flex-shrink-0" />
                        <span className="text-sm font-medium">{feature}</span>
                      </div>
                    ))}
                  </div>

                  {/* Bottom accent */}
                  <div className="pt-6 border-t border-gold/20">
                    <div className="flex items-center justify-between">
                      <span className="text-gold font-bold">No upfront costs</span>
                      <div className="flex -space-x-2">
                        {[...Array(3)].map((_, i) => (
                          <div key={i} className="w-8 h-8 bg-gold/20 rounded-full border-2 border-gold/50"></div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Floating accent elements */}
            <div className="absolute -top-4 -right-4 bg-gold rounded-full p-3 shadow-gold animate-pulse">
              <Star className="h-6 w-6 text-navy" />
            </div>
            <div className="absolute -bottom-4 -left-4 bg-navy rounded-full p-3 shadow-navy animate-float">
              <CheckCircle className="h-6 w-6 text-gold" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
