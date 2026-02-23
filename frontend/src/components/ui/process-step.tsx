import { LucideIcon, CheckCircle } from "lucide-react";

interface ProcessStepProps {
  step: number;
  icon: LucideIcon;
  title: string;
  description: string;
  details: string[];
}

export function ProcessStep({ step, icon: Icon, title, description, details }: ProcessStepProps) {
  return (
    <div className="relative group">
      {/* Step Number */}
      <div className="absolute -top-4 -left-4 bg-gradient-to-br from-gold to-yellow-500 text-navy font-black text-2xl w-12 h-12 rounded-full flex items-center justify-center shadow-2xl z-10 group-hover:scale-110 transition-transform duration-300">
        {step}
      </div>

      {/* Main Card */}
      <div className="bg-white border-2 border-gray-100 rounded-2xl p-8 h-full shadow-lg hover:shadow-2xl transition-all duration-500 hover:-translate-y-2 military-border hover:border-gold/50">
        {/* Icon */}
        <div className="bg-gradient-to-br from-navy to-navy-light p-4 rounded-xl w-fit mb-6 shadow-xl group-hover:shadow-navy/50 transition-all duration-300">
          <Icon className="h-8 w-8 text-gold" />
        </div>

        {/* Content */}
        <div className="space-y-4">
          <h3 className="text-2xl font-black text-navy leading-tight group-hover:text-navy-dark transition-colors">
            {title}
          </h3>
          <p className="text-gray-600 font-medium leading-relaxed">
            {description}
          </p>

          {/* Details List */}
          <ul className="space-y-3 pt-4">
            {details.map((detail, index) => (
              <li key={index} className="flex items-start group-hover:translate-x-1 transition-transform duration-300">
                <CheckCircle className="h-5 w-5 text-gold mt-0.5 mr-3 flex-shrink-0" />
                <span className="text-sm text-gray-700 font-semibold">{detail}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Connecting Line (except for last item) */}
      {step < 4 && (
        <div className="hidden lg:block absolute top-16 -right-4 w-8 h-0.5 bg-gradient-to-r from-gold to-transparent"></div>
      )}
    </div>
  );
}