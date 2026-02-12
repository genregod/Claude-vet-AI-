"""
Fine-Tuning Dataset Generator

Transforms cleaned documents into instruction-tuning format:
1. Instruction/Response pairs (JSONL)
2. Multi-turn conversation pairs (JSONL)

Categories:
  - Regulatory Q&A
  - Claims Strategy
  - Appeals Navigation
  - Case Analysis
  - Form Completion
  - Discharge Upgrade
  - Medical Evidence
  - Presumptive Conditions
  - Landmark Case Law
  - VSO Best Practices
"""

import json
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.data_collection.config import (
    CLEANED_DIR,
    TRAINING_DIR,
    SOURCE_CATEGORIES,
    MIN_RESPONSE_LENGTH,
    MAX_RESPONSE_LENGTH,
    MIN_INSTRUCTION_LENGTH,
    ensure_directories,
)
from scripts.data_collection.logger import get_logger

logger = get_logger("pipeline.training_data")

LEGAL_DISCLAIMER = (
    "Note: This information is for educational purposes only and does not "
    "constitute legal advice. Veterans should consult with a VA-accredited "
    "attorney, claims agent, or Veterans Service Officer for personalized guidance."
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEMPLATE GENERATORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_regulatory_qa(text: str, source_info: dict) -> list[dict]:
    """Generate regulatory Q&A pairs from CFR/USC text."""
    pairs = []
    category = source_info.get("category", "")

    # Split into sections
    sections = re.split(r'\n={3,}\n', text)

    for section in sections:
        section = section.strip()
        if len(section) < 100:
            continue

        # Extract section identifier
        section_ref = _extract_section_reference(section)

        # Generate Q&A pairs based on content patterns
        if "rating" in section.lower() or "diagnostic code" in section.lower():
            pairs.extend(_rating_criteria_qa(section, section_ref))
        elif "service connection" in section.lower():
            pairs.extend(_service_connection_qa(section, section_ref))
        elif "effective date" in section.lower():
            pairs.extend(_effective_date_qa(section, section_ref))
        elif "appeal" in section.lower() or "review" in section.lower():
            pairs.extend(_appeals_qa(section, section_ref))
        elif "evidence" in section.lower() or "duty to assist" in section.lower():
            pairs.extend(_evidence_qa(section, section_ref))

        # General summary Q&A for any substantial section
        if len(section.split()) > 50:
            summary_qa = {
                "instruction": f"Summarize the key provisions of {section_ref or 'this regulation'}.",
                "context": section[:2000],
                "response": _create_summary_response(section, section_ref),
                "category": "regulatory_qa",
                "source": category,
            }
            if _validate_pair(summary_qa):
                pairs.append(summary_qa)

    return pairs


def generate_claims_strategy(text: str, source_info: dict) -> list[dict]:
    """Generate claims strategy training pairs."""
    pairs = []

    # PTSD claims strategy
    if "ptsd" in text.lower() or "post-traumatic" in text.lower():
        pairs.append({
            "instruction": "What steps should a veteran take to file a PTSD disability claim with the VA?",
            "context": text[:2000],
            "response": _build_response_from_context(
                text,
                "To file a PTSD disability claim, a veteran should",
                [
                    "Gather evidence of a current PTSD diagnosis",
                    "Identify and document the in-service stressor",
                    "Complete VA Form 21-0781 (PTSD Stressor Statement)",
                    "Obtain supporting evidence (buddy statements, service records)",
                    "File VA Form 21-526EZ",
                    "38 CFR 3.304(f)",
                ]
            ),
            "category": "claims_strategy",
            "source": source_info.get("category", ""),
        })

    # TDIU claims
    if "unemployability" in text.lower() or "tdiu" in text.lower():
        pairs.append({
            "instruction": "How does a veteran apply for Total Disability based on Individual Unemployability (TDIU)?",
            "context": text[:2000],
            "response": _build_response_from_context(
                text,
                "To apply for TDIU, the veteran must meet specific criteria",
                [
                    "Schedular requirements: one disability at 60% or combined 70% with one at 40%",
                    "VA Form 21-8940",
                    "Evidence of inability to maintain substantially gainful employment",
                    "38 CFR 4.16",
                ]
            ),
            "category": "claims_strategy",
            "source": source_info.get("category", ""),
        })

    # Secondary service connection
    if "secondary" in text.lower() and "service connection" in text.lower():
        pairs.append({
            "instruction": "What is secondary service connection and how do I establish it?",
            "context": text[:2000],
            "response": _build_response_from_context(
                text,
                "Secondary service connection is established under 38 CFR 3.310",
                [
                    "Two theories: causation and aggravation",
                    "Nexus letter required",
                    "Allen v. Brown (aggravation theory)",
                    "Medical evidence linking secondary to primary condition",
                ]
            ),
            "category": "claims_strategy",
            "source": source_info.get("category", ""),
        })

    return pairs


def generate_appeals_navigation(text: str, source_info: dict) -> list[dict]:
    """Generate appeals navigation training pairs."""
    pairs = []

    if "supplemental claim" in text.lower() or "higher-level review" in text.lower() or "board appeal" in text.lower():
        pairs.append({
            "instruction": "My VA disability claim was denied. What are my options under the Appeals Modernization Act?",
            "context": text[:2000],
            "response": (
                "Under the Appeals Modernization Act (AMA), you have three options after a claim denial:\n\n"
                "1. **Supplemental Claim** (VA Form 20-0995): File when you have new and relevant evidence. "
                "Full duty to assist applies. No time limit, but file within 1 year to preserve your effective date.\n\n"
                "2. **Higher-Level Review** (VA Form 20-0996): A senior reviewer re-examines the existing evidence. "
                "No new evidence allowed. Must file within 1 year of the decision.\n\n"
                "3. **Board Appeal** (VA Form 10182): Appeal to the Board of Veterans' Appeals. Must file within "
                "1 year. Three docket options: Direct Review (fastest), Evidence Submission (90 days to submit new evidence), "
                "or Hearing (present your case to a Veterans Law Judge).\n\n"
                "The best lane depends on your specific situation. If you have new evidence (like a nexus letter or "
                "buddy statements), a Supplemental Claim is often the best path. If you believe the evidence already "
                "supports your claim, a Higher-Level Review may be appropriate.\n\n"
                f"{LEGAL_DISCLAIMER}"
            ),
            "category": "appeals_navigation",
            "source": source_info.get("category", ""),
        })

    return pairs


def generate_multi_turn_conversations(text: str, source_info: dict) -> list[dict]:
    """Generate multi-turn conversation training data."""
    conversations = []
    category = source_info.get("category", "")

    # PTSD claim multi-turn
    if "ptsd" in text.lower():
        conversations.append({
            "conversations": [
                {"role": "user", "content": "I was diagnosed with PTSD after deployment. Can I file a VA disability claim?"},
                {"role": "assistant", "content": (
                    "Yes, you can file a VA disability claim for PTSD. To establish service connection "
                    "for PTSD under 38 CFR 3.304(f), you need three elements:\n\n"
                    "1. A current PTSD diagnosis from a qualified mental health professional\n"
                    "2. An in-service stressor\n"
                    "3. A nexus (medical link) between the stressor and your PTSD\n\n"
                    "What type of stressor are you claiming? Combat, fear of hostile military activity, "
                    "military sexual trauma (MST), or another type of stressor?"
                )},
                {"role": "user", "content": "It was combat-related. I served in Afghanistan."},
                {"role": "assistant", "content": (
                    "Good news — for combat-related PTSD, the VA has relaxed evidentiary standards. "
                    "Under 38 CFR 3.304(f)(2), if your stressor is related to fear of hostile military "
                    "or terrorist activity, you don't need independent verification of the stressor. "
                    "The VA will concede the stressor if:\n\n"
                    "- Your stressor is consistent with the places, types, and circumstances of your service\n"
                    "- A VA psychiatrist or psychologist confirms the stressor is adequate to support a PTSD diagnosis\n\n"
                    "Here's what you should do:\n"
                    "1. File VA Form 21-0966 (Intent to File) to preserve your effective date\n"
                    "2. Complete VA Form 21-0781 (PTSD Stressor Statement) with details about your combat experiences\n"
                    "3. Gather your deployment records and any service treatment records mentioning mental health\n"
                    "4. Get buddy statements from fellow service members who witnessed the stressor events\n"
                    "5. If you have a private PTSD diagnosis, submit it with your claim\n"
                    "6. File VA Form 21-526EZ\n\n"
                    f"{LEGAL_DISCLAIMER}"
                )},
            ],
            "category": "claims_strategy",
            "source": category,
        })

    # Discharge upgrade multi-turn
    if "discharge" in text.lower() and ("upgrade" in text.lower() or "review" in text.lower()):
        conversations.append({
            "conversations": [
                {"role": "user", "content": "I received an Other Than Honorable discharge. Can I still get VA benefits?"},
                {"role": "assistant", "content": (
                    "An OTH discharge doesn't automatically bar you from all VA benefits. There are two paths:\n\n"
                    "1. **VA Character of Discharge Determination**: Under 38 CFR 3.12, VA makes its own "
                    "determination of whether your service was 'under conditions other than dishonorable.' "
                    "You can apply for benefits and VA will review your case. You may be eligible for "
                    "healthcare for service-connected conditions even without an upgrade.\n\n"
                    "2. **Discharge Upgrade**: You can apply to your service branch's Discharge Review Board "
                    "(DD Form 293) or Board for Correction of Military Records (DD Form 149) to have your "
                    "discharge upgraded.\n\n"
                    "Do you know if your discharge was related to any mental health condition, PTSD, TBI, or MST?"
                )},
                {"role": "user", "content": "Yes, I was struggling with PTSD symptoms but wasn't diagnosed until after I got out."},
                {"role": "assistant", "content": (
                    "This is significant — and you may have a strong case for a discharge upgrade. Under the "
                    "Hagel Memo (2014), Kurta Memo (2017), and Wilkie Memo (2018), military boards must apply "
                    "'liberal consideration' to discharge upgrade applications involving PTSD, TBI, MST, or "
                    "other mental health conditions.\n\n"
                    "Key principles:\n"
                    "- You do NOT need to have been diagnosed during service\n"
                    "- Your post-service PTSD diagnosis is sufficient evidence\n"
                    "- The board must consider whether PTSD symptoms contributed to the misconduct\n"
                    "- Liberal consideration means resolving reasonable doubt in your favor\n\n"
                    "Recommended steps:\n"
                    "1. Obtain your complete military personnel file (SF-180 to NPRC)\n"
                    "2. Get a current PTSD evaluation from a mental health provider\n"
                    "3. Ask the provider to write an opinion stating your PTSD likely existed during service "
                    "and may have contributed to the behavior leading to discharge\n"
                    "4. Gather buddy statements about behavioral changes during service\n"
                    "5. File DD Form 293 (DRB) if within 15 years, or DD Form 149 (BCMR) for any timeframe\n"
                    "6. Request a personal appearance hearing for highest chance of success\n\n"
                    "Many veterans legal clinics provide free representation for discharge upgrade cases. "
                    f"I'd recommend seeking legal assistance for this process.\n\n{LEGAL_DISCLAIMER}"
                )},
            ],
            "category": "discharge_upgrade",
            "source": category,
        })

    return conversations


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _extract_section_reference(text: str) -> str:
    """Extract legal section reference from text."""
    patterns = [
        r'(38 CFR \d+\.\d+(?:\([a-z]\)(?:\(\d+\))?)?)',
        r'(38 USC \d+[a-z]?)',
        r'(10 USC \d+[a-z]?)',
        r'(§\s*\d+\.\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return ""


def _create_summary_response(text: str, section_ref: str) -> str:
    """Create a summary response from text content."""
    words = text.split()
    # Take the first ~300 words as the basis for a summary
    summary_text = " ".join(words[:300])

    if section_ref:
        response = f"Under {section_ref}, the key provisions include:\n\n{summary_text}"
    else:
        response = f"The key provisions include:\n\n{summary_text}"

    if len(response) > MAX_RESPONSE_LENGTH:
        response = response[:MAX_RESPONSE_LENGTH - 100] + f"...\n\n{LEGAL_DISCLAIMER}"
    else:
        response += f"\n\n{LEGAL_DISCLAIMER}"

    return response


def _build_response_from_context(text: str, intro: str, key_points: list[str]) -> str:
    """Build a response that incorporates context and key points."""
    response_parts = [intro + ":\n"]

    for i, point in enumerate(key_points, 1):
        response_parts.append(f"{i}. {point}")

    # Add relevant context from source
    relevant_snippets = []
    for point in key_points:
        # Find sentences in text containing keywords from the point
        keywords = [w.lower() for w in point.split() if len(w) > 4]
        for sentence in re.split(r'[.!?]\s+', text):
            if any(kw in sentence.lower() for kw in keywords[:3]):
                if 20 < len(sentence) < 500:
                    relevant_snippets.append(sentence.strip())
                    break

    if relevant_snippets:
        response_parts.append("\nSpecifically:")
        for snippet in relevant_snippets[:3]:
            response_parts.append(f"- {snippet}")

    response_parts.append(f"\n{LEGAL_DISCLAIMER}")

    return "\n".join(response_parts)


def _rating_criteria_qa(section: str, section_ref: str) -> list[dict]:
    """Generate Q&A pairs about rating criteria."""
    pairs = []
    if section_ref:
        pairs.append({
            "instruction": f"What are the rating criteria under {section_ref}?",
            "context": section[:2000],
            "response": _create_summary_response(section, section_ref),
            "category": "regulatory_qa",
        })
    return pairs


def _service_connection_qa(section: str, section_ref: str) -> list[dict]:
    pairs = []
    if section_ref:
        pairs.append({
            "instruction": f"What does {section_ref} say about establishing service connection?",
            "context": section[:2000],
            "response": _create_summary_response(section, section_ref),
            "category": "regulatory_qa",
        })
    return pairs


def _effective_date_qa(section: str, section_ref: str) -> list[dict]:
    pairs = []
    if section_ref:
        pairs.append({
            "instruction": f"How are effective dates determined under {section_ref}?",
            "context": section[:2000],
            "response": _create_summary_response(section, section_ref),
            "category": "regulatory_qa",
        })
    return pairs


def _appeals_qa(section: str, section_ref: str) -> list[dict]:
    pairs = []
    ref = section_ref or "these provisions"
    pairs.append({
        "instruction": f"What are the appeals procedures under {ref}?",
        "context": section[:2000],
        "response": _create_summary_response(section, section_ref),
        "category": "appeals_navigation",
    })
    return pairs


def _evidence_qa(section: str, section_ref: str) -> list[dict]:
    pairs = []
    ref = section_ref or "these provisions"
    pairs.append({
        "instruction": f"What are the evidence requirements under {ref}?",
        "context": section[:2000],
        "response": _create_summary_response(section, section_ref),
        "category": "claims_strategy",
    })
    return pairs


def _validate_pair(pair: dict) -> bool:
    """Validate a training data pair meets quality standards."""
    instruction = pair.get("instruction", "")
    response = pair.get("response", "")

    if len(instruction) < MIN_INSTRUCTION_LENGTH:
        return False
    if len(response) < MIN_RESPONSE_LENGTH:
        return False
    return True


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN PIPELINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def generate_training_data() -> dict:
    """
    Generate training data from all cleaned documents.

    Outputs:
      - training/instruction_response.jsonl
      - training/multi_turn_conversations.jsonl
      - training/training_stats.json
    """
    logger.info("=" * 60)
    logger.info("STARTING TRAINING DATA GENERATION")
    logger.info("=" * 60)

    ensure_directories()

    all_pairs = []
    all_conversations = []
    seen_hashes = set()

    stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "instruction_response_pairs": 0,
        "multi_turn_conversations": 0,
        "categories_processed": 0,
        "files_processed": 0,
        "duplicates_removed": 0,
        "by_category": {},
    }

    for category in SOURCE_CATEGORIES:
        cleaned_dir = CLEANED_DIR / category
        if not cleaned_dir.exists():
            continue

        cat_pairs = 0
        cat_convos = 0

        for filepath in sorted(cleaned_dir.glob("*.txt")):
            if filepath.name.endswith(".meta.json"):
                continue

            text = filepath.read_text(encoding="utf-8", errors="replace")
            if len(text) < 100:
                continue

            stats["files_processed"] += 1
            source_info = {"category": category, "filename": filepath.name}

            # Generate instruction/response pairs
            pairs = []
            pairs.extend(generate_regulatory_qa(text, source_info))
            pairs.extend(generate_claims_strategy(text, source_info))
            pairs.extend(generate_appeals_navigation(text, source_info))

            # Deduplicate
            for pair in pairs:
                pair_hash = hashlib.md5(
                    (pair.get("instruction", "") + pair.get("response", "")).encode()
                ).hexdigest()
                if pair_hash not in seen_hashes and _validate_pair(pair):
                    seen_hashes.add(pair_hash)
                    all_pairs.append(pair)
                    cat_pairs += 1
                else:
                    stats["duplicates_removed"] += 1

            # Generate multi-turn conversations
            convos = generate_multi_turn_conversations(text, source_info)
            for convo in convos:
                convo_hash = hashlib.md5(
                    json.dumps(convo.get("conversations", []), sort_keys=True).encode()
                ).hexdigest()
                if convo_hash not in seen_hashes:
                    seen_hashes.add(convo_hash)
                    all_conversations.append(convo)
                    cat_convos += 1

        stats["by_category"][category] = {
            "pairs": cat_pairs,
            "conversations": cat_convos,
        }
        stats["categories_processed"] += 1

        if cat_pairs or cat_convos:
            logger.info(f"  {category}: {cat_pairs} pairs, {cat_convos} conversations")

    # Write output files
    ir_path = TRAINING_DIR / "instruction_response.jsonl"
    with open(ir_path, "w", encoding="utf-8") as f:
        for pair in all_pairs:
            f.write(json.dumps(pair, ensure_ascii=False) + "\n")

    mt_path = TRAINING_DIR / "multi_turn_conversations.jsonl"
    with open(mt_path, "w", encoding="utf-8") as f:
        for convo in all_conversations:
            f.write(json.dumps(convo, ensure_ascii=False) + "\n")

    stats["instruction_response_pairs"] = len(all_pairs)
    stats["multi_turn_conversations"] = len(all_conversations)
    stats["completed_at"] = datetime.now(timezone.utc).isoformat()

    # Save stats
    stats_path = TRAINING_DIR / "training_stats.json"
    stats_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    logger.info("=" * 60)
    logger.info(f"TRAINING DATA GENERATION COMPLETE")
    logger.info(f"  Instruction/Response pairs: {len(all_pairs)}")
    logger.info(f"  Multi-turn conversations: {len(all_conversations)}")
    logger.info(f"  Files processed: {stats['files_processed']}")
    logger.info(f"  Duplicates removed: {stats['duplicates_removed']}")
    logger.info(f"  Output: {ir_path}")
    logger.info(f"  Output: {mt_path}")
    logger.info("=" * 60)

    return stats


if __name__ == "__main__":
    generate_training_data()
