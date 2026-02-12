# Data Collection & Fine-Tuning Dataset Pipeline — Master Prompt

> **Usage:** Copy everything below the line into a new Claude Code session pointed at this repository.

---

You are working on the **Valor Assist** project at `/home/user/Claude-vet-AI-/`. This is a RAG-powered AI assistant for U.S. military veterans navigating VA disability claims, appeals, discharge upgrades, and military record corrections. The existing backend (FastAPI + ChromaDB + Claude 3.5 Sonnet) is functional but the knowledge base is skeletal — only 4 seed documents totaling ~1,657 words in `app/data/raw/`.

## YOUR MISSION

Build a comprehensive, production-grade **data collection, scraping, cleaning, and preparation pipeline** that will gather every source necessary to make this system equivalent in knowledge to a **bar-certified attorney specializing in veterans law**, a **certified Veterans Service Officer (VSO)**, and an **accredited Veterans Claims Representative** — all rolled into one.

This data will serve two purposes:
1. **Immediate RAG knowledge base** — cleaned text chunks for the existing ChromaDB pipeline
2. **Fine-tuning dataset** — structured instruction/response pairs for training a custom model

## PHASE 1: Build the Scraping & Collection Infrastructure

Create a `scripts/data_collection/` directory with modular, source-specific scrapers. Each scraper should:
- Be an independent Python module that can run standalone or as part of the full pipeline
- Handle rate limiting, retries with exponential backoff, and polite crawling (respect robots.txt)
- Save raw downloads to `app/data/raw/{source_category}/` with consistent naming
- Log progress and errors to `logs/data_collection.log`
- Support incremental updates (don't re-download what we already have)
- Include checksums/hashes to detect changes in source material

### Required dependencies to add to a `requirements-data.txt`:
- `requests` + `httpx` (async HTTP)
- `beautifulsoup4` + `lxml` (HTML parsing)
- `scrapy` (for large-scale crawling jobs)
- `selenium` + `webdriver-manager` (for JavaScript-rendered pages)
- `pdfplumber` or `pymupdf` (PDF extraction)
- `python-docx` (Word document extraction)
- `pandas` (data structuring)
- `tqdm` (progress bars)
- `tenacity` (retry logic)
- `fake-useragent` (polite scraping headers)
- `jsonlines` (fine-tuning dataset format)

## PHASE 2: Source-by-Source Data Collection

Build a dedicated scraper/downloader for EACH of the following source categories. Every source must be downloaded, extracted to plain text, cleaned, and tagged with metadata.

---

### 1. TITLE 38 — CODE OF FEDERAL REGULATIONS (38 CFR)

**What:** The complete body of VA regulations governing veterans benefits.
**Where:**
- eCFR (official): `https://www.ecfr.gov/current/title-38`
- GovInfo bulk XML: `https://www.govinfo.gov/bulkdata/CFR/`
**Priority sections:**
- Part 3 — Adjudication (ratings, service connection, effective dates, evidence)
- Part 4 — Schedule for Rating Disabilities (VASRD) — EVERY diagnostic code
- Part 17 — Medical care eligibility
- Part 19 — Board of Veterans' Appeals rules of practice
- Part 20 — Board of Veterans' Appeals appeals regulations
- Part 21 — Vocational Rehabilitation and Education
**Collect:** ALL sections of Title 38 CFR, not just these. Every part, every section.

---

### 2. TITLE 38 — UNITED STATES CODE (38 USC)

**What:** The statutory foundation for all VA benefits and veterans' rights.
**Where:**
- USLM (official XML): `https://uscode.house.gov/download/download.shtml`
- GovInfo: `https://www.govinfo.gov/content/pkg/USCODE-2023-title38/`
**Priority chapters:**
- Chapter 11 — Compensation for Service-Connected Disability
- Chapter 13 — Dependency and Indemnity Compensation
- Chapter 15 — Pension for Non-Service-Connected Disability
- Chapter 51 — Claims, Effective Dates, and Payments
- Chapter 71 — Board of Veterans' Appeals
- Chapter 72 — United States Court of Appeals for Veterans Claims
**Collect:** The ENTIRE title, all chapters and sections.

---

### 3. UNIFORM CODE OF MILITARY JUSTICE (UCMJ) — 10 USC Chapter 47

**What:** Military criminal law. Essential for understanding discharge characterizations, court-martial records, and how punitive discharges affect VA eligibility.
**Where:**
- USLM: `https://uscode.house.gov/` (Title 10, Subtitle A, Part II, Chapter 47)
- Manual for Courts-Martial (MCM): `https://jsc.defense.gov/Military-Law/Current-Publications/`
**Collect:**
- All UCMJ articles (Articles 1–146a)
- The Manual for Courts-Martial (MCM) — full text including Rules for Courts-Martial, Military Rules of Evidence, and Discussion sections
- Executive Orders amending the MCM

---

### 4. VA ADJUDICATION PROCEDURES MANUAL (M21-1)

**What:** The VA's internal manual that adjudicators use to rate claims. This IS the playbook.
**Where:**
- VA's knowledge base: `https://www.knowva.ebenefits.va.gov/system/templates/selfservice/va_ssnew/help/customer/locale/en-US/portal/554400000001018/`
- Web archive fallbacks for older versions
**Collect:**
- ALL parts (I through XVI)
- Every section, subsection, and appendix
- Particular focus on Part III (Claims), Part IV (Rating Procedures), Part V (Appeals)

---

### 5. VA SCHEDULE FOR RATING DISABILITIES (VASRD) — 38 CFR Part 4

**What:** The diagnostic code schedule used to assign disability percentages.
**Where:** Embedded in 38 CFR Part 4, but also needs structured extraction.
**Collect:**
- Every diagnostic code (DC 5000–9999+) with:
  - Code number
  - Condition name
  - Rating criteria for each percentage level (0%, 10%, 20%, 30%, 40%, 50%, 60%, 70%, 80%, 90%, 100%)
  - Applicable notes and special provisions
- Structure as both raw text AND a structured JSON/CSV lookup table

---

### 6. BOARD OF VETERANS' APPEALS (BVA) DECISIONS

**What:** Precedential and non-precedential decisions from the BVA.
**Where:**
- BVA Decision Search: `https://www.index.va.gov/search/va/bva.jsp`
- Bulk via VA FOIA or public APIs
**Collect:**
- Minimum 10,000 decisions across all claim types
- Priority: PTSD, TBI, MST, tinnitus, back conditions, knee conditions, sleep apnea, mental health, Gulf War illness, Agent Orange presumptives, burn pit exposure
- Extract: docket number, date, issue(s), holding (granted/denied/remanded), reasoning, cited regulations

---

### 7. U.S. COURT OF APPEALS FOR VETERANS CLAIMS (CAVC)

**What:** The Article I federal court that reviews BVA decisions. Precedential opinions are binding on the VA.
**Where:**
- CAVC website: `https://www.uscourts.cavc.gov/opinions.php`
- Public Access to Court Electronic Records (PACER) for older decisions
**Collect:**
- ALL published (precedential) opinions
- Key single-judge and panel decisions
- Focus on landmark cases: *Gilbert v. Derwinski*, *Caluza v. Brown*, *Shedden v. Principi*, *Jandreau v. Nicholson*, *Buchanan v. Nicholson*, *Vazquez-Flores v. Peake*, *Shade v. Shinseki*, *Bryant v. Shinseki*, etc.
- Extract: case name, docket, date, issue, holding, key legal principles established

---

### 8. U.S. COURT OF APPEALS FOR THE FEDERAL CIRCUIT (Veterans Cases)

**What:** Reviews CAVC decisions. Binding precedent on all veterans law.
**Where:**
- Federal Circuit: `https://cafc.uscourts.gov/home/case-information/opinions-orders/`
- Filter for cases originating from the CAVC
**Collect:**
- All Federal Circuit opinions in veterans law cases
- Landmark decisions on standard of review, benefit of the doubt, duty to assist

---

### 9. BOARD FOR CORRECTION OF MILITARY RECORDS (BCMR) — All Branches

**What:** Each service branch has its own board that can correct military records, including discharge upgrades.
**Where and what boards:**
- **Army (ABCMR):** `https://arba.army.pentagon.mil/abcmr-overview.html`
- **Navy/Marines (BCNR):** `https://www.secnav.navy.mil/mra/bcnr/`
- **Air Force/Space Force (AFBCMR):** `https://www.afpc.af.mil/Board-for-Correction-of-Military-Records/`
- **Coast Guard (BCMR-CG):** Via DHS
**Collect:**
- Board procedures and application instructions
- Published decisions/case summaries
- DD Form 149 instructions and requirements
- Standards of review for each board
- Precedential decisions on discharge upgrades, PTSD/TBI/MST liberalizing standards (Hagel memo, Kurta memo, Wilkie memo)

---

### 10. DISCHARGE REVIEW BOARDS (DRB) — All Branches

**What:** Reviews discharge characterizations (less-than-honorable to honorable).
**Where:**
- **Army DRB:** `https://arba.army.pentagon.mil/adrb-overview.html`
- **Navy DRB:** `https://www.secnav.navy.mil/mra/bcnr/Pages/ndrb.aspx`
- **Air Force DRB:** `https://www.afpc.af.mil/Discharge-Review-Board/`
**Collect:**
- Procedures, DD Form 293 instructions
- Published decisional documents
- Standards for discharge characterization changes
- Documentary vs. personal hearing procedures
- Success rate data if available

---

### 11. DoD POLICY MEMORANDA ON LIBERAL CONSIDERATION

**What:** Critical policy directives requiring liberal consideration for PTSD, TBI, MST, and mental health in discharge upgrade and records correction cases.
**Collect:**
- **Hagel Memo** (2014) — Supplemental guidance for PTSD-related discharge reviews
- **Carson Memo** (2014) — PTSD liberal consideration instructions
- **Kurta Memo** (2017) — Clarifying guidance for liberal consideration of discharge upgrade requests involving mental health, TBI, sexual assault
- **Wilkie Memo** (2018) — Standards for liberal consideration in BCMR cases
- **August 2017 DoD guidance** on consideration of equity, injustice, and clemency
- Full text of each, plus any implementing instructions from each service branch

---

### 12. VA FORMS & INSTRUCTIONS

**What:** Every VA form relevant to claims, appeals, and benefits.
**Where:** `https://www.va.gov/find-forms/`
**Priority forms:**
- VA Form 21-526EZ (Disability Compensation)
- VA Form 20-0995 (Supplemental Claim)
- VA Form 20-0996 (Higher-Level Review)
- VA Form 10182 (Board Appeal / Notice of Disagreement)
- VA Form 21-4138 (Statement in Support of Claim)
- VA Form 21-0781 (PTSD Stressor Statement)
- VA Form 21-0781a (MST Stressor Statement)
- VA Form 21-8940 (TDIU Application)
- VA Form 21-22 (Appointment of VSO)
- VA Form 21-22a (Appointment of Individual Agent/Attorney)
- DD Form 214 (interpretation guide)
- DD Form 149 (BCMR Application)
- DD Form 293 (DRB Application)
**Collect:** Form instructions, field-by-field guidance, and any related VA fact sheets.

---

### 13. VETERANS SERVICE OFFICER (VSO) TRAINING MATERIALS

**What:** The knowledge base required to pass VSO accreditation.
**Where:**
- VA Office of General Counsel accreditation standards: `https://www.va.gov/ogc/accreditation.asp`
- 38 CFR Part 14 (Legal Services, General Counsel, and Accreditation)
- National Association of County Veterans Service Officers (NACVSO) training
- The American Legion service officer training materials (publicly available portions)
- DAV (Disabled American Veterans) service officer guides
- VFW service officer training resources
**Collect:**
- VA accreditation requirements (38 CFR 14.629)
- Exam preparation materials
- Best practices guides for claims development
- Ethics rules for VA-accredited representatives

---

### 14. VETERANS CLAIMS REPRESENTATIVE KNOWLEDGE

**What:** Specialized procedural knowledge for filing and prosecuting VA claims.
**Collect:**
- Duty to Assist obligations (38 USC 5103A)
- Nexus letter requirements and standards
- Independent Medical Opinion (IMO) best practices
- C&P exam procedures and what examiners look for
- Effective date rules and strategies
- CUE (Clear and Unmistakable Error) claims — standards and procedures
- Individual Unemployability (TDIU) — schedular and extraschedular
- Special Monthly Compensation (SMC) levels and criteria
- Aid & Attendance / Housebound benefits
- Secondary service connection strategies
- Aggravation claims
- Presumptive conditions by era (Vietnam/Agent Orange, Gulf War, Post-9/11 burn pits/PACT Act)
- Buddy statements and lay evidence standards

---

### 15. THE PACT ACT (Sergeant First Class Heath Robinson Honoring Our Promise to Address Comprehensive Toxics Act of 2022)

**What:** Landmark legislation expanding VA benefits for toxic exposure.
**Where:** Public Law 117-168, codified amendments to Title 38
**Collect:**
- Full text of the PACT Act
- VA implementation guidance
- New presumptive conditions list
- Burn pit registry information
- Concession of toxic exposure for covered veterans
- Timeline provisions and phase-in schedule

---

### 16. VA APPEALS MODERNIZATION ACT (AMA) — 2017/2019

**What:** The current appeals framework replacing the legacy system.
**Collect:**
- Full text of the AMA (Public Law 115-55)
- VA Rapid Appeals Modernization Program (RAMP) transition materials
- Three review lanes: Supplemental Claim, Higher-Level Review, Board Appeal
- Board Appeal docket options: Direct Review, Evidence Submission, Hearing
- Duty to Assist in each lane
- Procedural timelines and deadlines

---

### 17. VA CLINICAL PRACTICE GUIDELINES

**What:** Medical guidance the VA uses for service-connected conditions.
**Where:** `https://www.healthquality.va.gov/guidelines/`
**Collect (priority):**
- PTSD/Acute Stress treatment guidelines
- TBI management guidelines
- Chronic pain management
- MST-related conditions
- Substance Use Disorder (as secondary to service-connected conditions)
- Gulf War illness diagnostic criteria

---

### 18. MILITARY PERSONNEL REGULATIONS (Discharge Characterizations)

**What:** The regulatory basis for how discharges are characterized.
**Collect:**
- **Army:** AR 635-200 (Enlisted Separations)
- **Navy/Marines:** MILPERSMAN 1910 series
- **Air Force:** AFI 36-3208 (Administrative Separation)
- Discharge characterization criteria: Honorable, General (Under Honorable), Other Than Honorable, Bad Conduct, Dishonorable
- Character of service determination for VA benefits eligibility (38 CFR 3.12)
- Insanity exception and compelling circumstances exception

---

### 19. VA INSPECTOR GENERAL REPORTS & GAO REPORTS

**What:** Systemic issues, processing errors, and quality reviews.
**Where:**
- VA OIG: `https://www.va.gov/oig/`
- GAO: `https://www.gao.gov/` (filter for VA-related)
**Collect:**
- Reports on claims processing accuracy
- Regional Office performance reviews
- Systemic error patterns that veterans can use to identify mistakes in their own cases

---

### 20. SUPPLEMENTARY LEGAL RESOURCES

**Collect:**
- Veterans Benefits Manual (Lexis/Nexis — public excerpts and cited portions from case law)
- VA General Counsel Precedent Opinions (binding on VA adjudicators)
- CAVC Rules of Practice and Procedure
- Federal Circuit Rules of Practice
- Attorney fee agreements under 38 USC 5904
- Equal Access to Justice Act (EAJA) for attorney fees from VA

---

## PHASE 3: Data Cleaning Pipeline

Create `scripts/data_collection/clean.py` that processes ALL collected raw data:

1. **Format Normalization**
   - Convert PDF, DOCX, HTML to clean plaintext
   - Normalize Unicode, fix encoding issues
   - Remove navigation elements, boilerplate, headers/footers, page numbers

2. **Legal Text Processing**
   - Preserve section numbering and hierarchy (e.g., "38 CFR 3.304(f)(3)")
   - Maintain cross-references between regulations
   - Keep citation formatting intact
   - Preserve table structures as structured text

3. **PII Redaction** (extend existing `app/utils/text_cleaning.py`)
   - SSNs, VA file numbers, dates of birth
   - Veteran names in BVA/CAVC decisions (replace with [VETERAN])
   - Attorney names in public decisions can stay
   - Addresses, phone numbers, emails

4. **Deduplication**
   - Hash-based dedup across all sources
   - Version tracking for regulations that get updated

5. **Quality Validation**
   - Minimum word count thresholds per document type
   - Legal citation format validation
   - Completeness checks (e.g., all CFR sections present)

---

## PHASE 4: Fine-Tuning Dataset Generation

Create `scripts/data_collection/generate_training_data.py` that transforms cleaned documents into instruction-tuning format:

### Dataset Formats

**Format 1: Instruction/Response pairs (JSONL)**
```json
{
  "instruction": "What are the rating criteria for PTSD under 38 CFR 4.130, Diagnostic Code 9411?",
  "context": "[relevant regulation text]",
  "response": "Under DC 9411, PTSD is rated using the General Rating Formula for Mental Disorders..."
}
```

**Format 2: Multi-turn conversation (JSONL)**
```json
{
  "conversations": [
    {"role": "user", "content": "My claim for PTSD was denied. What are my options?"},
    {"role": "assistant", "content": "Under the Appeals Modernization Act, you have three options..."},
    {"role": "user", "content": "What if I have a new buddy statement?"},
    {"role": "assistant", "content": "A new buddy statement constitutes new and relevant evidence under 38 CFR 3.156..."}
  ]
}
```

### Training Data Categories to Generate

1. **Regulatory Q&A** — Questions about specific CFR/USC provisions with cited answers
2. **Claims Strategy** — How to develop and file specific claim types
3. **Appeals Navigation** — Step-by-step guidance for each appeal lane
4. **Case Analysis** — Given a fact pattern, identify applicable regulations and strategy
5. **Form Completion** — Field-by-field guidance for every VA/DD form
6. **Discharge Upgrade** — Strategies for each board, each branch, each basis
7. **BCMR/DRB Procedures** — Application preparation and hearing preparation
8. **Medical Evidence** — What nexus letters need, C&P exam preparation
9. **Presumptive Conditions** — Era-specific toxic exposure and presumptives
10. **Landmark Case Law** — CAVC/Fed Circuit holdings and how to apply them
11. **VSO Best Practices** — Professional standards, ethics, effective advocacy

### Quality Standards for Training Data

- Every response MUST cite specific legal authority (regulation, statute, or case)
- Responses must include appropriate legal disclaimers
- Maintain empathetic, veteran-first tone
- Never fabricate case citations or regulatory provisions
- Distinguish between binding precedent and persuasive authority
- Note when regulations have been recently amended

---

## PHASE 5: Pipeline Orchestration

Create `scripts/data_collection/run_pipeline.py` — a master orchestrator:

```
Usage:
  python -m scripts.data_collection.run_pipeline --phase collect    # Download everything
  python -m scripts.data_collection.run_pipeline --phase clean      # Clean all raw data
  python -m scripts.data_collection.run_pipeline --phase prepare    # Generate training data
  python -m scripts.data_collection.run_pipeline --phase ingest     # Load into ChromaDB
  python -m scripts.data_collection.run_pipeline --phase all        # Full pipeline
  python -m scripts.data_collection.run_pipeline --phase status     # Show collection progress
```

Include a `data_manifest.json` that tracks:
- Every source category and its collection status
- Document counts, word counts, and hash checksums
- Last collection date per source
- Cleaning and preparation status

---

## CONSTRAINTS & ETHICS

1. **Only collect publicly available legal materials.** All targeted sources are public government records, published court decisions, and public regulations. Do NOT attempt to access paywalled databases (Westlaw, LexisNexis, etc.).
2. **Respect rate limits.** Minimum 2-second delay between requests to any single domain. Obey robots.txt.
3. **No PII in training data.** Aggressively redact any personally identifiable information from case decisions.
4. **Legal disclaimer.** The system provides legal information, not legal advice. This must be baked into the training data.
5. **Accuracy over volume.** It is better to have 100% accurate data on 80% of topics than 80% accurate data on 100% of topics. Every training example should be verifiable.

---

## DELIVERABLES

When complete, the pipeline should produce:

| Output | Location | Format |
|--------|----------|--------|
| Raw downloaded files | `app/data/raw/{category}/` | .txt, .pdf, .html |
| Cleaned documents | `app/data/cleaned/{category}/` | .txt, .md |
| Training dataset | `app/data/training/` | .jsonl |
| Data manifest | `app/data/data_manifest.json` | JSON |
| ChromaDB vectors | `app/data/chroma_db/` | ChromaDB native |
| Pipeline logs | `logs/data_collection.log` | Text log |
| Collection status report | `app/data/collection_report.md` | Markdown |

---

## START HERE

Begin by:
1. Creating the `scripts/data_collection/` directory structure with `__init__.py` files
2. Creating `requirements-data.txt` with all needed dependencies
3. Building the pipeline orchestrator skeleton
4. Implementing the eCFR scraper (38 CFR) as the first source — this is the highest-priority dataset
5. Then proceed source-by-source in the order listed above

Work methodically. Build one scraper at a time, test it, verify the output, then move to the next. Commit progress frequently.
