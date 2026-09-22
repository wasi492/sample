# Design.md — Sample Tracking System

*Visual direction inspired by professional LIMS-style tools (sidebar nav +
clean data views), adapted to our actual page set: List, Register, Search,
Sample Detail, Recently Deleted.*

## 1. Color Palette

| Role | Color | Use |
|---|---|---|
| Sidebar background | Near-black `#0b0d0f` | Left navigation rail |
| Accent strip | Steel blue `#6ba0cc` | Top bar accent / page header band |
| Primary action | Muted blue `#648faf` | Buttons: Save, Register, Generate Report |
| Secondary | Light blue `#a5c1d9` | Secondary elements, hover states |
| Page background | Off-white `#f9fafb` | Main content area |
| Card/panel background | White `#FFFFFF` | Tables, forms, detail panels |
| Text (primary) | Near-black `#0b0d0f` | Body text, headers |
| Text (muted) | Grey `#5f6b78` | Labels, secondary info, timestamps |
| Status: Under Testing | Amber `#E0A93E` | Status pill |
| Status: Report Sent | Green `#4CAF6D` | Status pill |
| Danger | Muted red `#D64545` | Delete / permanent delete only |

*Palette sourced from Realtime Colors. Near-black sidebar with cool blue
accents — professional, calm, and highly readable.*

## 2. Typography

- **Font:** Noto Sans Glagolitic (loaded via Google Fonts), with system sans-serif fallback (`-apple-system, "Segoe UI", Roboto, sans-serif`).
- **Scale:** 3 sizes only
  - Page title: 22px, semi-bold
  - Section headers (e.g. "Test Results", "Sample Info"): 16px, semi-bold
  - Body/table text: 14px, regular
- No all-caps labels. Sentence case throughout ("Received from", not "RECEIVED FROM").

## 3. Layout

```
┌──────┬─────────────────────────────────────────┐
│      │  [Coral accent strip: page title]        │
│ Side │─────────────────────────────────────────│
│ nav  │                                           │
│      │   Main content area (white/off-white)    │
│ (📋  │   - Sample list table, OR                │
│  🔍  │   - Register form, OR                    │
│  🗑)  │   - Sample detail panel                  │
│      │                                           │
└──────┴─────────────────────────────────────────┘
```

- **Sidebar (left, ~64px collapsed or ~200px with labels):** icons/links for List, Register, Search, Recently Deleted, Backup. Indigo background, white icons/text.
- **Top strip:** thin coral band with the current page name — gives every page a clear identity, echoes the reference without copying a specific product's branding.
- **Main content:** left-aligned, generous padding (24px), one column — this is a data tool, not a marketing page, so no centered hero treatment.

## 4. Components

- **Buttons:** solid indigo background, white text, small radius (4px, not fully rounded pill-shaped). Label states the action: "Save Results," "Generate Report," "Delete." Danger actions (permanent delete) use the muted red instead.
- **Tables:** thin `#E5E5EA` row dividers, no heavy borders, comfortable row height (~44px) so it's easy to scan a list of samples. Header row: muted grey text, semi-bold, sentence case.
- **Status pills:** small rounded-rect badges using the status colors above, not plain text — makes scanning the list for "what's still Under Testing" fast.
- **Forms:** labels above inputs (not inline placeholders as the only label — placeholders disappear once you start typing, which is bad for a data-entry tool where someone might get interrupted mid-form).
- **Empty states** (e.g. no search results, no deleted samples): a plain sentence explaining the state, no illustration — keep it functional.

## 5. What we're deliberately not doing

- No dashboard charts/graphs (that reference screenshot's bar charts and pie charts are for a bigger analytics product — out of scope here, and explicitly deferred in PRD.md's stats/reporting item)
- No card-grid layout for the sample list — a table is the correct structure for this data, not cards
- No gradients, drop shadows on every element, or decorative icons beyond the sidebar nav
