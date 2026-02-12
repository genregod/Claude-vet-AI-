"""
Federal Circuit Scraper — U.S. Court of Appeals for the Federal Circuit

Collects opinions in veterans law cases originating from the CAVC.
The Federal Circuit reviews CAVC decisions and its precedent is binding
on all veterans law.

Source: https://cafc.uscourts.gov/home/case-information/opinions-orders/
"""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper


class FederalCircuitScraper(BaseScraper):
    """Scraper for Federal Circuit veterans law opinions."""

    @property
    def source_name(self) -> str:
        return "federal_circuit"

    FEDCIR_BASE = "https://cafc.uscourts.gov"
    OPINIONS_URL = f"{FEDCIR_BASE}/home/case-information/opinions-orders/"
    SEARCH_URL = f"{FEDCIR_BASE}/home/case-information/opinions-orders/search/"

    # Known landmark Federal Circuit veterans law cases
    LANDMARK_CASES = [
        "Combee v. Brown",
        "Disabled American Veterans v. Secretary of Veterans Affairs",
        "Henderson v. Shinseki",
        "Nat'l Org. of Veterans' Advocates v. Secretary of Veterans Affairs",
        "Paralyzed Veterans of America v. Secretary of Veterans Affairs",
        "Wagner v. Principi",
        "NOVA v. Secretary of Veterans Affairs",
        "Cushman v. Shinseki",
        "Willoughby v. McDonald",
        "George v. McDonough",
        "Arellano v. McDonough",
        "Rudisill v. McDonough",
        "Buffington v. McDonough",
    ]

    # Veterans-related search terms to find relevant cases
    VET_SEARCH_TERMS = [
        "veterans affairs",
        "veterans claims",
        "service connection",
        "disability compensation",
        "Board of Veterans Appeals",
        "CAVC",
        "38 USC",
        "38 CFR",
        "VA benefits",
        "duty to assist",
        "benefit of the doubt",
        "standard of review veterans",
    ]

    def collect(self) -> dict:
        """Collect Federal Circuit veterans law opinions."""
        extra_stats = {
            "opinions_collected": 0,
            "landmark_found": 0,
        }

        # Step 1: Collect the opinions/orders index
        self.logger.info("Fetching Federal Circuit opinions index...")
        self._collect_opinions_index()

        # Step 2: Search for veterans-related cases
        self.logger.info("Searching for veterans law opinions...")
        for term in self.VET_SEARCH_TERMS:
            self.logger.info(f"  Search term: '{term}'")
            count = self._search_opinions(term)
            extra_stats["opinions_collected"] += count

        # Step 3: Search for specific landmark cases
        self.logger.info("Searching for landmark Federal Circuit cases...")
        for case_name in self.LANDMARK_CASES:
            self.logger.info(f"  Case: {case_name}")
            found = self._search_landmark(case_name)
            if found:
                extra_stats["landmark_found"] += 1

        return extra_stats

    def _collect_opinions_index(self) -> None:
        """Fetch the main opinions/orders page."""
        filename = "fedcir_opinions_index.html"
        if self.file_exists(filename):
            return

        response = self.fetch(self.OPINIONS_URL)
        if response and response.status_code == 200:
            self.save_file(
                filename,
                response.text,
                metadata={"type": "index", "url": self.OPINIONS_URL}
            )

    def _search_opinions(self, search_term: str) -> int:
        """Search Federal Circuit opinions for a given term."""
        count = 0
        safe_term = re.sub(r'[^\w\s]', '', search_term).replace(" ", "_")[:50]

        params = {
            "searchTerm": search_term,
            "dateFrom": "",
            "dateTo": "",
            "origin": "CAVC",  # Filter for CAVC-origin cases
        }

        response = self.fetch(self.SEARCH_URL, params=params)
        if not response or response.status_code != 200:
            return 0

        # Save search results
        results_filename = f"fedcir_search_{safe_term}.html"
        self.save_file(
            results_filename,
            response.text,
            metadata={
                "type": "search_results",
                "search_term": search_term,
            }
        )

        # Parse and download individual opinions
        soup = BeautifulSoup(response.text, "lxml")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            if self._is_opinion_document(href):
                full_url = urljoin(self.FEDCIR_BASE, href)
                saved = self._download_opinion(full_url, text)
                if saved:
                    count += 1

        return count

    def _search_landmark(self, case_name: str) -> bool:
        """Search for a specific landmark case."""
        safe_name = re.sub(r'[^\w\s-]', '', case_name).replace(" ", "_")
        filename = f"fedcir_landmark_{safe_name}.pdf"

        if self.file_exists(filename) or self.file_exists(filename.replace(".pdf", ".txt")):
            self.stats["files_skipped"] += 1
            return True

        params = {"searchTerm": case_name}
        response = self.fetch(self.SEARCH_URL, params=params)

        if not response or response.status_code != 200:
            return False

        soup = BeautifulSoup(response.text, "lxml")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if self._is_opinion_document(href):
                full_url = urljoin(self.FEDCIR_BASE, href)
                return self._download_opinion(full_url, case_name, prefix="landmark")

        return False

    def _download_opinion(self, url: str, title: str, prefix: str = "opinion") -> bool:
        """Download a single Federal Circuit opinion."""
        safe_title = re.sub(r'[^\w\s-]', '', title)[:80].strip().replace(" ", "_")
        is_pdf = url.lower().endswith(".pdf")
        ext = ".pdf" if is_pdf else ".txt"
        filename = f"fedcir_{prefix}_{safe_title}{ext}"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return False

        response = self.fetch(url)
        if not response or response.status_code != 200:
            return False

        if is_pdf:
            content = response.content
        else:
            content = self._extract_text(response.text, title)

        self.save_file(
            filename,
            content,
            metadata={
                "type": "federal_circuit_opinion",
                "title": title,
                "url": url,
                "format": "pdf" if is_pdf else "text",
            }
        )
        return True

    def _extract_text(self, html: str, title: str) -> str:
        """Extract text from an opinion HTML page."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()

        lines = [
            "U.S. COURT OF APPEALS FOR THE FEDERAL CIRCUIT",
            f"Veterans Law Case: {title}",
            "=" * 70,
            "",
        ]

        body = soup.find("body")
        if body:
            text = body.get_text(separator="\n", strip=True)
            lines.append(text)

        return "\n".join(lines)

    @staticmethod
    def _is_opinion_document(href: str) -> bool:
        """Check if a link points to an opinion document."""
        href_lower = href.lower()
        return any(ext in href_lower for ext in [".pdf", ".htm"]) and \
               not any(kw in href_lower for kw in ["login", "register", "account"])


def main():
    """Run the Federal Circuit scraper standalone."""
    scraper = FederalCircuitScraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
