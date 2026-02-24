import { FileText, Gavel, GraduationCap, Home, ClipboardList, Stethoscope } from "lucide-react";

export function Services() {
  const services = [
    {
      icon: ClipboardList,
      title: "Initial Claims",
      description: "Complete support for filing your first VA disability claim with maximum impact.",
      features: [
        "Comprehensive C&P exam preparation",
        "Complete medical record analysis",
        "Evidence-based claim strategy",
        "Expert form completion & submission"
      ],
      learnMoreLink: "#initial-claims"
    },
    {
      icon: Gavel,
      title: "Appeals & Reviews", 
      description: "Fight denied claims with our proven appeal strategies and legal expertise.",
      features: [
        "Higher-Level Review preparation",
        "Board of Veterans' Appeals representation",
        "New evidence development & submission",
        "Court of Appeals for Veterans Claims"
      ],
      learnMoreLink: "#appeals"
    },
    {
      icon: Stethoscope,
      title: "Medical Evidence",
      description: "Professional medical evidence gathering and nexus letter preparation.",
      features: [
        "Independent medical examinations",
        "Nexus letter coordination",
        "Medical record organization",
        "Expert medical testimony"
      ],
      learnMoreLink: "#medical-evidence"
    },
    {
      icon: FileText,
      title: "Increase Ratings",
      description: "Maximize your disability rating with thorough reassessment strategies.",
      features: [
        "Rating increase evaluation",
        "Worsened condition documentation",
        "Secondary condition claims",
        "Individual Unemployability pursuit"
      ],
      learnMoreLink: "#increase-ratings"
    },
    {
      icon: Home,
      title: "Housing Benefits",
      description: "Access VA home loans and adaptive housing grants for disabled veterans.",
      features: [
        "VA home loan certification",
        "Specially Adapted Housing grants",
        "Special Housing Adaptation grants",
        "Temporary Residence Adaptation"
      ],
      learnMoreLink: "#housing"
    },
    {
      icon: GraduationCap,
      title: "Education Benefits",
      description: "Navigate GI Bill benefits and vocational rehabilitation programs effectively.",
      features: [
        "GI Bill benefit optimization",
        "Vocational Rehabilitation & Employment",
        "Dependents' education benefits",
        "Yellow Ribbon Program guidance"
      ],
      learnMoreLink: "#education"
    }
  ];

  return (
    <section id="services" className="py-24 bg-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header with modern design */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center glass-card rounded-full px-6 py-2 mb-6">
            <span className="text-navy font-bold text-sm tracking-wider">COMPREHENSIVE SUPPORT</span>
          </div>
          <h2 className="text-5xl font-black mb-6">
            <span className="gradient-text">VA Claims Services</span>
            <span className="block text-gray-800 text-3xl mt-3 font-medium">Tailored to Your Needs</span>
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
            Expert guidance at every step of your VA claims journey - from initial filing to successful resolution
          </p>
        </div>

        {/* Services Grid with modern card design */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
          {services.map((service, index) => (
            <div key={index} className="group relative">
              <div className="absolute inset-0 bg-gradient-to-r from-gold/20 to-navy/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
              <div className="relative bg-navy rounded-2xl p-8 h-full shadow-xl hover:shadow-2xl transition-all duration-300">
                {/* Icon */}
                <div className="bg-gold p-4 rounded-xl w-fit mb-6 shadow-lg">
                  <service.icon className="h-8 w-8 text-navy" />
                </div>
                
                {/* Content */}
                <h3 className="text-2xl font-bold text-white mb-3">{service.title}</h3>
                <p className="text-gray-200 mb-6 leading-relaxed">{service.description}</p>
                
                {/* Features with cleaner design */}
                <ul className="space-y-3 mb-8">
                  {service.features.map((feature, i) => (
                    <li key={i} className="flex items-start">
                      <div className="w-2 h-2 bg-gold rounded-full mt-2 mr-3 flex-shrink-0"></div>
                      <span className="text-sm text-gray-100">{feature}</span>
                    </li>
                  ))}
                </ul>
                
                {/* CTA with hover effect */}
                <a
                  href={service.learnMoreLink}
                  className="inline-flex items-center text-gold font-bold hover:text-yellow-400 transition-colors group/link"
                >
                  Learn More
                  <svg className="w-4 h-4 ml-1 transform group-hover/link:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>
              </div>
            </div>
          ))}
        </div>

        {/* Bottom CTA with modern design */}
        <div className="mt-20 relative">
          <div className="absolute inset-0 bg-gradient-to-r from-gold/20 to-navy/20 rounded-3xl blur-2xl"></div>
          <div className="relative bg-gradient-to-br from-navy to-navy-dark rounded-3xl p-12 text-white text-center overflow-hidden">
            {/* Background pattern */}
            <div className="absolute inset-0 hero-pattern opacity-10"></div>
            
            <div className="relative z-10">
              <h3 className="text-4xl font-bold mb-4">
                Ready to Maximize Your VA Benefits?
              </h3>
              <p className="text-xl mb-8 text-gold/90 max-w-2xl mx-auto">
                Join thousands of veterans who've successfully claimed their rightful benefits with our expert guidance
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                <button className="bg-gradient-to-r from-gold to-yellow-400 text-navy font-bold text-lg px-8 py-4 rounded-2xl shadow-2xl transform hover:scale-105 transition-all duration-300 hover:shadow-gold/50">
                  Start My Free Evaluation
                </button>
                <span className="text-gold/80 font-medium">No obligation • 100% confidential</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
