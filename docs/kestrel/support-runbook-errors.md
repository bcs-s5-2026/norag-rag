# Kestrel Analytics — Support Runbook: Error Codes

Internal document · Owner: Customer Support · Last reviewed: 2 September 2026

## How to use this runbook

Every error shown to a Kestrel user carries a code of the form `KST-` followed by four digits. The first digit gives the area: 1 for sign-in, 2 for connectors, 3 for queries and dashboards, 4 for members and seats, 5 for delivery and embedding, 6 for billing.

For each code, this runbook gives what the user sees, the usual cause, what support can do, and when to escalate. Always ask the customer for the workspace name, the exact code and the time it happened. If a code is not listed here, escalate it to the on-call engineer of the Platform team.

Escalations go to the team that owns the service involved. The owning team of each service and its on-call channel are listed in the Service Catalog.

## Severity levels

| Level | Meaning | Target first response |
|---|---|---|
| SEV-1 | Many customers cannot use Kestrel, or data is exposed | 15 minutes, page on-call |
| SEV-2 | One customer is blocked in production, no workaround | 1 hour |
| SEV-3 | Degraded behaviour with a workaround | Next business day |
| SEV-4 | Question, cosmetic issue | Normal queue |

## Sign-in (KST-1xxx)

### KST-1001 — Invalid credentials

**User sees:** "The e-mail or password is incorrect."
**Cause:** wrong password, or the user is signing in to a workspace that enforces single sign-on.
**Support action:** check whether the workspace enforces single sign-on. If it does, tell the user to use **Sign in with SSO**. Otherwise point them to **Forgot password**. Support never sets a password for a user.
**Escalate:** no.

### KST-1007 — Two-factor code rejected

**User sees:** "This code is not valid."
**Cause:** in most cases the clock of the device running the authenticator app is wrong; time-based codes depend on the time being correct within about 30 seconds.
**Support action:** ask the user to turn on automatic date and time on their device and try again. If they have lost their device, follow the second-factor reset procedure in the Product Guide (an Admin of the workspace resets it; support only does it after identity verification).
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
**Support action:** ask the customer to confirm the database is reachable from outside their network, on the host and port configured in the connector.
**Escalate:** to Data Integrations if several customers report it for the same source type at the same time.

### KST-2044 — Source refused the connection

**User sees:** "Your data source refused the connection from Kestrel."
**Cause:** the database only accepts connections from an allowlist of IP addresses, and the Kestrel addresses are missing from it.
**Support action:** ask the customer to add both 203.0.113.10 and 203.0.113.11 to the allowlist of their database or firewall. Adding only one of them leads to errors that come and go, because connections can come from either address.
**Escalate:** no.

### KST-2051 — Credentials rejected

**User sees:** "The username or password for this data source is incorrect."
**Cause:** the database password was changed, or the database user was removed.
**Support action:** an Admin must edit the connector and enter the new credentials. Support cannot see stored credentials.
**Escalate:** no.

## Queries and dashboards (KST-3xxx)

### KST-3012 — Query time limit exceeded

**User sees:** "This query took too long and was stopped."
**Cause:** a dataset query ran for more than 120 seconds.
**Support action:** suggest adding a filter, pre-aggregating in the source database, or refreshing less often. The time limit is the same on every plan and cannot be raised.
**Escalate:** to Analytics Engine only if a query that used to finish quickly suddenly times out for many datasets of the same customer.

### KST-3020 — Dataset refresh failed

**User sees:** a red clock on the tiles.
**Cause:** the tooltip shows a second code with the real cause, usually a KST-2xxx connector error.
**Support action:** handle the underlying code.
**Escalate:** depends on the underlying code.

## Members and seats (KST-4xxx)

### KST-4012 — No seat available

**User sees:** "This workspace has no seat available. Ask an Admin."
**Cause:** the person is accepting an invitation, but all seats of the plan are already used. Pending invitations do not use a seat; the check happens at acceptance.
**Support action:** explain that an Admin of the workspace must remove a member to free a seat, or the Owner must add seats or move to a larger plan. Once a seat is free, the same invitation link works again as long as it is less than 7 days old.
**Escalate:** no.

### KST-4019 — Ownership transfer pending

**User sees:** "An ownership transfer is waiting for confirmation."
**Cause:** the Owner started a transfer, and one of the two people has not confirmed it by e-mail.
**Support action:** ask both people to check their inbox and spam folder. The transfer can be cancelled by the current Owner from **Settings → Members**.
**Escalate:** no.

## Delivery and embedding (KST-5xxx)

### KST-5031 — Scheduled report not delivered

**User sees:** the schedule shows "Last delivery failed".
**Cause:** the report was generated but the e-mail was not sent. This error is raised by postroom, the service that sends all Kestrel e-mails. A single occurrence is usually a temporary problem with a recipient's mail server.
**Support action:** check whether the recipient's address is correct and whether the next delivery succeeds. Ask the customer to check that messages from kestrel.example are not blocked by their mail filter.
**Escalate:** if the error happens on two consecutive deliveries, or for several customers on the same day, escalate to the team that owns postroom, as SEV-2.

### KST-5038 — Embed token expired

**User sees:** an embedded dashboard shows "This link has expired".
**Cause:** the embed token passed by the customer's application is older than its lifetime (24 hours by default).
**Support action:** the customer's server must request a new token before the old one expires. On Business and Enterprise, the lifetime can be raised up to 30 days.
**Escalate:** no.

## Billing (KST-6xxx)

### KST-6002 — Payment declined

**User sees:** "Your payment was declined."
**Cause:** the card was refused by the bank: insufficient funds, expired card, or a security block.
**Support action:** ask the Owner to update the payment method before the next automatic retry. Follow the current Billing and Refund Policy for retries, grace period and read-only rules. Support cannot take card details over e-mail or chat.
**Escalate:** to Payments Core only if the customer shows that the bank approved the payment.

### KST-6010 — Duplicate charge detected

**User sees:** nothing; this code appears in the admin console when two charges for the same period are found.
**Cause:** a retry and a manual payment went through for the same invoice.
**Support action:** confirm the duplicate in the admin console and request a full refund of the second charge; billing errors are always refunded.
**Escalate:** to Payments Core if more than three customers are affected on the same day (possible incident).
