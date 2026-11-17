# Kestrel Analytics — Product Guide

Version 4.2 · Last updated: 12 August 2026 · Audience: customers and workspace administrators

## 1. What Kestrel does

Kestrel Analytics is a dashboard and business intelligence service for teams. You connect your data sources, build datasets on top of them, and turn those datasets into dashboards that refresh automatically. Dashboards can be shared with colleagues, sent as scheduled PDF reports, or embedded in your own web applications.

Everything in Kestrel lives inside a **workspace**. A workspace has members, connectors, datasets and dashboards. Most customers use one workspace per company; larger organisations sometimes create one workspace per department. Members of one workspace cannot see the content of another workspace, even inside the same organisation.

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
| Audit log | — | — | — | 90 days | 1 year |
| Public share links | — | Yes | Yes | Yes | Yes |

Plans can be changed at any time from **Settings → Plan**. An upgrade takes effect immediately. A downgrade takes effect at the end of the current billing period; if the workspace uses more than the lower plan allows (for example more dashboards than the limit), the extra items become read-only until you remove them.

## 3. Workspace roles

Every member has one role in the workspace:

- **Owner**: exactly one per workspace. The Owner can do everything an Admin can, and is the only person who can change the plan, delete the workspace or transfer ownership.
- **Admin**: manages members, connectors and security settings.
- **Editor**: creates and edits datasets and dashboards.
- **Viewer**: opens dashboards and reports, but cannot change them.

To transfer ownership, the current Owner opens **Settings → Members**, selects a member and chooses **Transfer ownership**. The new Owner must already be an Admin of the workspace. Both people receive a confirmation e-mail, and the transfer completes only after both have confirmed. Until then the transfer is shown as pending.

## 4. Inviting people

Admins invite people from **Settings → Members → Invite**. An invitation is sent by e-mail and is valid for 7 days. After that the link expires and a new invitation must be sent.

Pending invitations do not use a seat. A seat is used only when the person accepts the invitation. If the workspace has no free seat at that moment, the invitation cannot be accepted until an Admin frees a seat or the Owner moves to a larger plan.

Members can be removed at any time. Their dashboards are not deleted: they are transferred to the Admin who removed them.

## 5. Signing in

### 5.1 Password and two-factor authentication

Members sign in with their e-mail address and a password, unless the workspace uses single sign-on. We strongly recommend turning on two-factor authentication from **Profile → Security**. Kestrel supports authenticator apps that generate time-based six-digit codes. When you turn it on, Kestrel shows 10 backup codes. Each backup code works once. Store them somewhere safe and separate from your authenticator device.

Admins can make two-factor authentication mandatory for every member from **Settings → Security**. Members who have not set it up are asked to do so at their next sign-in.

### 5.2 Single sign-on

On the Business and Enterprise plans, workspaces can use single sign-on with any SAML 2.0 identity provider. To set it up, an Admin opens **Settings → Security → Single sign-on**, downloads the Kestrel service provider metadata, registers Kestrel in the identity provider, and pastes the identity provider metadata URL back into Kestrel. We recommend testing with one Admin account before choosing **Enforce for all members**. When single sign-on is enforced, passwords are disabled and two-factor authentication is handled by your identity provider.

### 5.3 Regaining access to your account

If you no longer have your authenticator device, use one of your backup codes at the second-factor prompt, then set up two-factor authentication again from **Profile → Security**.

If you have neither your authenticator device nor any backup code, ask an Admin of your workspace to reset your second factor from **Settings → Members**. You will set it up again at your next sign-in.

If you are the only Admin, or the workspace Owner, write to support from the e-mail address registered on the account. For security reasons support verifies your identity before resetting anything; this verification can take up to 2 business days.

To reset a forgotten password, choose **Forgot password** on the sign-in page. The reset link is valid for 1 hour.

## 6. Data connectors

A connector stores the connection details for one data source. Kestrel supports PostgreSQL, MySQL, Google BigQuery, Snowflake, Google Sheets and CSV upload. A single CSV file can be up to 200 MB.

Connector credentials are encrypted at rest and are never shown again after they are saved. If your database only accepts connections from known addresses, add both Kestrel addresses to its allowlist: **203.0.113.10** and **203.0.113.11**. Connections can come from either address.

Each dataset query has a time limit of 120 seconds. Queries that take longer are stopped. If this happens often, add a filter, pre-aggregate the data in your database, or schedule a less frequent refresh.

## 7. Dashboards and refresh

Dashboards are built from tiles. Each tile reads one dataset. When a dataset refreshes, every tile that uses it is updated. The refresh frequency of a dataset cannot be faster than the fastest refresh of your plan (see section 2).

You can see when a dataset was last refreshed by hovering over the clock icon in the corner of any tile. A red clock means the last refresh failed; the tooltip shows the error code.

## 8. Scheduled reports

Any dashboard can be sent as a PDF on a schedule: daily, weekly or monthly. A schedule can have up to 50 recipients, who do not need to be members of the workspace. The schedule uses the time zone of the person who created it.

Reports are generated a few minutes before the scheduled time and delivered by e-mail. If a recipient's mail server rejects the message three times, that recipient is removed from the schedule and the schedule creator is notified.

## 9. Sharing and embedding

**Public links** let anyone with the link view a dashboard without signing in. They are available on every plan except Free, and an Admin can turn them off for the whole workspace.

**Embedding** places a dashboard inside your own web application. Your server requests an embed token from the Kestrel API and passes it to the page. By default an embed token expires after 24 hours. On the Business and Enterprise plans, the lifetime can be raised up to 30 days from **Settings → Embedding**.

## 10. Exporting and deleting data

The Owner can export the whole workspace (dashboards, datasets definitions and settings) as a ZIP file from **Settings → Workspace → Export**. Data from your sources is not included: Kestrel stores only the cached results needed to display dashboards.

When the Owner deletes a workspace, it is first disabled for 30 days. During that period it can be restored by contacting support. After 30 days it is deleted permanently and cannot be recovered.

Requests about personal data (access, correction, deletion) can be sent to privacy@kestrel.example. We answer within one month.

## 11. Getting help

| Plan | Channels | First response target |
|---|---|---|
| Free | Help centre, community forum | Best effort |
| Starter | E-mail | 2 business days |
| Team | E-mail, chat | 1 business day |
| Business | E-mail, chat | 8 business hours |
| Enterprise | E-mail, chat, named contact | 4 hours, 24/7 for critical incidents |

When you contact support, include the workspace name, the error code if one is shown (it starts with `KST-`), and the time it happened.
