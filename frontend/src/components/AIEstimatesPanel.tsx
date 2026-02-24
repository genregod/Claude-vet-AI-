/**
 * AI Estimates Panel
 * 
 * Displays real-time AI-generated disability rating estimates,
 * compensation figures, backpay, and decision timeline as the
 * veteran fills out the questionnaire.
 */

import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  TrendingUp,
  DollarSign,
  Clock,
  BarChart3,
  Shield,
  AlertCircle,
  CheckCircle2,
  Bot,
} from "lucide-react";
import type { AIEstimates } from "@/lib/claimsApi";

interface AIEstimatesPanelProps {
  estimates: AIEstimates;
  isLoading?: boolean;
}

function formatCurrency(amount: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDays(days: number): string {
  if (days <= 0) return "—";
  if (days < 30) return `${days} days`;
  const months = Math.round(days / 30);
  return `~${months} month${months === 1 ? "" : "s"}`;
}

function ConfidenceBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    low: "bg-yellow-100 text-yellow-800 border-yellow-300",
    moderate: "bg-blue-100 text-blue-800 border-blue-300",
    high: "bg-green-100 text-green-800 border-green-300",
  };
  return (
    <Badge variant="outline" className={colors[level] || colors.low}>
      {level.charAt(0).toUpperCase() + level.slice(1)} Confidence
    </Badge>
  );
}

function ConnectionStrength({ strength }: { strength: string }) {
  const icon =
    strength === "strong" ? (
      <CheckCircle2 className="h-3 w-3 text-green-600" />
    ) : strength === "moderate" ? (
      <AlertCircle className="h-3 w-3 text-yellow-600" />
    ) : (
      <AlertCircle className="h-3 w-3 text-red-500" />
    );
  return (
    <span className="inline-flex items-center gap-1 text-xs">
      {icon}
      {strength}
    </span>
  );
}

export function AIEstimatesPanel({ estimates, isLoading }: AIEstimatesPanelProps) {
  const hasEstimates = estimates.estimated_combined_rating > 0;

  return (
    <Card className="border-navy/20 bg-gradient-to-b from-white to-gray-50 shadow-lg sticky top-4">
      <CardContent className="p-5 space-y-5">
        {/* Header */}
        <div className="flex items-center gap-2">
          <div className="bg-navy p-2 rounded-lg">
            <Bot className="h-5 w-5 text-gold" />
          </div>
          <div>
            <h3 className="font-bold text-navy text-sm">AI Claims Analysis</h3>
            <p className="text-xs text-gray-500">Updated in real-time</p>
          </div>
          {isLoading && (
            <div className="ml-auto">
              <div className="h-4 w-4 border-2 border-navy/30 border-t-navy rounded-full animate-spin" />
            </div>
          )}
        </div>

        <Separator />

        {!hasEstimates ? (
          <div className="text-center py-6 space-y-2">
            <BarChart3 className="h-10 w-10 text-gray-300 mx-auto" />
            <p className="text-sm text-gray-500 font-medium">
              Complete the disabilities section to see your estimated rating
            </p>
            <p className="text-xs text-gray-400">
              Your answers are evaluated by our AI in real-time
            </p>
          </div>
        ) : (
          <>
            {/* Combined Rating */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-navy" />
                  <span className="text-sm font-semibold text-gray-700">
                    Estimated Combined Rating
                  </span>
                </div>
                <ConfidenceBadge level={estimates.confidence_level} />
              </div>
              <div className="flex items-end gap-2">
                <span className="text-4xl font-black text-navy">
                  {estimates.estimated_combined_rating}%
                </span>
              </div>
              <Progress
                value={estimates.estimated_combined_rating}
                className="h-3"
              />
            </div>

            <Separator />

            {/* Compensation Estimates */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-green-50 rounded-xl p-3 border border-green-100">
                <div className="flex items-center gap-1.5 mb-1">
                  <DollarSign className="h-3.5 w-3.5 text-green-700" />
                  <span className="text-xs font-semibold text-green-800">
                    Monthly
                  </span>
                </div>
                <span className="text-lg font-bold text-green-900">
                  {formatCurrency(estimates.estimated_monthly_compensation)}
                </span>
              </div>
              <div className="bg-blue-50 rounded-xl p-3 border border-blue-100">
                <div className="flex items-center gap-1.5 mb-1">
                  <DollarSign className="h-3.5 w-3.5 text-blue-700" />
                  <span className="text-xs font-semibold text-blue-800">
                    Est. Backpay
                  </span>
                </div>
                <span className="text-lg font-bold text-blue-900">
                  {formatCurrency(estimates.estimated_backpay)}
                </span>
              </div>
            </div>

            {/* Decision Timeline */}
            <div className="bg-amber-50 rounded-xl p-3 border border-amber-100">
              <div className="flex items-center gap-1.5 mb-1">
                <Clock className="h-3.5 w-3.5 text-amber-700" />
                <span className="text-xs font-semibold text-amber-800">
                  Est. Decision Timeline
                </span>
              </div>
              <span className="text-lg font-bold text-amber-900">
                {formatDays(estimates.estimated_decision_timeline_days)}
              </span>
              <p className="text-xs text-amber-700 mt-0.5">
                Based on current VA processing times
              </p>
            </div>

            <Separator />

            {/* Individual Condition Ratings */}
            {estimates.individual_ratings.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Shield className="h-4 w-4 text-navy" />
                  <span className="text-sm font-semibold text-gray-700">
                    Individual Ratings
                  </span>
                </div>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {estimates.individual_ratings.map((rating, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between bg-gray-50 rounded-lg p-2.5 border"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-xs font-medium text-gray-800 truncate">
                          {rating.condition}
                        </p>
                        <ConnectionStrength
                          strength={rating.service_connection_strength}
                        />
                      </div>
                      <div className="ml-2 text-right">
                        <span className="text-sm font-bold text-navy">
                          {rating.estimated_rating}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Notes */}
            {estimates.notes.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  AI Notes
                </span>
                {estimates.notes.map((note, idx) => (
                  <p key={idx} className="text-xs text-gray-600 leading-relaxed">
                    - {note}
                  </p>
                ))}
              </div>
            )}
          </>
        )}

        {/* Disclaimer */}
        <div className="bg-gray-100 rounded-lg p-2.5">
          <p className="text-[10px] text-gray-500 leading-relaxed">
            These are AI-generated estimates for informational purposes only.
            Actual VA ratings are determined by the Rating Veterans Service
            Representative (RVSR) based on your complete evidence package.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
