"""
VA Forms Scraper — Every VA form relevant to claims, appeals, and benefits.

Collects form PDFs, instructions, and field-by-field guidance from
the official VA forms repository.

Source: https://www.va.gov/find-forms/
API: https://api.va.gov/services/va_forms/v0/forms
"""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper


class VAFormsScraper(BaseScraper):
    """Scraper for VA forms and their instructions."""

    @property
    def source_name(self) -> str:
        return "va_forms"

    VA_FORMS_BASE = "https://www.va.gov/find-forms/"
    VA_FORMS_API = "https://api.va.gov/services/va_forms/v0/forms"

    # Priority forms for veterans disability claims
    PRIORITY_FORMS = {
        "21-526EZ": {
            "name": "Application for Disability Compensation and Related Compensation Benefits",
            "category": "disability_compensation",
            "description": "Primary form for filing initial disability compensation claims and claims for increase.",
        },
        "20-0995": {
            "name": "Decision Review Request: Supplemental Claim",
            "category": "appeals",
            "description": "Used to file a Supplemental Claim with new and relevant evidence under the AMA.",
        },
        "20-0996": {
            "name": "Decision Review Request: Higher-Level Review",
            "category": "appeals",
            "description": "Request for a senior reviewer to re-examine an existing decision under the AMA.",
        },
        "10182": {
            "name": "Decision Review Request: Board Appeal (Notice of Disagreement)",
            "category": "appeals",
            "description": "Appeal to the Board of Veterans' Appeals under the AMA.",
        },
        "21-4138": {
            "name": "Statement in Support of Claim",
            "category": "supporting",
            "description": "General-purpose statement form for providing additional information to support a claim.",
        },
        "21-0781": {
            "name": "Statement in Support of Claim for Service Connection for PTSD",
            "category": "ptsd",
            "description": "Required stressor statement for PTSD claims based on combat, fear of hostile activity, etc.",
        },
        "21-0781a": {
            "name": "Statement in Support of Claim for PTSD Secondary to Personal Assault/MST",
            "category": "mst",
            "description": "Stressor statement for PTSD claims based on military sexual trauma or personal assault.",
        },
        "21-8940": {
            "name": "Veterans Application for Increased Compensation Based on Unemployability (TDIU)",
            "category": "tdiu",
            "description": "Application for Total Disability based on Individual Unemployability.",
        },
        "21-22": {
            "name": "Appointment of Veterans Service Organization as Claimant's Representative",
            "category": "representation",
            "description": "Designates a VSO to represent the veteran in VA claims.",
        },
        "21-22a": {
            "name": "Appointment of Individual as Claimant's Representative",
            "category": "representation",
            "description": "Designates an individual attorney or claims agent as representative.",
        },
        "21-0966": {
            "name": "Intent to File a Claim for Compensation and/or Pension",
            "category": "claims",
            "description": "Preserves an effective date while the veteran prepares a formal claim.",
        },
        "21-4142": {
            "name": "Authorization to Disclose Information to VA",
            "category": "evidence",
            "description": "Authorizes release of private medical records to VA.",
        },
        "21-4142a": {
            "name": "General Release for Medical Provider Information to VA",
            "category": "evidence",
            "description": "Companion form to 21-4142 for specific medical provider authorization.",
        },
        "21-686c": {
            "name": "Declaration of Status of Dependents",
            "category": "dependents",
            "description": "Add or remove dependents for additional compensation.",
        },
        "26-1880": {
            "name": "Request for Certificate of Eligibility (Home Loan)",
            "category": "home_loan",
            "description": "Apply for VA home loan Certificate of Eligibility.",
        },
        "10-10EZ": {
            "name": "Application for Health Benefits",
            "category": "healthcare",
            "description": "Enroll in VA healthcare.",
        },
        "22-1990": {
            "name": "Application for VA Education Benefits",
            "category": "education",
            "description": "Apply for GI Bill and other education benefits.",
        },
        "28-1900": {
            "name": "Disabled Veterans Application for Vocational Rehabilitation",
            "category": "voc_rehab",
            "description": "Apply for Chapter 31 Vocational Rehabilitation and Employment.",
        },
        "21-534EZ": {
            "name": "Application for DIC, Death Pension, and/or Accrued Benefits",
            "category": "survivors",
            "description": "Survivor benefits application for spouses and dependents.",
        },
        "21-2680": {
            "name": "Examination for Housebound Status or Permanent Need for Aid & Attendance",
            "category": "smc",
            "description": "Medical examination form for Special Monthly Compensation.",
        },
    }

    # DD Forms (military forms, not VA)
    DD_FORMS = {
        "DD-214": {
            "name": "Certificate of Release or Discharge from Active Duty",
            "category": "military_records",
            "description": "The most important military document — shows service dates, characterization, and reason for separation.",
        },
        "DD-149": {
            "name": "Application for Correction of Military Record",
            "category": "bcmr",
            "description": "Application to Board for Correction of Military Records.",
        },
        "DD-293": {
            "name": "Application for the Review of Discharge from the Armed Forces",
            "category": "drb",
            "description": "Application to Discharge Review Board for upgrade of discharge characterization.",
        },
        "SF-180": {
            "name": "Request Pertaining to Military Records",
            "category": "military_records",
            "description": "Request military records from the National Personnel Records Center.",
        },
    }

    def collect(self) -> dict:
        """Collect all priority VA forms and DD forms."""
        extra_stats = {
            "va_forms_collected": 0,
            "dd_forms_collected": 0,
            "instructions_collected": 0,
        }

        # Step 1: Try the VA Forms API
        self.logger.info("Querying VA Forms API...")
        api_forms = self._query_forms_api()
        if api_forms:
            self.logger.info(f"API returned {len(api_forms)} forms")

        # Step 2: Collect each priority VA form
        for form_num, form_info in self.PRIORITY_FORMS.items():
            self.logger.info(f"Collecting VA Form {form_num}: {form_info['name']}")

            # Check if API gave us a direct URL
            api_data = api_forms.get(form_num) if api_forms else None
            collected = self._collect_va_form(form_num, form_info, api_data)
            if collected:
                extra_stats["va_forms_collected"] += 1

            # Also collect form instructions
            instruction = self._collect_form_instructions(form_num, form_info)
            if instruction:
                extra_stats["instructions_collected"] += 1

        # Step 3: Collect DD form information
        for form_num, form_info in self.DD_FORMS.items():
            self.logger.info(f"Collecting {form_num}: {form_info['name']}")
            collected = self._collect_dd_form_info(form_num, form_info)
            if collected:
                extra_stats["dd_forms_collected"] += 1

        # Step 4: Create a comprehensive forms reference
        self._create_forms_reference()

        return extra_stats

    def _query_forms_api(self) -> Optional[dict]:
        """Query the VA Forms API for form metadata and download URLs."""
        forms_data = {}

        response = self.fetch(self.VA_FORMS_API)
        if not response or response.status_code != 200:
            self.logger.warning("VA Forms API not available, will use web scraping")
            return None

        try:
            data = response.json()
            forms_list = data.get("data", [])
            for form in forms_list:
                attrs = form.get("attributes", {})
                form_name = attrs.get("form_name", "")
                forms_data[form_name] = {
                    "url": attrs.get("url", ""),
                    "title": attrs.get("title", ""),
                    "last_revision": attrs.get("last_revision_on", ""),
                    "pages": attrs.get("pages", 0),
                    "sha256": attrs.get("sha256", ""),
                }
        except Exception as e:
            self.logger.error(f"Error parsing forms API response: {e}")

        # Save API data
        if forms_data:
            self.save_file(
                "va_forms_api_data.json",
                json.dumps(forms_data, indent=2),
                metadata={"type": "forms_api", "count": len(forms_data)}
            )

        return forms_data

    def _collect_va_form(self, form_num: str, form_info: dict,
                          api_data: Optional[dict] = None) -> bool:
        """Collect a VA form PDF."""
        safe_num = form_num.replace("-", "_").replace(" ", "_")
        pdf_filename = f"va_form_{safe_num}.pdf"

        if self.file_exists(pdf_filename):
            self.stats["files_skipped"] += 1
            return True

        # Try API URL first
        if api_data and api_data.get("url"):
            response = self.fetch(api_data["url"])
            if response and response.status_code == 200:
                self.save_file(
                    pdf_filename,
                    response.content,
                    metadata={
                        "type": "va_form",
                        "form_number": form_num,
                        "name": form_info["name"],
                        "category": form_info["category"],
                        "format": "pdf",
                        "url": api_data["url"],
                    }
                )
                return True

        # Fallback: try common VA form URL patterns
        url_patterns = [
            f"https://www.vba.va.gov/pubs/forms/VBA-{form_num}-ARE.pdf",
            f"https://www.va.gov/vaforms/va/pdf/VA{form_num.replace('-', '')}.pdf",
            f"https://www.va.gov/find-forms/about-form-{form_num.lower()}/",
        ]

        for url in url_patterns:
            response = self.fetch(url)
            if response and response.status_code == 200:
                if url.endswith(".pdf"):
                    self.save_file(
                        pdf_filename,
                        response.content,
                        metadata={
                            "type": "va_form",
                            "form_number": form_num,
                            "name": form_info["name"],
                            "category": form_info["category"],
                            "format": "pdf",
                            "url": url,
                        }
                    )
                else:
                    # It's an about page — extract info
                    text = self._extract_form_page(response.text, form_num, form_info)
                    self.save_file(
                        f"va_form_{safe_num}_about.txt",
                        text,
                        metadata={
                            "type": "va_form_about",
                            "form_number": form_num,
                            "name": form_info["name"],
                            "url": url,
                        }
                    )
                return True

        self.logger.warning(f"Could not download VA Form {form_num}")
        return False

    def _collect_form_instructions(self, form_num: str, form_info: dict) -> bool:
        """Collect instructions and guidance for a VA form."""
        safe_num = form_num.replace("-", "_").replace(" ", "_")
        filename = f"va_form_{safe_num}_instructions.txt"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True

        # Try the VA "about form" page
        about_url = f"https://www.va.gov/find-forms/about-form-{form_num.lower()}/"
        response = self.fetch(about_url)

        if response and response.status_code == 200:
            text = self._extract_form_page(response.text, form_num, form_info)
            if len(text) > 100:
                self.save_file(
                    filename,
                    text,
                    metadata={
                        "type": "form_instructions",
                        "form_number": form_num,
                        "name": form_info["name"],
                        "url": about_url,
                    }
                )
                return True

        return False

    def _collect_dd_form_info(self, form_num: str, form_info: dict) -> bool:
        """Collect DD form information (these are DoD forms, not VA)."""
        safe_num = form_num.replace("-", "_").replace(" ", "_")
        filename = f"dd_form_{safe_num}_info.txt"

        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True

        # Create comprehensive reference for each DD form
        content = self._generate_dd_form_reference(form_num, form_info)
        self.save_file(
            filename,
            content,
            metadata={
                "type": "dd_form_info",
                "form_number": form_num,
                "name": form_info["name"],
                "category": form_info["category"],
            }
        )
        return True

    def _extract_form_page(self, html: str, form_num: str, form_info: dict) -> str:
        """Extract form information from a VA form page."""
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "header", "footer"]):
            tag.decompose()

        lines = [
            f"VA FORM {form_num}",
            form_info["name"],
            "=" * 70,
            "",
            f"Category: {form_info['category']}",
            f"Description: {form_info['description']}",
            "",
            "-" * 50,
            "FORM DETAILS",
            "-" * 50,
            "",
        ]

        content = soup.find("main") or soup.find("div", class_=re.compile(r"content", re.I)) or soup.find("body")
        if content:
            for elem in content.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
                text = elem.get_text(separator=" ", strip=True)
                if not text:
                    continue
                tag = elem.name
                if tag in ("h1", "h2", "h3"):
                    lines.extend(["", text, "-" * min(len(text), 50), ""])
                elif tag == "li":
                    lines.append(f"  - {text}")
                else:
                    lines.extend([text, ""])

        return "\n".join(lines)

    def _generate_dd_form_reference(self, form_num: str, form_info: dict) -> str:
        """Generate reference content for DD forms."""
        if form_num == "DD-214":
            return self._dd214_reference()
        elif form_num == "DD-149":
            return self._dd149_reference()
        elif form_num == "DD-293":
            return self._dd293_reference()
        elif form_num == "SF-180":
            return self._sf180_reference()
        else:
            return (
                f"{form_num}: {form_info['name']}\n"
                f"{'=' * 70}\n\n"
                f"{form_info['description']}\n"
            )

    def _dd214_reference(self) -> str:
        return """DD FORM 214 — CERTIFICATE OF RELEASE OR DISCHARGE FROM ACTIVE DUTY
======================================================================

OVERVIEW:
The DD-214 is the single most important military document a veteran possesses.
It serves as proof of military service and contains critical information that
determines VA benefits eligibility.

KEY BLOCKS:
- Block 1: Name
- Block 4a-b: Grade, Pay Grade at separation
- Block 12a-d: Date Entered Active Duty, Separation Date, Net Active Service
- Block 13: Decorations, Medals, Badges, Citations, Campaign Ribbons
- Block 18: Remarks (may contain critical information about service)
- Block 24: Character of Service (MOST IMPORTANT FOR VA BENEFITS)
  - Honorable
  - General (Under Honorable Conditions)
  - Other Than Honorable (OTH)
  - Bad Conduct Discharge (BCD)
  - Dishonorable Discharge (DD)
- Block 25: Separation Authority (regulation used for discharge)
- Block 26: Separation Code (alphanumeric code indicating reason)
- Block 28: Narrative Reason for Separation

CHARACTER OF SERVICE AND VA BENEFITS ELIGIBILITY:
- Honorable: Full VA benefits eligibility
- General (Under Honorable): Full VA benefits eligibility
- Other Than Honorable: MAY be eligible depending on VA character of
  discharge determination (38 CFR 3.12). Must apply; VA makes case-by-case
  determination. Can also seek discharge upgrade via DRB or BCMR.
- Bad Conduct Discharge (by Special Court-Martial): Same as OTH — VA
  makes determination. Can seek upgrade via BCMR (not DRB).
- Bad Conduct Discharge (by General Court-Martial): Generally bars VA
  benefits. BCMR upgrade possible but difficult.
- Dishonorable: Statutory bar to VA benefits (38 USC 5303). Only BCMR
  upgrade or Presidential pardon can restore eligibility.

EXCEPTIONS TO BARS:
- Insanity at time of offense (38 CFR 3.12(b))
- Compelling circumstances (38 CFR 3.12(c)(6))
- Service-connected disability incurred before the discharge

OBTAINING DD-214:
- Online: National Personnel Records Center (NPRC) via eVetRecs
- By Mail: SF-180 to NPRC, St. Louis, MO
- In Person: County Veterans Service Officer may assist

NOTE: Veterans should have BOTH the short form (Member Copy 4) and the
long form (Member Copy 1) which contains more detailed information.
"""

    def _dd149_reference(self) -> str:
        return """DD FORM 149 — APPLICATION FOR CORRECTION OF MILITARY RECORD
======================================================================

PURPOSE:
DD Form 149 is used to request that the Board for Correction of Military
Records (BCMR) of the appropriate service branch correct any military record,
including discharge characterization.

FILING DEADLINE:
- 3 years from date of discovery of the alleged error or injustice
- HOWEVER, boards routinely waive this deadline in the interest of justice
- Particularly for cases involving PTSD, TBI, MST, or other mental health

KEY SECTIONS:
Block 7: Describe the specific correction you are requesting
Block 8: Provide detailed justification (THIS IS THE MOST CRITICAL SECTION)
  - Explain what error or injustice occurred
  - Cite specific regulations, policies, or standards that were violated
  - Reference Hagel/Kurta/Wilkie memos if mental health related
  - Describe how the error affected your military record
Block 9: List all supporting evidence attached

WHAT BCMR CAN CORRECT:
- Discharge characterization (including court-martial discharges)
- Narrative reason for separation
- Separation code
- Reenlistment eligibility code
- Rank/grade at discharge
- Dates of service
- Awards and decorations
- Any other military record entry

TIPS FOR STRONG APPLICATIONS:
1. Be specific about what correction is requested
2. Provide detailed narrative explaining the injustice
3. Submit supporting evidence (medical records, buddy statements, etc.)
4. Reference applicable liberal consideration memos
5. Explain how mental health conditions (if applicable) contributed
6. Include post-service evidence of rehabilitation and good character
7. Request a personal hearing if possible (significantly higher success rates)

LEGAL REPRESENTATION:
- Veterans may be represented by VSOs, attorneys, or agents
- Pro bono legal assistance available through veterans legal clinics
- Some law school clinics specialize in discharge upgrade cases
"""

    def _dd293_reference(self) -> str:
        return """DD FORM 293 — APPLICATION FOR REVIEW OF DISCHARGE
======================================================================

PURPOSE:
DD Form 293 is used to request that the Discharge Review Board (DRB)
review and upgrade the characterization of or reason for discharge.

FILING DEADLINE:
- 15 years from date of discharge
- No waiver authority (unlike BCMR)
- If past 15 years, must use DD Form 149 (BCMR) instead

DRB AUTHORITY:
- CAN change: discharge characterization, narrative reason, separation code
- CANNOT change: court-martial discharges (BCD, DD)
- CANNOT change: medical disability findings
- For court-martial discharges, must apply to BCMR instead

REVIEW OPTIONS:
1. Documentary Review (Records Review):
   - Board reviews application and military records only
   - No personal appearance
   - Can be done by mail
   - Lower success rate than personal hearing

2. Personal Appearance Hearing:
   - Veteran appears before the board
   - Can present testimony and evidence
   - Can bring witnesses
   - Can be represented by counsel
   - Significantly higher success rate
   - Hearings held in Washington, DC (with some traveling panels)

KEY ARGUMENTS FOR UPGRADE:
1. Inequity: Discharge was too harsh given the circumstances
2. Impropriety: Procedures were not properly followed
3. Liberal consideration: Mental health conditions (PTSD/TBI/MST)
   mitigated the misconduct under Hagel/Kurta/Wilkie standards

SUPPORTING EVIDENCE:
- Medical records (service and post-service)
- Mental health evaluations
- Buddy statements about behavior changes
- Character references
- Post-service accomplishments
- Employment records
- Community service
- Letters from treatment providers
"""

    def _sf180_reference(self) -> str:
        return """SF-180 — REQUEST PERTAINING TO MILITARY RECORDS
======================================================================

PURPOSE:
Standard Form 180 is used to request military records from the National
Personnel Records Center (NPRC) or other records repositories.

WHAT YOU CAN REQUEST:
- DD-214 (Report of Separation)
- Complete military personnel file (OMPF)
- Service medical/health records
- Unit records
- Awards and decorations documentation

WHERE TO SEND:
National Personnel Records Center (NPRC)
1 Archives Drive
St. Louis, MO 63138

IMPORTANT NOTES:
- There is NO fee for veterans requesting their own records
- Processing time varies (weeks to months)
- Some records were destroyed in the 1973 NPRC fire
  (primarily Army personnel discharged 1912-1964 and
   Air Force personnel discharged 1947-1964)
- Reconstruction may be possible using alternative sources

ONLINE ALTERNATIVES:
- eVetRecs: https://www.archives.gov/veterans/military-service-records
- eBenefits: https://www.ebenefits.va.gov
- milConnect: https://milconnect.dmdc.osd.mil
"""

    def _create_forms_reference(self) -> None:
        """Create a consolidated VA forms quick-reference guide."""
        filename = "va_forms_quick_reference.txt"
        if self.file_exists(filename):
            return

        lines = [
            "VA FORMS QUICK REFERENCE GUIDE",
            "=" * 70,
            "",
            "DISABILITY COMPENSATION FORMS:",
            "-" * 40,
        ]

        for form_num, info in self.PRIORITY_FORMS.items():
            lines.append(f"  VA Form {form_num}: {info['name']}")
            lines.append(f"    {info['description']}")
            lines.append("")

        lines.extend([
            "",
            "MILITARY/DD FORMS:",
            "-" * 40,
        ])

        for form_num, info in self.DD_FORMS.items():
            lines.append(f"  {form_num}: {info['name']}")
            lines.append(f"    {info['description']}")
            lines.append("")

        self.save_file(
            filename,
            "\n".join(lines),
            metadata={"type": "forms_reference"}
        )


def main():
    """Run the VA Forms scraper standalone."""
    scraper = VAFormsScraper()
    stats = scraper.run()
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
