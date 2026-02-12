"""
USC Scraper — Title 38 (Veterans' Benefits) and Title 10 Chapter 47 (UCMJ)

Collects the complete statutory text for:
  - Title 38 USC (Veterans' Benefits) — ALL chapters
  - Title 10 USC Chapter 47 (UCMJ) — Articles 1-146a
  - Manual for Courts-Martial (MCM)

Sources:
  - Office of the Law Revision Counsel: https://uscode.house.gov/
  - GovInfo: https://www.govinfo.gov/
"""

import json
import re
import xml.etree.ElementTree as ET
from typing import Optional

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper
from scripts.data_collection.config import GOVINFO_BASE


class USCScraper(BaseScraper):
    """Scraper for Title 38 USC and UCMJ (10 USC Ch. 47)."""

    @property
    def source_name(self) -> str:
        return "title_38_usc"

    # GovInfo provides bulk downloads of the US Code
    GOVINFO_USC_38 = f"{GOVINFO_BASE}/content/pkg/USCODE-2023-title38/xml/USCODE-2023-title38.xml"
    GOVINFO_USC_10 = f"{GOVINFO_BASE}/content/pkg/USCODE-2023-title10/xml/USCODE-2023-title10.xml"

    # OLRC (Office of Law Revision Counsel) web interface
    OLRC_BASE = "https://uscode.house.gov"
    OLRC_TITLE_38 = f"{OLRC_BASE}/view.xhtml?req=granuleid:USC-prelim-title38&saved=%7CZ3JhbnVsZWlkOlVTQy1wcmVsaW0tdGl0bGUzOA%3D%3D%7C&edition=prelim"
    OLRC_TITLE_10_CH47 = f"{OLRC_BASE}/view.xhtml?path=/prelim@title10/subtitleA/part2/chapter47&edition=prelim"

    # MCM (Manual for Courts-Martial) from JSC
    MCM_URL = "https://jsc.defense.gov/Portals/99/Documents/2024MCM.pdf"
    MCM_FALLBACK = "https://jsc.defense.gov/Military-Law/Current-Publications/"

    # Key chapters of Title 38 USC
    TITLE_38_CHAPTERS = {
        "11": "Compensation for Service-Connected Disability",
        "13": "Dependency and Indemnity Compensation",
        "15": "Pension for Non-Service-Connected Disability",
        "17": "Hospital, Nursing Home, Domiciliary, and Medical Care",
        "19": "Insurance",
        "20": "Benefits for Homeless Veterans",
        "21": "Specially Adapted Housing for Disabled Veterans",
        "23": "Burial Benefits",
        "30": "All-Volunteer Force Educational Assistance",
        "31": "Training and Rehabilitation for Veterans with Service-Connected Disabilities",
        "33": "Post-9/11 Educational Assistance",
        "34": "Veterans Health Care Eligibility Reform",
        "35": "Survivors and Dependents Educational Assistance",
        "36": "Administration of Educational Benefits",
        "37": "Housing and Small Business Loans",
        "39": "Automobiles and Adaptive Equipment",
        "41": "Job Counseling, Training, and Placement Service",
        "42": "Employment and Training of Veterans",
        "43": "Employment and Reemployment Rights of Members of the Uniformed Services",
        "51": "Claims, Effective Dates, and Payments",
        "53": "Special Provisions Relating to Benefits",
        "55": "Minors, Incompetents, and Other Wards",
        "57": "Records and Investigations",
        "59": "Agents and Attorneys",
        "61": "Penal and Forfeiture Provisions",
        "63": "Outreach Activities",
        "71": "Board of Veterans Appeals",
        "72": "United States Court of Appeals for Veterans Claims",
        "73": "Veterans Health Administration — Organization and Functions",
        "74": "Veterans Health Administration — Personnel",
        "76": "Health Professionals Educational Assistance Program",
        "77": "Veterans Benefits Administration",
        "78": "Veterans Canteen Service",
        "79": "Information Security Education Assistance Program",
        "81": "General",
    }

    def collect(self) -> dict:
        """Collect Title 38 USC, UCMJ, and MCM."""
        extra_stats = {
            "title_38_sections": 0,
            "ucmj_articles": 0,
        }

        # Step 1: Try GovInfo bulk XML for Title 38
        self.logger.info("Collecting Title 38 USC from GovInfo...")
        self._collect_govinfo_title38()

        # Step 2: Scrape individual chapters from OLRC website
        self.logger.info("Collecting Title 38 USC chapters from OLRC...")
        for chapter, name in self.TITLE_38_CHAPTERS.items():
            self.logger.info(f"  Chapter {chapter}: {name}")
            self._collect_olrc_chapter("38", chapter, name)
            extra_stats["title_38_sections"] += 1

        # Step 3: Collect UCMJ (10 USC Chapter 47)
        self.logger.info("Collecting UCMJ (10 USC Chapter 47)...")
        self._collect_ucmj()
        extra_stats["ucmj_articles"] += 1

        # Step 4: Collect Manual for Courts-Martial
        self.logger.info("Collecting Manual for Courts-Martial...")
        self._collect_mcm()

        return extra_stats

    def _collect_govinfo_title38(self) -> None:
        """Download Title 38 USC XML from GovInfo bulk data."""
        filename = "title_38_usc_full.xml"
        if self.file_exists(filename):
            self.logger.info("GovInfo Title 38 XML already exists, skipping")
            self.stats["files_skipped"] += 1
            return

        response = self.fetch(self.GOVINFO_USC_38)
        if response and response.status_code == 200:
            self.save_file(
                filename,
                response.content,
                metadata={
                    "type": "usc_full",
                    "title": "38",
                    "format": "xml",
                    "source_url": self.GOVINFO_USC_38,
                }
            )
        else:
            self.logger.warning("Failed to download GovInfo Title 38 XML")

    def _collect_olrc_chapter(self, title: str, chapter: str, chapter_name: str) -> None:
        """Collect a chapter of the USC from the OLRC website."""
        filename = f"title_{title}_usc_chapter_{chapter.zfill(3)}.html"
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return

        url = f"{self.OLRC_BASE}/view.xhtml?req=granuleid:USC-prelim-title{title}-chapter{chapter}&saved=%7CZ3JhbnVsZWlkOlVTQy1wcmVsaW0tdGl0bGUzOA%3D%3D%7C&edition=prelim"
        response = self.fetch(url)

        if response and response.status_code == 200:
            html = response.text
            plain_text = self._html_to_text(html, f"Title {title} USC, Chapter {chapter}: {chapter_name}")

            self.save_file(
                filename,
                html,
                metadata={
                    "type": "usc_chapter",
                    "title": title,
                    "chapter": chapter,
                    "chapter_name": chapter_name,
                    "format": "html",
                    "url": url,
                }
            )

            txt_filename = f"title_{title}_usc_chapter_{chapter.zfill(3)}.txt"
            self.save_file(
                txt_filename,
                plain_text,
                metadata={
                    "type": "usc_chapter",
                    "title": title,
                    "chapter": chapter,
                    "chapter_name": chapter_name,
                    "format": "text",
                }
            )

    def _collect_ucmj(self) -> None:
        """Collect UCMJ (10 USC Chapter 47) — Articles 1-146a."""
        # Try GovInfo for Title 10 first (entire title, will filter)
        filename_xml = "title_10_usc_ch47_ucmj.xml"
        if self.file_exists(filename_xml):
            self.stats["files_skipped"] += 1
            return

        # Fetch chapter 47 from OLRC
        url = self.OLRC_TITLE_10_CH47
        response = self.fetch(url)

        if response and response.status_code == 200:
            html = response.text
            plain_text = self._html_to_text(
                html,
                "UNIFORM CODE OF MILITARY JUSTICE (UCMJ) — 10 USC Chapter 47"
            )

            self.save_file(
                "ucmj_10_usc_ch47.html",
                html,
                metadata={
                    "type": "ucmj",
                    "title": "10",
                    "chapter": "47",
                    "format": "html",
                    "url": url,
                }
            )

            self.save_file(
                "ucmj_10_usc_ch47.txt",
                plain_text,
                metadata={
                    "type": "ucmj",
                    "title": "10",
                    "chapter": "47",
                    "format": "text",
                }
            )

        # Also try to get individual UCMJ articles
        self._collect_ucmj_articles()

    def _collect_ucmj_articles(self) -> None:
        """Collect individual UCMJ articles (10 USC 801-946a)."""
        # UCMJ articles map to 10 USC sections 801-946a
        # Article 1 = 10 USC 801, Article 2 = 10 USC 802, etc.
        ucmj_section_ranges = [
            (801, 806),    # Articles 1-6 (General Provisions)
            (806, 821),    # Apprehension and Restraint
            (821, 836),    # Non-Judicial Punishment
            (836, 843),    # Pre-Trial Procedure
            (843, 876),    # Trial Procedure
            (876, 940),    # Punitive Articles
            (940, 947),    # Post-Trial Procedure and Review
        ]

        for start, end in ucmj_section_ranges:
            for section in range(start, end + 1):
                section_str = str(section)
                filename = f"ucmj_10usc_{section_str}.txt"
                if self.file_exists(filename):
                    self.stats["files_skipped"] += 1
                    continue

                url = f"{self.OLRC_BASE}/view.xhtml?req=granuleid:USC-prelim-title10-section{section_str}&edition=prelim"
                response = self.fetch(url)
                if response and response.status_code == 200:
                    text = self._html_to_text(
                        response.text,
                        f"10 USC § {section_str} (UCMJ)"
                    )
                    self.save_file(
                        filename,
                        text,
                        metadata={
                            "type": "ucmj_article",
                            "title": "10",
                            "section": section_str,
                        }
                    )

    def _collect_mcm(self) -> None:
        """Download the Manual for Courts-Martial PDF."""
        filename = "manual_for_courts_martial.pdf"
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return

        response = self.fetch(self.MCM_URL)
        if response and response.status_code == 200:
            self.save_file(
                filename,
                response.content,
                metadata={
                    "type": "mcm",
                    "format": "pdf",
                    "url": self.MCM_URL,
                }
            )
        else:
            self.logger.warning("Failed to download MCM, trying fallback page...")
            response = self.fetch(self.MCM_FALLBACK)
            if response and response.status_code == 200:
                # Parse the publications page for PDF links
                soup = BeautifulSoup(response.text, "lxml")
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if "mcm" in href.lower() and href.endswith(".pdf"):
                        pdf_url = href if href.startswith("http") else f"https://jsc.defense.gov{href}"
                        pdf_resp = self.fetch(pdf_url)
                        if pdf_resp and pdf_resp.status_code == 200:
                            self.save_file(
                                filename,
                                pdf_resp.content,
                                metadata={
                                    "type": "mcm",
                                    "format": "pdf",
                                    "url": pdf_url,
                                }
                            )
                            break

    def _html_to_text(self, html: str, header: str) -> str:
        """Convert HTML to structured plain text."""
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        lines = [header, "=" * 70, ""]

        for element in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            tag = element.name
            if tag in ("h1", "h2"):
                lines.extend(["", "=" * 60, text, "=" * 60, ""])
            elif tag == "h3":
                lines.extend(["", "-" * 50, text, "-" * 50, ""])
            elif tag in ("h4", "h5", "h6"):
                lines.extend(["", text, "-" * min(len(text), 50), ""])
            elif tag == "li":
                lines.append(f"  • {text}")
            else:
                lines.extend([text, ""])

        return "\n".join(lines)


class UCMJScraper(BaseScraper):
    """Dedicated scraper for UCMJ materials (saves to separate directory)."""

    @property
    def source_name(self) -> str:
        return "ucmj_10_usc"

    def collect(self) -> dict:
        """Collect UCMJ via the USC scraper and copy relevant files."""
        usc = USCScraper()
        # Only collect the UCMJ portions
        self.logger.info("Collecting UCMJ from USC scraper...")
        usc._collect_ucmj()
        usc._collect_mcm()

        # Copy stats
        return {
            "ucmj_files": usc.stats["files_downloaded"],
        }


def main():
    """Run the USC scraper standalone."""
    scraper = USCScraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
