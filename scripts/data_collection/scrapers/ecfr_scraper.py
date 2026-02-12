"""
eCFR Scraper — Title 38 Code of Federal Regulations

Collects the complete body of VA regulations from the official eCFR API.
Priority sections:
  - Part 3: Adjudication
  - Part 4: Schedule for Rating Disabilities (VASRD)
  - Part 17: Medical care eligibility
  - Part 19: Board of Veterans' Appeals rules of practice
  - Part 20: Board of Veterans' Appeals appeals regulations
  - Part 21: Vocational Rehabilitation and Education

Source: https://www.ecfr.gov/api/versioner/v1
"""

import json
import re
import xml.etree.ElementTree as ET
from typing import Optional

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper
from scripts.data_collection.config import ECFR_API_BASE


class ECFRScraper(BaseScraper):
    """Scraper for Title 38 CFR from the eCFR API."""

    @property
    def source_name(self) -> str:
        return "title_38_cfr"

    # eCFR REST API endpoints
    STRUCTURE_URL = f"{ECFR_API_BASE}/structure/current/title-38.json"
    FULL_TEXT_URL = f"{ECFR_API_BASE}/full/current/title-38.xml"
    PART_URL_TEMPLATE = "https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-38/chapter-I/part-{part}"

    # All parts of 38 CFR we want (comprehensive list)
    PRIORITY_PARTS = [
        "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
        "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
        "31", "32", "33", "34", "35", "36", "37", "38", "39", "40",
        "41", "42", "43", "44", "45", "46", "47", "48", "49", "50",
        "51", "52", "53", "54", "55", "56", "57", "58", "59", "60",
        "61", "62", "63", "64", "65", "66", "67", "68", "69", "70",
        "71", "72", "73", "74", "75", "76", "77", "78", "79", "80",
    ]

    def collect(self) -> dict:
        """Collect all of Title 38 CFR."""
        extra_stats = {"parts_collected": 0, "sections_collected": 0}

        # Step 1: Get the structure to understand what's available
        self.logger.info("Fetching eCFR Title 38 structure...")
        structure = self._fetch_structure()
        if structure:
            self.save_file(
                "title_38_structure.json",
                json.dumps(structure, indent=2),
                metadata={"type": "structure", "title": "38"}
            )

        # Step 2: Discover actual available parts from structure
        available_parts = self._get_available_parts(structure)
        self.logger.info(f"Found {len(available_parts)} parts in Title 38 CFR")

        # Step 3: Fetch each part
        for part_num in available_parts:
            self.logger.info(f"Collecting 38 CFR Part {part_num}...")
            success = self._collect_part(part_num)
            if success:
                extra_stats["parts_collected"] += 1

        # Step 4: Also try to get the full XML dump
        self.logger.info("Attempting full Title 38 XML download...")
        self._collect_full_xml()

        return extra_stats

    def _fetch_structure(self) -> Optional[dict]:
        """Fetch the eCFR structural outline for Title 38."""
        response = self.fetch(self.STRUCTURE_URL)
        if response and response.status_code == 200:
            try:
                return response.json()
            except Exception as e:
                self.logger.error(f"Failed to parse structure JSON: {e}")
        return None

    def _get_available_parts(self, structure: Optional[dict]) -> list[str]:
        """Extract available part numbers from the structure data."""
        if not structure:
            # Fall back to trying all known parts
            self.logger.warning("No structure data; falling back to known parts list")
            return self.PRIORITY_PARTS

        parts = []
        try:
            # The eCFR structure API nests: children -> chapters -> parts
            children = structure.get("children", [])
            for child in children:
                # Chapters or subchapters
                for sub in child.get("children", []):
                    if sub.get("type") == "part":
                        identifier = sub.get("identifier", "")
                        if identifier:
                            parts.append(identifier)
                    # Parts may be nested deeper
                    for subsub in sub.get("children", []):
                        if subsub.get("type") == "part":
                            identifier = subsub.get("identifier", "")
                            if identifier:
                                parts.append(identifier)
                        for subsubsub in subsub.get("children", []):
                            if subsubsub.get("type") == "part":
                                identifier = subsubsub.get("identifier", "")
                                if identifier:
                                    parts.append(identifier)
        except Exception as e:
            self.logger.error(f"Error parsing structure: {e}")
            return self.PRIORITY_PARTS

        if not parts:
            return self.PRIORITY_PARTS

        # Deduplicate and sort
        parts = sorted(set(parts), key=lambda x: int(x) if x.isdigit() else 0)
        return parts

    def _collect_part(self, part_num: str) -> bool:
        """
        Collect a single CFR part via the eCFR content API.

        Returns True if successfully collected.
        """
        filename = f"38_cfr_part_{part_num.zfill(3)}.html"

        # Check for incremental update — skip if we already have it
        if self.file_exists(filename) and not self._should_update(filename):
            self.logger.debug(f"Skipping existing Part {part_num}")
            self.stats["files_skipped"] += 1
            return True

        # Try the enhanced renderer API first
        url = self.PART_URL_TEMPLATE.format(part=part_num)
        response = self.fetch(url)

        if response and response.status_code == 200:
            html_content = response.text

            # Also extract plain text version
            plain_text = self._html_to_structured_text(html_content, part_num)

            # Save HTML version
            self.save_file(
                filename,
                html_content,
                metadata={
                    "type": "cfr_part",
                    "title": "38",
                    "part": part_num,
                    "format": "html",
                    "url": url,
                }
            )

            # Save plain text version
            txt_filename = f"38_cfr_part_{part_num.zfill(3)}.txt"
            self.save_file(
                txt_filename,
                plain_text,
                metadata={
                    "type": "cfr_part",
                    "title": "38",
                    "part": part_num,
                    "format": "text",
                    "url": url,
                }
            )

            # If this is Part 4 (VASRD), also extract diagnostic codes
            if part_num == "4":
                self._extract_diagnostic_codes(html_content)

            return True
        else:
            self.logger.warning(f"Failed to fetch Part {part_num} from enhanced API")
            # Fallback: try the XML API
            return self._collect_part_xml(part_num)

    def _collect_part_xml(self, part_num: str) -> bool:
        """Fallback: collect a part via the XML full-text API with part filter."""
        url = f"{ECFR_API_BASE}/full/current/title-38.xml"
        params = {"part": part_num}
        response = self.fetch(url, params=params)

        if response and response.status_code == 200:
            filename = f"38_cfr_part_{part_num.zfill(3)}.xml"
            self.save_file(
                filename,
                response.content,
                metadata={
                    "type": "cfr_part",
                    "title": "38",
                    "part": part_num,
                    "format": "xml",
                }
            )
            return True
        return False

    def _collect_full_xml(self) -> None:
        """Attempt to download the complete Title 38 XML."""
        # This is a large file — only download if we don't have it
        filename = "title_38_full.xml"
        if self.file_exists(filename):
            self.logger.info("Full XML already exists, skipping")
            return

        response = self.fetch(self.FULL_TEXT_URL)
        if response and response.status_code == 200:
            self.save_file(
                filename,
                response.content,
                metadata={
                    "type": "cfr_full",
                    "title": "38",
                    "format": "xml",
                }
            )

    def _html_to_structured_text(self, html: str, part_num: str) -> str:
        """
        Convert eCFR HTML to structured plain text preserving
        section numbering and hierarchy.
        """
        soup = BeautifulSoup(html, "lxml")

        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        lines = []
        lines.append(f"TITLE 38 — CODE OF FEDERAL REGULATIONS")
        lines.append(f"Part {part_num}")
        lines.append("=" * 70)
        lines.append("")

        # Process section by section
        for section in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "div"]):
            class_list = section.get("class", [])
            if isinstance(class_list, str):
                class_list = [class_list]

            text = section.get_text(separator=" ", strip=True)
            if not text:
                continue

            # Preserve hierarchy markers
            tag_name = section.name
            if tag_name in ("h1", "h2"):
                lines.append("")
                lines.append("=" * 60)
                lines.append(text)
                lines.append("=" * 60)
                lines.append("")
            elif tag_name == "h3":
                lines.append("")
                lines.append("-" * 50)
                lines.append(text)
                lines.append("-" * 50)
                lines.append("")
            elif tag_name in ("h4", "h5", "h6"):
                lines.append("")
                lines.append(text)
                lines.append("-" * len(text))
                lines.append("")
            else:
                # Regular paragraph
                lines.append(text)
                lines.append("")

        return "\n".join(lines)

    def _extract_diagnostic_codes(self, html: str) -> None:
        """
        Extract VASRD diagnostic codes from Part 4 into a structured format.
        Saves both JSON and CSV lookup tables.
        """
        self.logger.info("Extracting VASRD diagnostic codes from Part 4...")
        soup = BeautifulSoup(html, "lxml")

        codes = []
        text = soup.get_text()

        # Pattern to match diagnostic codes (e.g., "5000", "9411")
        # Typically formatted as "Diagnostic Code XXXX" or just the code in tables
        dc_pattern = re.compile(
            r"(?:Diagnostic [Cc]ode|DC)\s*(\d{4})\s*[-—:]\s*(.+?)(?:\n|$)",
            re.MULTILINE
        )

        for match in dc_pattern.finditer(text):
            code_num = match.group(1)
            condition = match.group(2).strip()
            codes.append({
                "diagnostic_code": code_num,
                "condition": condition,
                "source": "38 CFR Part 4",
            })

        if codes:
            # Save as JSON
            self.save_file(
                "vasrd_diagnostic_codes.json",
                json.dumps(codes, indent=2),
                metadata={
                    "type": "vasrd_codes",
                    "count": len(codes),
                }
            )
            self.logger.info(f"Extracted {len(codes)} diagnostic codes")
        else:
            self.logger.warning("No diagnostic codes extracted — pattern may need adjustment for actual HTML structure")

    def _should_update(self, filename: str) -> bool:
        """Check if a file should be re-downloaded based on age."""
        meta_path = self.output_dir / f"{filename}.meta.json"
        if not meta_path.exists():
            return True
        try:
            meta = json.loads(meta_path.read_text())
            # Re-download if metadata is missing collection timestamp
            return "collected_at" not in meta
        except Exception:
            return True


def main():
    """Run the eCFR scraper standalone."""
    scraper = ECFRScraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
