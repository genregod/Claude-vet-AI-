"""
VA M21-1 Adjudication Procedures Manual Scraper

Collects the complete VA M21-1 manual — the internal playbook VA adjudicators
use when rating disability claims.

Parts I-XVI including all sections, subsections, and appendices.
Priority: Part III (Claims), Part IV (Rating Procedures), Part V (Appeals)

Source: https://www.knowva.ebenefits.va.gov/ and web archive fallbacks
"""

import json
import re
from typing import Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper


class VAM21Scraper(BaseScraper):
    """Scraper for the VA M21-1 Adjudication Procedures Manual."""

    @property
    def source_name(self) -> str:
        return "va_m21_1_manual"

    # KnowVA base (the VA's internal knowledge management system, publicly accessible)
    KNOWVA_BASE = "https://www.knowva.ebenefits.va.gov"
    KNOWVA_M21_PORTAL = (
        f"{KNOWVA_BASE}/system/templates/selfservice/va_ssnew/"
        "help/customer/locale/en-US/portal/554400000001018/"
    )

    # Web Archive fallback for older/missing content
    WAYBACK_BASE = "https://web.archive.org/web/2024"

    # M21-1 Parts structure (Roman numerals I-XVI)
    M21_PARTS = {
        "I": "Introduction and General Information",
        "II": "Duty to Notify, Duty to Assist, and Evidence Gathering",
        "III": "General Claims Process",
        "IV": "Rating Procedures",
        "V": "Appeals",
        "VI": "Decision Reviews Under the Appeals Modernization Act",
        "VII": "Benefit Type Determination",
        "VIII": "Compensation",
        "IX": "Pension and Parents Dependency and Indemnity Compensation",
        "X": "Dependency and Indemnity Compensation",
        "XI": "Special Monthly Compensation",
        "XII": "Special Considerations",
        "XIII": "Education and Training",
        "XIV": "Vocational Rehabilitation and Employment",
        "XV": "Administration",
        "XVI": "Appendices",
    }

    def collect(self) -> dict:
        """Collect the full M21-1 manual."""
        extra_stats = {"parts_collected": 0, "sections_collected": 0}

        # Step 1: Fetch the main portal page to discover navigation links
        self.logger.info("Fetching M21-1 portal page...")
        portal_links = self._discover_portal_links()

        # Step 2: If portal discovery succeeded, crawl discovered links
        if portal_links:
            self.logger.info(f"Discovered {len(portal_links)} links from M21-1 portal")
            for link_url, link_text in portal_links:
                self._collect_manual_page(link_url, link_text)
                extra_stats["sections_collected"] += 1
        else:
            self.logger.warning("Portal discovery failed, using direct part URLs")

        # Step 3: Try to collect each known part directly
        for part_num, part_name in self.M21_PARTS.items():
            self.logger.info(f"Collecting M21-1 Part {part_num}: {part_name}")
            success = self._collect_part(part_num, part_name)
            if success:
                extra_stats["parts_collected"] += 1

        # Step 4: Try the Wayback Machine for any missing content
        self.logger.info("Checking Wayback Machine for additional M21-1 content...")
        self._collect_from_wayback()

        return extra_stats

    def _discover_portal_links(self) -> list[tuple[str, str]]:
        """Discover all M21-1 content links from the KnowVA portal."""
        links = []
        response = self.fetch(self.KNOWVA_M21_PORTAL)

        if not response or response.status_code != 200:
            return links

        soup = BeautifulSoup(response.text, "lxml")

        # Save the portal page itself
        self.save_file(
            "m21_1_portal_index.html",
            response.text,
            metadata={"type": "m21_1_portal", "url": self.KNOWVA_M21_PORTAL}
        )

        # Find all links that look like M21-1 content pages
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            text = a_tag.get_text(strip=True)

            # Filter for relevant links
            if any(kw in href.lower() or kw in text.lower() for kw in [
                "m21", "adjudication", "rating", "compensation",
                "claims", "appeals", "pension", "smc"
            ]):
                full_url = urljoin(self.KNOWVA_BASE, href)
                links.append((full_url, text))

        return links

    def _collect_manual_page(self, url: str, title: str) -> None:
        """Collect a single manual page."""
        # Create a safe filename from the URL
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").replace("/", "_")
        safe_title = re.sub(r'[^\w\s-]', '', title)[:80].strip()
        filename = f"m21_1_{path_parts}_{safe_title}.html"
        filename = re.sub(r'\s+', '_', filename)

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return

        response = self.fetch(url)
        if response and response.status_code == 200:
            html = response.text
            plain_text = self._extract_manual_text(html, title)

            self.save_file(
                filename,
                html,
                metadata={
                    "type": "m21_1_section",
                    "title": title,
                    "url": url,
                    "format": "html",
                }
            )

            txt_filename = filename.replace(".html", ".txt")
            self.save_file(
                txt_filename,
                plain_text,
                metadata={
                    "type": "m21_1_section",
                    "title": title,
                    "format": "text",
                }
            )

            # Discover and follow sub-links
            soup = BeautifulSoup(html, "lxml")
            for sub_link in soup.find_all("a", href=True):
                sub_href = sub_link["href"]
                sub_text = sub_link.get_text(strip=True)
                if self._is_m21_content_link(sub_href, sub_text):
                    sub_url = urljoin(url, sub_href)
                    safe_sub = re.sub(r'[^\w]', '_', sub_text)[:60]
                    sub_filename = f"m21_1_sub_{safe_sub}.html"
                    if not self.file_exists(sub_filename):
                        self._collect_manual_page(sub_url, sub_text)

    def _collect_part(self, part_num: str, part_name: str) -> bool:
        """Attempt to collect a specific M21-1 part."""
        filename = f"m21_1_part_{part_num}.html"
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True

        # Try various URL patterns used by KnowVA
        urls_to_try = [
            f"{self.KNOWVA_M21_PORTAL}content/M21-1-Part-{part_num}",
            f"{self.KNOWVA_M21_PORTAL}?id=M21-1-Part-{part_num}",
            f"{self.KNOWVA_BASE}/system/templates/selfservice/va_ssnew/help/customer/locale/en-US/portal/554400000001018/content/M21-1-Part-{part_num}",
        ]

        for url in urls_to_try:
            response = self.fetch(url)
            if response and response.status_code == 200:
                # Check if we got actual content (not just a redirect/error page)
                if len(response.text) > 500:
                    plain_text = self._extract_manual_text(response.text, f"M21-1 Part {part_num}: {part_name}")

                    self.save_file(
                        filename,
                        response.text,
                        metadata={
                            "type": "m21_1_part",
                            "part": part_num,
                            "part_name": part_name,
                            "format": "html",
                            "url": url,
                        }
                    )

                    self.save_file(
                        f"m21_1_part_{part_num}.txt",
                        plain_text,
                        metadata={
                            "type": "m21_1_part",
                            "part": part_num,
                            "part_name": part_name,
                            "format": "text",
                        }
                    )
                    return True

        self.logger.warning(f"Could not collect M21-1 Part {part_num}")
        return False

    def _collect_from_wayback(self) -> None:
        """Try Wayback Machine for M21-1 content."""
        # Known archived URLs for M21-1
        wayback_urls = [
            f"{self.WAYBACK_BASE}/https://www.knowva.ebenefits.va.gov/system/templates/selfservice/va_ssnew/help/customer/locale/en-US/portal/554400000001018/",
        ]

        for url in wayback_urls:
            filename = "m21_1_wayback_index.html"
            if self.file_exists(filename):
                continue

            response = self.fetch(url, respect_robots=False)
            if response and response.status_code == 200:
                self.save_file(
                    filename,
                    response.text,
                    metadata={
                        "type": "m21_1_wayback",
                        "url": url,
                        "format": "html",
                    }
                )

    def _extract_manual_text(self, html: str, title: str) -> str:
        """Extract structured text from an M21-1 HTML page."""
        soup = BeautifulSoup(html, "lxml")

        for tag in soup(["script", "style", "nav"]):
            tag.decompose()

        lines = [
            "VA ADJUDICATION PROCEDURES MANUAL (M21-1)",
            title,
            "=" * 70,
            "",
        ]

        # M21-1 uses specific content structures
        content_div = soup.find("div", class_="content") or soup.find("main") or soup.find("body")
        if not content_div:
            content_div = soup

        for element in content_div.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th"]):
            text = element.get_text(separator=" ", strip=True)
            if not text:
                continue

            tag = element.name
            if tag in ("h1", "h2"):
                lines.extend(["", "=" * 60, text, "=" * 60, ""])
            elif tag in ("h3", "h4"):
                lines.extend(["", "-" * 50, text, "-" * 50, ""])
            elif tag in ("h5", "h6"):
                lines.extend(["", text, ""])
            elif tag == "li":
                lines.append(f"  • {text}")
            elif tag in ("td", "th"):
                lines.append(f"  | {text}")
            else:
                lines.extend([text, ""])

        return "\n".join(lines)

    @staticmethod
    def _is_m21_content_link(href: str, text: str) -> bool:
        """Determine if a link points to M21-1 content."""
        combined = f"{href} {text}".lower()
        m21_indicators = [
            "m21-1", "m21_1", "adjudication", "rating procedure",
            "claims process", "compensation", "service connection",
        ]
        exclusions = [
            "javascript:", "mailto:", "#", "login", "logout",
        ]

        if any(ex in href.lower() for ex in exclusions):
            return False

        return any(ind in combined for ind in m21_indicators)


def main():
    """Run the M21-1 scraper standalone."""
    scraper = VAM21Scraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
