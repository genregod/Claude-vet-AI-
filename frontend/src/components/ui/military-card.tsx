
import { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { LucideIcon, ArrowRight } from "lucide-react";

interface MilitaryCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  features: string[];
  learnMoreLink: string;
  children?: ReactNode;
}

export function MilitaryCard({ icon: Icon, title, description, features, learnMoreLink }: MilitaryCardProps) {
  return (
    <Card className="h-full group hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-3 military-border bg-white border-2 border-gray-100 hover:border-gold/50 hover:bg-gradient-to-br hover:from-white hover:to-gold/5">
      <CardHeader className="pb-6">
        <div className="flex items-start mb-6">
          <div className="bg-gradient-to-br from-gold via-yellow-400 to-yellow-500 p-4 rounded-2xl mr-4 shadow-2xl group-hover:shadow-gold/50 transition-all duration-500 group-hover:scale-110">
            <Icon className="h-10 w-10 text-navy" />
          </div>
          <div className="flex-1">
            <CardTitle className="text-2xl font-black text-navy mb-3 leading-tight group-hover:text-navy-dark transition-colors">
              {title}
            </CardTitle>
          </div>
        </div>
        <CardDescription className="text-gray-600 text-lg leading-relaxed font-medium">
          {description}
        </CardDescription>
      </CardHeader>
      
      <CardContent className="pt-0">
        <div className="mb-8">
          <ul className="space-y-4">
            {features.map((feature, i) => (
              <li key={i} className="flex items-start group-hover:translate-x-1 transition-transform duration-300">
                <div className="w-3 h-3 bg-gradient-to-br from-gold to-yellow-500 rounded-full mt-2.5 mr-4 flex-shrink-0 shadow-lg"></div>
                <span className="text-base text-gray-700 font-semibold leading-relaxed">{feature}</span>
              </li>
            ))}
          </ul>
        </div>
        
        <a
          href={learnMoreLink}
          className="inline-flex items-center text-navy font-black text-base hover:text-gold transition-colors duration-300 group-hover:translate-x-2 transform group"
        >
          Learn More
          <ArrowRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform duration-300" />
        </a>
      </CardContent>
    </Card>
  );
}
