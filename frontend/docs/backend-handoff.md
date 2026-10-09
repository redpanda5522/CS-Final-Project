# Frontend ↔ backend handoff

This is the current **proposed v1 HTTP contract** implemented by the frontend. The shared [integration discussion](https://chatgpt.com/share/6ac7e75a-7bb4-83ea-a8b4-7c5b7a6f2746) describes the same two-endpoint plan. Agree on the open ML questions below before treating either request as a valid model input.

## What runs where

- The frontend owns input controls, basic validation, loading/error UI, and rendering the returned prediction. Its request code is in [`src/api/analysis.ts`](../src/api/analysis.ts); its manual serializer is in [`src/types/procedure.ts`](../src/types/procedure.ts).
- The backend owns both `/api/analyses/*` endpoints, authoritative validation, file parsing, feature construction in the trained model's exact order, model invocation, and response generation.
- GitHub shares the code and this contract. At runtime the browser sends an HTTP request to the backend; no input data is sent through GitHub.
- The frontend currently expects a **synchronous JSON result** for each request. There is no job polling, authentication, or persistent history API. Analyses shown in the UI exist only until page refresh.

## File submission

`POST /api/analyses/file` with `multipart/form-data`. The single form field is named **`file`** and contains the original uploaded bytes and filename. The browser does not send its CSV preview, chosen preview row, region summary, or a converted feature vector. Do not require any of those fields from this endpoint.

The UI accepts `.csv`, `.json`, and `.xlsx`, with nonempty files up to **10 MiB (10,485,760 bytes)**. This is a provisional product limit; the backend must enforce its own size and content checks. A file's extension alone does not prove its format. If a format or shape is unsupported by the model pipeline, return a clear 4xx error.

Example request (with a file containing non-sensitive test data):

```bash
curl -i -F 'file=@sample.csv' http://localhost:8000/api/analyses/file
```

## Manual submission

`POST /api/analyses/manual` with `Content-Type: application/json`. Exact example:

```json
{
  "schemaVersion": "catheter-regions-v2",
  "groupingVersion": "left-named-column-v1",
  "units": { "temperature": "C", "pressure": "g" },
  "catheters": [
    { "id": "550e8400-e29b-41d4-a716-446655440000", "regionId": "la", "temperature": 37, "pressure": 12 },
    { "id": "550e8400-e29b-41d4-a716-446655440001", "regionId": "ra", "temperature": null, "pressure": null }
  ]
}
```

`catheters` is an ordered array of **1–4** items. Each `id` is a client-generated UUID for distinguishing entries; it is not a database record ID. `regionId` must be one of `la`, `ra`, `lspv`, `lipv`, `rspv`, `ripv`, `svc`, `ivc`. Multiple catheters may use the same region. Each measurement is a finite JSON number or `null` when blank; pressure/contact force cannot be negative. Units apply to the whole array: temperature is `unspecified`, `C`, or `F`; pressure is `unspecified`, `g`, `mmHg`, or `kPa`. `g` means contact force, while `mmHg` and `kPa` mean pressure. Do not silently convert force into pressure. The frontend allows a numeric measurement with an `unspecified` unit; the backend/ML team must decide whether to accept or reject that case. No image coordinates or raw CSV `V` flags are sent.

The frontend rejects missing regions, more than four catheters, nonnumeric measurements, and negative pressure. The backend must validate these again; callers can bypass the UI. Reject unknown schema/grouping versions and region IDs explicitly.

Example request:

```bash
curl -i http://localhost:8000/api/analyses/manual \
  -H 'Content-Type: application/json' \
  --data-binary '{"schemaVersion":"catheter-regions-v2","groupingVersion":"left-named-column-v1","units":{"temperature":"C","pressure":"g"},"catheters":[{"id":"550e8400-e29b-41d4-a716-446655440000","regionId":"la","temperature":37,"pressure":12}]}'
```

## Response and errors

Both endpoints return HTTP `200` and one JSON object:

```json
{
  "analysisId": "analysis-123",
  "predictedOutcome": "success",
  "probability": 0.72,
  "outcomeDefinition": "The agreed clinical outcome and follow-up period",
  "modelVersion": "v1"
}
```

`analysisId` and `outcomeDefinition` must be nonempty strings. `predictedOutcome` is exactly `success` or `failure`; `probability` is a finite number in `[0, 1]` and means **P(success)**, not confidence that the predicted class is correct. `modelVersion` is optional and, when present, a string. Return `Content-Type: application/json`. The UI rejects malformed responses.

For a validation or processing failure, return an appropriate 4xx/5xx status and a JSON `detail` string, for example `{"detail":"Unsupported file format"}`. FastAPI's standard `detail` array with `msg` fields is also displayed. Do not return a successful-looking prediction if parsing or feature construction fails. The frontend keeps the user on the review step and displays the error.

## Local integration check

1. Start the backend at `http://localhost:8000` with both routes. A fixed test response with the shape above is enough for the first connection check.
2. In `frontend/.env.local`, set `VITE_USE_MOCK_API=false`; restart Vite after changing it.
3. Run `npm install` and `npm run dev` from `frontend/`. Vite proxies `/api` to port 8000; browser requests use same-origin relative URLs, so local CORS configuration is unnecessary through the proxy.
4. Submit one manual entry and one test file. Confirm the backend receives the exact JSON or original file, and the UI displays the test response. Then submit an invalid request and confirm the error appears in the UI.
5. For deployment, route `/api/*` to the backend and all frontend routes to `index.html`, or agree on a new API base URL and update `src/api/analysis.ts`.

## Decisions to settle with the ML team

- Define `success` and `failure`, follow-up period, threshold for `predictedOutcome`, and whether `probability` is calibrated.
- Decide whether one file means **one procedure** or a **batch of rows**. The current UI and response support one prediction per upload. A batch requires a different response and result screen.
- Specify accepted CSV/JSON/XLSX schemas and whether `id`, `recur`, or `redo` are permitted in uploaded data. The CSV preview only summarizes region flags; it is not the model parser.
- Define how manual region IDs and optional measurements map to trained features. The frontend cannot infer thousands of raw `V` flags or invent missing features. [`src/config/column-groups.json`](../src/config/column-groups.json) is a grouping reference, not a validated feature specification.
- Resolve missing measurement and unspecified-unit policies, and whether force and pressure need separate model fields.

Until these decisions are made, a fixed backend test response proves the transport and UI integration only; it does not validate the clinical or ML prediction pipeline.
