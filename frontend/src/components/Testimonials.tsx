
import { Star, Quote, Shield } from "lucide-react";

export function Testimonials() {
  const testimonials = [
    {
      name: "Master Sergeant John Rodriguez",
      branch: "U.S. Army (Retired)",
      service: "22 Years of Service",
      rating: "100% P&T",
      quote: "After 3 years of fighting the VA alone, ValorAssist got me 100% P&T in just 4 months. They knew exactly what evidence was needed and how to present it. Life-changing.",
      image: "🪖"
    },
    {
      name: "Petty Officer Sarah Chen", 
      branch: "U.S. Navy (Veteran)",
      service: "8 Years of Service",
      rating: "90% Service Connected",
      quote: "The team understood my complex medical conditions and connected them to my service. They turned my 30% rating into 90%. I finally got the benefits I earned.",
      image: "⚓"
    },
    {
      name: "Staff Sergeant Mike Thompson",
      branch: "U.S. Air Force (Retired)",
      service: "16 Years of Service", 
      rating: "80% Individual Unemployability",
      quote: "ValorAssist didn't just file paperwork - they fought for me like I was family. Their knowledge of VA regulations is unmatched. Highly recommend to any veteran.",
      image: "✈️"
    }
  ];

  return (
    <section id="testimonials" className="py-24 bg-gradient-to-br from-navy via-navy-light to-navy-dark text-white overflow-hidden relative">
      {/* Background Pattern */}
      <div className="absolute inset-0 chevron-bg opacity-5"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center bg-gold/20 border border-gold/50 rounded-full px-6 py-2 mb-6 backdrop-blur-sm">
            <Shield className="h-5 w-5 text-gold mr-2" />
            <span className="text-gold font-bold text-sm">VETERAN SUCCESS STORIES</span>
          </div>
          <h2 className="text-5xl font-black mb-6 leading-tight">
            Heroes Helping
            <span className="text-gold block">Heroes Succeed</span>
          </h2>
          <p className="text-xl text-gray-300 max-w-3xl mx-auto leading-relaxed font-medium">
            Real veterans sharing how we helped them get the benefits they earned through their service.
          </p>
        </div>

        {/* Testimonials Grid */}
        <div className="grid lg:grid-cols-3 gap-8 mb-16">
          {testimonials.map((testimonial, index) => (
            <div 
              key={index}
              className="bg-white/10 backdrop-blur-sm border border-gold/20 rounded-2xl p-8 hover:bg-white/15 transition-all duration-500 hover:-translate-y-2 hover:shadow-2xl hover:shadow-gold/20"
            >
              {/* Quote Icon */}
              <div className="text-gold/50 mb-6">
                <Quote className="h-12 w-12" />
              </div>

              {/* Rating Stars */}
              <div className="flex items-center mb-6">
                {[...Array(5)].map((_, i) => (
                  <Star key={i} className="h-6 w-6 text-gold fill-gold" />
                ))}
              </div>

              {/* Quote */}
              <blockquote className="text-lg leading-relaxed mb-8 font-medium text-gray-200">
                "{testimonial.quote}"
              </blockquote>

              {/* Veteran Info */}
              <div className="border-t border-gold/20 pt-6">
                <div className="flex items-center space-x-4">
                  <div className="text-4xl">{testimonial.image}</div>
                  <div>
                    <div className="font-bold text-white text-lg">{testimonial.name}</div>
                    <div className="text-gold font-semibold text-sm">{testimonial.branch}</div>
                    <div className="text-gray-400 text-sm">{testimonial.service}</div>
                  </div>
                </div>
                <div className="mt-4 bg-gold/20 rounded-full px-4 py-2 w-fit">
                  <span className="text-gold font-bold text-sm">{testimonial.rating}</span>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Trust Indicators */}
        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-8 border border-gold/20">
          <div className="text-center mb-8">
            <h3 className="text-3xl font-bold text-gold mb-2">Trusted by Veterans Nationwide</h3>
            <p className="text-gray-300">Join thousands of veterans who've gotten the benefits they deserve</p>
          </div>
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <div>
              <div className="text-4xl font-black text-gold mb-2">4.9★</div>
              <div className="text-white font-semibold">Average Rating</div>
              <div className="text-sm text-gray-400">1,200+ Reviews</div>
            </div>
            <div>
              <div className="text-4xl font-black text-gold mb-2">98%</div>
              <div className="text-white font-semibold">Success Rate</div>
              <div className="text-sm text-gray-400">Claims Approved</div>
            </div>
            <div>
              <div className="text-4xl font-black text-gold mb-2">15K+</div>
              <div className="text-white font-semibold">Veterans Served</div>
              <div className="text-sm text-gray-400">Since 2019</div>
            </div>
            <div>
              <div className="text-4xl font-black text-gold mb-2">$180M</div>
              <div className="text-white font-semibold">Benefits Secured</div>
              <div className="text-sm text-gray-400">For Our Veterans</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
