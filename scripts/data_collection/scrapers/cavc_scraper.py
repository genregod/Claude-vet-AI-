"""
CAVC Scraper — U.S. Court of Appeals for Veterans Claims

Collects all published (precedential) opinions and key single-judge decisions.
The CAVC is the Article I federal court that reviews BVA decisions.

Landmark cases:
  Gilbert v. Derwinski, Caluza v. Brown, Shedden v. Principi,
  Jandreau v. Nicholson, Buchanan v. Nicholson, Vazquez-Flores v. Peake,
  Shade v. Shinseki, Bryant v. Shinseki, etc.

Source: https://www.uscourts.cavc.gov/opinions.php
"""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper


class CAVCScraper(BaseScraper):
    """Scraper for U.S. Court of Appeals for Veterans Claims opinions."""

    @property
    def source_name(self) -> str:
        return "cavc_opinions"

    CAVC_BASE = "https://www.uscourts.cavc.gov"
    OPINIONS_URL = f"{CAVC_BASE}/opinions.php"
    OPINIONS_SEARCH = f"{CAVC_BASE}/opinions_search.php"
    RULES_URL = f"{CAVC_BASE}/rules_of_practice.php"

    # Landmark CAVC cases — these are the most important precedents
    LANDMARK_CASES = [
        "Gilbert v. Derwinski",
        "Caluza v. Brown",
        "Shedden v. Principi",
        "Jandreau v. Nicholson",
        "Buchanan v. Nicholson",
        "Vazquez-Flores v. Peake",
        "Shade v. Shinseki",
        "Bryant v. Shinseki",
        "Colvin v. Derwinski",
        "Nieves-Rodriguez v. Peake",
        "Stefl v. Nicholson",
        "Barr v. Nicholson",
        "McLendon v. Nicholson",
        "Stegall v. West",
        "Gonzales v. West",
        "Dingess v. Nicholson",
        "Hickson v. West",
        "Horn v. Shinseki",
        "Mauerhan v. Principi",
        "Mittleider v. West",
        "Correia v. McDonald",
        "Sharp v. Shulkin",
        "Francway v. Wilkie",
        "Saunders v. Wilkie",
        "Procopio v. Wilkie",
        "Allen v. Brown",
        "El-Amin v. Shinseki",
        "Walker v. Shinseki",
        "Tatum v. Shinseki",
        "Rice v. Shinseki",
        "Bradley v. Peake",
        "Buie v. Shinseki",
        "Akle v. Derwinski",
        "Deluca v. Brown",
        "Esteban v. Brown",
    ]

    # Years to search for published opinions
    SEARCH_YEARS = list(range(1989, 2026))  # CAVC established in 1988

    def collect(self) -> dict:
        """Collect CAVC opinions."""
        extra_stats = {
            "opinions_collected": 0,
            "landmark_cases_found": 0,
            "years_searched": 0,
        }

        # Step 1: Fetch the main opinions page to discover structure
        self.logger.info("Fetching CAVC opinions index...")
        self._collect_opinions_index()

        # Step 2: Collect opinions by year
        self.logger.info("Collecting published opinions by year...")
        for year in self.SEARCH_YEARS:
            self.logger.info(f"  Year: {year}")
            count = self._collect_opinions_for_year(year)
            extra_stats["opinions_collected"] += count
            extra_stats["years_searched"] += 1

        # Step 3: Specifically search for landmark cases
        self.logger.info("Searching for landmark CAVC cases...")
        for case_name in self.LANDMARK_CASES:
            self.logger.info(f"  Searching: {case_name}")
            found = self._search_landmark_case(case_name)
            if found:
                extra_stats["landmark_cases_found"] += 1

        # Step 4: Collect CAVC Rules of Practice
        self.logger.info("Collecting CAVC Rules of Practice...")
        self._collect_rules()

        return extra_stats

    def _collect_opinions_index(self) -> None:
        """Fetch and parse the main opinions page."""
        response = self.fetch(self.OPINIONS_URL)
        if not response or response.status_code != 200:
            return

        self.save_file(
            "cavc_opinions_index.html",
            response.text,
            metadata={"type": "index", "url": self.OPINIONS_URL}
        )

        # Parse for opinion archive links
        soup = BeautifulSoup(response.text, "lxml")
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            if any(kw in href.lower() for kw in ["opinion", "decision", "archive"]):
                full_url = urljoin(self.CAVC_BASE, href)
                self.logger.debug(f"Found opinion link: {text} -> {full_url}")

    def _collect_opinions_for_year(self, year: int) -> int:
        """Collect all published opinions for a given year."""
        count = 0
        filename = f"cavc_opinions_{year}.html"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return 0

        # Try the opinions search with year parameter
        params = {
            "year": str(year),
            "type": "published",
        }

        response = self.fetch(self.OPINIONS_SEARCH, params=params)
        if not response or response.status_code != 200:
            # Fallback: try direct year URL patterns
            alt_url = f"{self.CAVC_BASE}/opinions_{year}.php"
            response = self.fetch(alt_url)

        if not response or response.status_code != 200:
            return 0

        soup = BeautifulSoup(response.text, "lxml")

        # Save the year index
        self.save_file(
            filename,
            response.text,
            metadata={
                "type": "cavc_year_index",
                "year": year,
                "format": "html",
            }
        )

        # Find and download individual opinion PDFs/HTMLs
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            if self._is_opinion_link(href):
                full_url = urljoin(self.CAVC_BASE, href)
                saved = self._download_opinion(full_url, text, year)
                if saved:
                    count += 1

        return count

    def _download_opinion(self, url: str, title: str, year: int) -> bool:
        """Download a single CAVC opinion."""
        # Create safe filename
        safe_title = re.sub(r'[^\w\s-]', '', title)[:80].strip().replace(" ", "_")
        ext = ".pdf" if url.lower().endswith(".pdf") else ".txt"
        filename = f"cavc_{year}_{safe_title}{ext}"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return False

        response = self.fetch(url)
        if not response or response.status_code != 200:
            return False

        if url.lower().endswith(".pdf"):
            content = response.content
        else:
            content = self._extract_opinion_text(response.text, title)

        self.save_file(
            filename,
            content,
            metadata={
                "type": "cavc_opinion",
                "title": title,
                "year": year,
                "url": url,
                "format": "pdf" if ext == ".pdf" else "text",
            }
        )
        return True

    def _search_landmark_case(self, case_name: str) -> bool:
        """Search for a specific landmark case by name."""
        safe_name = re.sub(r'[^\w\s-]', '', case_name).replace(" ", "_")
        filename = f"cavc_landmark_{safe_name}.txt"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True

        # Search the CAVC opinions search
        params = {
            "query": case_name,
            "type": "published",
        }
        response = self.fetch(self.OPINIONS_SEARCH, params=params)

        if not response or response.status_code != 200:
            self.logger.warning(f"Search failed for landmark case: {case_name}")
            return False

        soup = BeautifulSoup(response.text, "lxml")

        # Find the first matching opinion link
        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)
            if self._is_opinion_link(href):
                full_url = urljoin(self.CAVC_BASE, href)
                opinion_resp = self.fetch(full_url)
                if opinion_resp and opinion_resp.status_code == 200:
                    if full_url.lower().endswith(".pdf"):
                        content = opinion_resp.content
                    else:
                        content = self._extract_opinion_text(opinion_resp.text, case_name)

                    self.save_file(
                        filename if not full_url.endswith(".pdf") else filename.replace(".txt", ".pdf"),
                        content,
                        metadata={
                            "type": "cavc_landmark",
                            "case_name": case_name,
                            "url": full_url,
                        }
                    )
                    return True

        # Even if we can't find the full text, save the search results page
        search_text = self._extract_opinion_text(response.text, f"Search results: {case_name}")
        if len(search_text) > 200:
            self.save_file(
                f"cavc_search_{safe_name}.txt",
                search_text,
                metadata={
                    "type": "cavc_search_results",
                    "case_name": case_name,
                }
            )

        return False

    def _collect_rules(self) -> None:
        """Collect CAVC Rules of Practice and Procedure."""
        filename = "cavc_rules_of_practice.html"
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return

        response = self.fetch(self.RULES_URL)
        if response and response.status_code == 200:
            self.save_file(
                filename,
                response.text,
                metadata={
                    "type": "cavc_rules",
                    "url": self.RULES_URL,
                    "format": "html",
                }
            )

            plain_text = self._extract_opinion_text(response.text, "CAVC Rules of Practice and Procedure")
            self.save_file(
                "cavc_rules_of_practice.txt",
                plain_text,
                metadata={"type": "cavc_rules", "format": "text"}
            )

    def _extract_opinion_text(self, html: str, title: str) -> str:
        """Extract structured text from a CAVC opinion HTML page."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()

        lines = [
            "U.S. COURT OF APPEALS FOR VETERANS CLAIMS",
            title,
            "=" * 70,
            "",
        ]

        content = soup.find("div", class_=re.compile(r"content|opinion|body", re.I))
        if not content:
            content = soup.find("body")

        if content:
            for elem in content.find_all(["h1", "h2", "h3", "h4", "p", "pre", "li"]):
                text = elem.get_text(separator=" ", strip=True)
                if not text:
                    continue
                tag = elem.name
                if tag in ("h1", "h2"):
                    lines.extend(["", "=" * 60, text, "=" * 60, ""])
                elif tag in ("h3", "h4"):
                    lines.extend(["", text, "-" * min(len(text), 60), ""])
                elif tag == "pre":
                    lines.extend([text, ""])
                elif tag == "li":
                    lines.append(f"  - {text}")
                else:
                    lines.extend([text, ""])

        return "\n".join(lines)

    @staticmethod
    def _is_opinion_link(href: str) -> bool:
        """Check if an href points to an opinion document."""
        href_lower = href.lower()
        return any(ext in href_lower for ext in [".pdf", ".htm", ".html", ".txt"]) and \
               any(kw in href_lower for kw in ["opinion", "decision", "doc", "pub"])


def main():
    """Run the CAVC scraper standalone."""
    scraper = CAVCScraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
