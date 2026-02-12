"""
Import Existing Data — Bridges the VA Model Training data from origin/main
into the pipeline's directory structure and formats.

The existing data in `VA Model Training/` contains two formats:

1. eCFR regulatory chunks (prompt/completion JSONL):
   - ecfr_part_3_adjudication.jsonl      (2,028 records — 38 CFR Part 3)
   - ecfr_part_17_medical.jsonl           (1,859 records — 38 CFR Part 17)
   - ecfr_part_19_appeals_legacy.jsonl    (  79 records — 38 CFR Part 19)
   - ecfr_part_20_appeals_rules.jsonl     ( 313 records — 38 CFR Part 20)
   - ecfr_part_21_education.jsonl         (4,021 records — 38 CFR Part 21)
   - ecfr_part_36_loan_guaranty.jsonl     (1,581 records — 38 CFR Part 36)
   - ecfr_parts_6_8_8a_9_life_insurance   ( 413 records — 38 CFR Parts 6/8/8a/9)

2. VA.gov page scrapes (prompt/completion JSONL):
   - va_appeals_full.jsonl                (   6 records)
   - va_education_full.jsonl              (   8 records)
   - va_health_care_full.jsonl            (  10 records)
   - va_home_loans_full.jsonl             ( 277 records)
   - va_life_insurance_full.jsonl         (   5 records)
   - va_survivor_benefits_full.jsonl      ( 507 records)

3. Fine-tuning Q&A pairs (messages/chat JSONL):
   - training_data_qa.jsonl.txt           (2,703 records)
   - validation_data_qa.jsonl.txt         (2,703 records)

4. PDFs (planning docs, BVA scrape lists):
   - BVA scrape list generation.pdf
   - VA Claims Links Compilation_.pdf
   - VA model build.pdf / VA model.pdf
   - Veterans_First_AI_Notebook.ipynb.pdf/.txt

This module:
  - Copies eCFR JSONL → app/data/raw/title_38_cfr/ as .txt (extracted completions)
  - Copies VA.gov JSONL → app/data/raw/{category}/ as .txt
  - Copies training Q&A → app/data/training/ (already in fine-tune format)
  - Copies PDFs → app/data/raw/bva_decisions/ (BVA scrape list)
  - Generates a manifest of everything imported
"""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from scripts.data_collection.config import (
    EXISTING_DATA_DIR,
    RAW_DIR,
    TRAINING_DIR,
    DATA_DIR,
    ensure_directories,
)
from scripts.data_collection.logger import get_logger

logger = get_logger("pipeline.import_existing")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAPPING: existing files → pipeline categories
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ECFR_FILES = {
    "ecfr_part_3_adjudication.jsonl": {
        "category": "title_38_cfr",
        "part": "3",
        "title": "38 CFR Part 3 — Adjudication",
    },
    "ecfr_part_17_medical.jsonl": {
        "category": "title_38_cfr",
        "part": "17",
        "title": "38 CFR Part 17 — Medical",
    },
    "ecfr_part_19_appeals_legacy.jsonl": {
        "category": "title_38_cfr",
        "part": "19",
        "title": "38 CFR Part 19 — Appeals (Legacy)",
    },
    "ecfr_part_20_appeals_rules.jsonl": {
        "category": "title_38_cfr",
        "part": "20",
        "title": "38 CFR Part 20 — Appeals Rules",
    },
    "ecfr_part_21_education.jsonl": {
        "category": "title_38_cfr",
        "part": "21",
        "title": "38 CFR Part 21 — Education",
    },
    "ecfr_part_36_loan_guaranty.jsonl": {
        "category": "title_38_cfr",
        "part": "36",
        "title": "38 CFR Part 36 — Loan Guaranty",
    },
    "ecfr_parts_6_8_8a_9_life_insurance.jsonl": {
        "category": "title_38_cfr",
        "part": "6_8_8a_9",
        "title": "38 CFR Parts 6, 8, 8a, 9 — Life Insurance",
    },
}

VA_GOV_FILES = {
    "va_appeals_full.jsonl": {
        "category": "appeals_modernization",
        "title": "VA.gov — Appeals and Decision Reviews",
    },
    "va_education_full.jsonl": {
        "category": "title_38_cfr",  # education regs overlap
        "title": "VA.gov — Education Benefits",
    },
    "va_health_care_full.jsonl": {
        "category": "va_clinical_guidelines",
        "title": "VA.gov — Health Care",
    },
    "va_home_loans_full.jsonl": {
        "category": "va_forms",  # home loan forms/procedures
        "title": "VA.gov — Home Loans",
    },
    "va_life_insurance_full.jsonl": {
        "category": "supplementary_legal",
        "title": "VA.gov — Life Insurance",
    },
    "va_survivor_benefits_full.jsonl": {
        "category": "claims_procedures",
        "title": "VA.gov — Survivor Benefits / DIC",
    },
}

TRAINING_FILES = {
    "training_data_qa.jsonl.txt": {
        "output_name": "existing_training_qa.jsonl",
        "split": "train",
    },
    "validation_data_qa.jsonl.txt": {
        "output_name": "existing_validation_qa.jsonl",
        "split": "validation",
    },
}

PDF_FILES = {
    "BVA scrape list generation.pdf": "bva_decisions",
    "VA Claims Links Compilation_.pdf": "supplementary_legal",
    "VA model build.pdf": "supplementary_legal",
    "VA model.pdf": "supplementary_legal",
    "Veterans_First_AI_Notebook.ipynb.pdf": "supplementary_legal",
    "Veterans_First_AI_Notebook.ipynb.txt": "supplementary_legal",
}


def _extract_completions_to_text(jsonl_path: Path, title: str) -> str:
    """
    Read a prompt/completion JSONL file and concatenate all completions
    into a single structured text document for RAG indexing.
    """
    lines = [title, "=" * 70, ""]
    record_count = 0

    with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                completion = record.get("completion", "")
                if completion:
                    lines.append(completion)
                    record_count += 1
            except json.JSONDecodeError:
                continue

    lines.append("")
    lines.append(f"[Source: VA Model Training — {record_count} records]")
    return "\n".join(lines)


def _convert_messages_to_standard_jsonl(jsonl_path: Path) -> list[dict]:
    """
    Read a messages-format JSONL file and convert to our standard
    multi-turn conversation format.

    Input format:  {"messages": [{"role":"user","content":"..."}, {"role":"assistant","content":"..."}]}
    Output format: {"conversations": [...], "category": "...", "source": "existing_va_model_training"}
    """
    records = []
    with open(jsonl_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                messages = record.get("messages", [])
                if messages:
                    # Convert messages format to our conversations format
                    conversations = []
                    for msg in messages:
                        conversations.append({
                            "role": msg.get("role", "user"),
                            "content": msg.get("content", ""),
                        })
                    records.append({
                        "conversations": conversations,
                        "category": "existing_va_qa",
                        "source": "va_model_training",
                    })
            except json.JSONDecodeError:
                continue
    return records


def import_existing_data() -> dict:
    """
    Import all existing VA Model Training data into the pipeline structure.

    Returns stats dict.
    """
    logger.info("=" * 70)
    logger.info("IMPORTING EXISTING VA MODEL TRAINING DATA")
    logger.info("=" * 70)

    ensure_directories()

    if not EXISTING_DATA_DIR.exists():
        logger.error(f"Existing data directory not found: {EXISTING_DATA_DIR}")
        return {"error": "VA Model Training directory not found"}

    stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "ecfr_files_imported": 0,
        "ecfr_records_total": 0,
        "va_gov_files_imported": 0,
        "va_gov_records_total": 0,
        "training_records_imported": 0,
        "validation_records_imported": 0,
        "pdf_files_copied": 0,
    }

    # ── Step 1: Import eCFR JSONL files ──
    logger.info("Step 1: Importing eCFR regulatory data...")
    for filename, info in ECFR_FILES.items():
        src = EXISTING_DATA_DIR / filename
        if not src.exists():
            logger.warning(f"  Missing: {filename}")
            continue

        category = info["category"]
        part = info["part"]
        title = info["title"]
        dest_dir = RAW_DIR / category

        # Save the original JSONL (preserves raw data)
        dest_jsonl = dest_dir / filename
        if not dest_jsonl.exists():
            shutil.copy2(src, dest_jsonl)
            logger.info(f"  Copied JSONL: {filename} → raw/{category}/")

        # Also extract completions to a single .txt for RAG
        txt_name = f"38_cfr_part_{part}_existing.txt"
        dest_txt = dest_dir / txt_name
        if not dest_txt.exists():
            text = _extract_completions_to_text(src, title)
            dest_txt.write_text(text, encoding="utf-8")
            word_count = len(text.split())
            logger.info(f"  Extracted: {txt_name} ({word_count:,} words)")
            stats["ecfr_records_total"] += sum(1 for _ in open(src))

        stats["ecfr_files_imported"] += 1

    # ── Step 2: Import VA.gov scrape files ──
    logger.info("Step 2: Importing VA.gov page scrapes...")
    for filename, info in VA_GOV_FILES.items():
        src = EXISTING_DATA_DIR / filename
        if not src.exists():
            logger.warning(f"  Missing: {filename}")
            continue

        category = info["category"]
        title = info["title"]
        dest_dir = RAW_DIR / category

        # Copy original JSONL
        dest_jsonl = dest_dir / filename
        if not dest_jsonl.exists():
            shutil.copy2(src, dest_jsonl)

        # Extract to text
        stem = Path(filename).stem
        txt_name = f"{stem}_existing.txt"
        dest_txt = dest_dir / txt_name
        if not dest_txt.exists():
            text = _extract_completions_to_text(src, title)
            dest_txt.write_text(text, encoding="utf-8")
            word_count = len(text.split())
            logger.info(f"  Extracted: {txt_name} ({word_count:,} words) → raw/{category}/")
            stats["va_gov_records_total"] += sum(1 for _ in open(src))

        stats["va_gov_files_imported"] += 1

    # ── Step 3: Import training/validation Q&A data ──
    logger.info("Step 3: Importing training Q&A data...")
    for filename, info in TRAINING_FILES.items():
        src = EXISTING_DATA_DIR / filename
        if not src.exists():
            logger.warning(f"  Missing: {filename}")
            continue

        output_name = info["output_name"]
        split = info["split"]
        dest = TRAINING_DIR / output_name

        if not dest.exists():
            # Convert messages format to our standard format
            records = _convert_messages_to_standard_jsonl(src)
            with open(dest, "w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            logger.info(f"  Converted: {filename} → training/{output_name} ({len(records)} records)")

            if split == "train":
                stats["training_records_imported"] = len(records)
            else:
                stats["validation_records_imported"] = len(records)

        # Also copy the original file as-is for OpenAI fine-tuning compatibility
        orig_dest = TRAINING_DIR / filename
        if not orig_dest.exists():
            shutil.copy2(src, orig_dest)
            logger.info(f"  Preserved original: {filename} → training/")

    # ── Step 4: Copy PDFs and reference docs ──
    logger.info("Step 4: Copying PDFs and reference documents...")
    for filename, category in PDF_FILES.items():
        src = EXISTING_DATA_DIR / filename
        if not src.exists():
            continue

        dest_dir = RAW_DIR / category
        dest = dest_dir / filename
        if not dest.exists():
            shutil.copy2(src, dest)
            logger.info(f"  Copied: {filename} → raw/{category}/")
            stats["pdf_files_copied"] += 1

    stats["completed_at"] = datetime.now(timezone.utc).isoformat()

    # ── Summary ──
    logger.info("=" * 70)
    logger.info("IMPORT COMPLETE")
    logger.info(f"  eCFR regulatory files: {stats['ecfr_files_imported']}")
    logger.info(f"  VA.gov scrape files:   {stats['va_gov_files_imported']}")
    logger.info(f"  Training Q&A records:  {stats['training_records_imported']}")
    logger.info(f"  Validation Q&A records:{stats['validation_records_imported']}")
    logger.info(f"  PDFs copied:           {stats['pdf_files_copied']}")
    logger.info("=" * 70)

    # Save import report
    report_path = DATA_DIR / "import_report.json"
    report_path.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    return stats


if __name__ == "__main__":
    import_existing_data()
