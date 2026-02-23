
import { Shield, Phone, Mail, MapPin } from "lucide-react";

export function Footer() {
  return (
    <footer className="bg-gradient-to-br from-gray-900 to-gray-950 text-white relative overflow-hidden">
      {/* Background pattern */}
      <div className="absolute inset-0 hero-pattern opacity-5"></div>
      
      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Main Footer Content */}
        <div className="py-16 grid lg:grid-cols-4 md:grid-cols-2 gap-12">
          {/* Company Info */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <div className="bg-gradient-to-br from-gold to-yellow-400 p-3 rounded-xl shadow-lg transform hover:scale-105 transition-transform">
                  <Shield className="h-10 w-10 text-navy" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-gold rounded-full animate-pulse"></div>
              </div>
              <div>
                <h3 className="text-3xl font-black">ValorAssist</h3>
                <p className="text-gold font-medium">Excellence in Veteran Claims</p>
              </div>
            </div>
            <p className="text-gray-400 leading-relaxed max-w-md">
              Dedicated to helping veterans secure the benefits they've earned through their service. 
              We combine cutting-edge technology with compassionate, veteran-focused support.
            </p>
            <div className="space-y-3">
              <a href="tel:1-800-838-3726" className="flex items-center space-x-3 hover:text-gold transition-colors group">
                <div className="bg-gray-800 p-2.5 rounded-lg group-hover:bg-gold/20 transition-colors">
                  <Phone className="h-5 w-5 text-gold" />
                </div>
                <span className="font-medium">1-800-VETERAN</span>
              </a>
              <a href="mailto:info@valorassist.com" className="flex items-center space-x-3 hover:text-gold transition-colors group">
                <div className="bg-gray-800 p-2.5 rounded-lg group-hover:bg-gold/20 transition-colors">
                  <Mail className="h-5 w-5 text-gold" />
                </div>
                <span className="font-medium">info@valorassist.com</span>
              </a>
              <div className="flex items-center space-x-3">
                <div className="bg-gray-800 p-2.5 rounded-lg">
                  <MapPin className="h-5 w-5 text-gold" />
                </div>
                <span className="font-medium">Serving Veterans Nationwide</span>
              </div>
            </div>
          </div>

          {/* Services */}
          <div className="space-y-6">
            <h4 className="text-xl font-bold gradient-text-gold">Our Services</h4>
            <nav className="space-y-2">
              {[
                "Initial Claims",
                "Appeals & Reviews",
                "Medical Evidence",
                "Rating Increases",
                "Housing Benefits",
                "Education Benefits"
              ].map((service) => (
                <a 
                  key={service}
                  href={`#${service.toLowerCase().replace(/ & /g, '-').replace(/ /g, '-')}`} 
                  className="block text-gray-400 hover:text-gold transition-colors py-1"
                >
                  {service}
                </a>
              ))}
            </nav>
          </div>

          {/* Resources */}
          <div className="space-y-6">
            <h4 className="text-xl font-bold gradient-text-gold">Resources</h4>
            <nav className="space-y-2">
              {[
                "VA Benefits Guide",
                "Disability Calculator",
                "Claims Checklist",
                "Success Stories",
                "FAQ",
                "Contact Support"
              ].map((resource) => (
                <a 
                  key={resource}
                  href="#" 
                  className="block text-gray-400 hover:text-gold transition-colors py-1"
                >
                  {resource}
                </a>
              ))}
            </nav>
          </div>
        </div>

        {/* Trust Indicators with modern design */}
        <div className="py-12 border-t border-gray-800">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "A+", label: "BBB Rating", sublabel: "Accredited Business" },
              { value: "VA", label: "Certified", sublabel: "Accredited Agents" },
              { value: "5.0", label: "Stars", sublabel: "500+ Reviews" },
              { value: "100%", label: "Veteran", sublabel: "Owned & Operated" }
            ].map((item, index) => (
              <div key={index} className="text-center group cursor-pointer">
                <div className="bg-gray-800/50 rounded-xl p-6 hover:bg-gold/10 transition-all duration-300 hover:scale-105">
                  <div className="text-3xl font-black gradient-text-gold mb-1">{item.value}</div>
                  <div className="text-sm font-semibold text-white">{item.label}</div>
                  <div className="text-xs text-gray-500">{item.sublabel}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Bottom Bar with modern styling */}
        <div className="py-6 border-t border-gray-800">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="text-sm text-gray-500">
              © 2024 ValorAssist. All rights reserved. Proudly serving those who served.
            </div>
            <div className="flex space-x-6 text-sm text-gray-500">
              <a href="#" className="hover:text-gold transition-colors">Privacy Policy</a>
              <a href="#" className="hover:text-gold transition-colors">Terms of Service</a>
              <a href="#" className="hover:text-gold transition-colors">Disclaimer</a>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
