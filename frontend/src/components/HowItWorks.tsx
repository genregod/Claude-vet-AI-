import { FileSearch, Users, FileText, Trophy } from "lucide-react";

export function HowItWorks() {
  const steps = [
    {
      icon: FileSearch,
      title: "Free Case Review",
      description: "Our expert team analyzes your service records and medical history to identify all eligible claims.",
      details: [
        "Comprehensive service record analysis",
        "Medical history evaluation", 
        "Benefit eligibility assessment",
        "Custom strategy development"
      ]
    },
    {
      icon: Users,
      title: "Expert Guidance",
      description: "Work directly with VA-accredited representatives and former VA employees who know the system.",
      details: [
        "VA-accredited representation",
        "Former VA employee insights",
        "Personalized claim strategy",
        "Direct expert communication"
      ]
    },
    {
      icon: FileText,
      title: "Complete Documentation",
      description: "We handle all paperwork, evidence gathering, and submission to maximize your claim's success.",
      details: [
        "Professional form completion",
        "Medical evidence coordination",
        "Supporting documentation",
        "Timely submission management"
      ]
    },
    {
      icon: Trophy,
      title: "Maximize Benefits",
      description: "Get the highest possible rating and benefits you've earned through your honorable service.",
      details: [
        "Optimal rating achievement",
        "Backdated compensation",
        "Secondary condition claims",
        "Ongoing support & appeals"
      ]
    }
  ];

  return (
    <section id="how-it-works" className="py-24 bg-gradient-to-b from-gray-50 to-white overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header with modern design */}
        <div className="text-center mb-20">
          <div className="inline-flex items-center glass-card rounded-full px-6 py-2 mb-6">
            <span className="text-navy font-bold text-sm tracking-wider">SIMPLE & EFFECTIVE</span>
          </div>
          <h2 className="text-5xl font-black mb-6">
            <span className="gradient-text">Your Path to Benefits</span>
            <span className="block text-gray-800 text-3xl mt-3 font-medium">Four Steps to Success</span>
          </h2>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto leading-relaxed">
            Our streamlined process removes the guesswork and complexity from VA claims
          </p>
        </div>

        {/* Process Steps with connecting lines */}
        <div className="relative">
          {/* Connecting line for desktop */}
          <div className="hidden lg:block absolute top-20 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-gold to-transparent"></div>
          
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8 mb-16">
            {steps.map((step, index) => (
              <div key={index} className="relative">
                {/* Step number with modern styling */}
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-br from-gold to-yellow-400 text-navy font-black text-xl w-10 h-10 rounded-full flex items-center justify-center shadow-lg z-20">
                  {index + 1}
                </div>
                
                <div className="glass-card rounded-2xl p-6 h-full hover:shadow-xl transition-all duration-300 border border-gray-100 hover:border-gold/30">
                  {/* Icon */}
                  <div className="bg-gradient-to-br from-navy/10 to-navy/5 p-4 rounded-xl w-fit mx-auto mb-4 mt-8">
                    <step.icon className="h-8 w-8 text-navy" />
                  </div>
                  
                  {/* Content */}
                  <h3 className="text-xl font-bold text-center gradient-text mb-3">{step.title}</h3>
                  <p className="text-gray-600 text-sm text-center mb-4 leading-relaxed">{step.description}</p>
                  
                  {/* Details with subtle design */}
                  <ul className="space-y-2">
                    {step.details.map((detail, i) => (
                      <li key={i} className="flex items-start">
                        <div className="w-1.5 h-1.5 bg-gold rounded-full mt-1.5 mr-2 flex-shrink-0"></div>
                        <span className="text-xs text-gray-700">{detail}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Success Stats with modern design */}
        <div className="relative mt-20">
          {/* Background decoration */}
          <div className="absolute -inset-4 bg-gradient-to-r from-gold/10 to-navy/10 rounded-3xl blur-2xl"></div>
          
          <div className="relative glass-card rounded-3xl p-12 overflow-hidden">
            {/* Pattern overlay */}
            <div className="absolute inset-0 hero-pattern opacity-5"></div>
            
            <div className="relative z-10">
              <div className="text-center mb-12">
                <h3 className="text-4xl font-black gradient-text mb-4">Proven Track Record</h3>
                <p className="text-xl text-gray-600">Real results for real veterans</p>
              </div>
              
              <div className="grid md:grid-cols-4 gap-8">
                {[
                  { value: "98%", label: "Success Rate", sublabel: "Claims Approved" },
                  { value: "$48K", label: "Average Award", sublabel: "Per Veteran" },
                  { value: "60", label: "Days Average", sublabel: "Processing Time" },
                  { value: "25K+", label: "Veterans Served", sublabel: "Since 2015" }
                ].map((stat, index) => (
                  <div key={index} className="text-center group">
                    <div className="relative">
                      <div className="text-5xl font-black gradient-text-gold group-hover:scale-110 transition-transform duration-300">
                        {stat.value}
                      </div>
                      <div className="text-lg font-semibold text-navy mt-2">{stat.label}</div>
                      <div className="text-sm text-gray-600">{stat.sublabel}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
