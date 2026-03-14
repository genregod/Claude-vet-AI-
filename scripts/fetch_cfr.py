#!/usr/bin/env python3
"""
Fetch VA-related 38 CFR parts from eCFR API and save as .txt to app/data/raw/.
Also converts existing JSONL training files to plain text for ingestion.
"""
import sys, re, json, time, logging
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)-7s  %(message)s")
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR   = REPO_ROOT / "app" / "data" / "raw"
JSONL_DIR = REPO_ROOT / "VA Model Training"

# Parts to fetch from eCFR (Title 38)
CFR_PARTS = {
    "3":  "38_cfr_part_3_adjudication",
    "4":  "38_cfr_part_4_rating_schedule",
    "19": "38_cfr_part_19_bva_legacy_appeals",
    "20": "38_cfr_part_20_bva_rules",
    "21": "38_cfr_part_21_education_benefits",
    "36": "38_cfr_part_36_loan_guaranty",
}

ECFR_URL = "https://www.ecfr.gov/api/versioner/v1/full/2024-01-01/title-38.xml"


def fetch_part(part: str) -> str:
    """Fetch a CFR part from eCFR API and return plain text."""
    logger.info("Fetching 38 CFR Part %s from eCFR …", part)
    resp = requests.get(ECFR_URL, params={"part": part}, timeout=120)
    resp.raise_for_status()

    # Strip XML tags, collapse whitespace
    root = ET.fromstring(resp.content)
    texts = []
    for elem in root.iter():
        if elem.text and elem.text.strip():
            texts.append(elem.text.strip())
        if elem.tail and elem.tail.strip():
            texts.append(elem.tail.strip())

    raw = " ".join(texts)
    # Collapse runs of whitespace
    return re.sub(r"\s{2,}", " ", raw).strip()


def jsonl_to_text(jsonl_path: Path) -> str:
    """Extract text content from a JSONL Q&A training file."""
    lines = []
    for line in jsonl_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            # Handle various JSONL formats
            if "text" in obj:
                lines.append(obj["text"])
            elif "messages" in obj:
                for m in obj["messages"]:
                    if isinstance(m, dict) and "content" in m:
                        lines.append(m["content"])
            elif "prompt" in obj and "completion" in obj:
                lines.append(obj["prompt"] + " " + obj["completion"])
            elif "question" in obj and "answer" in obj:
                lines.append(obj["question"] + " " + obj["answer"])
            else:
                # Dump all string values
                lines.append(" ".join(str(v) for v in obj.values() if isinstance(v, str)))
        except json.JSONDecodeError:
            lines.append(line)
    return "\n\n".join(lines)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Fetch from eCFR
    for part, filename in CFR_PARTS.items():
        out_path = RAW_DIR / f"{filename}.txt"
        if out_path.exists():
            logger.info("Skipping Part %s — already exists", part)
            continue
        try:
            text = fetch_part(part)
            out_path.write_text(text, encoding="utf-8")
            logger.info("  Saved %s (%d chars)", out_path.name, len(text))
            time.sleep(1)  # be polite to eCFR
        except Exception as e:
            logger.error("  Failed Part %s: %s", part, e)

    # 2. Convert existing JSONL files
    jsonl_map = {
        "ecfr_part_17_medical.jsonl":                "38_cfr_part_17_medical",
        "ecfr_parts_6_8_8a_9_life_insurance.jsonl":  "38_cfr_parts_6_8_9_life_insurance",
    }
    for jsonl_name, out_name in jsonl_map.items():
        src = JSONL_DIR / jsonl_name
        out_path = RAW_DIR / f"{out_name}.txt"
        if not src.exists():
            logger.warning("JSONL not found: %s", src)
            continue
        if out_path.exists():
            logger.info("Skipping %s — already exists", out_name)
            continue
        logger.info("Converting %s …", jsonl_name)
        text = jsonl_to_text(src)
        out_path.write_text(text, encoding="utf-8")
        logger.info("  Saved %s (%d chars)", out_path.name, len(text))

    logger.info("=== Fetch complete. Files in %s ===", RAW_DIR)
    for f in sorted(RAW_DIR.glob("*.txt")):
        logger.info("  %s  (%d KB)", f.name, f.stat().st_size // 1024)


if __name__ == "__main__":
    main()
