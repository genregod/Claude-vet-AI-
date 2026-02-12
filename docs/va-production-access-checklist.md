# VA Lighthouse API — Production Access Application Checklist

> **Form URL:** https://www.va.gov/production-access/production-access-application
> **Important:** The form cannot be saved once you begin. Prepare ALL answers below before starting.

---

## Section 1: Basic Information

### 1.1 Company Contacts and Information

- [ ] **Company/Organization Name:** [YOUR ORGANIZATION NAME]
- [ ] **Point of Contact Name:** [YOUR NAME]
- [ ] **Point of Contact Email:** [YOUR EMAIL]
- [ ] **Point of Contact Phone:** [YOUR PHONE]
- [ ] **Company Address:** [YOUR ADDRESS]
- [ ] **Company Website:** [YOUR WEBSITE URL]

### 1.2 Notification Email Address

- [ ] **Email for API status updates:** [YOUR OPS/DEV EMAIL]
  > This should be a monitored address (not personal). Use a distribution list or alias if possible (e.g., api-alerts@yourcompany.com).

### 1.3 App Information and Value to Veterans

**Use this response:**

> Valor Assist is an AI-powered veterans claims assistance platform that helps U.S. military veterans navigate VA disability claims, appeals, discharge upgrades, and military records corrections. The application combines a curated legal knowledge base spanning Title 38 CFR, Title 38 USC, BVA decisions, CAVC case law, and the M21-1 Adjudication Procedures Manual with a conversational AI interface powered by Anthropic Claude.
>
> The platform provides veterans with cited, regulation-grounded guidance equivalent to what they would receive from an accredited Veterans Service Officer or Veterans Claims Representative. It identifies underrated conditions, missed secondary claims, viable appeal strategies, and eligibility for benefits such as TDIU and Special Monthly Compensation.
>
> Valor Assist serves veterans who lack convenient access to in-person VSO representation, particularly those in rural areas, those unfamiliar with the claims process, and those navigating the system for the first time. The application is free for veterans to use.

### 1.4 Business Model Description

**Use this response:**

> Valor Assist operates as a veteran service platform. The application is provided free of charge to veterans. The platform does not monetize or sell veteran data under any circumstances. Revenue is generated solely through [CHOOSE ONE: voluntary donations from users / grant funding from veteran service organizations / freemium model where basic claims guidance is free and premium case evaluation features require a subscription / pro bono — this is a nonprofit service].
>
> No veteran data — including VA API data, health records, claims information, or personal information — is used for advertising, marketing, data brokerage, or any commercial purpose. Veteran data accessed through VA APIs is used exclusively to provide personalized claims guidance to the individual veteran who authorized access.

### 1.5 Primary Users Are Veterans — App Directory Information

Since veterans are the primary users, VA requires:

- [ ] **Key URLs:**
  - Production URL: [YOUR APP URL, e.g., https://valorassist.com]
  - App Store listing (if applicable): [URL or N/A]
  - Google Play listing (if applicable): [URL or N/A]

- [ ] **Brief app description (for VA app directory):**

> Valor Assist is a free AI-powered assistant that helps veterans understand their VA disability claims, identify underrated or missing conditions, navigate the three-lane appeals process under the Appeals Modernization Act, and prepare evidence for supplemental claims, higher-level reviews, and board appeals. The app provides regulation-cited guidance, form completion instructions, and facility lookup.

- [ ] **Compatible devices and browsers:**

> **Desktop:** Chrome 90+, Firefox 90+, Safari 15+, Edge 90+
> **Mobile:** iOS Safari 15+ (iPhone/iPad), Chrome for Android 90+
> **Responsive:** Fully responsive design works on all screen sizes
> **Accessibility:** Section 508 compliant, WCAG 2.1 AA conformant

### 1.6 VA Facilities API — PatientWaitTime Screenshot

- [ ] **Required if using VA Facilities API:** Screenshot showing your app displays a message similar to: *"For more information about how wait times are calculated, visit the Access To Care page."* with a link to https://www.accesstocare.va.gov/PWT/SearchWaitTimes

> **Action needed:** Build the Facilities search feature in the frontend, include the wait time disclaimer, and take a screenshot before filling out the form.

---

## Section 2: Technical Information

### 2.1 Secure Credential Storage

**Use this response:**

> API keys, client secrets, and OAuth client IDs are stored as environment variables, never committed to source code or version control. In production, credentials are managed through AWS Secrets Manager with automatic rotation policies. Access to secrets is restricted to the application runtime via IAM roles attached to ECS Fargate task definitions — no human operator has direct access to production credentials.
>
> OAuth2 access tokens received from VA.gov are held exclusively in encrypted in-memory session state during the veteran's active session. Tokens are encrypted using Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256 authentication) at the individual field level before being placed in session storage. Tokens are never written to disk, logged, or persisted to a database. Sessions expire and tokens are destroyed after 60 minutes of inactivity.
>
> The encryption key used for Fernet is generated via Python's `cryptography` library and stored in AWS Secrets Manager, separate from application code.

### 2.2 PHI/PII Storage and Handling

**Use this response:**

> Valor Assist accesses Protected Health Information (PHI) and Personally Identifiable Information (PII) through the Veterans Health API (FHIR) and Veteran Verification API. This data is handled as follows:
>
> **In-transit:** All API communication uses TLS 1.2+ (HTTPS). No plaintext transmission occurs.
>
> **At-rest (session only):** Fetched VA data is encrypted at the individual field level using Fernet symmetric encryption (AES-128-CBC) before being held in in-memory session state. Data is NOT persisted to any database or filesystem. Sessions are destroyed after 60 minutes of inactivity or upon user logout.
>
> **In the AI pipeline:** VA data used for case evaluation is injected into the AI prompt as ephemeral context. It is not stored in the knowledge base, vector store, or any persistent layer. The AI model (Anthropic Claude) does not retain conversation data between sessions.
>
> **PII redaction:** An automated PII redaction pipeline strips SSNs (###-##-####), VA file numbers (C-########), dates of birth, phone numbers, and email addresses from any data that enters logging or the knowledge base. Redaction is applied before storage, not after.
>
> **Audit logging:** Every access to VA data is recorded in a tamper-evident audit log with: user ID, action type, data classification (PII/PHI/credential), field name, resource identifier, timestamp, and reason for access. Audit logs do not contain the data values themselves.
>
> **No secondary use:** PHI/PII is never used for analytics, machine learning training, marketing, or any purpose other than providing the individual veteran with personalized claims guidance during their active session.

### 2.3 Security and Related Procedures

#### 2.3.1 Safeguards Against Unauthorized or Duplicate Requests

> - **Authentication:** All API-accessing endpoints require a valid JWT access token issued after ID.me identity verification (LOA3). Tokens have a 15-minute TTL.
> - **Authorization:** OAuth2 scopes are enforced per-endpoint. A veteran can only access their own data.
> - **Rate limiting:** Per-IP sliding window rate limiting at 30 requests per minute on the application layer, with VA's 60 requests/minute API limit respected upstream.
> - **CSRF protection:** OAuth2 state parameters are validated on every callback. PKCE (Proof Key for Code Exchange) is used for the authorization code flow.
> - **Duplicate request prevention:** Idempotency checks on Benefits Intake and Decision Reviews submissions using request hashing to prevent double-filing.
> - **CORS:** Restricted to whitelisted frontend origins only. No wildcard origins.

#### 2.3.2 Breach Response Process

> Valor Assist maintains a documented incident response procedure:
>
> 1. **Detection:** Automated monitoring of access patterns, failed authentication attempts, and anomalous API usage via audit logs.
> 2. **Containment (0–1 hour):** Immediately revoke all affected OAuth tokens, rotate API credentials, and disable affected user sessions.
> 3. **Assessment (1–24 hours):** Determine scope of breach using audit logs. Identify affected users, data types accessed, and attack vector.
> 4. **Notification (within 72 hours):** Notify VA Lighthouse API team, affected veterans, and applicable regulatory bodies. Provide veterans with clear instructions on protective actions.
> 5. **Remediation:** Patch vulnerability, conduct root cause analysis, update security procedures, and submit incident report to VA.
> 6. **Post-incident review:** Document lessons learned and implement preventive measures.

#### 2.3.3 Vulnerability Management and Patch Processes

> - **Dependency scanning:** Automated vulnerability scanning of all Python dependencies via `pip-audit` and GitHub Dependabot, run on every pull request and weekly on the main branch.
> - **Container scanning:** Docker images are scanned for known CVEs using Trivy before deployment.
> - **Patch cadence:** Critical vulnerabilities (CVSS 9.0+) are patched within 24 hours. High vulnerabilities (CVSS 7.0–8.9) within 7 days. Medium and below within 30 days.
> - **Infrastructure updates:** ECS Fargate base images are rebuilt weekly with latest security patches.
> - **Penetration testing:** Annual third-party penetration test of the application and infrastructure.
> - **Code review:** All code changes require pull request review before merge to main.

### 2.4 OAuth Scopes Requested

- [ ] **List the scopes your application will request:**

```
profile
veteran_status.read
service_history.read
disability_rating.read
claim.read
claim.write
patient/Patient.read
patient/Condition.read
patient/MedicationRequest.read
```

### 2.5 Benefits Intake API — Specific Requirements

#### 2.5.1 Source Field Naming Convention

> Valor Assist uses the following naming convention for the `source` field in Benefits Intake API submissions:
>
> Format: `VALORASSIST-{FORM_TYPE}-{USER_ID_HASH}-{TIMESTAMP}`
>
> Examples:
> - `VALORASSIST-526EZ-a1b2c3-20260212T143022Z`
> - `VALORASSIST-0995-d4e5f6-20260212T150100Z`
>
> This convention allows VA to trace any submission back to our platform, the specific form type, and the originating session without exposing PII.

#### 2.5.2 Centralized Back-End Log for Submissions

> Yes, Valor Assist maintains a centralized, append-only submission log for all Benefits Intake API submissions. Each log entry contains:
>
> - Submission timestamp (UTC)
> - Document type (526EZ, 0995, 0996, 10182, etc.)
> - VA confirmation/tracking number returned by the API
> - User ID (internal, non-PII)
> - Submission status (accepted, rejected, error)
> - File hash (SHA-256) of the submitted document for integrity verification
>
> Logs are stored in a tamper-evident format and retained for 7 years in compliance with VA records requirements. Logs do not contain the document contents or any veteran PII.

### 2.6 Veterans Health API (FHIR) — Specific Requirements

#### 2.6.1 Medical Advice Disclaimers — Screenshot Required

- [ ] **Screenshot showing medical disclaimer in the app.** The app must display language similar to:

> *"This application provides general health information and claims guidance only. It does not provide medical advice, diagnosis, or treatment. Always consult with a qualified healthcare provider for medical decisions. If you are experiencing a medical emergency, call 911 or go to your nearest emergency room. For the Veterans Crisis Line, call 988 then press 1."*

> **Action needed:** Ensure this disclaimer is visible on the ChatPage and EvaluatePage. Take screenshots of both.

#### 2.6.2 MyHealthApplication.com Listing

- [ ] **Register and publish Valor Assist on MyHealthApplication.com**
  - URL: https://myhealthapplication.com/list-your-app
  - This is free to register
  - VA will check this listing before your demo

#### 2.6.3 CARIN Alliance Code of Conduct

- [ ] **Attest to the CARIN Alliance Code of Conduct**
  - URL: https://www.carinalliance.com/our-work/trust-framework-and-code-of-conduct/
  - Registration is free
  - VA will check if your app is listed on the CARIN website

---

## Section 3: Privacy Policy and Terms of Service

### 3.1 URLs Required

- [ ] **Terms of Service URL:** [YOUR URL, e.g., https://valorassist.com/terms]
- [ ] **Privacy Policy URL:** [YOUR URL, e.g., https://valorassist.com/privacy]

> **Critical:** Since the app uses Authorization Code Grant (ACG/OAuth), VA will review both documents for quality, plain language, and content before scheduling the demo. They may require changes.

### 3.2 Desktop Readability Requirements

Both documents must meet:

- [ ] Grade reading level of 12 or below
- [ ] No obvious typos
- [ ] Font size 14px or larger
- [ ] No long, unbroken paragraphs
- [ ] No ALL-CAPS paragraphs (a sentence or two is OK)
- [ ] No run-on sentences
- [ ] No narrow column widths
- [ ] Text and background colors meet WCAG contrast ratio of at least 4.5:1

### 3.3 Mobile Readability Requirements

Both documents must meet:

- [ ] Font size 14px or larger
- [ ] No long, unbroken paragraphs
- [ ] No ALL-CAPS paragraphs (a sentence or two is OK)
- [ ] No run-on sentences
- [ ] No narrow column widths

### 3.4 Data Retention and Deletion (must be in Terms/Privacy Policy)

- [ ] Specify data retention policy, including how long you hold user data (including non-VA data) if the account is dormant
- [ ] Give users an easy way to request permanent data deletion, with instructions on how to do this
- [ ] State the company will permanently delete 100% of a user's data, including non-VA data, at the user's request
- [ ] State how soon data deletion will happen after request (VA requires within 45 days)

### 3.5 Privacy and Data Practices (must be in Terms/Privacy Policy)

- [ ] Define the specific types of data collected (geolocation, financial, medical, contacts, personal info)
- [ ] Clearly describe how data will be used, including sharing of de-identified, anonymized, or pseudonymized data
- [ ] State whether data is shared with third parties such as marketers and partners
- [ ] Name the entities with which data is shared, including third parties, and indicate how they use it
- [ ] State that no user data is sold for profit or other monetary transactions
- [ ] Clearly indicate if data is used for transactions that could involve money (e.g., targeted advertising)
- [ ] Address how data sharing could impact others (e.g., genetic or family history)
- [ ] Clearly state that third-party use or disclosure of user information (including de-identified/anonymized/pseudonymized) is prohibited without user consent
- [ ] Indicate that third-party vendors and contractors are bound to the same data commitments as the company
- [ ] Specify that in a data breach, the company will notify users and provide instructions for protective actions
- [ ] Specify what happens to user data if the company transfers ownership or ceases operations. Must include at least one of:
  - [ ] Users can securely dispose of, transmit, or download their health information
  - [ ] New owner's policies are consistent with original policies
  - [ ] Users can close their account
- [ ] Indicate the company will notify users of changes in ownership
- [ ] Clearly state the company will notify users of changes to the privacy policy and terms of service

---

## Section 4: Pre-Application Action Items

These must be completed BEFORE you fill out the form:

### Must-Do Before Form Submission

| # | Action | Status | Notes |
|---|--------|--------|-------|
| 1 | Register on MyHealthApplication.com | [ ] | Free; required for FHIR API |
| 2 | Attest to CARIN Alliance Code of Conduct | [ ] | Free; required for FHIR API |
| 3 | Deploy Terms of Service to a public URL | [ ] | Must meet all formatting requirements |
| 4 | Deploy Privacy Policy to a public URL | [ ] | Must meet all formatting requirements |
| 5 | Build medical disclaimer into app UI | [ ] | Screenshot required |
| 6 | Build PatientWaitTime disclaimer into Facilities feature | [ ] | Screenshot required if using Facilities API |
| 7 | Take screenshots of disclaimers | [ ] | Desktop + mobile views |
| 8 | Ensure Section 508 compliance | [ ] | https://section508.va.gov/ |
| 9 | Ensure WCAG 2.1 AA compliance (4.5:1 contrast) | [ ] | Test with axe DevTools or WAVE |
| 10 | Prepare sandbox demo | [ ] | VA may schedule a demo call |
| 11 | Set up notification email alias | [ ] | For API status updates |

### Nice-to-Have Before Submission

| # | Action | Notes |
|---|--------|-------|
| 12 | Annual pentest report (or plan for one) | Strengthens security answers |
| 13 | Dependabot / pip-audit CI pipeline | Shows active vuln management |
| 14 | Documented incident response plan | Reference in breach response answer |
| 15 | Data retention schedule document | Reference in policy answers |

---

## Section 5: Post-Submission Process

Per the PDF:

> "We use the data you submit to determine whether to schedule a demo or request technical or policy-related changes. If we need changes, we'll send you an email."

**Expected flow:**
1. Submit the production access form (cannot be saved — do it in one sitting)
2. VA reviews your submission
3. VA either:
   - **Schedules a demo** — be prepared to walk through your app live, showing OAuth flow, data handling, disclaimers, and security measures
   - **Requests changes** — typically to privacy policy language, security procedures, or UI disclaimers
4. After successful demo, VA grants production API credentials
5. Timeline varies (the PDF explicitly says "Timeline for getting production access varies")

---

## Key Constraints to Remember

- **All consumers must be US-based**
- **No monetizing or selling veteran data** — ever
- **Rate limit: 60 requests per minute** (our app is set to 30 client-side, well within)
- **Section 508 compliance encouraged** for all apps
- **Form cannot be saved** — prepare everything before you start
