# Kestrel: ten triples for manual grading

> **Superseded (8 Nov 2026, afternoon).** This file describes the first, partial v1 graph (gemini-3.5-flash-lite, 10 relations). The submitted V3 results, rebuilt graph (`concepts/kestrel_graph_v2/`) and the extraction-quality review (`evaluation/graph_review/kestrel-v2-10-triples.json`) are in REPORT.md, section "V3 final". The v1 grades below were AI-drafted reasons confirmed in chat, not an independent review.


Frozen graph `529ee6bf820a7554a5d0352d10d92e39d6df992e0ae81f99c9a584c34e797794`; seed 20261108; sample 10 of 10 distinct relations.

Human review complete: **10 correct / 0 wrong / 0 unsupported**. Reviewer: Feras M. Original ungraded JSON is preserved beside this file.
Context-expanded evidence is explicitly labelled; the original model quote is preserved. Read the whole source passage.

## 1. Payments Core → CONTACT_CHANNEL → #oncall-payments

Relation ID: `r_b6f24b97cf0a0f77fcc6a6afb1146589c41a33b9c1220b75776aa086f79b5205`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: Payments Core is associated with #oncall-payments in the service catalog.

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:2880:3680`; starting line 64.
Extraction model: `gemini-3.5-flash-lite`.

Supporting quotation:

````text
| Payments Core | Jonas Berg | #oncall-payments | 24/7 rotation |
````

Exact full source chunk:

````text
saging | 08:00–20:00, weekdays |
| Payments Core | Jonas Berg | #oncall-payments | 24/7 rotation |

Teams with weekday hours are covered outside those hours by the Platform on-call, who can page the team lead for SEV-1 incidents only.

## 3. Escalation rules

1. Support identifies the service involved, using the error code and the Support Runbook.
2. Support posts in the on-call channel of the team that owns that service, with the workspace name, the error code, the time, and the severity level.
3. For SEV-1, support also pages the on-call engineer through the paging tool; posting in the channel is not enough.
4. If the owning team is outside its working hours, escalate to the Platform on-call.
5. The owning team acknowledges in the thread and becomes responsible for the follow-up with sup
````

## 2. query-engine → OWNED_BY → Analytics Engine

Relation ID: `r_c90e3b89c497da363d65beb031fdd915bb8c895d5715094d41dad4a77c51ac8c`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: query-engine is owned by Analytics Engine.

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:720:1520`; starting line 16.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### query-engine

Runs dataset queries, enforces the 120-second query time limit, and caches results for dashboards.
Owner: **Analytics Engine**.
````

Exact full source chunk:

````text
e sign-on (SAML) and SCIM provisioning. Issues the session tokens used by every other service.
Owner: **Identity**.

### connector-hub

Stores connector credentials (encrypted with per-workspace keys) and opens the connections to customer data sources. All outgoing connections leave through two fixed addresses, 203.0.113.10 and 203.0.113.11.
Owner: **Data Integrations**.

### query-engine

Runs dataset queries, enforces the 120-second query time limit, and caches results for dashboards.
Owner: **Analytics Engine**.

### scheduler

Triggers dataset refreshes and scheduled reports at the right time, in the time zone of each schedule. Generates the report PDFs and hands them over for delivery.
Owner: **Analytics Engine**.

### postroom

Sends every e-mail that leaves Kestrel: scheduled report
````

## 3. embed-svc → OWNED_BY → Platform

Relation ID: `r_7ca92947065c0de5ec6265daa6da936e4ab3d5a1c1e17372708aa1d5721c69b9`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: embed-svc is owned by Platform.

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:1440:2240`; starting line 32.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### embed-svc

Issues and checks embed tokens for dashboards embedded in customer applications.
Owner: **Platform**.
````

Exact full source chunk:

````text
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
````

## 4. connector-hub → OWNED_BY → Data Integrations

Relation ID: `r_6fb425c8a336bd02862ef9c1b69316322b8ce8f59eaca00193ff2eecd81b2e28`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: connector-hub is owned by Data Integrations.

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:720:1520`; starting line 16.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### connector-hub

Stores connector credentials (encrypted with per-workspace keys) and opens the connections to customer data sources. All outgoing connections leave through two fixed addresses, 203.0.113.10 and 203.0.113.11.
Owner: **Data Integrations**.
````

Exact full source chunk:

````text
e sign-on (SAML) and SCIM provisioning. Issues the session tokens used by every other service.
Owner: **Identity**.

### connector-hub

Stores connector credentials (encrypted with per-workspace keys) and opens the connections to customer data sources. All outgoing connections leave through two fixed addresses, 203.0.113.10 and 203.0.113.11.
Owner: **Data Integrations**.

### query-engine

Runs dataset queries, enforces the 120-second query time limit, and caches results for dashboards.
Owner: **Analytics Engine**.

### scheduler

Triggers dataset refreshes and scheduled reports at the right time, in the time zone of each schedule. Generates the report PDFs and hands them over for delivery.
Owner: **Analytics Engine**.

### postroom

Sends every e-mail that leaves Kestrel: scheduled report
````

## 5. KST-5031 → RAISED_BY → postroom

Relation ID: `r_c913029a8f1c27d922d399f6c690aba1867d99142b3bc097256e618e202efb66`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: KST-5031 is explicitly raised by postroom.

Source: `support-runbook-errors.md`; chunk `40d9cab202952c424bd3bde73e166979a442b84cc5fb928a3b32d0849e7811cc:5760:6560`; starting line 100.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### KST-5031 — Scheduled report not delivered

**User sees:** the schedule shows "Last delivery failed".
**Cause:** the report was generated but the e-mail was not sent. This error is raised by postroom, the service that sends all Kestrel e-mails.
````

Exact full source chunk:

````text
(KST-5xxx)

### KST-5031 — Scheduled report not delivered

**User sees:** the schedule shows "Last delivery failed".
**Cause:** the report was generated but the e-mail was not sent. This error is raised by postroom, the service that sends all Kestrel e-mails. A single occurrence is usually a temporary problem with a recipient's mail server.
**Support action:** check whether the recipient's address is correct and whether the next delivery succeeds. Ask the customer to check that messages from kestrel.example are not blocked by their mail filter.
**Escalate:** if the error happens on two consecutive deliveries, or for several customers on the same day, escalate to the team that owns postroom, as SEV-2.

### KST-5038 — Embed token expired

**User sees:** an embedded dashboard shows "This link
````

## 6. postroom → OWNED_BY → Messaging

Relation ID: `r_8448c5dfc3ec645d2d67ccdcddbddf28339677e572fd5b8c040781cfc302f44e`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: postroom is owned by Messaging.

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:1440:2240`; starting line 32.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### postroom

Sends every e-mail that leaves Kestrel: scheduled reports, invitations, password resets, ownership transfer confirmations and billing notifications. Tracks bounces and removes a recipient from a schedule after three rejections.
Owner: **Messaging**.
````

Exact full source chunk:

````text
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
````

## 7. gateway → OWNED_BY → Platform

Relation ID: `r_284507b1134b504aa9c39d8093da64f6198176d70bb04e76e81484e09d1c3ea4`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: gateway is owned by Platform.

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:0:800`; starting line 1.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### gateway

Public entry point for the web app and the public API. Handles TLS, rate limiting and request routing to the other services. Rate limit: 600 API requests per minute per workspace; requests above the limit receive HTTP 429.
Owner: **Platform**.
````

Exact full source chunk:

````text
# Kestrel Analytics — Service Catalog

Internal document · Owner: Platform team · Last updated: 15 September 2026

This catalog lists the production services of Kestrel, what each one does, and which team owns it. The owning team is responsible for the service's on-call rotation, its alerts and its runbook entries. When in doubt about who owns something, ask in #platform-help.

## 1. Services

### gateway

Public entry point for the web app and the public API. Handles TLS, rate limiting and request routing to the other services. Rate limit: 600 API requests per minute per workspace; requests above the limit receive HTTP 429.
Owner: **Platform**.

### auth

Sign-in with password, two-factor authentication, single sign-on (SAML) and SCIM provisioning. Issues the session tokens used by every 
````

## 8. scheduler → OWNED_BY → Analytics Engine

Relation ID: `r_bc4e33c2d356c2699ac2acd97d17a601f6a99689585b7b6d65ba183de45f5b31`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: scheduler is owned by Analytics Engine.

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:720:1520`; starting line 16.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### scheduler

Triggers dataset refreshes and scheduled reports at the right time, in the time zone of each schedule. Generates the report PDFs and hands them over for delivery.
Owner: **Analytics Engine**.
````

Exact full source chunk:

````text
e sign-on (SAML) and SCIM provisioning. Issues the session tokens used by every other service.
Owner: **Identity**.

### connector-hub

Stores connector credentials (encrypted with per-workspace keys) and opens the connections to customer data sources. All outgoing connections leave through two fixed addresses, 203.0.113.10 and 203.0.113.11.
Owner: **Data Integrations**.

### query-engine

Runs dataset queries, enforces the 120-second query time limit, and caches results for dashboards.
Owner: **Analytics Engine**.

### scheduler

Triggers dataset refreshes and scheduled reports at the right time, in the time zone of each schedule. Generates the report PDFs and hands them over for delivery.
Owner: **Analytics Engine**.

### postroom

Sends every e-mail that leaves Kestrel: scheduled report
````

## 9. Kestrel Analytics — Billing and Refund Policy → OWNED_BY → Finance

Relation ID: `r_45dc5d6896e26563c2319c735bb796817f79cfbbf15999b3b089d199865e07a6`
Condition: none recorded

Grade: **correct**  Reviewer: **Feras M**
Reason: Finance is explicitly named as the Billing and Refund Policy owner.

Source: `billing-policy-2025.md`; chunk `7fe5d5cb764faf872662b4639a727eabbae1364cee0b280864453e6a61d9513f:0:800`; starting line 1.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
# Kestrel Analytics — Billing and Refund Policy

Effective date: 1 January 2025 · Policy owner: Finance
````

Exact full source chunk:

````text
# Kestrel Analytics — Billing and Refund Policy

Effective date: 1 January 2025 · Policy owner: Finance · Audience: customers and support staff

## 1. Scope

This policy explains how Kestrel Analytics charges for its plans, how invoices are issued, and when refunds are possible. It applies to all paid plans: Starter, Team, Business and Enterprise. Enterprise contracts may contain different terms; when they do, the contract takes precedence over this policy. Current prices are published on the Kestrel pricing page and are not repeated here.

## 2. Billing cycles

Paid plans are billed per seat, either monthly or annually. Monthly plans are charged on the same day each month as the original purchase. Annual plans are charged once a year, on the anniversary of the purchase.

Customers who cho
````

## 10. KST-1012 → ESCALATE_TO → Identity

Relation ID: `r_ca441cf1b12ba168ba8085c885ca6c133d6013f6d83cea8aede54619becdf59f`
Condition: if the metadata is correct and the error persists

Grade: **correct**  Reviewer: **Feras M**
Reason: KST-1012 escalates to Identity if the metadata is correct and the error persists.

Source: `support-runbook-errors.md`; chunk `40d9cab202952c424bd3bde73e166979a442b84cc5fb928a3b32d0849e7811cc:2160:2960`; starting line 35.
Extraction model: `gemini-3.5-flash-lite`.

**Offline source-context expansion; original response remains quarantined.**

Supporting quotation:

````text
### KST-1012 — SSO response rejected

**User sees:** "Your identity provider returned an invalid response."
**Cause:** the identity provider certificate has expired or was rotated, or the clock of the identity provider is out of sync.
**Support action:** ask a workspace Admin to upload the new identity provider metadata in **Settings → Security → Single sign-on**.
**Escalate:** to Identity if the metadata is correct and the error persists.
````

Exact full source chunk:

````text
only does it after identity verification).
**Escalate:** no.

### KST-1012 — SSO response rejected

**User sees:** "Your identity provider returned an invalid response."
**Cause:** the identity provider certificate has expired or was rotated, or the clock of the identity provider is out of sync.
**Support action:** ask a workspace Admin to upload the new identity provider metadata in **Settings → Security → Single sign-on**.
**Escalate:** to Identity if the metadata is correct and the error persists.

## Connectors (KST-2xxx)

### KST-2040 — Connection timed out

**User sees:** "Kestrel could not reach your data source in time."
**Cause:** the database is down, overloaded, or behind a firewall that silently drops the connection.
**Support action:** ask the customer to confirm the database 
````
