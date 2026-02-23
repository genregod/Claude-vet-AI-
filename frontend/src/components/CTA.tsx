
import { useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { Shield, Phone, Mail, Clock, ArrowRight } from "lucide-react";

export function CTA() {
  const [, setLocation] = useLocation();

  return (
    <section className="py-24 bg-gradient-to-br from-navy via-navy-light to-navy-dark text-white overflow-hidden relative">
      {/* Background Elements */}
      <div className="absolute inset-0 chevron-bg opacity-10"></div>
      <div className="absolute inset-0 bg-gradient-to-t from-navy-dark/50 to-transparent"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center space-y-12">
          {/* Main CTA Content */}
          <div className="space-y-8">
            <div className="inline-flex items-center bg-gold/20 border border-gold/50 rounded-full px-8 py-3 backdrop-blur-sm">
              <Shield className="h-6 w-6 text-gold mr-3" />
              <span className="text-gold font-bold text-lg">READY TO GET STARTED?</span>
            </div>

            <div className="space-y-6">
              <h2 className="text-6xl lg:text-7xl font-black leading-tight">
                Don't Wait.
                <span className="text-gold block">Get What You've Earned.</span>
              </h2>
              
              <p className="text-2xl font-bold text-gray-300 max-w-4xl mx-auto leading-relaxed">
                Every day you wait is money left on the table. Join thousands of veterans 
                who've maximized their benefits with our expert guidance.
              </p>
            </div>

            {/* Primary CTA */}
            <div className="space-y-6 pt-8">
              <Button
                onClick={() => setLocation("/start-claim")}
                className="bg-gradient-to-r from-gold via-yellow-400 to-gold text-navy font-black text-2xl px-16 py-8 rounded-2xl shadow-2xl transform hover:scale-105 transition-all duration-300 hover:shadow-gold/50 group"
              >
                START MY CLAIM TODAY
                <ArrowRight className="ml-4 h-8 w-8 group-hover:translate-x-2 transition-transform" />
              </Button>
              
              <p className="text-lg text-gold font-semibold">
                ✓ Free consultation • ✓ No upfront costs • ✓ 98% success rate
              </p>
            </div>
          </div>

          {/* Contact Options */}
          <div className="grid md:grid-cols-3 gap-8 pt-16 border-t border-gold/20">
            <div className="text-center space-y-4 group hover:bg-white/5 rounded-2xl p-6 transition-all duration-300">
              <div className="bg-gradient-to-br from-gold to-yellow-400 p-4 rounded-2xl mx-auto w-fit shadow-xl group-hover:scale-110 transition-transform duration-300">
                <Phone className="h-8 w-8 text-navy" />
              </div>
              <h3 className="text-xl font-bold text-gold">Call Now</h3>
              <p className="text-gray-300 font-medium">Speak with a VA expert today</p>
              <div className="text-2xl font-black text-white">1-800-VETERAN</div>
            </div>

            <div className="text-center space-y-4 group hover:bg-white/5 rounded-2xl p-6 transition-all duration-300">
              <div className="bg-gradient-to-br from-gold to-yellow-400 p-4 rounded-2xl mx-auto w-fit shadow-xl group-hover:scale-110 transition-transform duration-300">
                <Mail className="h-8 w-8 text-navy" />
              </div>
              <h3 className="text-xl font-bold text-gold">Email Us</h3>
              <p className="text-gray-300 font-medium">Get started with our online form</p>
              <div className="text-lg font-bold text-white">info@valorassist.com</div>
            </div>

            <div className="text-center space-y-4 group hover:bg-white/5 rounded-2xl p-6 transition-all duration-300">
              <div className="bg-gradient-to-br from-gold to-yellow-400 p-4 rounded-2xl mx-auto w-fit shadow-xl group-hover:scale-110 transition-transform duration-300">
                <Clock className="h-8 w-8 text-navy" />
              </div>
              <h3 className="text-xl font-bold text-gold">24/7 Support</h3>
              <p className="text-gray-300 font-medium">We're here when you need us</p>
              <div className="text-lg font-bold text-white">Always Available</div>
            </div>
          </div>

          {/* Final Trust Message */}
          <div className="pt-16">
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-gold/20 max-w-4xl mx-auto">
              <h3 className="text-3xl font-bold text-gold mb-4">
                Veteran-Owned. Veteran-Operated. Veteran-Focused.
              </h3>
              <p className="text-xl text-gray-200 font-medium leading-relaxed">
                We understand your service because we've served too. Our mission is simple: 
                get you every benefit you've earned through your dedication to our country.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
