"""
DoD Policy Memoranda Scraper — Liberal Consideration Memos

Collects critical policy directives requiring liberal consideration for
PTSD, TBI, MST, and mental health in discharge upgrade and records
correction cases.

Key memoranda:
  - Hagel Memo (2014) — Supplemental guidance for PTSD discharge reviews
  - Carson Memo (2014) — PTSD liberal consideration instructions
  - Kurta Memo (2017) — Liberal consideration for MH/TBI/MST discharge upgrades
  - Wilkie Memo (2018) — BCMR liberal consideration standards
  - August 2017 DoD guidance — Equity, injustice, and clemency

Plus: Service-branch-specific implementing instructions.
"""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper
from scripts.data_collection.config import DOD_MEMO_KEYWORDS


class DoDMemosScraper(BaseScraper):
    """Scraper for DoD policy memoranda on liberal consideration."""

    @property
    def source_name(self) -> str:
        return "dod_policy_memos"

    # Known URLs and search strategies for each memo
    MEMOS = {
        "hagel_memo_2014": {
            "title": "Secretary Hagel Supplemental Guidance for PTSD Discharge Reviews (2014)",
            "description": (
                "Directed DRBs to give liberal consideration to veterans with "
                "PTSD diagnoses seeking discharge upgrades. Established that PTSD "
                "may have been a mitigating factor in misconduct leading to discharge."
            ),
            "search_urls": [
                "https://www.defense.gov/News/Releases/",
                "https://arba.army.pentagon.mil/",
            ],
            "known_patterns": ["hagel", "ptsd", "liberal consideration", "2014"],
        },
        "carson_memo_2014": {
            "title": "Under Secretary Carson PTSD Liberal Consideration Memo (2014)",
            "description": (
                "Provided implementing guidance for the Hagel memo, detailing "
                "how boards should apply liberal consideration to PTSD-related "
                "discharge upgrade applications."
            ),
            "search_urls": [
                "https://www.defense.gov/News/Releases/",
            ],
            "known_patterns": ["carson", "ptsd", "liberal consideration"],
        },
        "kurta_memo_2017": {
            "title": "Under Secretary Kurta Clarifying Guidance for Discharge Upgrades (2017)",
            "description": (
                "Expanded liberal consideration beyond PTSD to include TBI, MST, "
                "and other mental health conditions. Established that boards should "
                "consider whether mental health conditions, including those not "
                "diagnosed at time of service, may have mitigated misconduct."
            ),
            "search_urls": [
                "https://www.defense.gov/News/Releases/",
                "https://arba.army.pentagon.mil/documents.html",
            ],
            "known_patterns": ["kurta", "mental health", "TBI", "MST", "liberal consideration", "2017"],
        },
        "wilkie_memo_2018": {
            "title": "Secretary Wilkie BCMR Liberal Consideration Standards (2018)",
            "description": (
                "Extended liberal consideration standards to BCMR proceedings. "
                "Directed that BCMRs apply the same liberal consideration "
                "standards as DRBs for cases involving PTSD, TBI, MST, and "
                "mental health conditions."
            ),
            "search_urls": [
                "https://www.defense.gov/News/Releases/",
            ],
            "known_patterns": ["wilkie", "bcmr", "liberal consideration", "2018"],
        },
        "dod_equity_clemency_2017": {
            "title": "DoD Guidance on Equity, Injustice, and Clemency (August 2017)",
            "description": (
                "Comprehensive DoD guidance on how boards should weigh equity, "
                "injustice, and clemency factors when reviewing discharge upgrade "
                "and records correction applications."
            ),
            "search_urls": [
                "https://www.defense.gov/News/Releases/",
            ],
            "known_patterns": ["equity", "injustice", "clemency", "2017"],
        },
    }

    # Service branch implementing guidance URLs
    BRANCH_IMPLEMENTING = {
        "army": {
            "name": "Army Implementing Instructions",
            "urls": [
                "https://arba.army.pentagon.mil/documents.html",
                "https://arba.army.pentagon.mil/abcmr-overview.html",
            ],
        },
        "navy": {
            "name": "Navy/Marine Corps Implementing Instructions",
            "urls": [
                "https://www.secnav.navy.mil/mra/bcnr/",
            ],
        },
        "air_force": {
            "name": "Air Force Implementing Instructions",
            "urls": [
                "https://www.afpc.af.mil/Board-for-Correction-of-Military-Records/",
            ],
        },
    }

    def collect(self) -> dict:
        """Collect all DoD policy memoranda."""
        extra_stats = {
            "memos_collected": 0,
            "branch_guidance_collected": 0,
        }

        # Step 1: Create comprehensive reference documents for each memo
        for memo_key, memo_info in self.MEMOS.items():
            self.logger.info(f"Collecting: {memo_info['title']}")
            collected = self._collect_memo(memo_key, memo_info)
            if collected:
                extra_stats["memos_collected"] += 1

        # Step 2: Collect branch-specific implementing instructions
        for branch, info in self.BRANCH_IMPLEMENTING.items():
            self.logger.info(f"Collecting {info['name']}...")
            for url in info["urls"]:
                collected = self._collect_branch_guidance(branch, url, info["name"])
                if collected:
                    extra_stats["branch_guidance_collected"] += 1

        # Step 3: Create consolidated liberal consideration reference
        self._create_liberal_consideration_reference()

        return extra_stats

    def _collect_memo(self, memo_key: str, memo_info: dict) -> bool:
        """Collect a specific policy memo from known sources."""
        filename = f"dod_memo_{memo_key}.txt"
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True

        # Try each search URL to find the memo
        for search_url in memo_info["search_urls"]:
            response = self.fetch(search_url)
            if not response or response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "lxml")

            # Search for links matching the memo's patterns
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True).lower()
                combined = f"{href} {text}"

                if self._matches_memo_patterns(combined, memo_info["known_patterns"]):
                    full_url = urljoin(search_url, href)
                    doc_resp = self.fetch(full_url)
                    if doc_resp and doc_resp.status_code == 200:
                        if full_url.lower().endswith(".pdf"):
                            self.save_file(
                                f"dod_memo_{memo_key}.pdf",
                                doc_resp.content,
                                metadata={
                                    "type": "dod_memo",
                                    "memo_key": memo_key,
                                    "title": memo_info["title"],
                                    "url": full_url,
                                    "format": "pdf",
                                }
                            )
                        else:
                            text_content = self._extract_text(doc_resp.text, memo_info["title"])
                            self.save_file(
                                filename,
                                text_content,
                                metadata={
                                    "type": "dod_memo",
                                    "memo_key": memo_key,
                                    "title": memo_info["title"],
                                    "url": full_url,
                                    "format": "text",
                                }
                            )
                        return True

        # If we couldn't find the actual document, save a reference entry
        self.logger.warning(f"Could not locate full text of {memo_key}, saving reference")
        self._save_memo_reference(memo_key, memo_info)
        return True

    def _save_memo_reference(self, memo_key: str, memo_info: dict) -> None:
        """Save a reference document for a memo we couldn't find in full."""
        filename = f"dod_memo_{memo_key}_reference.txt"
        if self.file_exists(filename):
            return

        content = (
            f"DoD POLICY MEMORANDUM REFERENCE\n"
            f"{'=' * 70}\n\n"
            f"TITLE: {memo_info['title']}\n\n"
            f"DESCRIPTION:\n{memo_info['description']}\n\n"
            f"STATUS: Full text not automatically located. Manual retrieval needed.\n"
            f"Search the following sources:\n"
        )
        for url in memo_info["search_urls"]:
            content += f"  - {url}\n"
        content += (
            f"\nSEARCH TERMS: {', '.join(memo_info['known_patterns'])}\n\n"
            f"NOTE: This memo is critical for discharge upgrade cases involving\n"
            f"PTSD, TBI, MST, or other mental health conditions. If you cannot\n"
            f"locate the full text online, request it via FOIA or contact the\n"
            f"appropriate service branch board.\n"
        )

        self.save_file(
            filename,
            content,
            metadata={
                "type": "dod_memo_reference",
                "memo_key": memo_key,
                "title": memo_info["title"],
                "status": "reference_only",
            }
        )

    def _collect_branch_guidance(self, branch: str, url: str, name: str) -> bool:
        """Collect service branch implementing guidance."""
        safe_branch = branch.replace(" ", "_")
        filename = f"dod_branch_{safe_branch}_guidance.html"
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True

        response = self.fetch(url)
        if not response or response.status_code != 200:
            return False

        self.save_file(
            filename,
            response.text,
            metadata={
                "type": "branch_guidance",
                "branch": branch,
                "name": name,
                "url": url,
            }
        )

        plain_text = self._extract_text(response.text, name)
        self.save_file(
            filename.replace(".html", ".txt"),
            plain_text,
            metadata={
                "type": "branch_guidance",
                "branch": branch,
                "format": "text",
            }
        )

        return True

    def _create_liberal_consideration_reference(self) -> None:
        """Create a consolidated liberal consideration reference document."""
        filename = "liberal_consideration_consolidated_reference.txt"
        if self.file_exists(filename):
            return

        content = """CONSOLIDATED REFERENCE: LIBERAL CONSIDERATION FOR DISCHARGE UPGRADES
======================================================================

OVERVIEW
--------
Liberal consideration is the standard applied by military boards (DRBs and BCMRs)
when reviewing applications for discharge upgrade or records correction from
veterans with PTSD, TBI, MST, or other mental health conditions.

REGULATORY FOUNDATION
---------------------
The liberal consideration framework derives from a series of DoD policy
memoranda issued between 2014 and 2018, building progressively broader
protections:

1. HAGEL MEMO (September 2014)
   - First directive establishing liberal consideration for PTSD
   - Directed DRBs to reconsider discharges where PTSD may have been
     a mitigating factor in misconduct leading to less-than-honorable discharge
   - Applied retroactively to all prior discharges

2. CARSON MEMO (2014)
   - Implementing guidance for the Hagel memo
   - Detailed how boards should analyze PTSD-related applications
   - Established evidentiary standards for PTSD nexus claims

3. KURTA MEMO (August 25, 2017)
   - Expanded liberal consideration to TBI, MST, and ALL mental health conditions
   - Key principle: boards should consider whether diagnosed or undiagnosed
     mental health conditions at the time of discharge may have mitigated
     the misconduct that led to the discharge characterization
   - Standards: Veterans do NOT need a PTSD/TBI/MST diagnosis from service
   - Boards should consider post-service diagnoses and evidence
   - Liberal consideration means the veteran gets benefit of the doubt

4. WILKIE MEMO (2018)
   - Extended liberal consideration to BCMR proceedings (not just DRBs)
   - Ensured BCMRs apply consistent standards across all service branches
   - Clarified that BCMRs can correct records beyond just discharge characterization

5. DOD EQUITY AND CLEMENCY GUIDANCE (August 2017)
   - Broader guidance on equity, injustice, and clemency
   - Boards should consider totality of circumstances
   - Post-service conduct is a relevant factor

KEY LEGAL PRINCIPLES
--------------------
a) A veteran need not prove a clinical diagnosis during service; post-service
   diagnosis is sufficient evidence that a condition existed during service.

b) Boards must give "liberal consideration" — which means resolving
   reasonable doubt in favor of the veteran.

c) Mental health conditions (including PTSD, TBI, MST effects) are recognized
   as potential mitigating factors for misconduct.

d) Patterns of misconduct consistent with known symptoms of mental health
   conditions support upgrade requests.

e) Service treatment records showing mental health concerns, behavioral
   changes, or substance use may indicate underlying conditions.

f) Buddy statements and lay evidence about behavioral changes during/after
   service are relevant and admissible.

APPLICATION TO VA BENEFITS
--------------------------
A successful discharge upgrade can:
- Restore full VA disability compensation eligibility
- Restore VA healthcare eligibility
- Restore GI Bill benefits
- Restore home loan guaranty
- Remove barriers to employment
- Correct the veteran's DD-214

FORMS:
- DD Form 293: Application to Discharge Review Board (DRB)
  - 15-year filing deadline from date of discharge
  - DRBs can change characterization and reason for discharge
  - Cannot change court-martial discharges

- DD Form 149: Application to Board for Correction of Military Records (BCMR)
  - 3-year filing deadline, but often waived in interest of justice
  - BCMRs can correct any military record, including discharge
  - Can upgrade court-martial discharges (unlike DRBs)
  - Broader authority than DRBs

IMPORTANT NOTE:
This document is for informational purposes only and does not constitute
legal advice. Veterans should consult with an accredited Veterans Service
Officer (VSO), VA-accredited attorney, or VA-accredited claims agent for
personalized guidance on their specific situation.
"""

        self.save_file(
            filename,
            content,
            metadata={
                "type": "consolidated_reference",
                "topic": "liberal_consideration",
            }
        )

    @staticmethod
    def _matches_memo_patterns(text: str, patterns: list[str]) -> bool:
        """Check if text matches enough memo identification patterns."""
        text_lower = text.lower()
        matches = sum(1 for p in patterns if p.lower() in text_lower)
        return matches >= 2  # Require at least 2 pattern matches

    def _extract_text(self, html: str, title: str) -> str:
        """Extract text from HTML."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()

        lines = [title, "=" * 70, ""]
        body = soup.find("main") or soup.find("body")
        if body:
            lines.append(body.get_text(separator="\n", strip=True))

        return "\n".join(lines)


def main():
    """Run the DoD memos scraper standalone."""
    scraper = DoDMemosScraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
