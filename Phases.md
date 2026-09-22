# Phases.md — Sample Tracking System

*Build order. Each phase should be working and testable before moving to
the next — don't jump ahead even if it seems fast to combine steps.*

## Phase 1 — Foundation
- Set up the project folder structure (per Architecture.md)
- Create `database.py`: connect to `lab.db`, create the three tables (`samples`, `test_parameters`, `sample_results`)
- Seed `test_parameters` with the known list from PRD.md Section 6
- **Done when:** running the app once creates `lab.db` with all tables and the seeded parameter list, verifiable by inspecting the file.

## Phase 2 — Register & List
- Build `/register` (GET + POST): form with name, received from, date received; auto-generates the next `SSP-####` ID on submit
- Build `/` (GET): list all non-deleted samples in a table
- **Done when:** you can register a sample through the browser and immediately see it in the list.

## Phase 3 — Search & Detail View
- Build `/search`: match against Sample ID, sender name, sample name, or date
- Build `/sample/<sample_id>`: shows one sample's full info
- **Done when:** you can find a sample multiple ways and land on its detail page.

## Phase 4 — Test Results Entry
- On the detail page, show all `test_parameters` as checkboxes/selects with a result input next to each
- Build `/sample/<sample_id>/results` (POST): saves selected parameters + entered results into `sample_results`
- Reopening the detail page must show previously saved results, pre-filled — this is the "editable, save without export" behavior
- **Done when:** you can enter results, leave the page, come back, and edit them again before anything is exported.

## Phase 5 — Status Control
- Add a manual status toggle (`Under Testing` ↔ `Report Sent`) on the detail page
- Build `/sample/<sample_id>/status` (POST)
- **Done when:** status changes only when you click it — never automatically.

## Phase 6 — Word Report Generation
- Build `report.py`: given a sample ID, pull its info + results, build a `.docx` with the SR.NO/TEST PARAMETER/RESULT table
- Build `/sample/<sample_id>/report` (GET): triggers generation and downloads the file
- **Done when:** the downloaded Word file matches the format in PRD.md Section 5.5, using only that sample's entered results.

## Phase 7 — Soft Delete & Recovery
- Build `/sample/<sample_id>/delete` (POST): sets `deleted = 1`
- Build `/deleted` (GET): lists soft-deleted samples
- Build `/sample/<sample_id>/restore` (POST) and `/sample/<sample_id>/delete_permanent` (POST)
- **Done when:** deleting a sample removes it from the main list but it's recoverable from `/deleted`, and only the permanent-delete action actually removes it from the database.

## Phase 8 — Excel Export
- Build `export.py`: pull all non-deleted samples, build an `.xlsx`
- Build `/export` (GET): triggers generation and downloads the file
- **Done when:** the downloaded spreadsheet matches what's shown in the main list view.

## Phase 9 — Backup Protection
- On app startup, copy `lab.db` into `backups/` with a timestamped filename; prune anything beyond the 5 most recent
- Build `/backup` (GET): downloads the current, live `lab.db` file
- **Done when:** restarting the app produces a new timestamped file in `backups/`, older ones beyond 5 are gone, and clicking "Download Backup" gives you a working copy of the database.

## Phase 10 — Polish
- Apply consistent styling via `static/style.css`
- Clean up navigation between pages (list, search, register, deleted)
- Fix any rough edges found while demoing
- **Done when:** the whole flow (register → search → edit results → generate report → export) feels smooth enough to demo without narrating around bugs.

---

**Do not skip ahead.** If Phase 4 feels tedious, resist folding it into
Phase 6 "since you're already in report.py" — each phase existing
separately is what makes it possible to test and trust each piece before
building on top of it.
