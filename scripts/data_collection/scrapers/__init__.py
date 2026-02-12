"""
Scraper registry — maps source categories to their scraper classes.

Usage:
    from scripts.data_collection.scrapers import SCRAPER_REGISTRY, get_scraper

    scraper = get_scraper("title_38_cfr")
    stats = scraper.run()
"""

from scripts.data_collection.scrapers.ecfr_scraper import ECFRScraper
from scripts.data_collection.scrapers.usc_scraper import USCScraper, UCMJScraper
from scripts.data_collection.scrapers.va_m21_scraper import VAM21Scraper
from scripts.data_collection.scrapers.bva_scraper import BVAScraper
from scripts.data_collection.scrapers.cavc_scraper import CAVCScraper
from scripts.data_collection.scrapers.federal_circuit_scraper import FederalCircuitScraper
from scripts.data_collection.scrapers.bcmr_drb_scraper import BCMRScraper, DRBScraper
from scripts.data_collection.scrapers.dod_memos_scraper import DoDMemosScraper
from scripts.data_collection.scrapers.va_forms_scraper import VAFormsScraper
from scripts.data_collection.scrapers.remaining_sources_scraper import (
    VSOTrainingScraper,
    ClaimsProceduresScraper,
    PACTActScraper,
    AMAActScraper,
    ClinicalGuidelinesScraper,
    MilitaryPersonnelRegsScraper,
    OIGGAOScraper,
    SupplementaryLegalScraper,
    VASRDScraper,
)

# Maps source category names to scraper classes
SCRAPER_REGISTRY: dict[str, type] = {
    "title_38_cfr": ECFRScraper,
    "title_38_usc": USCScraper,
    "ucmj_10_usc": UCMJScraper,
    "va_m21_1_manual": VAM21Scraper,
    "vasrd_rating_schedule": VASRDScraper,
    "bva_decisions": BVAScraper,
    "cavc_opinions": CAVCScraper,
    "federal_circuit": FederalCircuitScraper,
    "bcmr_decisions": BCMRScraper,
    "drb_decisions": DRBScraper,
    "dod_policy_memos": DoDMemosScraper,
    "va_forms": VAFormsScraper,
    "vso_training": VSOTrainingScraper,
    "claims_procedures": ClaimsProceduresScraper,
    "pact_act": PACTActScraper,
    "appeals_modernization": AMAActScraper,
    "va_clinical_guidelines": ClinicalGuidelinesScraper,
    "military_personnel_regs": MilitaryPersonnelRegsScraper,
    "va_oig_reports": OIGGAOScraper,
    "supplementary_legal": SupplementaryLegalScraper,
}

# Ordered list for priority-based collection
COLLECTION_ORDER = [
    "title_38_cfr",
    "title_38_usc",
    "ucmj_10_usc",
    "va_m21_1_manual",
    "vasrd_rating_schedule",
    "bva_decisions",
    "cavc_opinions",
    "federal_circuit",
    "bcmr_decisions",
    "drb_decisions",
    "dod_policy_memos",
    "va_forms",
    "vso_training",
    "claims_procedures",
    "pact_act",
    "appeals_modernization",
    "va_clinical_guidelines",
    "military_personnel_regs",
    "va_oig_reports",
    "supplementary_legal",
]


def get_scraper(source_name: str):
    """
    Get a scraper instance for a source category.

    Args:
        source_name: Key from SCRAPER_REGISTRY.

    Returns:
        Instantiated scraper object.

    Raises:
        KeyError: If source_name not in registry.
    """
    if source_name not in SCRAPER_REGISTRY:
        available = ", ".join(sorted(SCRAPER_REGISTRY.keys()))
        raise KeyError(
            f"Unknown source: '{source_name}'. Available: {available}"
        )
    return SCRAPER_REGISTRY[source_name]()


def get_all_scrapers():
    """Get all scrapers in priority order."""
    return [SCRAPER_REGISTRY[name]() for name in COLLECTION_ORDER if name in SCRAPER_REGISTRY]
