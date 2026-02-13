"""
Valor Assist — AI Claims Evaluator & Agent Router

Background AI evaluation engine that:
  1. Analyzes questionnaire answers as they're submitted
  2. Estimates disability rating (combined VA math)
  3. Estimates monthly compensation, backpay, and decision timeline
  4. Routes completed claims through the agent pipeline:
     Claims Agent → Supervisor Agent → Claims Assistant → FDC

Uses the Anthropic SDK with structured XML prompts to produce
JSON-structured estimates from the claim questionnaire data.
"""

from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime

import anthropic

from app.config import settings
from app.claim_session import (
    ClaimSession, ClaimStatus, AgentRole, AIEstimates,
    VA_CLAIMABLE_CONDITIONS, ALL_CLAIMABLE_CONDITIONS,
)
from app.vector_store import VectorStore

logger = logging.getLogger(__name__)


# ── VA Compensation Rates (2024) — approximate monthly rates ─────────

VA_COMPENSATION_RATES_MONTHLY = {
    0: 0.00,
    10: 171.23,
    20: 338.49,
    30: 524.31,
    40: 755.28,
    50: 1075.16,
    60: 1361.88,
    70: 1716.28,
    80: 1995.01,
    90: 2241.91,
    100: 3737.85,
}


# ── VA Combined Rating Math ─────────────────────────────────────────

def calculate_combined_rating(individual_ratings: list[int]) -> int:
    """
    Calculate combined VA disability rating using VA bilateral math.
    
    VA uses the "whole person" theory: each subsequent disability is
    applied to the remaining "healthy" percentage, not stacked.
    
    Example: 50% + 30% = 50 + (30% of remaining 50%) = 50 + 15 = 65%
    Rounded to nearest 10: 70%
    """
    if not individual_ratings:
        return 0
    
    # Sort descending — highest rating applied first
    sorted_ratings = sorted(individual_ratings, reverse=True)
    
    combined = 0.0
    for rating in sorted_ratings:
        remaining = 100.0 - combined
        combined += (remaining * rating / 100.0)
    
    # VA rounds to nearest 10
    combined_rounded = round(combined / 10) * 10
    return min(int(combined_rounded), 100)


def estimate_backpay(
    monthly_rate: float,
    service_end_date: str | None = None,
    claim_date: str | None = None,
) -> float:
    """
    Estimate potential backpay based on effective date.
    
    Backpay = monthly_rate × months_between(effective_date, estimated_decision)
    Effective date is typically the later of: service discharge + 1 year,
    or date of claim filing. If filed within 1 year of discharge,
    effective date = day after discharge.
    """
    try:
        if service_end_date:
            end_date = datetime.strptime(service_end_date, "%Y-%m-%d")
        else:
            end_date = datetime.now()
        
        # If claim filed within 1 year of discharge, backpay from discharge
        now = datetime.now()
        months_since = max(1, (now.year - end_date.year) * 12 + (now.month - end_date.month))
        
        # Cap at reasonable estimate (36 months typical max for initial claims)
        months_backpay = min(months_since, 36)
        
        return round(monthly_rate * months_backpay, 2)
    except (ValueError, TypeError):
        # If dates can't be parsed, estimate 12 months
        return round(monthly_rate * 12, 2)


def estimate_decision_timeline(
    num_conditions: int,
    has_medical_evidence: bool = False,
    is_presumptive: bool = False,
    claim_type: str = "initial",
) -> int:
    """
    Estimate VA decision timeline in days.
    
    Based on VA published averages:
    - Initial claims: 100-150 days
    - Supplemental claims: 60-90 days  
    - Higher-Level Review: 90-125 days
    - Board appeal: 365+ days
    - FDC (Fully Developed Claim): 30-60% faster
    """
    base_days = {
        "initial": 125,
        "supplemental": 75,
        "increase": 100,
        "hlr": 110,
        "board_appeal": 400,
    }
    
    days = base_days.get(claim_type, 125)
    
    # More conditions = longer processing
    days += max(0, (num_conditions - 2)) * 15
    
    # Strong medical evidence reduces time
    if has_medical_evidence:
        days = int(days * 0.7)
    
    # Presumptive conditions are faster
    if is_presumptive:
        days = int(days * 0.6)
    
    return max(30, days)


# ── Claim Evaluation Prompt ──────────────────────────────────────────

CLAIM_EVALUATION_PROMPT = """\
<role>
You are an expert VA disability claims analyst. Analyze the veteran's
questionnaire answers to estimate disability ratings, compensation,
and claim strategy. You must respond ONLY with valid JSON.
</role>

<veteran_data>
{veteran_data}
</veteran_data>

<va_rating_criteria>
VA disability ratings are assigned based on the VA Schedule for Rating
Disabilities (VASRD, 38 CFR Part 4). Key rating levels:
- 0% (service-connected but non-compensable)
- 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%, 100%

Common condition ratings:
- Tinnitus: 10% (maximum schedular)
- Hearing loss: 0-100% (based on audiometric testing)
- PTSD/Mental health: 0%, 10%, 30%, 50%, 70%, 100% (based on GAF/severity)
- Back conditions: 10-40% (based on range of motion)
- Knee conditions: 10-30% (based on range of motion/instability)
- Migraines: 0%, 10%, 30%, 50% (based on frequency/severity)
- Sleep apnea: 0%, 30%, 50%, 100% (based on treatment required)
- Radiculopathy: 10-60% (based on nerve group/severity)
- Skin conditions: 0-60% (based on body percentage affected)
- GERD: 10-60% (based on severity)
- Hypertension: 0-60% (based on readings)
- Diabetes: 10-100% (based on treatment/complications)
</va_rating_criteria>

<instructions>
Based on the veteran's reported conditions and circumstances, estimate:
1. Individual disability ratings for each claimed condition
2. Combined rating using VA bilateral math
3. Monthly compensation estimate
4. Potential service connection strength (strong/moderate/weak)

Respond with ONLY this JSON structure (no markdown, no explanation):
{{
  "individual_ratings": [
    {{
      "condition": "condition name",
      "estimated_rating": 30,
      "rationale": "brief reason",
      "service_connection_strength": "strong|moderate|weak",
      "applicable_cfr": "38 CFR section"
    }}
  ],
  "notes": ["key observation 1", "key observation 2"],
  "claim_strategy": "initial|supplemental|increase",
  "confidence_level": "low|moderate|high",
  "recommended_evidence": ["evidence type 1", "evidence type 2"]
}}
</instructions>

<context>
{context}
</context>
"""


# ── Supervisor Review Prompt ─────────────────────────────────────────

SUPERVISOR_REVIEW_PROMPT = """\
<role>
You are a senior VA claims supervisor agent reviewing a claims agent's
analysis. Your job is to validate the assessment, identify issues, and
prepare the claim for a claims assistant to convert into a Fully
Developed Claim (FDC).
</role>

<claims_agent_analysis>
{agent_analysis}
</claims_agent_analysis>

<veteran_profile>
{veteran_profile}
</veteran_profile>

<instructions>
Review the claims agent's work and provide:
1. Validation: Are the estimated ratings reasonable?
2. Missing items: What evidence or forms are still needed?
3. Strategy adjustments: Should the approach change?
4. FDC readiness: Is this claim ready for FDC preparation?

Respond with ONLY valid JSON:
{{
  "validated": true|false,
  "rating_adjustments": [
    {{
      "condition": "name",
      "original_rating": 30,
      "adjusted_rating": 50,
      "reason": "why"
    }}
  ],
  "missing_evidence": ["list of missing items"],
  "required_forms": ["VA Form 21-526EZ", "VA Form 21-0781"],
  "fdc_ready": true|false,
  "fdc_blockers": ["list of things blocking FDC status"],
  "strategy_notes": "overall strategy recommendation",
  "priority_level": "routine|expedited|priority"
}}
</instructions>

<context>
{context}
</context>
"""


# ── Claims Evaluator Engine ─────────────────────────────────────────

class ClaimsEvaluator:
    """
    Background AI engine that evaluates claim questionnaire answers
    and produces disability rating estimates, compensation figures,
    and claim strategy recommendations.
    """

    def __init__(self, vector_store: VectorStore | None = None):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._store = vector_store
        logger.info("ClaimsEvaluator initialized")

    def _build_veteran_data_string(self, session: ClaimSession) -> str:
        """Compile all answers into a structured string for AI analysis."""
        all_answers = session.get_all_answers_decrypted()
        parts = []
        
        for page_key, answers in all_answers.items():
            parts.append(f"\n=== {page_key.upper().replace('_', ' ')} ===")
            for key, value in answers.items():
                if isinstance(value, list):
                    parts.append(f"  {key}: {', '.join(str(v) for v in value)}")
                elif isinstance(value, dict):
                    for sub_key, sub_val in value.items():
                        parts.append(f"  {key}.{sub_key}: {sub_val}")
                else:
                    parts.append(f"  {key}: {value}")
        
        return "\n".join(parts) if parts else "No answers submitted yet."

    def _get_claimed_conditions(self, session: ClaimSession) -> list[str]:
        """Extract claimed conditions from questionnaire answers."""
        conditions = []
        all_answers = session.get_all_answers_decrypted()
        
        # Disabilities page
        disabilities = all_answers.get("disabilities", {})
        selected = disabilities.get("selected_conditions", [])
        if isinstance(selected, list):
            conditions.extend(selected)
        
        custom = disabilities.get("custom_conditions", "")
        if custom:
            conditions.extend([c.strip() for c in custom.split(",") if c.strip()])
        
        # Mental health page
        mental = all_answers.get("mental_health", {})
        mental_conditions = mental.get("conditions", [])
        if isinstance(mental_conditions, list):
            conditions.extend(mental_conditions)
        
        return conditions

    def evaluate_claim(self, session: ClaimSession) -> AIEstimates:
        """
        Run AI evaluation on current questionnaire answers.
        Called after each page submission to update estimates in real-time.
        """
        veteran_data = self._build_veteran_data_string(session)
        claimed_conditions = self._get_claimed_conditions(session)
        
        # If no conditions claimed yet, return early estimates
        if not claimed_conditions:
            return self._basic_estimates(session)
        
        # Retrieve relevant legal context
        context_str = ""
        if self._store:
            conditions_query = " ".join(claimed_conditions[:5])
            retrieved = self._store.query(
                query_text=f"VA disability rating criteria for: {conditions_query}",
                top_k=5,
            )
            if retrieved:
                context_str = "\n\n".join([
                    f"[{r['metadata'].get('source_type', 'unknown')}] "
                    f"{r['text'][:500]}"
                    for r in retrieved
                ])
        
        # Call Claude for AI evaluation
        try:
            prompt = CLAIM_EVALUATION_PROMPT.format(
                veteran_data=veteran_data,
                context=context_str or "No specific legal context retrieved.",
            )
            
            message = self._client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                temperature=0.1,  # Very low for consistent rating estimates
                system=prompt,
                messages=[{
                    "role": "user",
                    "content": "Analyze this veteran's claim data and provide rating estimates.",
                }],
            )
            
            ai_response = message.content[0].text
            estimates = self._parse_ai_response(ai_response, session)
            
            logger.info(
                "AI evaluation complete for session %s: combined=%d%%",
                session.session_id,
                estimates.estimated_combined_rating,
            )
            return estimates
            
        except Exception as exc:
            logger.exception("AI evaluation failed — using heuristic estimates")
            return self._heuristic_estimates(claimed_conditions, session)

    def _parse_ai_response(
        self, response_text: str, session: ClaimSession
    ) -> AIEstimates:
        """Parse Claude's JSON response into AIEstimates."""
        try:
            # Extract JSON from response (handle potential markdown wrapping)
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                raise ValueError("No JSON found in AI response")
            
            data = json.loads(json_match.group())
            
            individual_ratings = data.get("individual_ratings", [])
            rating_values = [
                r.get("estimated_rating", 0) for r in individual_ratings
            ]
            
            combined = calculate_combined_rating(rating_values)
            monthly = VA_COMPENSATION_RATES_MONTHLY.get(combined, 0.0)
            
            # Get service end date for backpay calculation
            service_answers = session.get_page_answers(
                __import__('app.claim_session', fromlist=['ClaimPage']).ClaimPage.MILITARY_SERVICE
            )
            service_end = service_answers.get("service_end_date", "")
            
            # Check for medical evidence and presumptive conditions
            medical_answers = session.get_page_answers(
                __import__('app.claim_session', fromlist=['ClaimPage']).ClaimPage.MEDICAL_EVIDENCE
            )
            has_evidence = bool(medical_answers.get("has_medical_records", False))
            
            is_presumptive = any(
                r.get("service_connection_strength") == "strong"
                and "presumptive" in r.get("rationale", "").lower()
                for r in individual_ratings
            )
            
            timeline = estimate_decision_timeline(
                num_conditions=len(individual_ratings),
                has_medical_evidence=has_evidence,
                is_presumptive=is_presumptive,
                claim_type=data.get("claim_strategy", "initial"),
            )
            
            backpay = estimate_backpay(monthly, service_end)
            
            return AIEstimates(
                estimated_rating_percent=combined,
                estimated_combined_rating=combined,
                estimated_monthly_compensation=monthly,
                estimated_backpay=backpay,
                estimated_decision_timeline_days=timeline,
                confidence_level=data.get("confidence_level", "moderate"),
                individual_ratings=individual_ratings,
                notes=data.get("notes", []),
                last_updated=time.time(),
            )
            
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning("Failed to parse AI response: %s", exc)
            return self._heuristic_estimates(
                self._get_claimed_conditions(session), session
            )

    def _basic_estimates(self, session: ClaimSession) -> AIEstimates:
        """Return basic estimates when no conditions are claimed yet."""
        return AIEstimates(
            notes=["Complete the disabilities section to receive rating estimates."],
            confidence_level="low",
            last_updated=time.time(),
        )

    def _heuristic_estimates(
        self, conditions: list[str], session: ClaimSession
    ) -> AIEstimates:
        """
        Fallback heuristic estimates when AI call fails.
        Uses common rating ranges for known condition types.
        """
        common_ratings = {
            "ptsd": 50, "tinnitus": 10, "hearing loss": 10,
            "back": 20, "knee": 10, "shoulder": 20,
            "migraine": 30, "sleep apnea": 50,
            "depression": 50, "anxiety": 30,
            "gerd": 10, "hypertension": 10,
            "radiculopathy": 20, "neuropathy": 20,
            "tbi": 40, "diabetes": 20,
            "flat feet": 10, "plantar fasciitis": 10,
        }
        
        individual_ratings = []
        rating_values = []
        
        for condition in conditions:
            condition_lower = condition.lower()
            estimated = 10  # default
            for keyword, rating in common_ratings.items():
                if keyword in condition_lower:
                    estimated = rating
                    break
            
            individual_ratings.append({
                "condition": condition,
                "estimated_rating": estimated,
                "rationale": "Based on typical VA rating ranges (heuristic estimate)",
                "service_connection_strength": "moderate",
            })
            rating_values.append(estimated)
        
        combined = calculate_combined_rating(rating_values)
        monthly = VA_COMPENSATION_RATES_MONTHLY.get(combined, 0.0)
        
        return AIEstimates(
            estimated_rating_percent=combined,
            estimated_combined_rating=combined,
            estimated_monthly_compensation=monthly,
            estimated_backpay=estimate_backpay(monthly),
            estimated_decision_timeline_days=estimate_decision_timeline(
                len(conditions)
            ),
            confidence_level="low",
            individual_ratings=individual_ratings,
            notes=[
                "These are preliminary heuristic estimates.",
                "Provide more details for AI-powered precise estimates.",
            ],
            last_updated=time.time(),
        )

    # ── Agent Routing Pipeline ───────────────────────────────────────

    def route_to_supervisor(self, session: ClaimSession) -> dict:
        """
        After claims agent analysis, route to supervisor for review.
        The supervisor validates ratings and checks FDC readiness.
        """
        veteran_data = self._build_veteran_data_string(session)
        agent_analysis = json.dumps(
            session.ai_estimates.to_dict(), indent=2
        )
        
        context_str = ""
        if self._store:
            conditions = self._get_claimed_conditions(session)
            if conditions:
                retrieved = self._store.query(
                    query_text=f"FDC fully developed claim requirements {' '.join(conditions[:3])}",
                    top_k=5,
                )
                if retrieved:
                    context_str = "\n\n".join([
                        f"[{r['metadata'].get('source_type', 'unknown')}] "
                        f"{r['text'][:500]}"
                        for r in retrieved
                    ])
        
        try:
            prompt = SUPERVISOR_REVIEW_PROMPT.format(
                agent_analysis=agent_analysis,
                veteran_profile=veteran_data,
                context=context_str or "No specific context available.",
            )
            
            message = self._client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                temperature=0.1,
                system=prompt,
                messages=[{
                    "role": "user",
                    "content": "Review the claims agent analysis and prepare supervisor assessment.",
                }],
            )
            
            response_text = message.content[0].text
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                result = json.loads(json_match.group())
                session.status = ClaimStatus.SUPERVISOR_REVIEW
                session.agent.current_handler = AgentRole.SUPERVISOR
                session.agent.notes.append(
                    f"Supervisor review completed at {time.time()}"
                )
                return result
            
            return {"error": "Could not parse supervisor response"}
            
        except Exception as exc:
            logger.exception("Supervisor review failed")
            return {"error": str(exc)}

    def prepare_fdc(self, session: ClaimSession) -> dict:
        """
        Claims assistant prepares Fully Developed Claim package.
        Returns required forms, evidence checklist, and claim summary.
        """
        session.status = ClaimStatus.FDC_PREP
        session.agent.current_handler = AgentRole.CLAIMS_ASSISTANT
        
        all_answers = session.get_all_answers_decrypted()
        conditions = self._get_claimed_conditions(session)
        
        fdc_package = {
            "claim_type": "Fully Developed Claim (FDC)",
            "primary_form": "VA Form 21-526EZ",
            "conditions_claimed": conditions,
            "estimated_combined_rating": session.ai_estimates.estimated_combined_rating,
            "required_forms": [
                "VA Form 21-526EZ (Application for Disability Compensation)",
            ],
            "evidence_checklist": [
                "DD-214 (Certificate of Release/Discharge)",
                "Service Treatment Records (STRs)",
                "Private medical records",
                "Buddy statements / Lay evidence",
            ],
            "status": "draft",
            "prepared_at": time.time(),
        }
        
        # Add condition-specific forms
        for condition in conditions:
            condition_lower = condition.lower()
            if any(term in condition_lower for term in ["ptsd", "mst", "trauma"]):
                fdc_package["required_forms"].append(
                    "VA Form 21-0781 (Statement in Support of Claim for PTSD)"
                )
                fdc_package["evidence_checklist"].append(
                    "Stressor statement with specific dates and locations"
                )
            if "hearing" in condition_lower or "tinnitus" in condition_lower:
                fdc_package["evidence_checklist"].append(
                    "Audiological examination results"
                )
            if any(term in condition_lower for term in ["burn pit", "exposure"]):
                fdc_package["required_forms"].append(
                    "VA Form 21-0781a (Statement in Support of Claim - Secondary)"
                )
                fdc_package["evidence_checklist"].append(
                    "Airborne Hazards and Open Burn Pit Registry enrollment"
                )
        
        # Deduplicate
        fdc_package["required_forms"] = list(set(fdc_package["required_forms"]))
        fdc_package["evidence_checklist"] = list(set(fdc_package["evidence_checklist"]))
        
        session.agent.notes.append(
            f"FDC package prepared at {time.time()}"
        )
        
        return fdc_package
