# Kestrel Analytics — Service Catalog

Internal document · Owner: Platform team · Last updated: 15 September 2026

This catalog lists the production services of Kestrel, what each one does, and which team owns it. The owning team is responsible for the service's on-call rotation, its alerts and its runbook entries. When in doubt about who owns something, ask in #platform-help.

## 1. Services

### gateway

Public entry point for the web app and the public API. Handles TLS, rate limiting and request routing to the other services. Rate limit: 600 API requests per minute per workspace; requests above the limit receive HTTP 429.
Owner: **Platform**.

### auth

Sign-in with password, two-factor authentication, single sign-on (SAML) and SCIM provisioning. Issues the session tokens used by every other service.
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

Sends every e-mail that leaves Kestrel: scheduled reports, invitations, password resets, ownership transfer confirmations and billing notifications. Tracks bounces and removes a recipient from a schedule after three rejections.
Owner: **Messaging**.

postroom replaced the older mailman service in November 2025. mailman is switched off; old alerts or documents that mention it refer to postroom today.

### embed-svc

Issues and checks embed tokens for dashboards embedded in customer applications.
Owner: **Platform**.

### ledger

Subscriptions, seats, invoices and payments. Generates invoice PDFs, runs the automatic payment retries, and applies the grace period and read-only rules of the Billing and Refund Policy. Talks to the payment processor; never stores full card numbers.
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
| Payments Core | Jonas Berg | #oncall-payments | 24/7 rotation |

Teams with weekday hours are covered outside those hours by the Platform on-call, who can page the team lead for SEV-1 incidents only.

## 3. Escalation rules

1. Support identifies the service involved, using the error code and the Support Runbook.
2. Support posts in the on-call channel of the team that owns that service, with the workspace name, the error code, the time, and the severity level.
3. For SEV-1, support also pages the on-call engineer through the paging tool; posting in the channel is not enough.
4. If the owning team is outside its working hours, escalate to the Platform on-call.
5. The owning team acknowledges in the thread and becomes responsible for the follow-up with support.

## 4. Changing ownership

A service changes owner only with the agreement of both engineering leads and an update of this catalog in the same week. Until the catalog is updated, the previous owner stays on call.
