
import { Button } from "@/components/ui/button";
import { Shield, FileText, Clock, Trophy, ArrowRight } from "lucide-react";

export function Demo() {
  return (
    <section className="py-24 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Content Side */}
          <div className="space-y-8">
            <div className="space-y-6">
              <div className="inline-flex items-center bg-navy/10 border border-navy/20 rounded-full px-6 py-2">
                <Shield className="h-5 w-5 text-navy mr-2" />
                <span className="text-navy font-bold text-sm">FREE CASE EVALUATION</span>
              </div>
              
              <h2 className="text-5xl font-black text-navy leading-tight">
                See If You Qualify for
                <span className="text-gold block">Additional Benefits</span>
              </h2>
              
              <p className="text-xl text-gray-600 leading-relaxed font-medium">
                Many veterans are under-compensated for their service-connected conditions. 
                Our free evaluation identifies missed opportunities and potential rating increases.
              </p>
            </div>

            {/* Features */}
            <div className="space-y-6">
              <div className="flex items-start space-x-4">
                <div className="bg-gradient-to-br from-gold to-yellow-400 p-3 rounded-xl shadow-lg">
                  <FileText className="h-6 w-6 text-navy" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-navy mb-2">Complete Record Review</h3>
                  <p className="text-gray-600 font-medium">Comprehensive analysis of your service records and current ratings</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="bg-gradient-to-br from-gold to-yellow-400 p-3 rounded-xl shadow-lg">
                  <Clock className="h-6 w-6 text-navy" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-navy mb-2">Quick 15-minute Call</h3>
                  <p className="text-gray-600 font-medium">Brief consultation with our VA-accredited representatives</p>
                </div>
              </div>

              <div className="flex items-start space-x-4">
                <div className="bg-gradient-to-br from-gold to-yellow-400 p-3 rounded-xl shadow-lg">
                  <Trophy className="h-6 w-6 text-navy" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-navy mb-2">Maximize Your Benefits</h3>
                  <p className="text-gray-600 font-medium">Identify all eligible claims and rating increase opportunities</p>
                </div>
              </div>
            </div>

            {/* CTA Button */}
            <div className="pt-8">
              <Button className="bg-gradient-to-r from-gold to-yellow-400 text-navy font-black text-lg px-12 py-6 rounded-xl shadow-2xl transform hover:scale-105 transition-all duration-300 hover:shadow-gold/50 group">
                GET MY FREE EVALUATION
                <ArrowRight className="ml-3 h-6 w-6 group-hover:translate-x-1 transition-transform" />
              </Button>
              <p className="text-sm text-gray-500 mt-4 font-semibold">
                ✓ No upfront fees • ✓ Confidential review • ✓ Veteran-owned company
              </p>
            </div>
          </div>

          {/* Visual Side */}
          <div className="relative">
            <div className="bg-gradient-to-br from-navy to-navy-light rounded-3xl p-8 text-white shadow-2xl">
              <div className="space-y-8">
                {/* Header */}
                <div className="text-center border-b border-gold/20 pb-6">
                  <div className="bg-gradient-to-br from-gold to-yellow-400 p-4 rounded-2xl mx-auto w-fit shadow-xl mb-4">
                    <Shield className="h-12 w-12 text-navy" />
                  </div>
                  <h3 className="text-2xl font-bold text-gold mb-2">Free Case Evaluation</h3>
                  <p className="text-gray-300">Discover your full benefit potential</p>
                </div>

                {/* Form Preview */}
                <div className="space-y-6">
                  <div className="space-y-4">
                    <div className="bg-navy-light rounded-lg p-4 border border-gold/20">
                      <label className="block text-sm font-semibold text-gold mb-2">Service Branch</label>
                      <div className="text-white font-medium">Army • Navy • Marines • Air Force • Coast Guard</div>
                    </div>
                    
                    <div className="bg-navy-light rounded-lg p-4 border border-gold/20">
                      <label className="block text-sm font-semibold text-gold mb-2">Current Rating</label>
                      <div className="text-white font-medium">0% • 10-30% • 40-60% • 70-90% • 100%</div>
                    </div>
                    
                    <div className="bg-navy-light rounded-lg p-4 border border-gold/20">
                      <label className="block text-sm font-semibold text-gold mb-2">Primary Concerns</label>
                      <div className="text-white font-medium">PTSD • Physical Injuries • Denied Claims • Low Rating</div>
                    </div>
                  </div>

                  {/* Trust Badges */}
                  <div className="border-t border-gold/20 pt-6">
                    <div className="flex items-center justify-center space-x-4 text-center">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gold">A+</div>
                        <div className="text-xs text-gray-400">BBB Rating</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gold">5★</div>
                        <div className="text-xs text-gray-400">Google Reviews</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-gold">VA</div>
                        <div className="text-xs text-gray-400">Accredited</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
