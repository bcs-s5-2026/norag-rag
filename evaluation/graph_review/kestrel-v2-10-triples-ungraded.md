# Kestrel: ten triples for manual grading

Frozen graph `f54cf5635cdf079b0efa5eab815e79c73dc73e349dea3d4971635326aa0e8481`; seed 20261108; sample 10 of 39 distinct relations.

No grades have been assigned. Use correct / wrong / unsupported; record your name and reason.
Context-expanded evidence is explicitly labelled; the original model quote is preserved. Read the whole source passage.

## 1. Public share links → AVAILABLE_ON → Business

Relation ID: `r_703f8e923be6f565e16354657f647a307efde73c3555b105271ad0818a73c66a`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `product-guide.md`; chunk `2a6de3b72fb4b0c85b697f8fdecdde1a0f37506eae3b24a05497f289ebb251c6:1440:2240`; starting line 23.
Extraction model: `gemini-3.6-flash`.

**One endpoint label comes from the section heading:** `# Kestrel Analytics — Product Guide > ## 2. Plans and limits > Table header: | | Free | Starter | Team | Business | Enterprise |`

Supporting quotation:

````text
| Public share links | — | Yes | Yes | Yes | Yes |
````

Exact full source chunk:

````text
M user provisioning | — | — | — | — | Yes |
| Audit log | — | — | — | 90 days | 1 year |
| Public share links | — | Yes | Yes | Yes | Yes |

Plans can be changed at any time from **Settings → Plan**. An upgrade takes effect immediately. A downgrade takes effect at the end of the current billing period; if the workspace uses more than the lower plan allows (for example more dashboards than the limit), the extra items become read-only until you remove them.

## 3. Workspace roles

Every member has one role in the workspace:

- **Owner**: exactly one per workspace. The Owner can do everything an Admin can, and is the only person who can change the plan, delete the workspace or transfer ownership.
- **Admin**: manages members, connectors and security settings.
- **Editor**: creates and edits d
````

## 2. SCIM user provisioning → AVAILABLE_ON → Enterprise

Relation ID: `r_b1654c074ed09c50b78a8769135958ff3f17ad5fc4ca7f3b97d8db64bbfd2591`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `product-guide.md`; chunk `2a6de3b72fb4b0c85b697f8fdecdde1a0f37506eae3b24a05497f289ebb251c6:720:1520`; starting line 9.
Extraction model: `gemini-3.6-flash`.

Supporting quotation:

````text
| | Free | Starter | Team | Business | Enterprise |
|---|---|---|---|---|---|
| Seats included | 2 | 5 | 20 | 100 | Custom |
| Dashboards | 3 | 25 | Unlimited | Unlimited | Unlimited |
| Data connectors | 1 | 3 | 10 | Unlimited | Unlimited |
| Fastest refresh | Daily | Hourly | Every 15 minutes | Every 5 minutes | Every minute |
| History kept | 30 days | 1 year | 2 years | 5 years | Custom |
| Single sign-on (SAML) | — | — | — | Yes | Yes |
| SCIM user provisioning | — | — | — | — | Yes |
````

Exact full source chunk:

````text
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
````

## 3. Public share links → AVAILABLE_ON → Enterprise

Relation ID: `r_3c10b844cdf5915e85c6a513b78b144cb331a1cb2993dc77c384fabe5bd84107`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `product-guide.md`; chunk `2a6de3b72fb4b0c85b697f8fdecdde1a0f37506eae3b24a05497f289ebb251c6:1440:2240`; starting line 23.
Extraction model: `gemini-3.6-flash`.

**One endpoint label comes from the section heading:** `# Kestrel Analytics — Product Guide > ## 2. Plans and limits > Table header: | | Free | Starter | Team | Business | Enterprise |`

Supporting quotation:

````text
| Public share links | — | Yes | Yes | Yes | Yes |
````

Exact full source chunk:

````text
M user provisioning | — | — | — | — | Yes |
| Audit log | — | — | — | 90 days | 1 year |
| Public share links | — | Yes | Yes | Yes | Yes |

Plans can be changed at any time from **Settings → Plan**. An upgrade takes effect immediately. A downgrade takes effect at the end of the current billing period; if the workspace uses more than the lower plan allows (for example more dashboards than the limit), the extra items become read-only until you remove them.

## 3. Workspace roles

Every member has one role in the workspace:

- **Owner**: exactly one per workspace. The Owner can do everything an Admin can, and is the only person who can change the plan, delete the workspace or transfer ownership.
- **Admin**: manages members, connectors and security settings.
- **Editor**: creates and edits d
````

## 4. connector-hub → OWNED_BY → Data Integrations

Relation ID: `r_6fb425c8a336bd02862ef9c1b69316322b8ce8f59eaca00193ff2eecd81b2e28`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:720:1520`; starting line 16.
Extraction model: `gemini-3.6-flash`.

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

## 5. Public share links → AVAILABLE_ON → Team

Relation ID: `r_80d1dc0f97cd12593b50f9b07afbc165cd255321c6f780c6e94dc67257748089`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `product-guide.md`; chunk `2a6de3b72fb4b0c85b697f8fdecdde1a0f37506eae3b24a05497f289ebb251c6:1440:2240`; starting line 23.
Extraction model: `gemini-3.6-flash`.

**One endpoint label comes from the section heading:** `# Kestrel Analytics — Product Guide > ## 2. Plans and limits > Table header: | | Free | Starter | Team | Business | Enterprise |`

Supporting quotation:

````text
| Public share links | — | Yes | Yes | Yes | Yes |
````

Exact full source chunk:

````text
M user provisioning | — | — | — | — | Yes |
| Audit log | — | — | — | 90 days | 1 year |
| Public share links | — | Yes | Yes | Yes | Yes |

Plans can be changed at any time from **Settings → Plan**. An upgrade takes effect immediately. A downgrade takes effect at the end of the current billing period; if the workspace uses more than the lower plan allows (for example more dashboards than the limit), the extra items become read-only until you remove them.

## 3. Workspace roles

Every member has one role in the workspace:

- **Owner**: exactly one per workspace. The Owner can do everything an Admin can, and is the only person who can change the plan, delete the workspace or transfer ownership.
- **Admin**: manages members, connectors and security settings.
- **Editor**: creates and edits d
````

## 6. single sign-on → AVAILABLE_ON → Enterprise

Relation ID: `r_080e992574e2b45155a42ee6a183fea93956235b45ab0cdad478ef49dc7701f0`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `product-guide.md`; chunk `2a6de3b72fb4b0c85b697f8fdecdde1a0f37506eae3b24a05497f289ebb251c6:3600:4400`; starting line 52.
Extraction model: `gemini-3.6-flash`.

Supporting quotation:

````text
On the Business and Enterprise plans, workspaces can use single sign-on
````

Exact full source chunk:

````text
ows 10 backup codes. Each backup code works once. Store them somewhere safe and separate from your authenticator device.

Admins can make two-factor authentication mandatory for every member from **Settings → Security**. Members who have not set it up are asked to do so at their next sign-in.

### 5.2 Single sign-on

On the Business and Enterprise plans, workspaces can use single sign-on with any SAML 2.0 identity provider. To set it up, an Admin opens **Settings → Security → Single sign-on**, downloads the Kestrel service provider metadata, registers Kestrel in the identity provider, and pastes the identity provider metadata URL back into Kestrel. We recommend testing with one Admin account before choosing **Enforce for all members**. When single sign-on is enforced, passwords are disable
````

## 7. audit-log → OWNED_BY → Identity

Relation ID: `r_a961c61d3a30d16480ba18ff472c0da58e98fdad910328ba42b9518e4b6863ee`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:2160:2960`; starting line 48.
Extraction model: `gemini-3.6-flash`.

Supporting quotation:

````text
### audit-log

Records security-relevant events (sign-ins, role changes, connector edits, exports) for workspaces on Business and Enterprise plans.
Owner: **Identity**.
````

Exact full source chunk:

````text
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
````

## 8. Analytics Engine → CONTACT_CHANNEL → #oncall-analytics

Relation ID: `r_1349e3f4d3fb1433cebb145063e68aea47e64e6a842cbebf1caad26b9f7e7b24`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:2160:2960`; starting line 48.
Extraction model: `gemini-3.6-flash`.

Supporting quotation:

````text
| Analytics Engine | Léa Fontaine | #oncall-analytics | 24/7 rotation |
````

Exact full source chunk:

````text
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
````

## 9. query-engine → OWNED_BY → Analytics Engine

Relation ID: `r_c90e3b89c497da363d65beb031fdd915bb8c895d5715094d41dad4a77c51ac8c`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `service-catalog.md`; chunk `12e8379afbbd255b94909badde635074233712d32d73cab654f4c8ab2c582888:720:1520`; starting line 16.
Extraction model: `gemini-3.6-flash`.

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

## 10. Billing and Refund Policy → OWNED_BY → Finance

Relation ID: `r_3bc48db4bd1f1594a754e043d98d5e44b05622a2777fb9853c00b11fbedf9ea2`
Condition: none recorded

Grade: __________  Reviewer: __________
Reason: __________

Source: `billing-policy-2026.md`; chunk `6bd088c131fb50e00ed933ef2758705ed1a308bfa8ee2672d07d64de8a29ee22:0:800`; starting line 1.
Extraction model: `gemini-3.6-flash`.

Supporting quotation:

````text
# Kestrel Analytics — Billing and Refund Policy

Effective date: 1 March 2026 · Policy owner: Finance
````

Exact full source chunk:

````text
# Kestrel Analytics — Billing and Refund Policy

Effective date: 1 March 2026 · Policy owner: Finance · Audience: customers and support staff

This policy replaces the Billing and Refund Policy effective 1 January 2025. Requests made before 1 March 2026 are handled under the previous policy.

## 1. Scope

This policy explains how Kestrel Analytics charges for its plans, how invoices are issued, and when refunds are possible. It applies to all paid plans: Starter, Team, Business and Enterprise. Enterprise contracts may contain different terms; when they do, the contract takes precedence over this policy. Current prices are published on the Kestrel pricing page and are not repeated here.

## 2. Billing cycles

Paid plans are billed per seat, either monthly or annually. Monthly plans are char
````
