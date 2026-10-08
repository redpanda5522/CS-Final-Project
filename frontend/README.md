# Ablation outcome frontend

React + TypeScript frontend for a postprocedure workflow: upload a procedure file or assign up to four catheters to heart regions, enter optional measurements, review, and submit for backend processing.

## Run

```bash
npm install
cp .env.example .env.local
npm run dev
```

Open the URL printed by Vite. Demo mode returns a labeled illustrative result and sends no data to the backend. `npm run build` checks types and builds the app. Set `VITE_USE_MOCK_API=false` and restart Vite for live requests. Vite proxies `/api` to `http://localhost:8000`.

## Region input

Manual entry requires a region for each catheter, not coordinates. Click a shaded region, use the short-code buttons, or select the full name in the dropdown. The numbered catheter attaches to a fixed display anchor for the selected region. The four-catheter maximum is enforced by the add control and payload validation. Multiple catheters may share a region. Temperature and pressure/contact force are optional; units apply to all catheters and changing units does not convert values.

Displayed regions: left/right atrium (LA/RA), left/right superior/inferior pulmonary veins (LSPV/LIPV/RSPV/RIPV), and superior/inferior vena cava (SVC/IVC). The illustration is educational, and overlay boundaries and catheter anchors are approximate. They are not patient-specific geometry or measured catheter coordinates.

The bundled diagram is **Heart diagram-en.svg by ZooFari**, via Wikimedia Commons, under CC BY-SA 3.0. Credit and license links appear beside the diagram; full source and adaptation terms are in `public/images/ATTRIBUTION.md`. The bundled SVG hides the original labels and connector lines; colored interactive overlays and catheter annotations are added in the UI.

## CSV interpretation

The supplied CSV header has 3,060 columns. Following the meeting instruction, a column matching `V` + digits (case-insensitive) joins the closest non-V column to its left, continuing until another named column appears. Example:

- `la_ecg_export`, `v3` → named group `la_ecg_export`.
- `la_cs_connector_eleclectrode_pos`, `v9` through `v14` → one named group.

Excluding `id`, `recur`, and `redo`, 3,057 input columns become **1,278 named groups**, including **1,779 V variations**. The generated mapping is in `src/config/column-groups.json`; only header metadata is included, never source records.

The collapse rule for binary indicators is **any 1 → 1; all 0 → 0; otherwise null (unspecified)**. This is a lossy presence summary, not a count, coordinate, mean, or reconstructed feature array. It follows the meeting's interpretation, which is not proven by the CSV values alone. Do not expand a region selection back into invented V flags. Confirm the aggregation and model input contract with the ML team.

Recognized location prefixes are associated with eight display regions. LA-related names (`la`, `la2`, `la3`, `lae`, `laedit`, `lafam`, `laf`, `lapre`, `las`, `lasound`, `lasou`) are provisionally associated with LA; `ra` and `rafam` with RA; exact pulmonary-vein and vena-cava prefixes with their matching region. These broader associations are provisional display choices. 695 named groups are mapped; 583 remain unmapped, including ambiguous labels such as `ls`, `li`, `rs`, `ri`, `tsp`, and nonregional settings. No anatomy is invented for these groups. Review associations in `src/config/regions.ts` and `column-groups.json` when the dictionary becomes available.

CSV upload previews collapse binary values per row, show recognized region flags on the diagram, and expose active named groups and unmapped groups in expandable details. Row selection does not reveal IDs or outcome columns. Shading indicates a recorded flag, not a detected catheter count. The four-catheter limit applies to manual entries; a dataset row can have flags for more than four regions and is not truncated. JSON/XLSX uploads have no region preview. Invalid/nonbinary CSV previews show a message but the original file can still be submitted for backend validation.

## Backend contract

**Start with [the backend handoff guide](docs/backend-handoff.md)** for exact requests, responses, error handling, local integration steps, and unresolved ML decisions. The current browser flow expects one synchronous prediction per submission; a multirow file workflow still needs agreement.

**File:** `POST /api/analyses/file`, multipart field `file`, containing the original CSV/JSON/XLSX file, unchanged. The browser's region preview never replaces the uploaded file. Current size limit: 10 MB.

**Manual:** `POST /api/analyses/manual`, JSON:

```json
{
  "schemaVersion": "catheter-regions-v2",
  "groupingVersion": "left-named-column-v1",
  "units": { "temperature": "C", "pressure": "g" },
  "catheters": [
    { "id": "catheter-uuid", "regionId": "la", "temperature": 37, "pressure": 12 }
  ]
}
```

This **replaces the earlier coordinate-based and binary-feature manual schemas**. No X/Y fields are sent. The backend must accept region IDs and enforce the 1–4 limit. Optional measurements are numbers or null. Temperature units: `unspecified`, `C`, `F`. Pressure units: `unspecified`, `g` (contact force), `mmHg`, `kPa`. Force and pressure are distinct quantities and must not be converted interchangeably.

The backend owns authoritative validation, formatting, missing-value policy, feature ordering, and ML invocation. `src/data/regionGrouping.ts` supplies the preview grouping logic; `column-groups.json` supplies the complete named-to-V mapping for a backend implementation. The frontend does not assume region data already matches the trained model.

Both endpoints currently expect:

```json
{
  "analysisId": "analysis-id",
  "predictedOutcome": "success",
  "probability": 0.72,
  "outcomeDefinition": "Agreed clinical outcome and follow-up period",
  "modelVersion": "v1"
}
```

`probability` is P(success), from 0 to 1. Define the clinical target, follow-up period, decision threshold, accepted files, and one-versus-many predictions before live integration. Account/authentication and permanent history are not implemented.

## Files and pages

- `src/components/ManualEntry.tsx`: region selection and four-catheter editor.
- `src/components/AtriaPlot.tsx`: sourced heart image, region overlays, attached catheter labels.
- `src/components/DatasetPreview.tsx`: CSV row/group preview.
- `src/config/regions.ts`: display regions, contours, anchors, grouping version.
- `src/config/column-groups.json`: exact named-group membership and provisional display association.
- `src/data/regionGrouping.ts`: CSV parsing, left-column grouping, binary collapse and region presence summaries.
- `src/types/procedure.ts`: manual state, cap/measurement validation, new payload.
- `src/pages/NewAnalysis.tsx`: input/review/result flow and API handoff.
- `src/api/analysis.ts`, `src/styles.css`, `src/pages/Help.tsx`: API types, styling and instructions.
- `package.json` / lockfile: Papa Parse added for CSV parsing.

Routes: `/` dashboard; `/analyses/new` submission; `/analyses` session history; `/analyses/:analysisId` result details; `/help` instructions. Drafts survive navigation. History and drafts live in memory; refresh clears new entries. No patient data is saved in localStorage. Production hosting must serve index.html for frontend routes and keep `/api` routed to the backend.

## Apply changes to your repository

This package contains the starter edited here, not newer edits made on your Mac. Review `git status` before copying. Apply changed files individually when needed, preserving teammates' changes. Run `npm install`, `npm run build`, then `npm run dev`. Check region selection, the catheter cap, review, upload preview, and navigation before staging and reviewing the diff. The source CSV is not bundled.
