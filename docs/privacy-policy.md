# Privacy Policy

**Valor Assist — AI Veterans Claims Assistant**

**Effective Date:** [DATE]
**Last Updated:** [DATE]

---

## Who We Are

Valor Assist ("[COMPANY NAME]," "we," "us," or "our") provides an AI-powered platform that helps U.S. military veterans understand and navigate VA disability claims, appeals, and benefits. This Privacy Policy explains what data we collect, how we use it, who we share it with, and how we protect it.

---

## What Data We Collect

We collect the following categories of information:

**Account information** you provide when you register:

- Email address
- First and last name
- Password (stored only as a cryptographic hash, never in plain text)

**Identity verification data** received from ID.me when you verify your identity:

- Verified name
- Verified veteran status
- Level of assurance (identity proofing level)
- ID.me unique identifier

**VA health and benefits data** accessed through VA.gov Lighthouse APIs when you explicitly authorize access:

- Disability rating (combined and individual ratings)
- Service history (branch, service dates, discharge characterization)
- Active and historical claims (claim type, status, decision dates)
- Medical conditions (diagnosis codes, clinical status, onset dates)
- Active medications (medication name, status, date prescribed)

**Usage data** collected automatically:

- IP address (used only for rate limiting, not stored long-term)
- Browser type and version
- Pages visited within the application
- Timestamps of actions taken

**Data we do NOT collect:**

- We do not collect geolocation data
- We do not collect financial information, banking details, or payment card numbers
- We do not collect contacts or address book data
- We do not collect biometric data
- We do not collect data from your device sensors, camera, or microphone

---

## How We Use Your Data

We use your data for the following purposes only:

- **Providing claims guidance:** Your VA data is used during your active session to generate personalized, regulation-cited guidance about your disability claims, appeals, and benefits eligibility.
- **Identity verification:** Your ID.me verification data confirms your veteran status so we can provide veteran-specific services.
- **Account management:** Your email and name are used to maintain your account and communicate service updates.
- **Security:** Your IP address is used for rate limiting and fraud prevention during your session.
- **Service improvement:** Anonymized, aggregated usage statistics (such as total number of sessions or most-asked question categories) may be used to improve the platform. These statistics contain no personally identifiable information.

We do NOT use your data for:

- Advertising or targeted marketing
- Data brokerage or sale to any party
- Training AI models on your personal information
- Profiling or automated decision-making that produces legal effects
- Any purpose you have not explicitly authorized

---

## How VA Data Is Handled

When you connect your VA.gov account, your VA health and benefits data receives the highest level of protection:

- **Accessed only with your explicit consent.** You must complete an OAuth2 authorization flow on VA.gov and affirmatively consent to each category of data access before any VA data is retrieved.
- **Encrypted immediately.** All VA data is encrypted using Fernet symmetric encryption (AES-128-CBC with HMAC-SHA256 verification) at the individual field level the moment it is received.
- **Held in memory only.** VA data is never written to disk, saved to a database, or persisted in any permanent storage. It exists only in encrypted in-memory session state.
- **Destroyed after your session.** When your session ends (after 60 minutes of inactivity or when you log out), all VA data is permanently destroyed.
- **Audit-logged.** Every access to your VA data is recorded in a tamper-evident audit log. The log records what was accessed and when, but does not contain the data values themselves.

---

## Who We Share Data With

**We do not sell your data.** No user data is sold for profit or any other monetary transaction. Period.

**We do not share your data with marketers, advertisers, or data brokers.** Your information is never provided to any entity for marketing, advertising, or commercial profiling purposes.

**Third parties who may process data on our behalf:**

| Entity | Purpose | Data Accessed |
|--------|---------|--------------|
| **Anthropic** (Claude AI) | AI-powered claims analysis | Only the text of your questions and anonymized context from your session are sent to generate responses. No PII or VA data is stored by Anthropic after the response is generated. |
| **Amazon Web Services (AWS)** | Cloud infrastructure hosting | Encrypted data transits through and is temporarily held in AWS infrastructure. AWS does not access or use this data. |
| **ID.me** | Identity and veteran status verification | ID.me provides verified identity attributes to us. We do not send your data back to ID.me. |

All third-party vendors and contractors listed above are contractually bound to the same commitments we make to you regarding use and disclosure of your data. They may not use your data for any purpose other than providing the specific service described above.

**Third-party use or disclosure of your information — including de-identified, anonymized, or pseudonymized data — is prohibited for any reason without your explicit consent.**

Data is not used for any transactions that involve money, such as targeted advertising, and is not sold or exchanged for monetary value under any circumstances.

---

## Impact of Data Sharing on Others

We are mindful that information associated with your account could affect others. For example, service history or medical records may reference family members, dependents, or next of kin. We treat all such information with the same protections described in this policy. We do not extract, index, or separately store information about third parties found in your records.

---

## Data Retention and Deletion

**Active session data (VA health and benefits information):**
Destroyed immediately when your session ends. Not retained.

**Account data (email, name, verification status):**
Retained as long as your account is active. If your account is dormant (no login for 12 months), we will send you a notice and delete your account data within 30 days unless you log in.

**Audit logs:**
Retained for 7 years for compliance and security purposes. Audit logs do not contain your personal data values — only metadata about what actions were performed.

**Requesting deletion of your data:**
You may request permanent deletion of all your data at any time by:

1. Logging into your account and selecting "Delete My Account" in your profile settings, or
2. Sending an email to [PRIVACY EMAIL ADDRESS] with the subject line "Data Deletion Request"

Upon receiving your request, we will permanently delete 100% of your data, including all account information, session records, and any non-VA data associated with your account. Deletion will be completed within 45 days of your request. You will receive a confirmation email when deletion is complete.

---

## Data Breach Notification

If a data breach occurs that affects your information, we will:

1. Notify you by email within 72 hours of confirming the breach
2. Clearly describe what data was affected
3. Explain what steps we are taking to address the breach
4. Provide instructions for any actions you may take to protect yourself, such as monitoring your VA accounts or changing passwords
5. Notify the VA Lighthouse API team and applicable regulatory authorities

---

## If Our Company Changes Ownership or Ceases Operations

If Valor Assist undergoes a transfer of ownership, merger, acquisition, or ceases business operations:

- We will notify you by email at least 30 days before any transfer of your data to a new owner.
- You will have the option to:
  - Download or transmit your data before the transfer
  - Request secure deletion of all your data
  - Close your account entirely
- Any new owner will be required to honor the commitments in this Privacy Policy. If the new owner's privacy practices are materially different, you will be given the choice to consent or delete your data before the new practices take effect.

---

## Changes to This Privacy Policy

We will notify you by email and through a prominent notice in the application whenever we make changes to this Privacy Policy or our Terms of Service. Changes will not take effect until at least 14 days after notification, giving you time to review them.

---

## Your Rights

You have the right to:

- **Access** your data — view what information we hold about you
- **Correct** your data — update inaccurate account information
- **Delete** your data — request permanent deletion as described above
- **Revoke VA access** — disconnect your VA.gov authorization at any time through your profile settings or directly through VA.gov
- **Withdraw consent** — revoke any consent you have provided at any time

---

## Contact Us

If you have questions about this Privacy Policy or how your data is handled:

- **Email:** [PRIVACY EMAIL ADDRESS]
- **Mail:** [COMPANY MAILING ADDRESS]

If you believe your privacy rights have been violated, you may also file a complaint with the VA at https://www.va.gov/privacy/ or contact the VA's Privacy Service at the address listed on that page.
