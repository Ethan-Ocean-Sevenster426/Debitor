# FSA Debtor System — User Acceptance Testing (UAT)

Use this script to verify the system end-to-end once it is on the cloud server.

**Before you start, create three test logins** (under **Users**, as Super Admin):
a **Super Admin**, an **Administrator**, and a **Lawyer**. Allocate at least one
debtor to the Administrator (Super Admin → Debtors Action → expand a debtor →
*Allocated to*). Make sure at least one sync has run so there's data.

For each test, mark **Pass / Fail** and note anything unexpected.

Legend: **SA** = Super Admin · **AD** = Administrator · **LW** = Lawyer.

---

## 0. Smoke & connection

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 0.1 | Browse to the site over HTTPS | Login page loads; URL is `https://…` (padlock) | |
| 0.2 | Log in as SA | Lands on the Dashboard | |
| 0.3 | SA → Connect to Xero → authorise | Returns to the app "connected"; tenant name shows | |
| 0.4 | SA → Schedule → **Refresh now** | Sync runs; debtor data appears on the Debtors Action page | |
| 0.5 | Wait for / trigger the hourly job | A new sync run is recorded (Schedule shows "last successful sync") | |

---

## 1. Authentication & roles

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 1.1 | Log in with a wrong password | Rejected with an error | |
| 1.2 | Log in as AD | Lands on **their** Dashboard (collections view) | |
| 1.3 | Log in as LW | Lands on the **Lawyers** page (not the main dashboard) | |
| 1.4 | Log out from each role | Returns to the login page | |

---

## 2. Permissions matrix (critical)

| # | Action | SA | AD | LW | P/F |
|---|--------|----|----|----|-----|
| 2.1 | See **Closed Debtors / Write-offs / Handover** in the nav | ✅ | ❌ | ❌ | |
| 2.2 | See **Filing** in the nav | ✅ | ❌ | ❌ | |
| 2.3 | See **Users / Schedule / Communication Setup** | ✅ | ❌ | ❌ | |
| 2.4 | See **Lawyers** page | ✅ | ✅ (view) | ✅ | |
| 2.5 | See **Dashboard / Debtors Action** | ✅ | ✅ | ❌ (redirects to Lawyers) | |
| 2.6 | **Mark closed / Write off / Mark for handover** buttons visible | ✅ | ❌ | ❌ | |
| 2.7 | **Send to lawyers / Approve / Bring back** | ✅ | ❌ | ❌ | |
| 2.8 | **Call / WhatsApp / Email + comments + uploads** | ✅ | ✅ | ❌ | |
| 2.9 | Tick legal steps / comment / upload on a matter | ✅ | ❌ (read-only) | ✅ | |
| 2.10 | AD opens `…/xero/filing/` directly in the URL | — | Redirected away (no access) | — | |
| 2.11 | LW opens `…/xero/aging/` directly | — | — | Redirected to Lawyers page | |

---

## 3. Super Admin dashboard

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 3.1 | Open SA Dashboard | **System Overview** tiles: total outstanding, debtors, calls required, missed, final demand, handover, **Recovered this month**, unallocated | |
| 3.2 | Check charts | Month-over-month outstanding line + age pie render | |
| 3.3 | **Recovered vs outstanding (month over month)** bar chart | Grouped bars per month: **red = outstanding**, **green = recovered**; legend shows both totals; hovering a bar shows the exact rand amount (system-wide) | |
| 3.4 | **Action Items & Lawyers** card | Shows top collector (if any), awaiting-approval count, active matters, "not yet in litigation", closed | |
| 3.5 | **Critical debtors** table | Lists biggest 60+-day books not yet with lawyers, with allocated admin | |
| 3.6 | **Administrator Tracking** table | Each admin: clients, outstanding, **Recovered (mo)**, calls, missed, final, handover | |
| 3.7 | Click an admin name | Drills into that admin's workload view | |
| 3.8 | Click "Awaiting your approval" | Goes to the Lawyers page | |

---

## 4. Administrator dashboard (collections)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 4.1 | Open AD Dashboard | Tiles for **their** allocation only: outstanding, companies, calls required, missed, final, handover, **Recovered this month** | |
| 4.2 | **Recovered vs outstanding (month over month)** bar chart | Red = outstanding, green = recovered per month, **scoped to their own book** (totals match their figures, not the system's) | |
| 4.3 | **Priority debtors** list | Their biggest / most-overdue books | |
| 4.4 | **Invoices to call about** | Lists their call-window invoices; a quick "log call" works and removes the row | |
| 4.5 | Confirm scope | No other admin's debtors appear anywhere on their dashboard | |

---

## 5. Lawyer dashboard (Lawyers page)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 5.1 | Open as LW | KPI header: **Active matters, Avg completion %, Not yet in litigation, Closed** | |
| 5.2 | Matter list | Active matters listed with progress bar + route summary | |
| 5.3 | "Not yet in litigation" count | Matches the number of active matters with no summons/application step ticked | |
| 5.4 | LW sees only active matters | No pending/closed matters visible to the lawyer | |

---

## 6. Debtors Action page (SA/AD)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 6.1 | Open the page | Debtors listed with aging buckets + totals; summary tiles act as filters | |
| 6.2 | Search a company / invoice number | List filters correctly | |
| 6.3 | Click a bucket / stage tile | List filters to that bucket / stage | |
| 6.4 | Expand a debtor row | Loads its invoice statement (no full page reload) | |
| 6.5 | Click **Contact details** | Shows the debtor's Xero contact info | |
| 6.6 | Status column | Combined **Missed:** and **Due:** badges show the right channels | |

---

## 7. Contact logging — call / WhatsApp / email

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 7.1 | On an in-window invoice, click **📞 Call** | Prompts for a note; logs the call; row shows "✓ called" — **without a full page reload** | |
| 7.2 | Click the **✕** undo next to "✓ called" | Re-opens the Call task in place | |
| 7.3 | Click **📱 WhatsApp** (single template) | Opens WhatsApp (wa.me) pre-filled; row shows "✓ WhatsApp" | |
| 7.4 | Click **✉ Email** | Opens the mail client (mailto) pre-filled; row shows "✓ emailed" | |
| 7.5 | Add a 2nd template (Communication Setup), reload, click a channel | Button now shows a **popup** to pick the template; choosing one sends that wording | |
| 7.6 | Confirm independence | Logging a Call does NOT clear the WhatsApp or Email task (3 independent tasks) | |
| 7.7 | Kebab (⋮) → WhatsApp/Email even when not flagged | Works as an ad-hoc contact | |

---

## 8. Comments & document uploads on invoices

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 8.1 | Expand an invoice's lifecycle (click the invoice row) | Timeline + "Add a comment" box appears | |
| 8.2 | Add a comment with the date picker | Comment appears in the timeline | |
| 8.3 | Attach one or more documents to a comment | Documents save and are downloadable from the timeline | |

---

## 9. Per-debtor handover rule (SA)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 9.1 | Expand a debtor → **⚙ Handover rule** | Inline form opens | |
| 9.2 | Set "Auto-hand over at N days" | Saved; the chip shows "N days (custom)" | |
| 9.3 | Set "Never auto-hand over" | Debtor's invoices no longer auto-list on Handover | |
| 9.4 | Reset to default | Reverts to the system default (65 days) | |
| 9.5 | **Handover Rules** page | Lists every debtor with a custom rule; reset works | |

---

## 10. Follow-up cadence shift (SA/AD) — pay arrangements

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 10.1 | Expand a debtor → **⏳ Follow-up** | Inline form opens | |
| 10.2 | Push reminders later by e.g. 30 days, save | Chip shows "+30 days" | |
| 10.3 | Check an invoice that *was* in the call window | It no longer shows Call/WhatsApp/Email due (cadence shifted) | |
| 10.4 | Set back to 0 | Normal cadence resumes | |

---

## 11. Missed / Due flags & go-live date

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 11.1 | Find an invoice 21–60 days overdue with no contact logged | Shows **Missed** for the un-actioned channel(s) | |
| 11.2 | SA → Schedule → set a **Go-live date** in the recent past | Invoices **issued before** that date stop showing Missed flags | |
| 11.3 | Confirm those invoices can still be called/WhatsApp/emailed | Yes — only the Missed flag is suppressed | |

---

## 12. Closed debtors & write-offs (SA only)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 12.1 | Debtor row → **Mark closed** | Moves to Closed Debtors; removed from dashboard totals | |
| 12.2 | Closed Debtors → **Reopen** | Returns to active | |
| 12.3 | Invoice kebab → **Write off** (reason required) | Moves to Write-off page; logged in the lifecycle | |
| 12.4 | Write-off page → **Move back** | Returns to Debtors Action | |

---

## 13. Handover → lawyers → approval

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 13.1 | SA → Handover page | Lists invoices past each debtor's threshold + any manually marked | |
| 13.2 | Expand a company → **⚖ Send to lawyers** | Status becomes "pending approval" | |
| 13.3 | As **AD**, try to approve | No approve button (only SA can) | |
| 13.4 | As **SA**, **Approve** | Status → active; company appears on the Lawyers page | |
| 13.5 | Handover status column | Shows the company's legal status (Pending / With lawyers / Closed) | |

---

## 14. Legal workflow (LW / SA)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 14.1 | Open an active matter | Shows **Collections → Summons → Application for payment** in sequence | |
| 14.2 | Outstanding invoices panel | Shows the company's invoices + their comments; **Full company report** opens | |
| 14.3 | Tick several steps | Saved; ticks persist; progress bar updates | |
| 14.4 | Add a comment on a step + **attach a document** | Comment + downloadable document appear under that step | |
| 14.5 | On Summons, click **Switch to Opposed** | Summons branch swaps to the Opposed steps; existing ticks/comments preserved | |
| 14.6 | Switch Application independently | Each route has its own Unopposed/Opposed state | |
| 14.7 | As AD, open the same matter | **Read-only** — no checkboxes / comment box | |
| 14.8 | As SA, **Bring back from lawyers** | Matter closes; company returns to normal management | |

---

## 15. Recovery tracking

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 15.1 | Pick an allocated, followed-up (call/WhatsApp/email logged) invoice and record a **payment in Xero**; run a sync | After sync, the admin's **Recovered this month** increases by the paid amount | |
| 15.2 | Pay an invoice already **at handover / with lawyers**; sync | Payment is recorded but **NOT** credited to the admin | |
| 15.3 | Pay an invoice with **no follow-up** logged; sync | Recorded but not credited | |
| 15.4 | SA dashboard "Top collector" | Reflects the admin with the most recovered this month | |

> Note: recovery counts **payments since go-live of this feature only** (no backfill).

---

## 16. Filing / Archive (SA only)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 16.1 | SA → **Filing** | Searchable list of every company (incl. closed) | |
| 16.2 | Search a company; open its file | Shows **Documents** (all uploads in one place), invoices + activity, and legal history | |
| 16.3 | Check the **Documents** list | Includes BOTH invoice-comment attachments AND **lawyer-uploaded legal documents** (labelled "Legal document") | |
| 16.4 | Check **Legal history** | Shows the lawyers' step **comments** and the documents attached to them | |
| 16.5 | Click a document | Downloads / opens correctly | |
| 16.6 | Open a closed/archived company | Its data is still accessible | |

---

## 17. Communication setup (SA only)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 17.1 | Open **Communication Setup** | Email + WhatsApp template sections; add-template forms styled correctly | |
| 17.2 | Add a second email & WhatsApp template | Saved; appears as a choice on the debtor buttons (see 7.5) | |
| 17.3 | Edit a template / change default / delete | All work; placeholders (e.g. `{name}`) render in the preview | |

---

## 18. Schedule & sync (SA only)

| # | Steps | Expected result | P/F |
|---|-------|-----------------|-----|
| 18.1 | Open **Schedule** | Shows last successful sync, status, and the cadence settings | |
| 18.2 | Change interval / fixed times, save | Saved; reflected on the status card | |
| 18.3 | **Refresh now** | Runs a sync; data updates | |
| 18.4 | Set the **Go-live date** here | Saved (used by the Missed-flag suppression in 11.2) | |

---

## 19. Sign-off

| Role | Tester | Date | Result |
|------|--------|------|--------|
| Super Admin |  |  |  |
| Administrator |  |  |  |
| Lawyer |  |  |  |

All critical (permissions, sync, contact logging, legal workflow, recovery)
sections must pass before go-live.
