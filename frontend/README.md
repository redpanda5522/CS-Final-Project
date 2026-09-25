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

**Manual entry:** `POST /api/analyses/manual`, `application/json`:

```json
{ "locations": { "location_1": true, "location_2": false, "location_3": true, "location_4": false, "location_5": false, "location_6": false } }
```

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

- Replace illustrative `location_1`–`location_6` IDs and labels in `src/config/fields.ts` with the dataset's actual feature names. Confirm that a location is a binary yes/no feature; if the data contains coordinates, the manual UI and payload must change.
- Add any required procedure settings (including names, types, allowed ranges, units, missing-value handling) to the form and `ManualInput`. Temperature, pressure, and ablation type were discussed as possible features, but are not assumed here.
- Agree on the accepted upload formats, maximum size, file template, and backend validation error shape. The 10 MB limit and CSV/JSON/XLSX list are provisional.
- Confirm whether an analysis is one procedure/file or multiple rows, and how multiple predictions are returned. This starter assumes **one analysis per submission**.
- Set the model outcome definition and decision threshold with the ML team. The UI does not infer success from probability.
- Add authentication, server-side authorization, audit handling, upload protections, and an approved deployment environment before handling identifiable patient data. This prototype has no accounts or persistence and deliberately does not save file contents or patient information in browser storage.

Key files: `src/App.tsx` (UI), `src/api/analysis.ts` (backend boundary), `src/config/fields.ts` (location schema), `src/styles.css` (layout).
