"""
BCMR & DRB Scrapers — Board for Correction of Military Records and
Discharge Review Boards for all service branches.

BCMR boards:
  - Army (ABCMR)
  - Navy/Marines (BCNR)
  - Air Force/Space Force (AFBCMR)
  - Coast Guard (BCMR-CG)

DRB boards:
  - Army DRB (ADRB)
  - Navy DRB (NDRB)
  - Air Force DRB (AFDRB)

Collects:
  - Board procedures and application instructions
  - Published decisions/case summaries
  - DD Form 149 and DD Form 293 instructions
  - Standards of review
  - Discharge upgrade standards (Hagel, Kurta, Wilkie memos)
"""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper
from scripts.data_collection.config import (
    ABCMR_URL, BCNR_URL, AFBCMR_URL,
    ARMY_DRB_URL, NAVY_DRB_URL, AF_DRB_URL,
)


class BCMRScraper(BaseScraper):
    """Scraper for Board for Correction of Military Records (all branches)."""

    @property
    def source_name(self) -> str:
        return "bcmr_decisions"

    # All BCMR board URLs and their configurations
    BOARDS = {
        "army_abcmr": {
            "name": "Army Board for Correction of Military Records (ABCMR)",
            "url": ABCMR_URL,
            "base_url": "https://arba.army.pentagon.mil",
            "branch": "Army",
        },
        "navy_bcnr": {
            "name": "Board for Correction of Naval Records (BCNR)",
            "url": BCNR_URL,
            "base_url": "https://www.secnav.navy.mil",
            "branch": "Navy/Marines",
        },
        "af_afbcmr": {
            "name": "Air Force Board for Correction of Military Records (AFBCMR)",
            "url": AFBCMR_URL,
            "base_url": "https://www.afpc.af.mil",
            "branch": "Air Force/Space Force",
        },
    }

    def collect(self) -> dict:
        """Collect BCMR materials from all branches."""
        extra_stats = {
            "boards_collected": 0,
            "decisions_found": 0,
            "procedures_collected": 0,
        }

        for board_key, board_info in self.BOARDS.items():
            self.logger.info(f"Collecting {board_info['name']}...")

            # Collect main board page
            main_collected = self._collect_board_main(board_key, board_info)
            if main_collected:
                extra_stats["boards_collected"] += 1

            # Crawl for decisions and procedures
            pages = self._crawl_board_pages(board_key, board_info)
            extra_stats["decisions_found"] += pages.get("decisions", 0)
            extra_stats["procedures_collected"] += pages.get("procedures", 0)

        # Collect DD Form 149 information
        self.logger.info("Collecting DD Form 149 information...")
        self._collect_dd_form_149()

        return extra_stats

    def _collect_board_main(self, board_key: str, board_info: dict) -> bool:
        """Collect the main page for a BCMR board."""
        filename = f"bcmr_{board_key}_main.html"
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True

        response = self.fetch(board_info["url"])
        if not response or response.status_code != 200:
            return False

        html = response.text
        plain_text = self._extract_board_text(html, board_info["name"])

        self.save_file(
            filename,
            html,
            metadata={
                "type": "bcmr_board_main",
                "board": board_key,
                "branch": board_info["branch"],
                "url": board_info["url"],
                "format": "html",
            }
        )

        self.save_file(
            f"bcmr_{board_key}_main.txt",
            plain_text,
            metadata={
                "type": "bcmr_board_main",
                "board": board_key,
                "branch": board_info["branch"],
                "format": "text",
            }
        )

        return True

    def _crawl_board_pages(self, board_key: str, board_info: dict) -> dict:
        """Crawl a board's website for decisions and procedural documents."""
        result = {"decisions": 0, "procedures": 0}

        response = self.fetch(board_info["url"])
        if not response or response.status_code != 200:
            return result

        soup = BeautifulSoup(response.text, "lxml")
        visited = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            full_url = urljoin(board_info["base_url"], href)

            if full_url in visited:
                continue
            visited.add(full_url)

            # Classify the link
            combined = f"{href} {text}".lower()

            if any(kw in combined for kw in ["decision", "case", "summary", "record"]):
                saved = self._download_board_document(
                    full_url, text, board_key, "decision"
                )
                if saved:
                    result["decisions"] += 1

            elif any(kw in combined for kw in [
                "procedure", "instruction", "guide", "apply",
                "application", "form", "standard", "review"
            ]):
                saved = self._download_board_document(
                    full_url, text, board_key, "procedure"
                )
                if saved:
                    result["procedures"] += 1

        return result

    def _download_board_document(self, url: str, title: str,
                                  board_key: str, doc_type: str) -> bool:
        """Download a board document (decision or procedure)."""
        safe_title = re.sub(r'[^\w\s-]', '', title)[:60].strip().replace(" ", "_")
        is_pdf = url.lower().endswith(".pdf")
        ext = ".pdf" if is_pdf else ".txt"
        filename = f"bcmr_{board_key}_{doc_type}_{safe_title}{ext}"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return False

        response = self.fetch(url)
        if not response or response.status_code != 200:
            return False

        if is_pdf:
            content = response.content
        else:
            content = self._extract_board_text(response.text, title)

        if isinstance(content, str) and len(content) < 100:
            return False

        self.save_file(
            filename,
            content,
            metadata={
                "type": f"bcmr_{doc_type}",
                "board": board_key,
                "title": title,
                "url": url,
                "format": "pdf" if is_pdf else "text",
            }
        )
        return True

    def _collect_dd_form_149(self) -> None:
        """Collect DD Form 149 instructions and requirements."""
        filename = "dd_form_149_info.txt"
        if self.file_exists(filename):
            return

        # DD Form 149 info is typically found on BCMR pages
        info_text = (
            "DD FORM 149 — APPLICATION FOR CORRECTION OF MILITARY RECORD\n"
            "=" * 70 + "\n\n"
            "DD Form 149 is the standard form used to apply to the Board for\n"
            "Correction of Military Records (BCMR) of the appropriate service branch.\n\n"
            "KEY SECTIONS:\n"
            "- Block 1: Personal Information\n"
            "- Block 7: Type of Correction Requested\n"
            "- Block 8: Justification/Rationale (most important section)\n"
            "- Block 9: Supporting Documents\n\n"
            "FILING DEADLINE: Generally 3 years from discovery of the error,\n"
            "but boards may waive the time limit in the interest of justice.\n\n"
            "LIBERAL CONSIDERATION: Under the Hagel, Kurta, and Wilkie memos,\n"
            "boards must apply liberal consideration standards for applications\n"
            "involving PTSD, TBI, MST, or other mental health conditions.\n"
        )

        self.save_file(
            filename,
            info_text,
            metadata={"type": "form_info", "form": "DD-149"}
        )

    def _extract_board_text(self, html: str, title: str) -> str:
        """Extract text from a BCMR/DRB HTML page."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        lines = [
            "BOARD FOR CORRECTION OF MILITARY RECORDS",
            title,
            "=" * 70,
            "",
        ]

        body = soup.find("main") or soup.find("div", class_=re.compile(r"content", re.I)) or soup.find("body")
        if body:
            for elem in body.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
                text = elem.get_text(separator=" ", strip=True)
                if not text:
                    continue
                tag = elem.name
                if tag in ("h1", "h2"):
                    lines.extend(["", "=" * 60, text, "=" * 60, ""])
                elif tag in ("h3", "h4"):
                    lines.extend(["", text, "-" * min(len(text), 60), ""])
                elif tag == "li":
                    lines.append(f"  - {text}")
                else:
                    lines.extend([text, ""])

        return "\n".join(lines)


class DRBScraper(BaseScraper):
    """Scraper for Discharge Review Boards (all branches)."""

    @property
    def source_name(self) -> str:
        return "drb_decisions"

    BOARDS = {
        "army_adrb": {
            "name": "Army Discharge Review Board (ADRB)",
            "url": ARMY_DRB_URL,
            "base_url": "https://arba.army.pentagon.mil",
            "branch": "Army",
        },
        "navy_ndrb": {
            "name": "Navy Discharge Review Board (NDRB)",
            "url": NAVY_DRB_URL,
            "base_url": "https://www.secnav.navy.mil",
            "branch": "Navy/Marines",
        },
        "af_afdrb": {
            "name": "Air Force Discharge Review Board (AFDRB)",
            "url": AF_DRB_URL,
            "base_url": "https://www.afpc.af.mil",
            "branch": "Air Force",
        },
    }

    def collect(self) -> dict:
        """Collect DRB materials from all branches."""
        extra_stats = {
            "boards_collected": 0,
            "documents_collected": 0,
        }

        for board_key, board_info in self.BOARDS.items():
            self.logger.info(f"Collecting {board_info['name']}...")

            # Collect main page
            filename = f"drb_{board_key}_main.html"
            if self.file_exists(filename):
                self.stats["files_skipped"] += 1
                extra_stats["boards_collected"] += 1
                continue

            response = self.fetch(board_info["url"])
            if not response or response.status_code != 200:
                continue

            html = response.text
            soup = BeautifulSoup(html, "lxml")
            for tag in soup(["script", "style", "nav"]):
                tag.decompose()

            plain_text_lines = [
                f"DISCHARGE REVIEW BOARD — {board_info['branch']}",
                board_info["name"],
                "=" * 70, "",
            ]
            body = soup.find("main") or soup.find("body")
            if body:
                plain_text_lines.append(body.get_text(separator="\n", strip=True))

            self.save_file(
                filename,
                html,
                metadata={
                    "type": "drb_main",
                    "board": board_key,
                    "branch": board_info["branch"],
                    "url": board_info["url"],
                }
            )

            self.save_file(
                f"drb_{board_key}_main.txt",
                "\n".join(plain_text_lines),
                metadata={
                    "type": "drb_main",
                    "board": board_key,
                    "branch": board_info["branch"],
                    "format": "text",
                }
            )

            extra_stats["boards_collected"] += 1

            # Crawl for linked documents
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                combined = f"{href} {text}".lower()

                if any(kw in combined for kw in [
                    "decision", "procedure", "form", "application",
                    "instruction", "guide", "standard", "dd-293", "dd293"
                ]):
                    full_url = urljoin(board_info["base_url"], href)
                    safe = re.sub(r'[^\w\s-]', '', text)[:50].replace(" ", "_")
                    doc_filename = f"drb_{board_key}_{safe}"
                    ext = ".pdf" if href.lower().endswith(".pdf") else ".html"
                    doc_filename += ext

                    if not self.file_exists(doc_filename):
                        doc_resp = self.fetch(full_url)
                        if doc_resp and doc_resp.status_code == 200:
                            content = doc_resp.content if ext == ".pdf" else doc_resp.text
                            self.save_file(
                                doc_filename,
                                content,
                                metadata={
                                    "type": "drb_document",
                                    "board": board_key,
                                    "title": text,
                                    "url": full_url,
                                }
                            )
                            extra_stats["documents_collected"] += 1

        # Collect DD Form 293 info
        self._collect_dd_form_293_info()

        return extra_stats

    def _collect_dd_form_293_info(self) -> None:
        """Create DD Form 293 reference information."""
        filename = "dd_form_293_info.txt"
        if self.file_exists(filename):
            return

        info_text = (
            "DD FORM 293 — APPLICATION FOR REVIEW OF DISCHARGE\n"
            "=" * 70 + "\n\n"
            "DD Form 293 is used to apply to a Discharge Review Board (DRB)\n"
            "to request a change in the character of or reason for discharge.\n\n"
            "KEY INFORMATION:\n"
            "- DRBs can upgrade discharges from Under Other Than Honorable (UOTHC)\n"
            "  to General (Under Honorable Conditions) or Honorable.\n"
            "- DRBs CANNOT change discharges issued by courts-martial (BCD, DD).\n"
            "- Filing deadline: 15 years from date of discharge.\n"
            "- Two review options: Documentary Review or Personal Hearing.\n\n"
            "HEARING TYPES:\n"
            "- Documentary Review: Board reviews application and records only.\n"
            "- Personal Appearance: Veteran appears before the board (DC area).\n\n"
            "LIBERAL CONSIDERATION APPLIES:\n"
            "Under Hagel (2014), Kurta (2017), and Wilkie (2018) memos,\n"
            "DRBs must give liberal consideration to applications involving\n"
            "PTSD, TBI, MST, or other mental health conditions that may have\n"
            "contributed to the misconduct leading to discharge.\n"
        )

        self.save_file(
            filename,
            info_text,
            metadata={"type": "form_info", "form": "DD-293"}
        )


def main():
    """Run both BCMR and DRB scrapers."""
    bcmr = BCMRScraper()
    bcmr_stats = bcmr.run()
    print("BCMR:", json.dumps(bcmr_stats, indent=2))

    drb = DRBScraper()
    drb_stats = drb.run()
    print("DRB:", json.dumps(drb_stats, indent=2))


if __name__ == "__main__":
    main()
