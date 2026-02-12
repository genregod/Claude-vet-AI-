"""
Remaining Sources Scrapers — Covers sources 13-20 from the master plan.

Includes:
  13. VSO Training Materials
  14. Veterans Claims Representative Knowledge
  15. PACT Act
  16. Appeals Modernization Act (AMA)
  17. VA Clinical Practice Guidelines
  18. Military Personnel Regulations
  19. VA OIG / GAO Reports
  20. Supplementary Legal Resources
"""

import json
import re
from typing import Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from scripts.data_collection.base_scraper import BaseScraper
from scripts.data_collection.config import VA_CLINICAL_GUIDELINES, VA_OIG_BASE, GAO_BASE


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 13. VSO TRAINING MATERIALS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class VSOTrainingScraper(BaseScraper):
    """Scraper for Veterans Service Officer training materials and accreditation."""

    @property
    def source_name(self) -> str:
        return "vso_training"

    VA_OGC_ACCREDITATION = "https://www.va.gov/ogc/accreditation.asp"
    VA_OGC_BASE = "https://www.va.gov/ogc/"

    def collect(self) -> dict:
        extra_stats = {"documents_collected": 0}

        # Collect VA OGC accreditation page
        self.logger.info("Collecting VA OGC accreditation information...")
        self._collect_page(
            self.VA_OGC_ACCREDITATION,
            "vso_accreditation_requirements.html",
            "VA Accreditation Requirements"
        )
        extra_stats["documents_collected"] += 1

        # Collect 38 CFR Part 14 reference
        self._create_cfr_part_14_reference()
        extra_stats["documents_collected"] += 1

        # Collect VSO best practices reference
        self._create_vso_best_practices()
        extra_stats["documents_collected"] += 1

        # Collect ethics rules reference
        self._create_ethics_reference()
        extra_stats["documents_collected"] += 1

        return extra_stats

    def _collect_page(self, url: str, filename: str, title: str) -> bool:
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True
        response = self.fetch(url)
        if response and response.status_code == 200:
            self.save_file(filename, response.text,
                           metadata={"type": "vso_training", "title": title, "url": url})
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "nav"]):
                tag.decompose()
            body = soup.find("main") or soup.find("body")
            text = f"{title}\n{'=' * 70}\n\n{body.get_text(separator=chr(10), strip=True) if body else ''}"
            self.save_file(filename.replace(".html", ".txt"), text,
                           metadata={"type": "vso_training", "format": "text"})
            return True
        return False

    def _create_cfr_part_14_reference(self) -> None:
        filename = "cfr_part_14_accreditation_reference.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """38 CFR PART 14 — LEGAL SERVICES, GENERAL COUNSEL, AND ACCREDITATION
======================================================================

38 CFR 14.629 — Requirements for Accreditation

TYPES OF ACCREDITED REPRESENTATIVES:
1. Veterans Service Organization (VSO) Representatives (14.629(a))
   - Must be certified by an approved VSO
   - Must complete VSO-specific training program
   - Must pass background check
   - Must maintain continuing education

2. Attorneys (14.629(b))
   - Must be admitted to practice in a US jurisdiction
   - Must be in good standing
   - Must file VA Form 21-22a
   - Must comply with VA ethics rules

3. Claims Agents (14.629(c))
   - Must pass written examination
   - Must demonstrate good moral character
   - Must complete continuing legal education
   - Must maintain active accreditation

FEE AGREEMENTS (38 USC 5904):
- Fees cannot be charged until after initial agency decision
- Fee agreements must be filed with VA OGC
- Maximum contingency fee: 33.3% of past-due benefits
- Direct-pay fee agreements: VA pays attorney from past-due benefits
- Equal Access to Justice Act (EAJA): Government may pay attorney fees

ETHICS:
- Cannot solicit VA business improperly
- Must maintain confidentiality
- Cannot charge excessive fees
- Must provide competent representation
- Must communicate with client about claim status
- Cannot abandon a client's claim without notice
""", metadata={"type": "reference", "topic": "cfr_part_14"})

    def _create_vso_best_practices(self) -> None:
        filename = "vso_best_practices_reference.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """VSO BEST PRACTICES FOR CLAIMS DEVELOPMENT
======================================================================

INITIAL CLAIM DEVELOPMENT:
1. Conduct thorough intake interview
2. Review complete military service records (DD-214, service treatment records)
3. Identify all potential service-connected conditions
4. Determine if conditions are direct, secondary, or presumptive
5. Identify lay evidence sources (buddy statements)
6. File Intent to File (VA Form 21-0966) to preserve effective date
7. Gather medical evidence before filing formal claim
8. Obtain nexus letters/Independent Medical Opinions where needed
9. Prepare detailed personal statement
10. File fully developed claim when possible

EVIDENCE DEVELOPMENT:
- Service treatment records (STRs)
- Post-service medical records
- Nexus letters from qualified medical professionals
- Buddy/lay statements (minimum 2-3 per condition)
- Personal statement from veteran
- Employment records (for TDIU claims)
- Marriage certificates, birth certificates (for dependents)

C&P EXAM PREPARATION:
- Review the Disability Benefits Questionnaire (DBQ) for each condition
- Prepare veteran for what to expect at the exam
- Advise veteran to be honest about WORST day symptoms
- Remind veteran to mention ALL symptoms, including secondary effects
- Advise veteran to bring list of medications and side effects
- If exam seems inadequate, request new exam with explanation

NEXUS LETTER REQUIREMENTS:
- Must be from qualified medical professional
- Must use "at least as likely as not" (50% or greater probability)
- Must provide rationale citing medical literature and service records
- Must address specific diagnostic criteria
- Must explain causal connection between service and condition
- Must be based on review of claims file or medical records

EFFECTIVE DATE STRATEGIES:
- File Intent to File immediately
- Claim as early as possible
- For increases: file when condition worsens
- Identify earlier effective dates through CUE claims
- Look for informal claims in the record (pre-AMA)
""", metadata={"type": "reference", "topic": "vso_best_practices"})

    def _create_ethics_reference(self) -> None:
        filename = "vso_ethics_rules_reference.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """VSO ETHICS AND PROFESSIONAL RESPONSIBILITY
======================================================================

CORE ETHICAL OBLIGATIONS (38 CFR 14.632):
1. COMPETENCE: Maintain knowledge of veterans benefits law
2. DILIGENCE: Pursue claims vigorously and promptly
3. COMMUNICATION: Keep clients informed of claim status
4. CONFIDENTIALITY: Protect client information
5. FEES: Do not charge unauthorized fees
6. CONFLICTS: Avoid conflicts of interest
7. CANDOR: Be truthful with VA and clients

PROHIBITED CONDUCT (38 CFR 14.633):
- Charging fees before initial agency decision (except EAJA)
- Soliciting improperly
- Delaying claims for personal benefit
- Failing to refund unearned fees
- Abandoning client representation without notice
- Engaging in conduct prejudicial to VA administration

CANCELLATION OF ACCREDITATION:
- Grounds: Violation of ethical rules, criminal conviction,
  incompetence, failure to maintain qualifications
- Process: Written charges, opportunity to respond, hearing if requested
- Appeal: To Board of Veterans' Appeals
""", metadata={"type": "reference", "topic": "vso_ethics"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 14. CLAIMS PROCEDURES KNOWLEDGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ClaimsProceduresScraper(BaseScraper):
    """Scraper/generator for veterans claims representative procedural knowledge."""

    @property
    def source_name(self) -> str:
        return "claims_procedures"

    def collect(self) -> dict:
        extra_stats = {"references_created": 0}
        references = [
            ("duty_to_assist.txt", self._duty_to_assist()),
            ("nexus_letter_standards.txt", self._nexus_letter_standards()),
            ("cp_exam_procedures.txt", self._cp_exam_procedures()),
            ("effective_date_rules.txt", self._effective_date_rules()),
            ("cue_claims.txt", self._cue_claims()),
            ("tdiu_procedures.txt", self._tdiu_procedures()),
            ("smc_levels.txt", self._smc_levels()),
            ("secondary_service_connection.txt", self._secondary_service_connection()),
            ("presumptive_conditions.txt", self._presumptive_conditions()),
            ("buddy_statements_lay_evidence.txt", self._buddy_statements()),
        ]
        for filename, content in references:
            if not self.file_exists(filename):
                self.save_file(filename, content,
                               metadata={"type": "claims_procedure_reference"})
                extra_stats["references_created"] += 1
            else:
                self.stats["files_skipped"] += 1
        return extra_stats

    def _duty_to_assist(self) -> str:
        return """DUTY TO ASSIST — 38 USC 5103A
======================================================================

VA's duty to assist requires the agency to help veterans develop their
claims by obtaining evidence and providing medical examinations.

WHAT VA MUST DO:
1. Obtain service treatment records (STRs)
2. Obtain relevant federal records (VA medical records, SSA records)
3. Make reasonable efforts to obtain private medical records
4. Provide C&P examination when:
   a. Evidence of current disability
   b. Evidence of in-service event, injury, or disease
   c. Indication that disability may be associated with service
   d. Insufficient evidence to make a decision
   (McLendon v. Nicholson, 20 Vet. App. 79 (2006))
5. Notify veteran of evidence needed (38 USC 5103)

DUTY TO ASSIST IN EACH AMA LANE:
- Supplemental Claim (0995): Full duty to assist applies
- Higher-Level Review (0996): NO duty to assist (decision on existing record)
- Board Appeal (10182): Duty to assist applies on Evidence and Hearing dockets

WHEN DUTY IS TRIGGERED:
- When a substantially complete application is filed
- When veteran identifies evidence that is relevant and obtainable
- When the record suggests additional development is needed

VETERAN'S RESPONSIBILITIES:
- Provide enough information to identify evidence
- Authorize release of private records (VA Form 21-4142)
- Report for scheduled C&P examinations
- Cooperate with evidence development

REMEDIES FOR DUTY TO ASSIST VIOLATIONS:
- Request remand for additional development
- File Supplemental Claim citing duty to assist failure
- Board can remand for duty to assist compliance
- CAVC can vacate and remand for duty to assist violations
"""

    def _nexus_letter_standards(self) -> str:
        return """NEXUS LETTER REQUIREMENTS AND STANDARDS
======================================================================

A nexus letter is a medical opinion establishing a connection between a
veteran's current disability and their military service.

LEGAL STANDARD:
"At least as likely as not" (50% or greater probability) that the condition
is related to military service. This is the benefit-of-the-doubt standard.

REQUIRED ELEMENTS:
1. AUTHOR QUALIFICATIONS
   - Medical doctor (MD/DO), psychologist (PhD/PsyD), or appropriate
     specialist for the condition
   - Statement of credentials and expertise
   - Nieves-Rodriguez v. Peake, 22 Vet. App. 295 (2008)

2. REVIEW OF RECORDS
   - Statement that claims file/medical records were reviewed
   - Specific records cited in the opinion
   - Service treatment records, post-service records, lay statements

3. DIAGNOSIS
   - Current diagnosis using accepted diagnostic criteria
   - DSM-5 for mental health conditions
   - Appropriate medical terminology

4. OPINION STATEMENT
   - Clear statement using "at least as likely as not" language
   - Must specifically address the connection to service
   - Example: "It is at least as likely as not (50% or greater
     probability) that the veteran's [condition] is related to
     [specific in-service event/exposure]."

5. RATIONALE
   - This is the MOST IMPORTANT part
   - Must explain WHY the opinion is what it is
   - Cite medical literature and studies
   - Reference specific service records
   - Explain the medical mechanism of connection
   - Address any contrary evidence
   - Stefl v. Nicholson, 21 Vet. App. 120 (2007)

COMMON DEFICIENCIES:
- Bare conclusions without rationale (inadequate)
- Speculative language ("could be," "might be," "possibly related")
- Failure to review service records
- Reliance solely on veteran's self-report without corroboration
- Failure to address contrary evidence
"""

    def _cp_exam_procedures(self) -> str:
        return """C&P EXAMINATION PROCEDURES AND PREPARATION
======================================================================

WHAT IS A C&P EXAM:
Compensation & Pension (C&P) examinations are medical evaluations ordered
by VA to assess the nature and severity of claimed disabilities.

TYPES OF C&P EXAMS:
1. Initial Service Connection: Establishes diagnosis and nexus
2. Increase: Assesses current severity for rating purposes
3. Review: Periodic re-evaluation of condition
4. Aid & Attendance: Evaluates need for SMC

WHAT TO EXPECT:
- Exam conducted by VA or contracted examiner
- Examiner reviews claims file
- Medical history interview
- Physical/mental status examination
- Range of motion testing (if musculoskeletal)
- Diagnostic testing if needed
- Examiner completes Disability Benefits Questionnaire (DBQ)

PREPARATION TIPS FOR VETERANS:
1. Know your conditions and symptoms thoroughly
2. Describe your WORST DAY symptoms, not average day
3. Bring list of all medications and side effects
4. Mention ALL functional limitations
5. For mental health: describe impact on work, social, daily life
6. For joints: DO NOT take pain medication before exam (mask symptoms)
7. If asked to demonstrate range of motion, stop at pain point
8. Describe flare-ups and their frequency/severity
9. Mention if conditions have worsened since last exam
10. Be honest — exaggeration undermines credibility

INADEQUATE EXAMS:
If a C&P exam is inadequate, VA must obtain a new one:
- Examiner didn't review claims file (Barr v. Nicholson)
- No rationale provided for opinion
- Relevant symptoms not addressed
- Range of motion not tested per Correia v. McDonald
- Functional loss during flare-ups not addressed per Sharp v. Shulkin
- Mental health exam didn't address all rating criteria per Mauerhan v. Principi
"""

    def _effective_date_rules(self) -> str:
        return """EFFECTIVE DATE RULES AND STRATEGIES
======================================================================

GENERAL RULE (38 USC 5110):
The effective date of an award is the date of receipt of claim OR
the date entitlement arose, WHICHEVER IS LATER.

KEY EFFECTIVE DATE RULES:

1. ORIGINAL CLAIM:
   - Filed within 1 year of discharge: Effective date = day after discharge
   - Filed after 1 year: Effective date = date of claim receipt

2. INTENT TO FILE (VA Form 21-0966):
   - Preserves effective date for up to 1 year
   - CRITICAL: File ITF immediately, gather evidence after

3. CLAIM FOR INCREASE:
   - Date of claim or date entitlement arose, whichever is later
   - Exception: If increase occurred within 1 year before claim,
     effective date can be up to 1 year before claim date

4. SUPPLEMENTAL CLAIM (New & Relevant Evidence):
   - If filed within 1 year of prior decision: relates back to original claim
   - If filed after 1 year: date of supplemental claim

5. CLEAR AND UNMISTAKABLE ERROR (CUE):
   - Effective date: date of the original erroneous decision
   - Can go back decades if CUE is established

6. LIBERALIZING LAW:
   - If claim filed within 1 year of liberalizing law: effective date
     of the law (38 CFR 3.114)
   - If filed after 1 year: date of claim

7. PRESUMPTIVE CONDITIONS:
   - PACT Act: Effective date may be based on earliest claim for
     condition now presumptive

STRATEGIES:
- ALWAYS file Intent to File before gathering evidence
- File claims as early as possible
- Review old claims for potential earlier effective dates
- Look for CUE in prior decisions
- File within 1 year of any new liberalizing legislation
"""

    def _cue_claims(self) -> str:
        return """CLEAR AND UNMISTAKABLE ERROR (CUE) CLAIMS
======================================================================

DEFINITION (38 CFR 3.105(a)):
A CUE exists when the correct facts, as known at the time, were not
before the adjudicator, OR the statutory/regulatory provisions extant
at the time were incorrectly applied.

THREE-PART TEST (Russell v. Principi, 3 Vet. App. 310 (1992)):
1. Either the correct facts were not before the adjudicator or the
   law/regulations were incorrectly applied
2. The error must be undebatable
3. The error must have manifestly changed the outcome

CUE IS NOT:
- Disagreement with how evidence was weighed
- Failure to fulfill duty to assist (unless duty to assist error
  is undebatable)
- A change in diagnosis or medical judgment
- Newly discovered evidence
- A change in the law after the decision

COMMON CUE EXAMPLES:
- VA failed to apply a regulation that clearly applied
- VA miscalculated combined rating using 38 CFR 4.25
- VA failed to consider evidence that was in the record
- VA applied the wrong diagnostic code when only one code clearly applied
- VA failed to grant an inferred claim that was reasonably raised

FILING A CUE CLAIM:
- Must specify the decision being challenged
- Must identify the specific error
- Must explain how the error changed the outcome
- File with the Regional Office (for RO decisions) or BVA (for BVA decisions)

EFFECT OF SUCCESSFUL CUE:
- Prior decision is revised
- Effective date reverts to the original decision date
- Retroactive benefits awarded from that date
- Can result in significant past-due benefits
"""

    def _tdiu_procedures(self) -> str:
        return """TOTAL DISABILITY BASED ON INDIVIDUAL UNEMPLOYABILITY (TDIU)
======================================================================

PURPOSE:
TDIU allows veterans who cannot maintain substantially gainful employment
due to service-connected disabilities to receive compensation at the
100% rate, even if their combined rating is less than 100%.

SCHEDULAR TDIU (38 CFR 4.16(a)):
Requirements:
- One disability rated 60% or more, OR
- Combined rating of 70% or more with at least one disability rated 40%+
- Disabilities of common etiology count as one disability
- Unable to secure or follow substantially gainful employment

EXTRASCHEDULAR TDIU (38 CFR 4.16(b)):
- Does not meet schedular requirements
- But evidence shows inability to work due to service-connected disabilities
- Referred to Director of Compensation Service for consideration
- Rarely granted but available when warranted

APPLICATION:
- VA Form 21-8940 (Veterans Application for Increased Compensation
  Based on Unemployability)
- Also can be inferred from the record (Rice v. Shinseki)

SUBSTANTIALLY GAINFUL EMPLOYMENT:
- More than marginal employment
- Marginal employment: Annual income below poverty threshold
- Protected/sheltered work environment may be marginal
- Consider education, training, work history, functional limitations

EVIDENCE TO SUPPORT TDIU:
1. Medical evidence of functional limitations
2. Vocational assessment or opinion
3. Employment history showing inability to maintain work
4. Employer statements about accommodations or termination
5. Social Security disability award (persuasive but not binding)
6. Statements from veteran about daily functional limitations

EFFECTIVE DATE:
- Date of claim or date unemployability arose, whichever is later
- Can be inferred from increased rating claims
- If unemployability existed at time of initial rating, may get
  earlier effective date

TDIU AND SMC:
- TDIU plus additional disability rated 60%+ may qualify for SMC(s)
  (Special Monthly Compensation housebound rate)
- Bradley v. Peake, 22 Vet. App. 280 (2008)
"""

    def _smc_levels(self) -> str:
        return """SPECIAL MONTHLY COMPENSATION (SMC) LEVELS AND CRITERIA
======================================================================

SMC provides additional compensation above the 100% rate for veterans
with specific severe disabilities or combinations.

SMC LEVELS (38 USC 1114):

SMC(k) — Loss or loss of use of specific body parts:
- One hand, one foot, one eye (or blindness)
- Creative organ
- Both buttocks
- Deafness (both ears)
- Rate: Added to any other compensation rate
- Can receive multiple SMC(k) awards

SMC(l) — Aid and Attendance:
- Need for regular aid and attendance of another person
- Due to service-connected disabilities
- Criteria: inability to dress, feed, or attend to needs of nature
- OR: incapacity requiring care to protect from hazards of daily life

SMC(m) through SMC(n) — Intermediate rates

SMC(o) — Highest statutory rate:
- Combinations of severe disabilities
- Including paraplegia, bilateral blindness with bilateral deafness,
  or conditions requiring highest level of care

SMC(p) — Paired extremities rate:
- Loss or loss of use of both lower extremities
- Loss or loss of use of both upper extremities

SMC(r)(1) — Higher level of aid and attendance:
- Need for aid and attendance at a higher level
- Typically nursing home level of care

SMC(r)(2) — Highest aid and attendance:
- Need for personal healthcare services in the home
- Would require hospitalization, nursing home, or equivalent care

SMC(s) — Housebound:
- Single 100% disability PLUS additional disability(ies) rated 60%+
- OR: permanently housebound due to service-connected disabilities
- Bradley v. Peake: TDIU counts as the "single 100% disability"
- Buie v. Shinseki: Clarified that SMC(s) can combine with TDIU

SMC(t) — Aid and Attendance for TBI:
- Residuals of TBI requiring aid and attendance
- Added by 2010 Caregivers Act

KEY STRATEGIES:
1. Always evaluate for SMC when rating is 100% or TDIU
2. Look for loss of use of extremities (SMC(k))
3. Check if housebound criteria met (SMC(s))
4. Aid and Attendance should be explored for severe conditions
5. Multiple SMC(k) awards can stack
"""

    def _secondary_service_connection(self) -> str:
        return """SECONDARY SERVICE CONNECTION — 38 CFR 3.310
======================================================================

DEFINITION:
Secondary service connection is established when a disability is
proximately due to or aggravated by a service-connected condition.

TWO THEORIES:
1. CAUSATION: Non-service-connected condition was CAUSED by
   service-connected condition
   - Example: Depression caused by chronic pain from service-connected
     back injury
   - Standard: "At least as likely as not" caused by SC condition

2. AGGRAVATION: Non-service-connected condition was AGGRAVATED
   (permanently worsened) by service-connected condition
   - Allen v. Brown, 7 Vet. App. 439 (1995)
   - Rating based on degree of aggravation only
   - Must establish baseline severity before aggravation
   - Example: Pre-existing hypertension aggravated by SC PTSD

COMMON SECONDARY CONDITIONS:
- Depression/anxiety secondary to chronic pain conditions
- Sleep apnea secondary to PTSD (weight gain from medications)
- Erectile dysfunction secondary to medications for SC conditions
- Radiculopathy secondary to spinal conditions
- Peripheral neuropathy secondary to diabetes
- GERD secondary to medications for SC conditions
- Migraines secondary to TBI
- Substance use disorder secondary to PTSD/chronic pain
- Hypertension secondary to PTSD or kidney conditions

EVIDENCE NEEDED:
1. Current diagnosis of claimed secondary condition
2. Established service connection for primary condition
3. Nexus opinion linking secondary to primary condition
4. Medical rationale explaining the mechanism
5. For aggravation: baseline severity evidence

IMPORTANT CASE LAW:
- Allen v. Brown: Established aggravation theory
- El-Amin v. Shinseki: Examiner must address both causation AND aggravation
- If nexus opinion only addresses causation, exam is inadequate
"""

    def _presumptive_conditions(self) -> str:
        return """PRESUMPTIVE SERVICE-CONNECTED CONDITIONS BY ERA
======================================================================

VIETNAM ERA — AGENT ORANGE (38 CFR 3.309(e)):
Service in Vietnam (including offshore) or Thailand military bases:
- AL Amyloidosis
- Bladder Cancer
- Chronic B-cell Leukemias
- Chloracne
- Diabetes Mellitus Type 2
- Hodgkin's Disease
- Hypertension
- Ischemic Heart Disease
- Monoclonal Gammopathy of Undetermined Significance (MGUS)
- Multiple Myeloma
- Non-Hodgkin's Lymphoma
- Parkinsonism
- Parkinson's Disease
- Peripheral Neuropathy, Early-Onset
- Porphyria Cutanea Tarda
- Prostate Cancer
- Respiratory Cancers
- Soft Tissue Sarcomas
- All Cancers (under PACT Act)

GULF WAR ERA (38 CFR 3.317):
Service in Southwest Asia theater (Aug 1990 - present):
- Undiagnosed illness manifested by chronic symptoms
- Medically unexplained chronic multi-symptom illness:
  - Chronic Fatigue Syndrome
  - Fibromyalgia
  - Irritable Bowel Syndrome
  - Functional Gastrointestinal Disorders
- Must manifest to 10% degree within presumptive period

POST-9/11 — PACT ACT (Public Law 117-168):
Toxic exposure presumptives:
- Burn pit/airborne hazard exposure for veterans who served in:
  - Southwest Asia, Africa, or other designated locations post-9/11
- New presumptive conditions include:
  - Various cancers (including many rare cancers)
  - Respiratory conditions (constrictive bronchiolitis, etc.)
  - Reproductive cancers
  - Brain cancers
  - Lymphatic cancers
  - And many others (full list in 38 CFR 3.320)

CHRONIC DISEASES (38 CFR 3.309(a)):
If manifested to 10% within 1 year of discharge:
- Arthritis
- Cardiovascular disease
- Diabetes
- Epilepsy
- Hansen's disease
- Hypertension
- Lupus
- Multiple Sclerosis (7 years)
- Myasthenia Gravis
- Organic diseases of the nervous system
- Peptic ulcers
- Psychoses (including PTSD per Walker v. Shinseki)
- Sarcoidosis
- Tropical diseases (within 1 year or specific periods)
- Tumors, malignant

FORMER POWS (38 CFR 3.309(c)):
Any duration of internment:
- Psychosis, anxiety states, dysthymic disorder
- Heart disease and hypertension
- Stroke and complications
- Osteoporosis
- Peptic ulcer disease
- Many other conditions
"""

    def _buddy_statements(self) -> str:
        return """BUDDY STATEMENTS AND LAY EVIDENCE STANDARDS
======================================================================

LEGAL FRAMEWORK:
Lay evidence is competent to establish observable facts and symptoms.
Jandreau v. Nicholson, 492 F.3d 1372 (Fed. Cir. 2007)
Buchanan v. Nicholson, 451 F.3d 1331 (Fed. Cir. 2006)

WHAT LAY EVIDENCE CAN ESTABLISH:
1. Observable symptoms (pain, limping, mood changes, memory loss)
2. Continuity of symptoms since service
3. In-service events and injuries
4. Behavioral changes during or after service
5. Impact of disabilities on daily functioning
6. Exposure to hazards or combat
7. Character and credibility of the veteran

WHAT LAY EVIDENCE CANNOT ESTABLISH:
- Complex medical diagnoses requiring specialized testing
- Internal medical conditions not observable to laypersons
- Medical causation requiring expertise (in most cases)

BUDDY STATEMENT BEST PRACTICES:

FORMAT:
- Written statement (VA Form 21-4138 or free-form letter)
- Full name, relationship to veteran, and contact information
- Statement must be signed and dated
- Include: "I declare under penalty of perjury that the foregoing
  is true and correct."

CONTENT SHOULD INCLUDE:
1. How the writer knows the veteran (relationship, duration)
2. Specific observations (not generalizations)
3. Dates and timeframes of observations
4. Descriptions of symptoms or behaviors witnessed
5. How veteran's condition changed from before to after service
6. Impact on veteran's daily life, work, and relationships
7. Specific examples and anecdotes

EFFECTIVE BUDDY STATEMENTS FOR SPECIFIC CLAIMS:
- PTSD: Describe behavioral changes, nightmares, startle response,
  avoidance, anger issues, substance use changes
- Physical injuries: Describe observable limitations, assistive devices,
  inability to perform tasks
- TBI: Describe cognitive changes, memory issues, personality changes
- MST: Describe behavioral changes, trust issues, relationship problems
  (corroborating markers under 38 CFR 3.304(f)(5))

NUMBER RECOMMENDED:
- 2-3 buddy statements per claimed condition
- Mix of family members, fellow service members, friends, coworkers
- Each should address different aspects of the condition

WEIGHT OF LAY EVIDENCE:
- VA must consider and weigh all lay evidence
- Cannot reject lay evidence solely because it's not from a medical professional
- Must provide reasons for accepting or rejecting lay evidence
- Consistent lay testimony strengthens claims significantly
"""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 15. PACT ACT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class PACTActScraper(BaseScraper):
    """Scraper for PACT Act (Public Law 117-168) materials."""

    @property
    def source_name(self) -> str:
        return "pact_act"

    CONGRESS_GOV = "https://www.congress.gov/bill/117th-congress/senate-bill/3373/text"
    VA_PACT_PAGE = "https://www.va.gov/resources/the-pact-act-and-your-va-benefits/"
    BURN_PIT_REGISTRY = "https://veteran.mobilehealth.va.gov/AHBurnPitRegistry/"

    def collect(self) -> dict:
        extra_stats = {"documents_collected": 0}

        # Collect from Congress.gov
        self.logger.info("Collecting PACT Act text from Congress.gov...")
        self._collect_page(self.CONGRESS_GOV, "pact_act_full_text.html", "PACT Act Full Text")
        extra_stats["documents_collected"] += 1

        # Collect VA PACT Act page
        self.logger.info("Collecting VA PACT Act implementation page...")
        self._collect_page(self.VA_PACT_PAGE, "va_pact_act_guide.html", "VA PACT Act Benefits Guide")
        extra_stats["documents_collected"] += 1

        # Create comprehensive PACT Act reference
        self._create_pact_reference()
        extra_stats["documents_collected"] += 1

        return extra_stats

    def _collect_page(self, url: str, filename: str, title: str) -> bool:
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True
        response = self.fetch(url)
        if response and response.status_code == 200:
            self.save_file(filename, response.text,
                           metadata={"type": "pact_act", "title": title, "url": url})
            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style", "nav"]):
                tag.decompose()
            body = soup.find("main") or soup.find("body")
            text = f"{title}\n{'=' * 70}\n\n{body.get_text(separator=chr(10), strip=True) if body else ''}"
            self.save_file(filename.replace(".html", ".txt"), text,
                           metadata={"type": "pact_act", "format": "text"})
            return True
        return False

    def _create_pact_reference(self) -> None:
        filename = "pact_act_comprehensive_reference.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """THE PACT ACT — COMPREHENSIVE REFERENCE
Sergeant First Class Heath Robinson Honoring Our Promise to Address
Comprehensive Toxics (PACT) Act of 2022
Public Law 117-168
======================================================================

OVERVIEW:
The PACT Act is the most significant expansion of VA benefits in decades,
primarily expanding coverage for veterans exposed to toxic substances
including burn pits, Agent Orange, and radiation.

KEY PROVISIONS:

1. TOXIC EXPOSURE PRESUMPTIONS
   - Veterans who served in covered locations are CONCEDED to have
     been exposed to toxic substances
   - No need to prove individual exposure
   - Covered locations include: Iraq, Afghanistan, Syria, and other
     Southwest Asia locations; Thailand; and specific test/cleanup sites

2. NEW PRESUMPTIVE CONDITIONS
   - Dozens of cancers and respiratory conditions linked to burn pit
     and other toxic exposures
   - Expands Agent Orange presumptives to include additional conditions
   - Covers veterans from Vietnam era through post-9/11

3. HEALTHCARE ELIGIBILITY
   - Expanded VA healthcare for toxic-exposed veterans
   - 10-year enrollment period for post-9/11 combat veterans
   - Enhanced screening for toxic exposure-related conditions

4. PHASE-IN SCHEDULE
   - Phase 1 (Aug 2022): Vietnam-era and Gulf War era veterans
   - Phase 2 (Aug 2024): Post-9/11 veterans
   - Phase 3 (Aug 2026): All remaining covered veterans
   - Note: Veterans should file claims NOW regardless of phase

5. EFFECTIVE DATES
   - For conditions that were previously denied: File Supplemental Claim
   - May receive effective date back to original denied claim
   - Intent to File recommended immediately

6. BURN PIT REGISTRY
   - Voluntary registry at VA for documenting exposure
   - Not required for claims but helpful for documentation

FILING A PACT ACT CLAIM:
1. File VA Form 21-526EZ
2. Indicate toxic exposure under PACT Act
3. Identify specific conditions
4. Provide service records showing service in covered location
5. Provide medical evidence of current diagnosis
6. VA will concede exposure — focus on diagnosis and nexus

IMPORTANT: Many previously denied claims can be reopened as
Supplemental Claims with the PACT Act as the new and relevant evidence.
""", metadata={"type": "reference", "topic": "pact_act"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 16. APPEALS MODERNIZATION ACT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AMAActScraper(BaseScraper):
    """Scraper for Appeals Modernization Act materials."""

    @property
    def source_name(self) -> str:
        return "appeals_modernization"

    CONGRESS_GOV = "https://www.congress.gov/bill/115th-congress/house-bill/2288/text"
    VA_AMA_PAGE = "https://www.va.gov/decision-reviews/"

    def collect(self) -> dict:
        extra_stats = {"documents_collected": 0}

        self.logger.info("Collecting AMA text from Congress.gov...")
        self._collect_page(self.CONGRESS_GOV, "ama_full_text.html", "Appeals Modernization Act Full Text")
        extra_stats["documents_collected"] += 1

        self.logger.info("Collecting VA decision reviews page...")
        self._collect_page(self.VA_AMA_PAGE, "va_decision_reviews.html", "VA Decision Reviews")
        extra_stats["documents_collected"] += 1

        self._create_ama_reference()
        extra_stats["documents_collected"] += 1

        return extra_stats

    def _collect_page(self, url: str, filename: str, title: str) -> bool:
        if self.file_exists(filename):
            self.stats["files_skipped"] += 1
            return True
        response = self.fetch(url)
        if response and response.status_code == 200:
            self.save_file(filename, response.text,
                           metadata={"type": "ama", "title": title, "url": url})
            soup = BeautifulSoup(response.text, "lxml")
            for t in soup(["script", "style", "nav"]):
                t.decompose()
            body = soup.find("main") or soup.find("body")
            text = f"{title}\n{'=' * 70}\n\n{body.get_text(separator=chr(10), strip=True) if body else ''}"
            self.save_file(filename.replace(".html", ".txt"), text,
                           metadata={"type": "ama", "format": "text"})
            return True
        return False

    def _create_ama_reference(self) -> None:
        filename = "ama_comprehensive_reference.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """APPEALS MODERNIZATION ACT (AMA) — COMPREHENSIVE REFERENCE
Public Law 115-55 (Effective February 19, 2019)
======================================================================

OVERVIEW:
The AMA replaced the legacy VA appeals system with three decision review
lanes, designed to be faster and more veteran-friendly.

THREE REVIEW LANES:

1. SUPPLEMENTAL CLAIM (VA Form 20-0995)
   - File when you have NEW AND RELEVANT evidence
   - Full duty to assist applies
   - VA will help develop the claim
   - No time limit to file
   - Can file multiple supplemental claims
   - If filed within 1 year of decision: preserves effective date
   - Best for: Claims denied for lack of evidence

2. HIGHER-LEVEL REVIEW (VA Form 20-0996)
   - Senior reviewer re-examines existing evidence
   - NO new evidence allowed
   - NO duty to assist
   - Informal conference available (similar to hearing)
   - Must file within 1 year of decision
   - Reviewer can identify duty to assist errors → returns to RO
   - Best for: Claims where evidence supports grant but was missed

3. BOARD APPEAL (VA Form 10182)
   - Appeal to Board of Veterans' Appeals
   - Must file within 1 year of decision
   - Three docket options:
     a. DIRECT REVIEW: No new evidence, no hearing
        - Fastest board option
        - Judge reviews existing record
     b. EVIDENCE SUBMISSION: Submit new evidence within 90 days
        - No hearing
        - Can submit evidence not previously considered
     c. HEARING: Virtual or in-person hearing with Veterans Law Judge
        - Can submit evidence at and after hearing (90 days)
        - Best opportunity to present your case directly
        - Highest success rate but longest wait time

LANE SWITCHING:
- After any decision, you can choose any lane
- Can go from HLR to Supplemental Claim (most common path)
- Can go from Board to Supplemental Claim
- Cannot file same-lane review of same-lane decision (except Supplemental)

KEY DEADLINES:
- 1 year from decision to file in any lane and preserve effective date
- Beyond 1 year: Only Supplemental Claim available (new effective date)
- Board Appeal: 90 days for evidence submission after hearing

LEGACY VS. AMA:
- Claims decided before Feb 19, 2019: Legacy system
- Claims decided after Feb 19, 2019: AMA system
- Veterans in legacy system could opt in to AMA via RAMP
- Most claims now processed under AMA

TIPS:
1. After any denial, carefully read the decision letter
2. Determine what evidence is missing or what error occurred
3. Choose the appropriate lane based on your situation
4. If unsure, Supplemental Claim is often the safest option
5. Always preserve effective dates by filing within 1 year
6. Consider consulting VSO or attorney for Board Appeals
""", metadata={"type": "reference", "topic": "ama"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 17. VA CLINICAL GUIDELINES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ClinicalGuidelinesScraper(BaseScraper):
    """Scraper for VA/DoD Clinical Practice Guidelines."""

    @property
    def source_name(self) -> str:
        return "va_clinical_guidelines"

    GUIDELINES_URL = VA_CLINICAL_GUIDELINES
    GUIDELINES_BASE = "https://www.healthquality.va.gov"

    PRIORITY_GUIDELINES = [
        "PTSD",
        "mTBI",  # mild TBI
        "Chronic Pain",
        "Substance Use Disorders",
        "Major Depressive Disorder",
        "Bipolar Disorder",
        "Schizophrenia",
        "Suicide Risk",
        "Chronic Kidney Disease",
        "Diabetes",
        "Heart Failure",
        "Hypertension",
        "Stroke Rehabilitation",
    ]

    def collect(self) -> dict:
        extra_stats = {"guidelines_collected": 0}

        self.logger.info("Fetching VA clinical guidelines index...")
        response = self.fetch(self.GUIDELINES_URL)
        if response and response.status_code == 200:
            self.save_file("clinical_guidelines_index.html", response.text,
                           metadata={"type": "index", "url": self.GUIDELINES_URL})

            soup = BeautifulSoup(response.text, "lxml")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                if any(g.lower() in text.lower() for g in self.PRIORITY_GUIDELINES):
                    full_url = urljoin(self.GUIDELINES_BASE, href)
                    safe_name = re.sub(r'[^\w\s-]', '', text)[:60].replace(" ", "_")
                    filename = f"guideline_{safe_name}"
                    ext = ".pdf" if href.lower().endswith(".pdf") else ".html"

                    if not self.file_exists(filename + ext):
                        doc_resp = self.fetch(full_url)
                        if doc_resp and doc_resp.status_code == 200:
                            content = doc_resp.content if ext == ".pdf" else doc_resp.text
                            self.save_file(filename + ext, content,
                                           metadata={"type": "clinical_guideline", "title": text, "url": full_url})
                            extra_stats["guidelines_collected"] += 1

        return extra_stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 18. MILITARY PERSONNEL REGULATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class MilitaryPersonnelRegsScraper(BaseScraper):
    """Scraper for military personnel regulations on discharge characterizations."""

    @property
    def source_name(self) -> str:
        return "military_personnel_regs"

    REGS = {
        "ar_635_200": {
            "name": "AR 635-200: Active Duty Enlisted Administrative Separations",
            "branch": "Army",
            "url": "https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN30234-AR_635-200-000-WEB-1.pdf",
        },
        "milpersman_1910": {
            "name": "MILPERSMAN 1910 Series: Enlisted Separations",
            "branch": "Navy/Marines",
            "url": "https://www.mynavyhr.navy.mil/References/MILPERSMAN/1000-Military-Personnel/1900-Separation/",
        },
        "afi_36_3208": {
            "name": "AFI 36-3208: Administrative Separation of Airmen",
            "branch": "Air Force",
            "url": "https://www.e-publishing.af.mil/",
        },
    }

    def collect(self) -> dict:
        extra_stats = {"regs_collected": 0}

        for reg_key, reg_info in self.REGS.items():
            self.logger.info(f"Collecting {reg_info['name']}...")
            filename = f"{reg_key}"
            ext = ".pdf" if reg_info["url"].endswith(".pdf") else ".html"
            filename += ext

            if self.file_exists(filename):
                self.stats["files_skipped"] += 1
                continue

            response = self.fetch(reg_info["url"])
            if response and response.status_code == 200:
                content = response.content if ext == ".pdf" else response.text
                self.save_file(filename, content,
                               metadata={"type": "personnel_reg", "reg_key": reg_key,
                                         "name": reg_info["name"], "branch": reg_info["branch"],
                                         "url": reg_info["url"]})
                extra_stats["regs_collected"] += 1

        # Create discharge characterization reference
        self._create_discharge_reference()
        extra_stats["regs_collected"] += 1

        return extra_stats

    def _create_discharge_reference(self) -> None:
        filename = "discharge_characterization_reference.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """DISCHARGE CHARACTERIZATIONS AND VA BENEFITS ELIGIBILITY
======================================================================

TYPES OF DISCHARGE:

1. HONORABLE DISCHARGE
   - Full VA benefits eligibility
   - Given when service performance meets or exceeds standards

2. GENERAL (UNDER HONORABLE CONDITIONS)
   - Full VA benefits eligibility
   - Given when service was satisfactory but did not meet all standards

3. OTHER THAN HONORABLE (OTH)
   - VA benefits: CASE-BY-CASE determination
   - VA makes Character of Discharge (COD) determination under 38 CFR 3.12
   - Some benefits may be available even without upgrade
   - Healthcare for service-connected conditions may be available
   - Discharge upgrade highly recommended

4. BAD CONDUCT DISCHARGE (BCD)
   - Special Court-Martial BCD: Same as OTH (case-by-case)
   - General Court-Martial BCD: Generally bars VA benefits
   - Can seek upgrade through BCMR

5. DISHONORABLE DISCHARGE
   - Statutory bar to VA benefits (38 USC 5303)
   - Only BCMR upgrade or Presidential pardon restores eligibility

CHARACTER OF DISCHARGE DETERMINATION (38 CFR 3.12):
VA makes its own determination of character of service for benefits purposes.

BARS TO BENEFITS (38 CFR 3.12(c)):
- Conscientious objector who refused duties
- AWOL for continuous period of 180+ days
- Sentence by general court-martial
- Resignation of officer for good of the service
- Acceptance of OTH to escape trial by general court-martial

EXCEPTIONS (38 CFR 3.12(b)):
- Insanity at time of commission of the offense
- Compelling circumstances for AWOL (38 CFR 3.12(c)(6))
- Minor infractions
- Service-connected disability incurred before discharge

38 CFR 3.12(d) — CHARACTER OF DISCHARGE DETERMINATION FACTORS:
- Reasons for discharge
- Length of service
- Performance ratings
- Nature of infractions
- Overall record
- Whether infractions were related to mental health conditions

IMPORTANT: Even with a bar to benefits, a veteran may be eligible for
healthcare for conditions incurred during the period of honorable service.
""", metadata={"type": "reference", "topic": "discharge_characterization"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 19. VA OIG & GAO REPORTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class OIGGAOScraper(BaseScraper):
    """Scraper for VA Office of Inspector General and GAO reports."""

    @property
    def source_name(self) -> str:
        return "va_oig_reports"

    VA_OIG_REPORTS = f"{VA_OIG_BASE}publications/report-landing.asp"
    GAO_VA_REPORTS = f"{GAO_BASE}reports-testimonies/"

    OIG_SEARCH_TERMS = [
        "claims processing accuracy",
        "disability compensation",
        "regional office performance",
        "rating consistency",
        "appeals processing",
        "duty to assist compliance",
    ]

    GAO_SEARCH_TERMS = [
        "VA disability claims processing",
        "veterans benefits accuracy",
        "VA appeals modernization",
    ]

    def collect(self) -> dict:
        extra_stats = {"oig_reports": 0, "gao_reports": 0}

        # VA OIG reports
        self.logger.info("Collecting VA OIG reports...")
        response = self.fetch(f"{VA_OIG_BASE}publications/report-landing.asp")
        if response and response.status_code == 200:
            self.save_file("va_oig_index.html", response.text,
                           metadata={"type": "oig_index"})
            soup = BeautifulSoup(response.text, "lxml")
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                if any(term in text.lower() for term in ["claim", "disability", "compensation", "rating", "appeal"]):
                    full_url = urljoin(VA_OIG_BASE, href)
                    safe = re.sub(r'[^\w\s-]', '', text)[:60].replace(" ", "_")
                    ext = ".pdf" if href.endswith(".pdf") else ".html"
                    fname = f"oig_{safe}{ext}"
                    if not self.file_exists(fname):
                        doc_resp = self.fetch(full_url)
                        if doc_resp and doc_resp.status_code == 200:
                            self.save_file(fname, doc_resp.content if ext == ".pdf" else doc_resp.text,
                                           metadata={"type": "oig_report", "title": text, "url": full_url})
                            extra_stats["oig_reports"] += 1

        # GAO reports
        self.logger.info("Collecting GAO veterans-related reports...")
        for term in self.GAO_SEARCH_TERMS:
            search_url = f"{GAO_BASE}search"
            params = {"query": term}
            response = self.fetch(search_url, params=params)
            if response and response.status_code == 200:
                safe_term = re.sub(r'[^\w]', '_', term)[:40]
                self.save_file(f"gao_search_{safe_term}.html", response.text,
                               metadata={"type": "gao_search", "term": term})
                extra_stats["gao_reports"] += 1

        return extra_stats


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 20. SUPPLEMENTARY LEGAL RESOURCES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class SupplementaryLegalScraper(BaseScraper):
    """Scraper for supplementary legal resources."""

    @property
    def source_name(self) -> str:
        return "supplementary_legal"

    VA_GC_OPINIONS = "https://www.va.gov/ogc/precedent-opinions.asp"
    EAJA_INFO = "https://www.uscourts.cavc.gov/forms_fees.php"

    def collect(self) -> dict:
        extra_stats = {"documents_collected": 0}

        # VA General Counsel Precedent Opinions
        self.logger.info("Collecting VA General Counsel Precedent Opinions...")
        response = self.fetch(self.VA_GC_OPINIONS)
        if response and response.status_code == 200:
            self.save_file("va_gc_precedent_opinions.html", response.text,
                           metadata={"type": "gc_opinions", "url": self.VA_GC_OPINIONS})

            soup = BeautifulSoup(response.text, "lxml")
            for tag in soup(["script", "style"]):
                tag.decompose()
            body = soup.find("main") or soup.find("body")
            if body:
                self.save_file("va_gc_precedent_opinions.txt",
                               f"VA GENERAL COUNSEL PRECEDENT OPINIONS\n{'=' * 70}\n\n{body.get_text(separator=chr(10), strip=True)}",
                               metadata={"type": "gc_opinions", "format": "text"})

            # Follow links to individual opinions
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True)
                if "opinion" in href.lower() or "opinion" in text.lower():
                    full_url = urljoin("https://www.va.gov/ogc/", href)
                    safe = re.sub(r'[^\w\s-]', '', text)[:50].replace(" ", "_")
                    ext = ".pdf" if href.endswith(".pdf") else ".html"
                    fname = f"gc_opinion_{safe}{ext}"
                    if not self.file_exists(fname):
                        doc_resp = self.fetch(full_url)
                        if doc_resp and doc_resp.status_code == 200:
                            self.save_file(fname, doc_resp.content if ext == ".pdf" else doc_resp.text,
                                           metadata={"type": "gc_opinion", "title": text, "url": full_url})
                            extra_stats["documents_collected"] += 1

        # Create supplementary legal references
        self._create_attorney_fees_reference()
        extra_stats["documents_collected"] += 1
        self._create_eaja_reference()
        extra_stats["documents_collected"] += 1

        return extra_stats

    def _create_attorney_fees_reference(self) -> None:
        filename = "attorney_fees_38usc5904.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """ATTORNEY FEES IN VA CLAIMS — 38 USC 5904
======================================================================

WHEN FEES CAN BE CHARGED:
- Only AFTER an agency of original jurisdiction (AOJ) has issued
  an initial decision on the claim
- Cannot charge fees for filing initial claims
- Can charge fees for appeals, supplemental claims, higher-level reviews

FEE AGREEMENTS:
1. Direct-Pay Fee Agreement:
   - VA withholds attorney fees from past-due benefits
   - Maximum 20% of past-due benefits for direct-pay agreements
   - Filed with VA Office of General Counsel
   - Most common arrangement

2. Non-Direct-Pay Fee Agreement:
   - Attorney bills veteran directly
   - No VA withholding
   - Must be reasonable
   - Filed with VA OGC

FEE REASONABLENESS FACTORS:
- Time and labor required
- Novelty and difficulty of questions
- Skill required
- Results obtained
- Customary fees for similar services
- Whether fee is fixed or contingent

PROHIBITED FEE PRACTICES:
- Charging fees before initial AOJ decision
- Excessive or unreasonable fees
- Splitting fees with non-accredited individuals
- Charging for VA Form 21-22a filing

EQUAL ACCESS TO JUSTICE ACT (EAJA):
- If veteran prevails against VA in court, government may pay fees
- Available at CAVC level
- Must show VA's position was not substantially justified
- Application must be filed within 30 days of final judgment
- Fees based on statutory rate (adjusted for cost of living)
""", metadata={"type": "reference", "topic": "attorney_fees"})

    def _create_eaja_reference(self) -> None:
        filename = "eaja_reference.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """EQUAL ACCESS TO JUSTICE ACT (EAJA) — 28 USC 2412
======================================================================

PURPOSE:
EAJA allows veterans who prevail against VA in court proceedings at
the CAVC to recover attorney fees and expenses from the government.

ELIGIBILITY:
1. Must be a "prevailing party" — obtained relief from the court
2. VA's position must not have been "substantially justified"
3. Net worth must be under $2,000,000 (individuals)
4. Must apply within 30 days of final judgment

APPLICATION PROCESS:
1. File EAJA application with CAVC
2. Include itemized fee statement
3. Include affidavit of net worth
4. VA has 30 days to respond
5. Court rules on reasonableness of fees

FEE RATES:
- Statutory rate: $125/hour (adjusted for cost of living)
- Higher rates may be awarded for specialized expertise
- 2024 adjusted rate: approximately $230-250/hour
- Expenses and costs also recoverable

PRACTICAL EFFECT:
- Makes it financially viable for attorneys to represent veterans
- Attorney can receive both direct-pay fee AND EAJA fees (but must
  offset — veteran receives the larger of the two)
- Incentivizes quality representation at CAVC level

IMPORTANT CASE LAW:
- Scarborough v. Principi: EAJA timing requirements
- Commissioner v. Jean: "Substantially justified" standard
""", metadata={"type": "reference", "topic": "eaja"})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VASRD (Structured rating schedule extraction)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class VASRDScraper(BaseScraper):
    """Dedicated scraper for the VA Schedule for Rating Disabilities (38 CFR Part 4)."""

    @property
    def source_name(self) -> str:
        return "vasrd_rating_schedule"

    ECFR_PART4_URL = "https://www.ecfr.gov/api/renderer/v1/content/enhanced/current/title-38/chapter-I/part-4"

    # Subparts of 38 CFR Part 4
    SUBPARTS = {
        "A": "General Policy in Rating",
        "B": "Disability Ratings (General)",
        # Body systems
        "musculoskeletal": "The Musculoskeletal System (DC 5000-5399)",
        "organs_of_special_sense": "Organs of Special Sense (DC 6000-6399)",
        "respiratory": "The Respiratory System (DC 6500-6899)",
        "cardiovascular": "The Cardiovascular System (DC 7000-7199)",
        "digestive": "The Digestive System (DC 7200-7399)",
        "genitourinary": "The Genitourinary System (DC 7500-7599)",
        "gynecological": "Gynecological Conditions (DC 7610-7699)",
        "hemic_lymphatic": "The Hemic and Lymphatic Systems (DC 7700-7799)",
        "skin": "The Skin (DC 7800-7899)",
        "endocrine": "The Endocrine System (DC 7900-7999)",
        "neurological": "Neurological Conditions (DC 8000-8599)",
        "mental_disorders": "Mental Disorders (DC 9000-9599)",
        "dental_oral": "Dental and Oral Conditions (DC 9900-9999)",
        "infectious_diseases": "Infectious Diseases (DC 6300-6399)",
    }

    def collect(self) -> dict:
        extra_stats = {"sections_collected": 0}

        # Collect full Part 4
        self.logger.info("Collecting 38 CFR Part 4 (VASRD)...")
        response = self.fetch(self.ECFR_PART4_URL)
        if response and response.status_code == 200:
            self.save_file("vasrd_part_4_full.html", response.text,
                           metadata={"type": "vasrd_full", "url": self.ECFR_PART4_URL})

            # Extract structured text
            text = self._extract_vasrd_text(response.text)
            self.save_file("vasrd_part_4_full.txt", text,
                           metadata={"type": "vasrd_full", "format": "text"})
            extra_stats["sections_collected"] += 1

        # Create mental disorders rating reference (most commonly claimed)
        self._create_mental_health_rating_reference()
        extra_stats["sections_collected"] += 1

        return extra_stats

    def _extract_vasrd_text(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav"]):
            tag.decompose()

        lines = [
            "VA SCHEDULE FOR RATING DISABILITIES (VASRD)",
            "38 CFR Part 4",
            "=" * 70, "",
        ]

        body = soup.find("body")
        if body:
            for elem in body.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th"]):
                text = elem.get_text(separator=" ", strip=True)
                if not text:
                    continue
                tag = elem.name
                if tag in ("h1", "h2"):
                    lines.extend(["", "=" * 60, text, "=" * 60, ""])
                elif tag in ("h3", "h4"):
                    lines.extend(["", text, "-" * min(len(text), 60), ""])
                elif tag in ("td", "th"):
                    lines.append(f"  | {text}")
                elif tag == "li":
                    lines.append(f"  - {text}")
                else:
                    lines.extend([text, ""])

        return "\n".join(lines)

    def _create_mental_health_rating_reference(self) -> None:
        filename = "mental_health_general_rating_formula.txt"
        if self.file_exists(filename):
            return
        self.save_file(filename, """GENERAL RATING FORMULA FOR MENTAL DISORDERS
38 CFR 4.130 — Diagnostic Codes 9201-9521
======================================================================

This formula applies to ALL mental disorder diagnostic codes including:
- DC 9201: Schizophrenia
- DC 9400: Generalized Anxiety Disorder
- DC 9411: PTSD
- DC 9434: Major Depressive Disorder
- DC 9440: Chronic Adjustment Disorder

RATING CRITERIA:

100% — Total occupational and social impairment, due to such symptoms as:
  - Gross impairment in thought processes or communication
  - Persistent delusions or hallucinations
  - Grossly inappropriate behavior
  - Persistent danger of hurting self or others
  - Intermittent inability to perform activities of daily living
  - Disorientation to time or place
  - Memory loss for names of close relatives, own occupation, or own name

70% — Occupational and social impairment, with deficiencies in most areas
  such as work, school, family relations, judgment, thinking, or mood,
  due to such symptoms as:
  - Suicidal ideation
  - Obsessional rituals which interfere with routine activities
  - Speech intermittently illogical, obscure, or irrelevant
  - Near-continuous panic or depression affecting the ability to
    function independently, appropriately, and effectively
  - Impaired impulse control (such as unprovoked irritability with
    periods of violence)
  - Spatial disorientation
  - Neglect of personal appearance and hygiene
  - Difficulty in adapting to stressful circumstances
  - Inability to establish and maintain effective relationships

50% — Occupational and social impairment with reduced reliability and
  productivity due to such symptoms as:
  - Flattened affect
  - Circumstantial, circumlocutory, or stereotyped speech
  - Panic attacks more than once a week
  - Difficulty in understanding complex commands
  - Impairment of short- and long-term memory
  - Impaired judgment
  - Impaired abstract thinking
  - Disturbances of motivation and mood
  - Difficulty in establishing and maintaining effective work
    and social relationships

30% — Occupational and social impairment with occasional decrease in
  work efficiency and intermittent periods of inability to perform
  occupational tasks, due to such symptoms as:
  - Depressed mood
  - Anxiety
  - Suspiciousness
  - Panic attacks (weekly or less often)
  - Chronic sleep impairment
  - Mild memory loss (such as forgetting names, directions, recent events)

10% — Occupational and social impairment due to mild or transient symptoms
  which decrease work efficiency and ability to perform occupational tasks
  only during periods of significant stress, or symptoms controlled by
  continuous medication.

0% — A mental condition has been formally diagnosed, but symptoms are not
  severe enough either to interfere with occupational and social functioning
  or to require continuous medication.

IMPORTANT NOTES:
- The symptoms listed are EXAMPLES, not an exhaustive list
  (Mauerhan v. Principi, 16 Vet. App. 436 (2002))
- Rating should be based on ALL symptoms and their frequency/severity
- The overall level of disability determines the rating, not checkboxes
- Mittleider rule: If SC and non-SC symptoms cannot be separated,
  all symptoms are attributed to the SC condition
""", metadata={"type": "reference", "topic": "mental_health_rating"})


def main():
    """Run all remaining source scrapers."""
    scrapers = [
        VSOTrainingScraper(),
        ClaimsProceduresScraper(),
        PACTActScraper(),
        AMAActScraper(),
        ClinicalGuidelinesScraper(),
        MilitaryPersonnelRegsScraper(),
        OIGGAOScraper(),
        SupplementaryLegalScraper(),
        VASRDScraper(),
    ]
    for scraper in scrapers:
        stats = scraper.run()
        print(f"{scraper.source_name}: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    main()
