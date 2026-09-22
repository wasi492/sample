# Architecture.md — Sample Tracking System (Prototype)

## 1. Tech Stack

- **Language:** Python
- **Web framework:** Flask
- **Database:** SQLite (single file, `lab.db`) — no server to install, just a file
- **Frontend:** Plain HTML templates (Jinja2, built into Flask) + basic CSS
- **No JavaScript framework, no ORM, no build tools** — kept out deliberately for the prototype. Nothing here needs them yet.

## 2. Folder Structure

```
sample-tracker/
├── app.py              # All routes live here
├── database.py         # Connect to DB, create tables, run queries
├── report.py           # Builds the .docx report for a sample (python-docx)
├── export.py           # Builds the .xlsx sample-list export (openpyxl)
├── lab.db              # SQLite database file (created automatically, not hand-edited)
├── backups/            # Auto-created timestamped copies of lab.db (last 5 kept)
├── templates/
│   ├── base.html         # Shared layout (nav, page title) — other pages extend this
│   ├── index.html        # List of all samples
│   ├── register.html     # Form to add a new sample
│   ├── search.html       # Search box + result
│   └── sample.html       # Single sample detail: enter test results, generate report, delete
└── static/
    └── style.css         # Basic styling
```

*Why so flat?* Even with report/export added, this is still ~6 pages and
two tables — splitting into blueprints/models/services folders is structure
you'd maintain without it buying you anything yet. `report.py` and
`export.py` are separated only because file-generation code is naturally
distinct from route logic, not because we're pre-building for scale.

## 3. Request Flow

Every page follows the same basic shape:

```
Browser request → Flask route (app.py) → database.py runs SQL → 
route passes data to a template → HTML sent back to browser
```

Concretely, for the three core routes:

| Route | Method | What it does |
|---|---|---|
| `/` | GET | Fetch all samples from DB → render `index.html` (list view) |
| `/register` | GET | Show the empty registration form |
| `/register` | POST | Read form data → generate next sequential Sample ID → insert into DB → redirect to `/` |
| `/search` | GET | Show search box; if `?q=...` is present, match against Sample ID, sender name, sample name, or date |
| `/sample/<sample_id>` | GET | Show one sample's full detail, including a form to enter/edit test results |
| `/sample/<sample_id>/results` | POST | Save selected test parameters + entered results for that sample |
| `/sample/<sample_id>/status` | POST | Update status (`Under Testing` ↔ `Report Sent`) |
| `/sample/<sample_id>/report` | GET | Generate and download the `.docx` report for that sample |
| `/sample/<sample_id>/delete` | POST | Soft delete: set `deleted = 1` → redirect to `/` |
| `/deleted` | GET | List samples where `deleted = 1` |
| `/sample/<sample_id>/restore` | POST | Set `deleted = 0` → redirect to `/deleted` |
| `/sample/<sample_id>/delete_permanent` | POST | Actually `DELETE FROM samples` — irreversible |
| `/export` | GET | Generate and download an `.xlsx` of the full sample list |
| `/backup` | GET | Download the current `lab.db` file directly |

## 4. Database Schema

Now that each sample needs an actual result *per* selected test parameter
(not just a list of test names), a proper relational structure earns its
keep — this isn't over-engineering, it's the minimum needed to store the
data correctly. Three tables:

**Table: `samples`**

| Column | Type | Notes |
|---|---|---|
| `sample_id` | TEXT, primary key | e.g. `SSP-0042` — sequential, generated in Python |
| `name` | TEXT | Sample name/type, e.g. "Fertilizer X" |
| `received_from` | TEXT | Who submitted the sample |
| `date_received` | TEXT | Stored as `YYYY-MM-DD` |
| `status` | TEXT | `Under Testing` or `Report Sent` — changed manually only, never auto-set |
| `deleted` | INTEGER | `0` normally, `1` when soft-deleted. Main list and search always filter `WHERE deleted = 0` |

**Table: `test_parameters`** *(master list, seeded once from data, not hardcoded in routes)*

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key | Auto-increment |
| `name` | TEXT | e.g. "Total Solids" |
| `unit` | TEXT | e.g. "%", "mg/L" |

**Table: `sample_results`** *(the junction — one row per test entered for a sample)*

| Column | Type | Notes |
|---|---|---|
| `sample_id` | TEXT, foreign key → `samples.sample_id` | |
| `parameter_id` | INTEGER, foreign key → `test_parameters.id` | |
| `result` | TEXT | Kept as text (not a strict number) since results can include units inline or non-numeric notes |

*Why text for `result` instead of a number?* Some results are plain numbers
(7.7), others already read like "850 mg/L". Forcing a numeric column now
means deciding a strict format before the real usage pattern is clear.
Text is the simplest thing that can't reject valid data — worth revisiting
only if you later need to do math across results (e.g. averages).

**Sample ID generation logic:** on each registration, take the highest
existing numeric suffix, add 1, and format as `SSP-{n:04d}`. Simple
`SELECT MAX(...)` — no separate counter table needed at this scale, and no
date logic, so same-day registrations never collide.

## 5. What's Deliberately Not Here

Matching the PRD's "still deferred" list — these aren't missing by accident:

- No user accounts/login (single shared internal tool for now)
- No audit/history table (no record of *who* changed what, or edit history)
- No PDF export (Word only)
- No API layer — templates are rendered server-side directly

## 6. Report & Export Generation

- **`report.py`** uses `python-docx` to build a `.docx` with the sample's
  header info and a table of only the parameters that have an entered
  result (SR. NO. / TEST PARAMETER / RESULT), generated fresh on each
  request rather than stored — always reflects current data.
- **`export.py`** uses `openpyxl` to build an `.xlsx` of the full `samples`
  list, also generated fresh on request.
- Both are called from their routes, write to a temp location, and are
  returned to the browser as a file download — nothing is written back
  into `lab.db`.

## 7. Backup Protection

- On app startup (before the first request is handled), copy `lab.db` into
  `backups/lab_backup_<timestamp>.db`. After copying, delete any backups
  beyond the 5 most recent — a simple `os.listdir` + sort by name (the
  timestamp format sorts correctly as plain text) + delete the oldest.
- `/backup` sends the *live* `lab.db` file as a direct download — not a
  backups/ copy — so a manual backup is always current to the second.
- This logic lives in `database.py` alongside the connection setup, not as
  a separate scheduler or background job — it only needs to run once per
  app start.

## 8. Path to "Real" Version (later, not now)

If this grows further: split `app.py` into Flask blueprints, add a
`history` table for audit trail, add PDF export, add a restore-from-backup
UI, and consider swapping SQLite for Postgres only if multiple concurrent
users become a real requirement. None of this needs deciding now.
