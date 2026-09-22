# Rules.md — Sample Tracking System

*Boundaries for any AI coding tool (Antigravity or otherwise) working on
this project. Read this alongside PRD.md and Architecture.md before writing
code.*

## 1. Stack — do not deviate without asking

- **Language:** Python only. No TypeScript/JS frameworks, no separate frontend build.
- **Web framework:** Flask. Do not introduce Django, FastAPI, or any other framework.
- **Database:** SQLite via Python's built-in `sqlite3` module. **No ORM** (no SQLAlchemy, no Peewee) — raw SQL in `database.py` only. This is intentional, not a gap to "fix."
- **Frontend:** Server-rendered Jinja2 templates + plain CSS. No React, Vue, Tailwind build pipeline, or npm dependencies of any kind.
- **File generation:** `python-docx` for Word reports, `openpyxl` for Excel export. No other file-generation libraries.

## 2. Structure — stay flat

- Follow the folder structure in Architecture.md exactly. Do not introduce `models/`, `services/`, `blueprints/`, or `controllers/` folders. The whole point of this stack is that `app.py` stays readable top to bottom.
- Do not split `app.py` into multiple route files unless it exceeds ~300 lines. Ask first.
- Do not add configuration management (`.env` files, config classes) beyond what's strictly needed to run locally.

## 3. What NOT to add without being asked

Anything in the PRD's "Later Phase Features" list is off-limits until
explicitly requested, even if it seems like an easy addition:
- No login/auth system
- No audit/history logging table
- No role-based permissions
- No notifications/reminders
- No PDF export
- No barcode/QR generation
- No stats/analytics dashboard

If a feature isn't in the current PRD, don't build it "while you're in
there" — flag it as a suggestion instead and wait for confirmation.

## 4. Error handling

- Keep it simple and visible: if a database operation fails, show a plain error message on the page — don't silently swallow exceptions.
- Validate on the server side (Flask), not just with HTML `required` attributes — but keep validation minimal (required fields present, dates in the right format). Don't build a validation framework.
- Sample ID generation must never produce a duplicate — always derive the next ID from the actual current max in the database, not a cached counter.

## 5. Data integrity rules

- Soft-deleted samples (`deleted = 1`) must never appear in `/`, `/search`, or report generation — always filter `WHERE deleted = 0` unless the route is specifically `/deleted`.
- Status only ever changes when the user explicitly clicks a status control. Generating a Word report must NOT change status as a side effect.
- The master `test_parameters` table is data, not code — never hardcode parameter names/units inside route logic or templates. Routes should query the table.

## 6. Code style

- Prioritize readability over cleverness — this is a learning project; prefer the obvious 5-line solution over a compact 1-liner.
- Comment non-obvious logic (e.g. the sample ID generation, the report table-building loop) in plain language.
- Keep functions short and named for what they do (`get_next_sample_id()`, not `helper1()`).

## 7. When uncertain

If a requirement is ambiguous or missing from PRD.md/Architecture.md, stop
and ask rather than guessing and building further on top of an assumption.
