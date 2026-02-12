"""
Pipeline Orchestrator — Master controller for the data collection pipeline.

Usage:
    python -m scripts.data_collection.run_pipeline --phase collect    # Download everything
    python -m scripts.data_collection.run_pipeline --phase clean      # Clean all raw data
    python -m scripts.data_collection.run_pipeline --phase prepare    # Generate training data
    python -m scripts.data_collection.run_pipeline --phase ingest     # Load into ChromaDB
    python -m scripts.data_collection.run_pipeline --phase all        # Full pipeline
    python -m scripts.data_collection.run_pipeline --phase status     # Show collection progress

Options:
    --source <name>    Only process a specific source category
    --verbose          Enable debug logging
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on the Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data_collection.config import (
    DATA_DIR,
    RAW_DIR,
    CLEANED_DIR,
    TRAINING_DIR,
    CHROMA_DIR,
    MANIFEST_FILE,
    REPORT_FILE,
    SOURCE_CATEGORIES,
    ensure_directories,
)
from scripts.data_collection.logger import get_logger

logger = get_logger("pipeline.orchestrator")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA MANIFEST
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def load_manifest() -> dict:
    """Load the data manifest from disk."""
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text())
        except json.JSONDecodeError:
            pass
    return {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sources": {},
    }


def save_manifest(manifest: dict) -> None:
    """Save the data manifest to disk."""
    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def update_manifest_source(manifest: dict, source_name: str, stats: dict) -> None:
    """Update manifest entry for a single source."""
    raw_dir = RAW_DIR / source_name
    cleaned_dir = CLEANED_DIR / source_name

    raw_files = list(raw_dir.glob("*")) if raw_dir.exists() else []
    raw_files = [f for f in raw_files if not f.name.endswith(".meta.json")]
    cleaned_files = list(cleaned_dir.glob("*.txt")) if cleaned_dir.exists() else []
    cleaned_files = [f for f in cleaned_files if not f.name.endswith(".meta.json")]

    raw_size = sum(f.stat().st_size for f in raw_files if f.is_file())
    cleaned_size = sum(f.stat().st_size for f in cleaned_files if f.is_file())

    manifest["sources"][source_name] = {
        "collection_status": "completed" if stats.get("files_downloaded", 0) > 0 or stats.get("files_skipped", 0) > 0 else "pending",
        "raw_file_count": len(raw_files),
        "raw_size_bytes": raw_size,
        "cleaned_file_count": len(cleaned_files),
        "cleaned_size_bytes": cleaned_size,
        "last_collected": stats.get("completed_at", ""),
        "errors": stats.get("errors", 0),
        "stats": stats,
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PHASE RUNNERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def run_collect(source_filter: str = None) -> dict:
    """Phase 1: Collect raw data from all sources."""
    from scripts.data_collection.scrapers import SCRAPER_REGISTRY, COLLECTION_ORDER

    logger.info("=" * 70)
    logger.info("PHASE 1: DATA COLLECTION")
    logger.info("=" * 70)

    ensure_directories()
    manifest = load_manifest()
    results = {}

    sources = [source_filter] if source_filter else COLLECTION_ORDER
    total = len(sources)

    for i, source_name in enumerate(sources, 1):
        if source_name not in SCRAPER_REGISTRY:
            logger.warning(f"Unknown source: {source_name}, skipping")
            continue

        logger.info(f"[{i}/{total}] Collecting: {source_name}")

        try:
            scraper_cls = SCRAPER_REGISTRY[source_name]
            scraper = scraper_cls()
            stats = scraper.run()
            results[source_name] = stats
            update_manifest_source(manifest, source_name, stats)
            save_manifest(manifest)
        except Exception as e:
            logger.exception(f"Failed to collect {source_name}: {e}")
            results[source_name] = {"error": str(e)}

    logger.info("=" * 70)
    logger.info("COLLECTION PHASE COMPLETE")
    for name, stats in results.items():
        downloaded = stats.get("files_downloaded", 0)
        skipped = stats.get("files_skipped", 0)
        errors = stats.get("errors", 0)
        logger.info(f"  {name}: {downloaded} new, {skipped} skipped, {errors} errors")
    logger.info("=" * 70)

    return results


def run_clean() -> dict:
    """Phase 2: Clean all collected raw data."""
    from scripts.data_collection.clean import run_cleaning_pipeline

    logger.info("=" * 70)
    logger.info("PHASE 2: DATA CLEANING")
    logger.info("=" * 70)

    return run_cleaning_pipeline()


def run_prepare() -> dict:
    """Phase 3: Generate training data from cleaned documents."""
    from scripts.data_collection.generate_training_data import generate_training_data

    logger.info("=" * 70)
    logger.info("PHASE 3: TRAINING DATA PREPARATION")
    logger.info("=" * 70)

    return generate_training_data()


def run_ingest() -> dict:
    """Phase 4: Load cleaned data into ChromaDB."""
    from scripts.data_collection.ingest import run_ingest_pipeline

    logger.info("=" * 70)
    logger.info("PHASE 4: CHROMADB INGEST")
    logger.info("=" * 70)

    return run_ingest_pipeline()


def run_status() -> dict:
    """Show collection progress and statistics."""
    logger.info("=" * 70)
    logger.info("DATA COLLECTION STATUS REPORT")
    logger.info("=" * 70)

    status = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sources": {},
        "totals": {
            "raw_files": 0,
            "raw_size_mb": 0,
            "cleaned_files": 0,
            "cleaned_size_mb": 0,
        },
    }

    for category in SOURCE_CATEGORIES:
        raw_dir = RAW_DIR / category
        cleaned_dir = CLEANED_DIR / category

        raw_files = []
        cleaned_files = []

        if raw_dir.exists():
            raw_files = [f for f in raw_dir.iterdir()
                         if f.is_file() and not f.name.endswith(".meta.json")]
        if cleaned_dir.exists():
            cleaned_files = [f for f in cleaned_dir.iterdir()
                             if f.is_file() and f.suffix == ".txt"
                             and not f.name.endswith(".meta.json")]

        raw_size = sum(f.stat().st_size for f in raw_files)
        cleaned_size = sum(f.stat().st_size for f in cleaned_files)

        cat_status = "empty"
        if raw_files:
            cat_status = "collected"
        if cleaned_files:
            cat_status = "cleaned"

        status["sources"][category] = {
            "status": cat_status,
            "raw_files": len(raw_files),
            "raw_size_mb": round(raw_size / (1024 * 1024), 2),
            "cleaned_files": len(cleaned_files),
            "cleaned_size_mb": round(cleaned_size / (1024 * 1024), 2),
        }

        status["totals"]["raw_files"] += len(raw_files)
        status["totals"]["raw_size_mb"] += raw_size / (1024 * 1024)
        status["totals"]["cleaned_files"] += len(cleaned_files)
        status["totals"]["cleaned_size_mb"] += cleaned_size / (1024 * 1024)

        # Display
        status_icon = {"empty": "[ ]", "collected": "[R]", "cleaned": "[C]"}
        icon = status_icon.get(cat_status, "[ ]")
        logger.info(
            f"  {icon} {category:40s} | "
            f"Raw: {len(raw_files):4d} files ({raw_size / 1024:.0f} KB) | "
            f"Clean: {len(cleaned_files):4d} files ({cleaned_size / 1024:.0f} KB)"
        )

    # Training data status
    training_stats_file = TRAINING_DIR / "training_stats.json"
    if training_stats_file.exists():
        try:
            training_stats = json.loads(training_stats_file.read_text())
            status["training"] = {
                "instruction_response_pairs": training_stats.get("instruction_response_pairs", 0),
                "multi_turn_conversations": training_stats.get("multi_turn_conversations", 0),
            }
            logger.info("")
            logger.info(f"  Training Data:")
            logger.info(f"    Instruction/Response pairs: {training_stats.get('instruction_response_pairs', 0)}")
            logger.info(f"    Multi-turn conversations: {training_stats.get('multi_turn_conversations', 0)}")
        except Exception:
            pass

    # ChromaDB status
    chroma_report = CHROMA_DIR / "ingest_report.json"
    if chroma_report.exists():
        try:
            ingest_stats = json.loads(chroma_report.read_text())
            status["chromadb"] = {
                "collection_size": ingest_stats.get("final_collection_size", 0),
            }
            logger.info(f"    ChromaDB collection: {ingest_stats.get('final_collection_size', 0)} documents")
        except Exception:
            pass

    # Totals
    status["totals"]["raw_size_mb"] = round(status["totals"]["raw_size_mb"], 2)
    status["totals"]["cleaned_size_mb"] = round(status["totals"]["cleaned_size_mb"], 2)

    logger.info("")
    logger.info(f"  TOTALS:")
    logger.info(f"    Raw files:     {status['totals']['raw_files']}")
    logger.info(f"    Raw size:      {status['totals']['raw_size_mb']:.1f} MB")
    logger.info(f"    Cleaned files: {status['totals']['cleaned_files']}")
    logger.info(f"    Cleaned size:  {status['totals']['cleaned_size_mb']:.1f} MB")
    logger.info("=" * 70)

    # Generate collection report markdown
    _generate_collection_report(status)

    return status


def run_all(source_filter: str = None) -> dict:
    """Run the complete pipeline: collect -> clean -> prepare -> ingest."""
    results = {}

    results["collect"] = run_collect(source_filter)
    results["clean"] = run_clean()
    results["prepare"] = run_prepare()
    results["ingest"] = run_ingest()
    results["status"] = run_status()

    return results


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REPORT GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def _generate_collection_report(status: dict) -> None:
    """Generate a markdown collection status report."""
    lines = [
        "# Valor Assist - Data Collection Status Report",
        "",
        f"Generated: {status['timestamp']}",
        "",
        "## Source Categories",
        "",
        "| Category | Status | Raw Files | Raw Size | Cleaned Files | Cleaned Size |",
        "|----------|--------|-----------|----------|---------------|--------------|",
    ]

    for category, info in status["sources"].items():
        lines.append(
            f"| {category} | {info['status']} | {info['raw_files']} | "
            f"{info['raw_size_mb']:.1f} MB | {info['cleaned_files']} | "
            f"{info['cleaned_size_mb']:.1f} MB |"
        )

    lines.extend([
        "",
        "## Totals",
        "",
        f"- **Raw files:** {status['totals']['raw_files']}",
        f"- **Raw size:** {status['totals']['raw_size_mb']:.1f} MB",
        f"- **Cleaned files:** {status['totals']['cleaned_files']}",
        f"- **Cleaned size:** {status['totals']['cleaned_size_mb']:.1f} MB",
    ])

    if "training" in status:
        lines.extend([
            "",
            "## Training Data",
            "",
            f"- **Instruction/Response pairs:** {status['training']['instruction_response_pairs']}",
            f"- **Multi-turn conversations:** {status['training']['multi_turn_conversations']}",
        ])

    if "chromadb" in status:
        lines.extend([
            "",
            "## ChromaDB",
            "",
            f"- **Collection size:** {status['chromadb']['collection_size']} documents",
        ])

    lines.extend([
        "",
        "## Status Legend",
        "",
        "- `empty`: No data collected yet",
        "- `collected`: Raw data downloaded",
        "- `cleaned`: Data cleaned and ready for use",
    ])

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Report saved to {REPORT_FILE}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CLI ENTRYPOINT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


def main():
    parser = argparse.ArgumentParser(
        description="Valor Assist Data Collection Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Phases:
  collect    Download raw data from all sources
  clean      Clean and normalize all raw data
  prepare    Generate fine-tuning training data
  ingest     Load cleaned data into ChromaDB
  all        Run the full pipeline (collect -> clean -> prepare -> ingest)
  status     Show collection progress and statistics

Examples:
  python -m scripts.data_collection.run_pipeline --phase status
  python -m scripts.data_collection.run_pipeline --phase collect --source title_38_cfr
  python -m scripts.data_collection.run_pipeline --phase all
        """,
    )

    parser.add_argument(
        "--phase",
        required=True,
        choices=["collect", "clean", "prepare", "ingest", "all", "status"],
        help="Pipeline phase to execute",
    )
    parser.add_argument(
        "--source",
        default=None,
        help="Only process a specific source category (for collect phase)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()

    if args.verbose:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)

    # Ensure directories exist
    ensure_directories()

    # Route to appropriate phase
    phase_map = {
        "collect": lambda: run_collect(args.source),
        "clean": run_clean,
        "prepare": run_prepare,
        "ingest": run_ingest,
        "all": lambda: run_all(args.source),
        "status": run_status,
    }

    runner = phase_map[args.phase]
    result = runner()

    # Print summary as JSON for programmatic use
    if args.phase != "status":
        print(json.dumps({"phase": args.phase, "success": True}, indent=2))


if __name__ == "__main__":
    main()
