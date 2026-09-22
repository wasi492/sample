# PRD.md — Sample Tracking System

*Status: prototype was demoed and approved. This version reflects the
supervisor's requested feature list for the full build.*

## 1. Overview

A desktop-style web application that replaces handwritten lab records with a
digital system for logging, tracking, and retrieving test samples (e.g.
fertilizers, soil, or similar materials submitted for laboratory analysis).

Every sample that enters the lab gets a unique ID and a digital record. That
record follows the sample through its entire lifecycle — from receipt, to
testing, to final result — and can be pulled up instantly by anyone
authorized to search it.

## 2. Problem Statement

The lab currently tracks samples on paper. This causes:
- Lost or illegible records
- No fast way to check the status of a sample ("is it still testing?")
- No way to search historical samples
- No structured link between a sample and its final report/result
- No visibility into lab throughput (how many pending vs. completed)

## 3. Target Users

| Role | Needs |
|---|---|
| **Lab technician / receptionist** | Quickly register a new incoming sample |
| **Lab analyst** | Update test status and enter results |
| **Lab manager / supervisor** | Search any sample, see overall pending/testing/completed counts, view reports |
| **Authorized viewer (e.g. client-facing staff)** | Search a sample by ID and see its current status/result — read-only |

*Assumption: this is an internal tool used by lab staff, not customer-facing. Adjust if clients need direct access.*

## 4. Goals

- Eliminate handwritten/paper sample logs
- Make any sample instantly searchable by ID (or other fields)
- Auto-generate a unique, human-readable Sample ID for every entry
- Track status through a defined lifecycle: **Pending → Testing → Completed**
- Preserve full history/timestamps for every sample and status change
- Attach or link the final report/result to the sample record
- (Later phase) Generate summary reports/statistics (e.g. samples per month, average turnaround time, tests by type)

## 5. Core Features (Full Build — post-prototype)

*Reflects the supervisor's requested feature list after seeing the
prototype. See Section 6 for what's still deferred.*

### 5.1 Sample Registration
- Create a new sample record with:
  - **Sample ID** — auto-generated, sequential, format `SSP-####` (e.g. `SSP-0042`). Simple counter, not date-based — avoids collisions when multiple samples are registered the same day.
  - Sample name/type (e.g. "Fertilizer X")
  - **Received From** — who submitted the sample (new field)
  - Date received
  - Status (defaults to "Under Testing")

### 5.2 Sample Search
- Search by **Sample ID, sender name, sample name, or date** — whichever's fastest to recall
- Search result shows the full record including entered test results

### 5.3 Status Tracking
- Two-stage status: **Under Testing → Report Sent**
- Changed manually only — generating the Word report does **not**
  auto-change status, since a report might be wrong and need fixing before
  it's actually final
- Simple list view of all samples with current status

### 5.4 Test Parameters & Results
- A master list of test parameters (name + unit) — see table below — that a sample's applicable tests are selected from
- Enter a numeric/text result per selected parameter for a sample
- Master list is stored as data, not hardcoded logic, so new parameters can be added later without code changes

### 5.5 Report Generation
- Generate a **Word (.docx) report** for a sample on demand, with a table of:

  | SR. NO. | TEST PARAMETER | RESULT |
  |---|---|---|
  | 1. | Total Solids | 0.78% |
  | 2. | pH | 7.7 |
  | ... | ... | ... |

- Only includes the test parameters actually selected/entered for that sample

### 5.6 Export
- Export the full sample list to **Excel (.xlsx)** — separate from the individual Word report, for backup/sharing
- *Assumption: this means the list of samples, not a bulk export of every generated report. Confirm if something else was meant.*

### 5.7 Delete
- Deleting a sample is a **soft delete** — it moves to a "Recently Deleted" view instead of vanishing immediately
- From "Recently Deleted," a sample can be **restored** back to the main list, or **permanently deleted** (this second step is the actual point of no return)

### 5.8 Backup Protection
- On every app startup, automatically copy `lab.db` into a `backups/` folder with a timestamp, keeping only the 5 most recent copies
- A manual **"Download Backup"** button to download the current database file directly, so a copy can be kept outside the machine (USB drive, cloud folder, etc.)
- *This is the real safety net — automatic snapshots protect against in-app mistakes; the manual download protects against the machine itself failing*

## 6. Master Test Parameter List

*Seeded from what's available now; more can be added later without a code
change since this lives as data, not hardcoded logic.*

| Parameter | Unit |
|---|---|
| Total Solids (TS) | % |
| Total Suspended Solids (TSS) | mg/L |
| Total Dissolved Solids (TDS) | mg/L *(corrected from a likely typo — confirm)* |
| Moisture Content | % |
| pH | — |
| Specific Gravity | — |
| COD | mg/L |
| BOD | mg/L |
| D.E | % |
| Total Sugar | % |
| Protein | % |
| Nitrogen | % |
| Starch | % |
| Ca | % |
| Mg | mg/L *(placeholder — confirm)* |
| SO4 | mg/L *(placeholder — confirm)* |
| Cl | mg/L *(placeholder — confirm)* |
| CO3 | mg/L *(placeholder — confirm)* |
| HCO3 | mg/L *(placeholder — confirm)* |
| Na | mg/L *(placeholder — confirm)* |
| K | mg/L *(placeholder — confirm)* |

## 7. Later Phase Features (still deferred)

- Notes field (beyond Received From)
- History/audit log (who changed what, when)
- Statistics/reporting dashboard (turnaround times, volume trends, by-test breakdown)
- Role-based permissions (who can edit vs. view only)
- Notifications (e.g. sample overdue)
- Barcode/QR code generation for physical sample labeling
- PDF export of reports (Word only for now)

## 8. Non-Functional Requirements

- **Speed:** Search must return a result near-instantly (local-first data access)
- **Reliability:** No data loss — every entered sample must be persisted
- **Simplicity:** Built for lab staff, not developers — minimal clicks to log or find a sample
- **Runs locally:** Desktop-style web app, self-contained, no dependency on external cloud services for MVP *(assumption based on "runs on their computer" — confirm if this should stay fully local vs. eventually hosted)*

## 9. Success Criteria

- A sample can be registered in under 30 seconds
- A sample can be found by ID, sender, name, or date in under 5 seconds
- A Word report can be generated for a sample with correctly selected test parameters and results
- The full sample list can be exported to Excel
- Zero reliance on paper logs or manually building the Word report by hand

## 10. Open Questions

- Does "export" mean the sample list only, or should individual reports be bulk-exportable too?
- Single lab/location, or multiple locations needing separation?
- How many concurrent users initially?
- Any regulatory/compliance requirement for record retention (common in testing labs)?
