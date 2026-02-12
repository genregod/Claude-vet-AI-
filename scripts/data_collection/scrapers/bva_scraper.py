"""
BVA Decisions Scraper — Board of Veterans' Appeals

Collects precedential and non-precedential BVA decisions.
Target: 10,000+ decisions across all major claim types.

Priority conditions:
  - PTSD, TBI, MST, tinnitus, back/knee conditions, sleep apnea,
    mental health, Gulf War illness, Agent Orange, burn pit exposure

Source: https://www.index.va.gov/search/va/bva.jsp
"""

import json
import re
import time
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper


class BVAScraper(BaseScraper):
    """Scraper for Board of Veterans' Appeals decisions."""

    @property
    def source_name(self) -> str:
        return "bva_decisions"

    BVA_SEARCH_URL = "https://www.index.va.gov/search/va/bva.jsp"
    BVA_SEARCH_API = "https://www.index.va.gov/search/va/bva_search.jsp"

    # Search terms grouped by claim type — will search for decisions on each
    SEARCH_QUERIES = {
        "ptsd": [
            "PTSD service connection",
            "post-traumatic stress disorder combat",
            "PTSD stressor verification",
            "PTSD 70 percent rating",
            "PTSD total disability",
        ],
        "tbi": [
            "traumatic brain injury service connection",
            "TBI residuals rating",
            "TBI secondary conditions",
        ],
        "mst": [
            "military sexual trauma",
            "MST PTSD claim",
            "personal assault stressor",
        ],
        "tinnitus": [
            "tinnitus service connection",
            "tinnitus bilateral rating",
        ],
        "back": [
            "lumbar spine service connection",
            "back condition rating increase",
            "degenerative disc disease veteran",
            "intervertebral disc syndrome",
        ],
        "knee": [
            "knee condition service connection",
            "knee replacement veteran",
            "knee instability rating",
        ],
        "sleep_apnea": [
            "sleep apnea service connection",
            "sleep apnea secondary to PTSD",
            "sleep apnea rating criteria",
        ],
        "mental_health": [
            "major depressive disorder service connection",
            "anxiety disorder veteran",
            "bipolar disorder service connection",
            "schizophrenia veteran",
        ],
        "gulf_war": [
            "Gulf War illness presumptive",
            "undiagnosed illness Southwest Asia",
            "chronic fatigue syndrome Gulf War",
            "fibromyalgia Gulf War",
            "irritable bowel syndrome Gulf War",
        ],
        "agent_orange": [
            "Agent Orange presumptive condition",
            "herbicide exposure Vietnam",
            "Agent Orange diabetes",
            "Agent Orange heart disease",
            "Agent Orange prostate cancer",
        ],
        "burn_pit": [
            "burn pit exposure",
            "toxic exposure presumptive",
            "PACT Act claim",
            "respiratory condition burn pit",
        ],
        "secondary_conditions": [
            "secondary service connection",
            "aggravation secondary condition",
        ],
        "tdiu": [
            "individual unemployability TDIU",
            "total disability based on individual unemployability",
        ],
        "smc": [
            "special monthly compensation",
            "aid and attendance",
            "housebound benefits",
        ],
        "cue": [
            "clear and unmistakable error",
            "CUE prior decision",
        ],
        "effective_date": [
            "earlier effective date",
            "effective date service connection",
        ],
        "discharge": [
            "character of discharge",
            "other than honorable discharge VA benefits",
            "discharge upgrade eligibility",
        ],
    }

    # Maximum decisions per search query
    MAX_PER_QUERY = 100
    # Target total decisions
    TARGET_TOTAL = 10000

    def collect(self) -> dict:
        """Collect BVA decisions across all claim categories."""
        extra_stats = {
            "decisions_collected": 0,
            "categories_searched": 0,
            "search_queries_run": 0,
        }

        total_collected = 0

        for category, queries in self.SEARCH_QUERIES.items():
            self.logger.info(f"Searching BVA decisions for category: {category}")
            extra_stats["categories_searched"] += 1

            for query in queries:
                if total_collected >= self.TARGET_TOTAL:
                    self.logger.info(f"Reached target of {self.TARGET_TOTAL} decisions")
                    return extra_stats

                self.logger.info(f"  Query: '{query}'")
                decisions = self._search_bva(query, category)
                extra_stats["search_queries_run"] += 1

                for decision in decisions:
                    saved = self._save_decision(decision, category)
                    if saved:
                        total_collected += 1
                        extra_stats["decisions_collected"] += 1

                self.logger.info(f"  Found {len(decisions)} decisions for '{query}'")

        return extra_stats

    def _search_bva(self, query: str, category: str) -> list[dict]:
        """
        Search the BVA decision database.

        Returns list of decision dicts with metadata.
        """
        decisions = []

        # The BVA search interface uses form POST
        params = {
            "RPP": "20",           # Results per page
            "RS": "0",             # Result start
            "is498": "true",
            "queryText": query,
            "submit": "Search",
        }

        offset = 0
        while len(decisions) < self.MAX_PER_QUERY:
            params["RS"] = str(offset)

            response = self.fetch(
                self.BVA_SEARCH_API,
                params=params,
            )

            if not response or response.status_code != 200:
                break

            new_decisions = self._parse_search_results(response.text, category, query)
            if not new_decisions:
                break

            decisions.extend(new_decisions)
            offset += 20

            # Don't hammer the server
            time.sleep(1)

        return decisions[:self.MAX_PER_QUERY]

    def _parse_search_results(self, html: str, category: str, query: str) -> list[dict]:
        """Parse BVA search results page."""
        decisions = []
        soup = BeautifulSoup(html, "lxml")

        # BVA search results typically contain links to decision documents
        for result in soup.find_all(["div", "tr"], class_=re.compile(r"result|record|row", re.I)):
            decision = self._extract_decision_metadata(result, category, query)
            if decision:
                decisions.append(decision)

        # Fallback: look for any links that look like BVA decisions
        if not decisions:
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                if self._looks_like_bva_decision(href, text):
                    full_url = urljoin(self.BVA_SEARCH_URL, href)
                    decisions.append({
                        "url": full_url,
                        "title": text,
                        "category": category,
                        "query": query,
                        "docket_number": self._extract_docket(text) or "unknown",
                    })

        return decisions

    def _extract_decision_metadata(self, element, category: str, query: str) -> Optional[dict]:
        """Extract decision metadata from a search result element."""
        links = element.find_all("a", href=True)
        text = element.get_text(separator=" ", strip=True)

        if not links and not text:
            return None

        url = None
        for link in links:
            href = link["href"]
            if self._looks_like_bva_decision(href, link.get_text()):
                url = urljoin(self.BVA_SEARCH_URL, href)
                break

        if not url:
            return None

        # Extract docket number (format: XXXXXXX-XX)
        docket_match = re.search(r'\b(\d{7}[-/]\d{2})\b', text)
        docket = docket_match.group(1) if docket_match else "unknown"

        # Extract date
        date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{2,4})', text)
        date = date_match.group(1) if date_match else "unknown"

        return {
            "url": url,
            "title": text[:200],
            "docket_number": docket,
            "date": date,
            "category": category,
            "query": query,
        }

    def _save_decision(self, decision: dict, category: str) -> bool:
        """Download and save a BVA decision."""
        docket = re.sub(r'[^\w-]', '_', decision.get("docket_number", "unknown"))
        filename = f"bva_{category}_{docket}.txt"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return False

        url = decision.get("url")
        if not url:
            return False

        response = self.fetch(url)
        if not response or response.status_code != 200:
            return False

        # Extract the decision text
        text = self._extract_decision_text(response.text, decision)

        if len(text) < 200:
            self.logger.debug(f"Decision too short, skipping: {docket}")
            return False

        self.save_file(
            filename,
            text,
            metadata={
                "type": "bva_decision",
                "docket_number": decision.get("docket_number"),
                "date": decision.get("date"),
                "category": category,
                "query": decision.get("query"),
                "url": url,
            }
        )
        return True

    def _extract_decision_text(self, html: str, decision: dict) -> str:
        """Extract the full text of a BVA decision from HTML."""
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        lines = [
            "BOARD OF VETERANS' APPEALS DECISION",
            f"Docket: {decision.get('docket_number', 'Unknown')}",
            f"Date: {decision.get('date', 'Unknown')}",
            f"Category: {decision.get('category', 'Unknown')}",
            "=" * 70,
            "",
        ]

        # Look for the main content area
        content = soup.find("div", class_=re.compile(r"content|decision|body", re.I))
        if not content:
            content = soup.find("pre")  # Some BVA decisions are in <pre> tags
        if not content:
            content = soup.find("body")

        if content:
            text = content.get_text(separator="\n", strip=True)
            lines.append(text)

        return "\n".join(lines)

    @staticmethod
    def _looks_like_bva_decision(href: str, text: str) -> bool:
        """Check if a link looks like it points to a BVA decision."""
        combined = f"{href} {text}".lower()
        indicators = [
            ".txt", "citation", "bva", "decision",
            "docket", "board of veterans",
        ]
        return any(ind in combined for ind in indicators)

    @staticmethod
    def _extract_docket(text: str) -> Optional[str]:
        """Extract a BVA docket number from text."""
        match = re.search(r'\b(\d{7}[-/]\d{2})\b', text)
        return match.group(1) if match else None


def main():
    """Run the BVA scraper standalone."""
    scraper = BVAScraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
