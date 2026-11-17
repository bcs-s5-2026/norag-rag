# V4 live answers — human review (reviewed by Feras M, 12 November 2026)

Source run: `evaluation/results/v4/live_final_2026-11-12.json` (8 questions, Gemini `gemini-3.5-flash-lite`, Kestrel corpus, dense + BM25 + graph, top-k 5).

Reviewer: Feras M  Date: 2026-11-12

Grades (same rules as V2): **correct** / **partial** / **wrong** / **unsupported** (says something the cited passages do not support).
The grades and notes below were given by Feras M and are recorded verbatim; the same values are in `live_final_2026-11-12-REVIEW.csv`. Questions, answers and passages are unchanged.

## 1. two_hop

**Question (exact):** Error KST-5031 happened on the last two scheduled reports. Which team should support contact, and where?

**Question as sent to the LLM and stored in the trace:** Error KST-5031 happened on the last two scheduled reports. Which team should support contact, and where?

**Outcome recorded in the trace:** answered · 3407 in / 289 out tokens · $0.001745 · redacted: {'emails': 1, 'phones': 0}

**Generated answer:**

> If error KST-5031 happens on two consecutive deliveries, it should be escalated as a SEV-2 to the team that owns postroom, which is the Messaging team (their on-call channel is #oncall-messaging).

**Expected answer (course question q08): Messaging, which owns postroom: post in #oncall-messaging as SEV-2. Outside 08:00–20:00 on weekdays, escalate to the Platform on-call.**

<details><summary>Cited passage: support-runbook-errors.md, characters 5760–6560</summary>

```
(KST-5xxx)

### KST-5031 — Scheduled report not delivered

**User sees:** the schedule shows "Last delivery failed".
**Cause:** the report was generated but the e-mail was not sent. This error is raised by postroom, the service that sends all Kestrel e-mails. A single occurrence is usually a temporary problem with a recipient's mail server.
**Support action:** check whether the recipient's address is correct and whether the next delivery succeeds. Ask the customer to check that messages from kestrel.example are not blocked by their mail filter.
**Escalate:** if the error happens on two consecutive deliveries, or for several customers on the same day, escalate to the team that owns postroom, as SEV-2.

### KST-5038 — Embed token expired

**User sees:** an embedded dashboard shows "This link
```

</details>

<details><summary>Cited passage: service-catalog.md, characters 1440–2240</summary>

```
ngine**.

### postroom

Sends every e-mail that leaves Kestrel: scheduled reports, invitations, password resets, ownership transfer confirmations and billing notifications. Tracks bounces and removes a recipient from a schedule after three rejections.
Owner: **Messaging**.

postroom replaced the older mailman service in November 2025. mailman is switched off; old alerts or documents that mention it refer to postroom today.

### embed-svc

Issues and checks embed tokens for dashboards embedded in customer applications.
Owner: **Platform**.

### ledger

Subscriptions, seats, invoices and payments. Generates invoice PDFs, runs the automatic payment retries, and applies the grace period and read-only rules of the Billing and Refund Policy. Talks to the payment processor; never stores full card
```

</details>

<details><summary>Cited passage: service-catalog.md, characters 2160–2960</summary>

```
illing and Refund Policy. Talks to the payment processor; never stores full card numbers.
Owner: **Payments Core**.

### audit-log

Records security-relevant events (sign-ins, role changes, connector edits, exports) for workspaces on Business and Enterprise plans.
Owner: **Identity**.

## 2. Teams

| Team | Engineering lead | On-call channel | Working hours (Paris time) |
|---|---|---|---|
| Platform | Samuel Okafor | #oncall-platform | 24/7 rotation |
| Identity | Priya Raman | #oncall-identity | 24/7 rotation |
| Data Integrations | Tomasz Wójcik | #oncall-data-integrations | 08:00–20:00, weekdays |
| Analytics Engine | Léa Fontaine | #oncall-analytics | 24/7 rotation |
| Messaging | Inès Moreau | #oncall-messaging | 08:00–20:00, weekdays |
| Payments Core | Jonas Berg | #oncall-payments
```

</details>

**Grade (Feras M):** partial

**Notes (Feras M):** Missing after-hours escalation to Platform.

---

## 2. corpus_email

**Question (exact):** How do I request a refund, and where do I send the request?

**Question as sent to the LLM and stored in the trace:** How do I request a refund, and where do I send the request?

**Outcome recorded in the trace:** answered · 3449 in / 136 out tokens · $0.001375 · redacted: {'emails': 1, 'phones': 0}

**Generated answer:**

> Refund requests must be sent by the workspace Owner, either from Settings → Plan → Request a refund or by e-mail to billing@kestrel.example.

**No expected answer in the question sets: judge against the cited passages.**

<details><summary>Cited passage: billing-policy-2026.md, characters 2880–3680</summary>

```
ed full months of the annual period. After 60 days, annual plans are not refundable.

Refund requests must be sent by the workspace Owner, either from **Settings → Plan → Request a refund** or by e-mail to billing@kestrel.example. Approved refunds are processed within 14 days and returned to the original payment method.

Charges caused by a billing error on our side (for example a duplicate charge) are always refunded in full, whatever the plan and whatever the date.

## 7. Failed payments

When a payment fails, the workspace Owner and the billing contact receive an e-mail straight away. We then retry the payment automatically 1 day, 3 days and 7 days after the first attempt.

Each retry uses the payment method on file at the time of the retry, so updating the card before the next retry is
```

</details>

**Grade (Feras M):** correct

**Notes (Feras M):** Both request methods are supported.

---

## 3. plain

**Question (exact):** Can I get a refund on my annual plan 45 days after it renewed?

**Question as sent to the LLM and stored in the trace:** Can I get a refund on my annual plan 45 days after it renewed?

**Outcome recorded in the trace:** answered · 3441 in / 330 out tokens · $0.001857 · redacted: {'emails': 1, 'phones': 0}

**Generated answer:**

> Whether you can get a refund depends on which policy applies to you. Under the 2025 policy, annual plans can only be refunded if the request is made within 30 days of the purchase or renewal date. Under the 2026 policy (effective March 1, 2026), annual plans can be refunded if the request is made within 60 days of the purchase or renewal date, pro-rated for the unused full months.

**Expected answer (course question q06): Yes, under the current (March 2026) policy: annual plans are refundable within 60 days of renewal, pro-rated from the request date. The old 2025 policy allowed only 30 days.**

<details><summary>Cited passage: billing-policy-2025.md, characters 2160–2960</summary>

```
 takes effect at the next renewal. No credit is given for removed seats during the current period.

## 6. Refunds

**Monthly plans** are not refundable. When a monthly plan is cancelled, it remains active until the end of the month already paid.

**Annual plans** can be refunded in full if the request is made within 30 days of the purchase or renewal date. After 30 days, annual plans are not refundable.

Refund requests must be sent by the workspace Owner to billing@kestrel.example. Approved refunds are processed within 10 business days and returned to the original payment method.

Charges caused by a billing error on our side (for example a duplicate charge) are always refunded in full, whatever the plan and whatever the date.

## 7. Failed payments

If a payment fails, we retry the card 
```

</details>

<details><summary>Cited passage: billing-policy-2026.md, characters 2160–2960</summary>

```
hs of its date.

## 5. Adding and removing seats

Seats can be added at any time. Added seats are charged immediately, pro-rated to the end of the current billing period.

Seats can be removed at any time. On monthly plans the reduction takes effect at the next monthly charge. On annual plans the reduction takes effect at the next renewal, and no credit is given for the current period.

## 6. Refunds

**Monthly plans** are not refundable. When a monthly plan is cancelled, it remains active until the end of the month already paid.

**Annual plans** can be refunded if the request is made within 60 days of the purchase or renewal date. The refund is pro-rated from the date of the request: you are refunded the unused full months of the annual period. After 60 days, annual plans are not refunda
```

</details>

<details><summary>Cited passage: billing-policy-2026.md, characters 2880–3680</summary>

```
ed full months of the annual period. After 60 days, annual plans are not refundable.

Refund requests must be sent by the workspace Owner, either from **Settings → Plan → Request a refund** or by e-mail to billing@kestrel.example. Approved refunds are processed within 14 days and returned to the original payment method.

Charges caused by a billing error on our side (for example a duplicate charge) are always refunded in full, whatever the plan and whatever the date.

## 7. Failed payments

When a payment fails, the workspace Owner and the billing contact receive an e-mail straight away. We then retry the payment automatically 1 day, 3 days and 7 days after the first attempt.

Each retry uses the payment method on file at the time of the retry, so updating the card before the next retry is
```

</details>

**Grade (Feras M):** correct

**Notes (Feras M):** Correct 2025 and 2026 policy comparison.

---

## 4. same_with_personal_data

**Question (exact):** My name is Sam Martin, my email is sam.martin@example.org and my phone is +33 6 12 34 56 78. Can I get a refund on my annual plan 45 days after it renewed?

**Question as sent to the LLM and stored in the trace:** My name is Sam Martin, my email is [EMAIL_1] and my phone is [PHONE_1]. Can I get a refund on my annual plan 45 days after it renewed?

**Outcome recorded in the trace:** answered · 3464 in / 275 out tokens · $0.001727 · redacted: {'emails': 2, 'phones': 1}

**Generated answer:**

> Whether you can get a refund depends on the effective date of your plan's policy. Under the 2025 billing policy, annual plans can only be refunded if requested within 30 days of the purchase or renewal date, meaning a request after 45 days would not be refundable. However, under the 2026 billing policy (effective 1 March 2026), annual plans can be refunded on a pro-rated basis if the request is made within 60 days of the purchase or renewal date.

**Expected answer (course question q06): Yes, under the current (March 2026) policy: annual plans are refundable within 60 days of renewal, pro-rated from the request date. The old 2025 policy allowed only 30 days.**

<details><summary>Cited passage: billing-policy-2025.md, characters 2160–2960</summary>

```
 takes effect at the next renewal. No credit is given for removed seats during the current period.

## 6. Refunds

**Monthly plans** are not refundable. When a monthly plan is cancelled, it remains active until the end of the month already paid.

**Annual plans** can be refunded in full if the request is made within 30 days of the purchase or renewal date. After 30 days, annual plans are not refundable.

Refund requests must be sent by the workspace Owner to billing@kestrel.example. Approved refunds are processed within 10 business days and returned to the original payment method.

Charges caused by a billing error on our side (for example a duplicate charge) are always refunded in full, whatever the plan and whatever the date.

## 7. Failed payments

If a payment fails, we retry the card 
```

</details>

<details><summary>Cited passage: billing-policy-2026.md, characters 2160–2960</summary>

```
hs of its date.

## 5. Adding and removing seats

Seats can be added at any time. Added seats are charged immediately, pro-rated to the end of the current billing period.

Seats can be removed at any time. On monthly plans the reduction takes effect at the next monthly charge. On annual plans the reduction takes effect at the next renewal, and no credit is given for the current period.

## 6. Refunds

**Monthly plans** are not refundable. When a monthly plan is cancelled, it remains active until the end of the month already paid.

**Annual plans** can be refunded if the request is made within 60 days of the purchase or renewal date. The refund is pro-rated from the date of the request: you are refunded the unused full months of the annual period. After 60 days, annual plans are not refunda
```

</details>

**Grade (Feras M):** correct

**Notes (Feras M):** Correct refund rule; email and phone were redacted.

---

## 5. not_in_corpus

**Question (exact):** Is there a Kestrel mobile app for iPhone?

**Question as sent to the LLM and stored in the trace:** Is there a Kestrel mobile app for iPhone?

**Outcome recorded in the trace:** abstained · 3205 in / 32 out tokens · $0.001042 · redacted: {'emails': 0, 'phones': 0}

**Generated answer:**

> The selected documents do not provide enough evidence.

**Expected answer (course question q09): Not in the documents.**

Cited passages: none (abstention).

**Grade (Feras M):** correct

**Notes (Feras M):** Correctly says the documents do not provide the answer.

---

## 6. from_concept_service

**Question (exact):** What do the documents say about ledger?

**Question as sent to the LLM and stored in the trace:** What do the documents say about ledger?

**Outcome recorded in the trace:** answered · 2981 in / 224 out tokens · $0.001454 · redacted: {'emails': 0, 'phones': 0}

**Generated answer:**

> Ledger handles subscriptions, seats, invoices, and payments, generates invoice PDFs, runs automatic payment retries, and applies the grace period and read-only rules of the Billing and Refund Policy. It communicates with the payment processor and never stores full card numbers. Its owner is Payments Core.

**No expected answer in the question sets: judge against the cited passages.**

<details><summary>Cited passage: service-catalog.md, characters 1440–2240</summary>

```
ngine**.

### postroom

Sends every e-mail that leaves Kestrel: scheduled reports, invitations, password resets, ownership transfer confirmations and billing notifications. Tracks bounces and removes a recipient from a schedule after three rejections.
Owner: **Messaging**.

postroom replaced the older mailman service in November 2025. mailman is switched off; old alerts or documents that mention it refer to postroom today.

### embed-svc

Issues and checks embed tokens for dashboards embedded in customer applications.
Owner: **Platform**.

### ledger

Subscriptions, seats, invoices and payments. Generates invoice PDFs, runs the automatic payment retries, and applies the grace period and read-only rules of the Billing and Refund Policy. Talks to the payment processor; never stores full card
```

</details>

<details><summary>Cited passage: service-catalog.md, characters 2160–2960</summary>

```
illing and Refund Policy. Talks to the payment processor; never stores full card numbers.
Owner: **Payments Core**.

### audit-log

Records security-relevant events (sign-ins, role changes, connector edits, exports) for workspaces on Business and Enterprise plans.
Owner: **Identity**.

## 2. Teams

| Team | Engineering lead | On-call channel | Working hours (Paris time) |
|---|---|---|---|
| Platform | Samuel Okafor | #oncall-platform | 24/7 rotation |
| Identity | Priya Raman | #oncall-identity | 24/7 rotation |
| Data Integrations | Tomasz Wójcik | #oncall-data-integrations | 08:00–20:00, weekdays |
| Analytics Engine | Léa Fontaine | #oncall-analytics | 24/7 rotation |
| Messaging | Inès Moreau | #oncall-messaging | 08:00–20:00, weekdays |
| Payments Core | Jonas Berg | #oncall-payments
```

</details>

**Grade (Feras M):** correct

**Notes (Feras M):** Service functions and owner match.

---

## 7. from_concept_hub

**Question (exact):** What do the documents say about Enterprise?

**Question as sent to the LLM and stored in the trace:** What do the documents say about Enterprise?

**Outcome recorded in the trace:** answered · 8055 in / 478 out tokens · $0.003612 · redacted: {'emails': 0, 'phones': 0}

**Generated answer:**

> According to the documents, the Enterprise plan offers custom seats, unlimited dashboards, unlimited data connectors, the fastest data refresh of every minute, custom history retention, single sign-on (SAML), SCIM user provisioning, a 1-year audit log, public share links, and the ability to pay by bank transfer against an invoice. Workspaces on Business and Enterprise plans can use single sign-on with any SAML 2.0 identity provider, and they also have security-relevant events recorded by the audit-log service.

**No expected answer in the question sets: judge against the cited passages.**

<details><summary>Cited passage: product-guide.md, characters 720–1520</summary>

```
one workspace cannot see the content of another workspace, even inside the same organisation.

## 2. Plans and limits

Each workspace is on exactly one plan. The plan sets the number of seats, how often data refreshes, and which administration features are available.

| | Free | Starter | Team | Business | Enterprise |
|---|---|---|---|---|---|
| Seats included | 2 | 5 | 20 | 100 | Custom |
| Dashboards | 3 | 25 | Unlimited | Unlimited | Unlimited |
| Data connectors | 1 | 3 | 10 | Unlimited | Unlimited |
| Fastest refresh | Daily | Hourly | Every 15 minutes | Every 5 minutes | Every minute |
| History kept | 30 days | 1 year | 2 years | 5 years | Custom |
| Single sign-on (SAML) | — | — | — | Yes | Yes |
| SCIM user provisioning | — | — | — | — | Yes |
| Audit log | — | — | — | 90 days | 
```

</details>

<details><summary>Cited passage: product-guide.md, characters 1440–2240</summary>

```
M user provisioning | — | — | — | — | Yes |
| Audit log | — | — | — | 90 days | 1 year |
| Public share links | — | Yes | Yes | Yes | Yes |

Plans can be changed at any time from **Settings → Plan**. An upgrade takes effect immediately. A downgrade takes effect at the end of the current billing period; if the workspace uses more than the lower plan allows (for example more dashboards than the limit), the extra items become read-only until you remove them.

## 3. Workspace roles

Every member has one role in the workspace:

- **Owner**: exactly one per workspace. The Owner can do everything an Admin can, and is the only person who can change the plan, delete the workspace or transfer ownership.
- **Admin**: manages members, connectors and security settings.
- **Editor**: creates and edits d
```

</details>

<details><summary>Cited passage: product-guide.md, characters 3600–4400</summary>

```
ows 10 backup codes. Each backup code works once. Store them somewhere safe and separate from your authenticator device.

Admins can make two-factor authentication mandatory for every member from **Settings → Security**. Members who have not set it up are asked to do so at their next sign-in.

### 5.2 Single sign-on

On the Business and Enterprise plans, workspaces can use single sign-on with any SAML 2.0 identity provider. To set it up, an Admin opens **Settings → Security → Single sign-on**, downloads the Kestrel service provider metadata, registers Kestrel in the identity provider, and pastes the identity provider metadata URL back into Kestrel. We recommend testing with one Admin account before choosing **Enforce for all members**. When single sign-on is enforced, passwords are disable
```

</details>

<details><summary>Cited passage: billing-policy-2026.md, characters 720–1520</summary>

```
id plans are billed per seat, either monthly or annually. Monthly plans are charged on the same day each month as the original purchase. Annual plans are charged once a year, on the anniversary of the purchase.

Customers who choose annual billing receive a 20% discount compared with twelve months of monthly billing. Switching from monthly to annual billing is possible at any time and takes effect immediately; the unused part of the current month is credited. Switching from annual to monthly billing takes effect at the next renewal.

## 3. Payment methods

We accept credit and debit cards (Visa, Mastercard, American Express) and SEPA direct debit for customers in the euro area. Team, Business and Enterprise customers can also pay by bank transfer against an invoice, with payment due within
```

</details>

<details><summary>Cited passage: service-catalog.md, characters 2160–2960</summary>

```
illing and Refund Policy. Talks to the payment processor; never stores full card numbers.
Owner: **Payments Core**.

### audit-log

Records security-relevant events (sign-ins, role changes, connector edits, exports) for workspaces on Business and Enterprise plans.
Owner: **Identity**.

## 2. Teams

| Team | Engineering lead | On-call channel | Working hours (Paris time) |
|---|---|---|---|
| Platform | Samuel Okafor | #oncall-platform | 24/7 rotation |
| Identity | Priya Raman | #oncall-identity | 24/7 rotation |
| Data Integrations | Tomasz Wójcik | #oncall-data-integrations | 08:00–20:00, weekdays |
| Analytics Engine | Léa Fontaine | #oncall-analytics | 24/7 rotation |
| Messaging | Inès Moreau | #oncall-messaging | 08:00–20:00, weekdays |
| Payments Core | Jonas Berg | #oncall-payments
```

</details>

**Grade (Feras M):** correct

**Notes (Feras M):** Plan features match the source passages.

---

## 8. from_concept_channel

**Question (exact):** What do the documents say about #oncall-payments?

**Question as sent to the LLM and stored in the trace:** What do the documents say about #oncall-payments?

**Outcome recorded in the trace:** answered · 3459 in / 198 out tokens · $0.001533 · redacted: {'emails': 0, 'phones': 0}

**Generated answer:**

> The documents state that #oncall-payments is the on-call channel for the Payments Core team, which operates on a 24/7 rotation.

**No expected answer in the question sets: judge against the cited passages.**

<details><summary>Cited passage: service-catalog.md, characters 2160–2960</summary>

```
illing and Refund Policy. Talks to the payment processor; never stores full card numbers.
Owner: **Payments Core**.

### audit-log

Records security-relevant events (sign-ins, role changes, connector edits, exports) for workspaces on Business and Enterprise plans.
Owner: **Identity**.

## 2. Teams

| Team | Engineering lead | On-call channel | Working hours (Paris time) |
|---|---|---|---|
| Platform | Samuel Okafor | #oncall-platform | 24/7 rotation |
| Identity | Priya Raman | #oncall-identity | 24/7 rotation |
| Data Integrations | Tomasz Wójcik | #oncall-data-integrations | 08:00–20:00, weekdays |
| Analytics Engine | Léa Fontaine | #oncall-analytics | 24/7 rotation |
| Messaging | Inès Moreau | #oncall-messaging | 08:00–20:00, weekdays |
| Payments Core | Jonas Berg | #oncall-payments
```

</details>

<details><summary>Cited passage: service-catalog.md, characters 2880–3680</summary>

```
saging | 08:00–20:00, weekdays |
| Payments Core | Jonas Berg | #oncall-payments | 24/7 rotation |

Teams with weekday hours are covered outside those hours by the Platform on-call, who can page the team lead for SEV-1 incidents only.

## 3. Escalation rules

1. Support identifies the service involved, using the error code and the Support Runbook.
2. Support posts in the on-call channel of the team that owns that service, with the workspace name, the error code, the time, and the severity level.
3. For SEV-1, support also pages the on-call engineer through the paging tool; posting in the channel is not enough.
4. If the owning team is outside its working hours, escalate to the Platform on-call.
5. The owning team acknowledges in the thread and becomes responsible for the follow-up with sup
```

</details>

**Grade (Feras M):** correct

**Notes (Feras M):** Correct Payments Core channel and rotation.

---
