# Ablation outcome frontend

A React + TypeScript prototype for a **postprocedure** workflow: a clinician uploads a procedure data file or enters catheter location flags, reviews the submission, and requests a model prediction from FastAPI. The browser does not convert uploaded data into model features.

## Run it

Requires Node.js 20.19+ (or 22.12+).

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open the URL printed by Vite. By default the app runs in **demo mode** and shows an explicitly labeled sample result. No uploaded file is transmitted in demo mode. Run `npm run build` to check types and produce a static build.

## Connect FastAPI

1. Change `.env.local` to `VITE_USE_MOCK_API=false` and restart Vite.
2. Run the backend on `http://localhost:8000`. Vite forwards `/api` requests there; change `vite.config.ts` if needed.
3. Implement the draft contract below or edit `src/api/analysis.ts` to match the team's agreed API.

**Upload:** `POST /api/analyses/file`, `multipart/form-data` with one field named `file` containing the original selected CSV, JSON, or XLSX. The backend validates the data, transforms it to model inputs, and predicts. The browser does not parse or transform the file.

**Manual entry:** `POST /api/analyses/manual`, `application/json`. The draft now uses exact CSV keys under `features`, not the old `locations` object:

```json
{
  "schemaVersion": "data-csv-header-v1",
  "features": {
    "la_ecg_export": 1,
    "la_navistar_connector_sensor_pos": 0,
    "temperaturesinrf_1la": null
  }
}
```

This example is abbreviated. The UI sends all 3,057 candidate keys, each as `0`, `1`, or `null` (unspecified). It excludes `id`, `recur`, and `redo`. Review permits partial entry in demo mode; live manual submission requires all candidate fields until a verified model subset or missing-value policy is implemented. The backend must update its request schema to match before integration.

Both endpoints currently expect a **draft** response:

```json
{
  "analysisId": "a1b2c3",
  "predictedOutcome": "success",
  "probability": 0.72,
  "outcomeDefinition": "No documented AF recurrence at 12 months",
  "modelVersion": "v1"
}
```

`probability` means **P(success)**, from 0 to 1. It must not be described as calibrated confidence without validation. Define the clinical outcome and follow-up period before using a concrete label in production. The response should use `predictedOutcome` values `success` or `failure`.

## Confirm before using real data

- The manual field list now comes from the supplied data.csv header: 323 rows and 3,060 unique columns. All columns other than `id` contain only 0/1 values. The 3,057 candidate inputs exclude `id`, `recur`, and `redo`; confirm their roles and model feature selection with the data/ML team. No patient rows or ID values are bundled.
- Confirm the meaning of 0/1 for every included field. Temperature and contact-force names in this CSV represent binary flags, not measured values with known units. Do not invent numeric ranges or anatomical definitions from names.
- 1,779 fields are named `v` plus a number; keep those exact keys until a dictionary maps them. Other names may be truncated or misspelled; preserve them for backend matching.
- Agree on the accepted upload formats, maximum size, file template, and backend validation error shape. The 10 MB limit and CSV/JSON/XLSX list are provisional.
- Confirm whether an analysis is one procedure/file or multiple rows, and how multiple predictions are returned. This starter assumes **one analysis per submission**.
- Set the model outcome definition and decision threshold with the ML team. The UI does not infer success from probability.
- Add authentication, server-side authorization, audit handling, upload protections, and an approved deployment environment before handling identifiable patient data. This prototype has no accounts or persistence and deliberately does not save file contents or patient information in browser storage.

## Changed files and what the form looks like

- `src/components/ManualEntry.tsx`: search box, group filter, entered-only filter, and 24 fields per page. Each exact column name has a dropdown for Unspecified, 0, or 1. Values survive paging, searching, review, and returning to edit.
- `src/config/dataset-fields.json`: all 3,057 header-derived candidate keys and name-based groups. Only header metadata, no source records.
- `src/config/fields.ts`: schema version, excluded fields, group list, null defaults, and input types. Update this and the JSON after the ML team confirms the dictionary and subset.
- `src/App.tsx`: uses the new form, reviews both 0 and 1 entries, and blocks incomplete live submissions.
- `src/api/analysis.ts`: replaces `locations` with `schemaVersion` and `features` in the manual request type.
- `src/styles.css`: styles the searchable field list and review.

Names are kept literal. Groups such as ECG flags, connector flags, temperature flags, contact-force flags, RF flags, and unmapped columns are organizational labels inferred from strings, not verified clinical definitions. This wide CSV is not yet a practical clinician-facing model schema; a reviewed subset and friendly labels are the next step.

When copying this update into an existing team repository, apply these changed files and review the diff rather than replacing unrelated teammate edits. Run `npm run build` from the frontend folder. The original uploaded CSV is not part of the download.


## Workspace pages (October update)

- `/`: dashboard with session counts, recent analyses, and New Analysis navigation.
- `/analyses/new`: existing file/manual/review/result flow, moved to `src/pages/NewAnalysis.tsx`.
- `/analyses`: searchable history with input-method filtering and empty states.
- `/analyses/:analysisId`: completed result detail with probability, outcome definition, model version, and submission summary.
- `/help`: user-facing workflow guide and FAQ.
- Unknown URLs display a not-found page.

`src/App.tsx` now owns routing, shared navigation, and session record state. `src/components/AnalysisTable.tsx` is reused on Dashboard and Analyses. `src/types/records.ts` describes summaries; `src/data/demoRecords.ts` contains fictional examples. Other pages are in `src/pages/`.

New dependencies: React Router. Run `npm install` after copying the updated `package.json` and `package-lock.json`.

Completed file or manual submissions append a summary to the session history. The New Analysis component stays mounted to preserve a draft while visiting another page. No files, manual field payloads, or summaries are stored in localStorage. Refresh clears new records and restores the demo examples when demo mode is enabled. Live mode starts with an empty history; persistent storage and retrieval remain backend tasks. Accounts/login are not implemented.

This uses BrowserRouter; a production static host must serve index.html for frontend routes. Keep `/api` routed to the backend. The Vite development server supports the frontend routes.

## Backend handoff in brief

The frontend owns file selection, form state, display validation, submission, and displaying responses/errors. It sends the original file as multipart data, or explicit manual binary values as JSON. The backend owns authoritative validation, parsing, missing-value handling, feature order/transformation, model invocation, and outcome interpretation.

The `/api/analyses/file` and `/api/analyses/manual` endpoints and existing response fields remain a proposal, not an agreement with the team's actual service. Confirm accepted file types, one-versus-many cases per file, response probability meaning, clinical target, and required manual features. For long processing jobs, replace the current synchronous response with job creation and status polling. Permanent history would require backend list/detail endpoints, which this update does not assume already exist.

Interpretation note: the supplied binary CSV may be an inventory of CARTO export files rather than actual placement or measurement values. Confirm how it was generated before using its columns as the model schema. The manual page is a provisional header-based editor.

## Applying to the team repository

Review your current git status and save local work first. This source bundle is based on the starter here; it does not contain newer edits made on your Mac. Apply the changed files individually if you have made other changes. In particular, App.tsx has been replaced by a shared shell; the submission flow has moved into pages/NewAnalysis.tsx. Review package.json/package-lock.json, styles.css, and README.md alongside the new components, data, types, and pages.

Run `npm install`, `npm run build`, and `npm run dev` inside your frontend folder. Test dashboard navigation, list search, result detail, new analysis, and Help before staging and committing.

## Interface copy cleanup

Removed development-note banners, team/schema-status bubbles, and temporary implementation notes from the pages. Demo mode and sample result labels remain visible. Outcome definition is hidden for demo fixtures and shown for real backend results. Workflow and required-field validation are unchanged.
