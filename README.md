# FSA Debtor System — Deployment Guide

A Django web application for managing Xero debtors: collections (call / WhatsApp /
email follow-ups), handover and a legal (LBINC) workflow with the lawyers, recovery
tracking, and role-based dashboards.

This guide is for a backend developer deploying the app to a cloud server.

---

## 1. Stack & architecture

| Part | Detail |
|------|--------|
| Language / framework | Python 3.14, **Django 6.0** |
| Database | **Microsoft SQL Server** (database name `FSA_Debtors`) via `mssql-django` + `pyodbc` (OS needs **ODBC Driver 18 for SQL Server**) |
| External API | **Xero** (OAuth 2.0; read-only accounting scopes) |
| Background job | Hourly **`manage.py sync_xero`** pulls open invoices from Xero into SQL Server |
| Uploads | User-attached documents stored under `MEDIA_ROOT` (needs persistent storage) |
| Frontend | Server-rendered Django templates (no separate JS build) |

It is a **single Django process** (it serves both the UI and the API). There is no
separate frontend to deploy.

---

## 2. Prerequisites on the server

1. **Python 3.14** (3.12+ should also work).
2. **Microsoft ODBC Driver 18 for SQL Server** installed on the OS:
   - Debian/Ubuntu: follow Microsoft's `msodbcsql18` apt instructions.
   - Windows: install "ODBC Driver 18 for SQL Server".
3. **A SQL Server database** the app can reach — Azure SQL, SQL Server on a VM, or
   AWS RDS for SQL Server. Create an empty database named `FSA_Debtors` (or set
   `DB_NAME`) and a login with `db_owner` on it.
4. **A Xero app** (https://developer.xero.com) with the production **redirect URI**
   registered (see §5).
5. A reverse proxy that terminates **HTTPS** (nginx, Caddy, or the platform's load
   balancer). Xero OAuth and secure cookies require HTTPS in production.

---

## 3. Environment variables

The app reads configuration from environment variables (or a `.env` file next to
`manage.py` — `python-dotenv` loads it). Copy **`.env.example` → `.env`** and fill in:

| Variable | Required | Notes |
|----------|----------|-------|
| `XERO_CLIENT_ID` | yes | From the Xero app |
| `XERO_CLIENT_SECRET` | yes | From the Xero app |
| `XERO_REDIRECT_URI` | yes | Must EXACTLY match the Xero app's redirect URI, e.g. `https://YOUR-DOMAIN/xero/callback/` |
| `DJANGO_SECRET_KEY` | yes | Long random string — generate a fresh one |
| `DJANGO_DEBUG` | yes | **`False`** in production |
| `DJANGO_ALLOWED_HOSTS` | yes | Comma-separated, e.g. `debtors.example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | yes | e.g. `https://debtors.example.com` |
| `DB_SERVER` | yes | SQL Server host |
| `DB_NAME` | yes | `FSA_Debtors` |
| `DB_PORT` | usually | `1433` |
| `DB_USER` / `DB_PASSWORD` | yes (cloud) | SQL auth login. **Leave blank only** for local Windows trusted auth. |
| `DB_DRIVER` | optional | Defaults to `ODBC Driver 18 for SQL Server` |

> When `DB_USER` is set the app uses **SQL authentication** (the cloud case). When
> it's blank it falls back to **Windows trusted auth** (local dev only).

---

## 4. Install & first-time setup

```bash
# 1. Get the code onto the server (this Debitor-main folder), then:
cd Debitor-main
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. Create .env from the template and fill it in
cp .env.example .env                # then edit .env

# 3. Sanity check + create the schema
python manage.py check
python manage.py migrate            # creates all tables in FSA_Debtors

# 4. Collect static files (served by nginx / the platform)
python manage.py collectstatic --noinput   # outputs to ./staticfiles

# 5. Create the first Super Admin login
python manage.py createsuperuser    # email + password (role defaults to Super Admin)
```

---

## 5. Configure the Xero app

In the Xero developer portal, on the app whose `XERO_CLIENT_ID` you're using:

- Add the **redirect URI**: `https://YOUR-DOMAIN/xero/callback/` (must match
  `XERO_REDIRECT_URI` exactly, including the trailing slash).
- Scopes used (read-only): `openid profile email offline_access
  accounting.contacts.read accounting.invoices.read accounting.settings.read`.

After deployment, a Super Admin logs in → **Connect to Xero** → authorises → the app
stores the tenant token and can sync.

---

## 6. Running the app (production)

**Do not** use `manage.py runserver` in production. Use a WSGI server behind HTTPS.

### Linux (gunicorn + nginx) — recommended
```bash
gunicorn mysite.wsgi:application --bind 127.0.0.1:8000 --workers 3 --timeout 120
```
Put it behind nginx (or the platform LB) terminating TLS and forwarding to
`127.0.0.1:8000`. nginx should also serve the static & media files:

```nginx
location /static/ { alias /path/to/Debitor-main/staticfiles/; }
location /media/  { alias /path/to/Debitor-main/media/; }
location /        { proxy_pass http://127.0.0.1:8000;
                    proxy_set_header Host $host;
                    proxy_set_header X-Forwarded-Proto $scheme; }
```
Run gunicorn as a **systemd** service so it restarts on boot/crash.

### Windows (IIS)
Use **IIS + wfastcgi** (or run gunicorn's Windows equivalent `waitress`). IIS serves
`\staticfiles` and `\media` as virtual directories.

> The app already trusts `X-Forwarded-Proto` and sets secure cookies when
> `DJANGO_DEBUG=False`, so it works correctly behind an HTTPS proxy.

---

## 7. The hourly Xero sync (important)

The dashboards and debtor pages read from a local snapshot that is refreshed by
`manage.py sync_xero`. It must run on a schedule. It is rate-limited to **half of
Xero's limits** and self-gates against the in-app **Schedule** settings.

### Linux — cron
```cron
# every hour, on the hour
0 * * * * cd /path/to/Debitor-main && /path/to/.venv/bin/python manage.py sync_xero >> /var/log/fsa_sync.log 2>&1
```

### Windows — Task Scheduler
The repo ships `run_sync.bat` (runs `manage.py sync_xero`). Register it as an hourly
Scheduled Task. Edit the Python path inside the .bat to match the server.

> The actual cadence (e.g. every N hours, or fixed times) is controlled in-app under
> **Schedule** (Super Admin). The OS job just needs to fire at least hourly; the app
> decides whether to run.

---

## 8. Files / persistent storage

- **Uploads** (`media/`) — invoice-comment and legal-document attachments live here.
  On ephemeral cloud filesystems (containers), mount a **persistent volume** at
  `media/`, or switch to object storage (S3/Azure Blob via `django-storages`).
- **Static** (`staticfiles/`) — produced by `collectstatic`; served by nginx/IIS.

---

## 9. Go-live checklist

- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_SECRET_KEY` is a fresh long random value (not the dev default)
- [ ] `DJANGO_ALLOWED_HOSTS` + `DJANGO_CSRF_TRUSTED_ORIGINS` set to the real domain
- [ ] HTTPS enforced at the proxy; HTTP redirects to HTTPS
- [ ] `XERO_REDIRECT_URI` matches the Xero app and uses `https://`
- [ ] `migrate` run; `createsuperuser` done; `collectstatic` done
- [ ] Hourly `sync_xero` scheduled
- [ ] `media/` on persistent storage; database **backups** enabled
- [ ] `python manage.py check --deploy` reviewed

---

## 10. First run after deploy

1. Browse to `https://YOUR-DOMAIN/` and log in as the Super Admin.
2. **Connect to Xero** and authorise.
3. Trigger the first sync: **Schedule → Refresh now** (or wait for the hourly job).
4. Create the other users under **Users** (Administrators, Lawyers).
5. Optionally set the **go-live date** (Schedule) and review **Communication Setup**
   templates.

Then run the **UAT** (`UAT.md`) to verify everything end-to-end.

---

## 11. Troubleshooting

| Symptom | Likely cause |
|--------|--------------|
| `Invalid HTTP_HOST header` | Domain missing from `DJANGO_ALLOWED_HOSTS` |
| CSRF "Origin checking failed" on a form POST | Domain missing from `DJANGO_CSRF_TRUSTED_ORIGINS`, or not on HTTPS |
| Xero "redirect_uri mismatch" | `XERO_REDIRECT_URI` ≠ the URI registered on the Xero app |
| `Can't open lib 'ODBC Driver 18...'` | ODBC Driver 18 not installed on the OS |
| Login works but no data | Xero not connected, or `sync_xero` hasn't run yet |
| Uploaded documents disappear after redeploy | `media/` not on persistent storage |

---

## 12. Roles & access levels

Every login has one **role** (set under **Users**). Access is enforced in the app
(not just hidden in the menu).

| Role | Can access / do | Cannot do |
|------|-----------------|-----------|
| **Super Admin** | **Everything** — Dashboard (system-wide), Debtors Action, Closed Debtors, Write-offs, Handover, Lawyers, **Filing**, Users, Schedule, Communication Setup. Manage users; allocate debtors; close/reopen; write off; handover rules + marking; **send to lawyers, approve, bring back**; plus all collections actions. | — |
| **Administrator** | **Collections only.** Dashboard (their own book), Debtors Action (their allocated debtors): log **calls / WhatsApps / emails**, add comments + **upload documents**, set a debtor's **follow-up cadence shift**. May **view** the Lawyers page (read-only). | Close/reopen debtors, write off, handover, allocate, send-to / approve lawyers, and the Filing / Users / Schedule / Communication Setup pages. |
| **Lawyer** | **Lawyers page only.** Their approved (active) legal matters: tick workflow steps, comment + **upload documents**, switch a route Unopposed ⇄ Opposed. | Everything else — debtor, dashboard, handover, filing pages all redirect them to the Lawyers page. |
| **Inspector** | Reserved role — no access by default. | — |

**Approval rule:** an Administrator (or Super Admin) **sends** a company to the
lawyers, but **only a Super Admin can approve** it before it appears on the Lawyers
page — and only a Super Admin can **bring it back** once the courts resolve it.

> The first account (`createsuperuser`) is a **Super Admin**. Create the other
> Administrator and Lawyer accounts from **Users** after first login. Administrators
> only see debtors **allocated** to them (Super Admin → Debtors Action → *Allocated to*).

**Dashboards** are role-specific:
- **Super Admin** — system-wide: outstanding by month, age pie, a **Recovered vs
  outstanding month-over-month** bar chart (red = outstanding, green = recovered),
  per-admin tracking (incl. money recovered), critical debtors and action items.
- **Administrator** — the same recovered-vs-outstanding chart and figures, **scoped
  to their own allocated book**, plus their call/WhatsApp/email action list.
- **Lawyer** — the Lawyers page with matter-progress KPIs.

Recovered figures are **forward-looking** (counted from when recovery tracking went
live; no historical backfill), so the green bars fill in over time as the sync
records payments.
