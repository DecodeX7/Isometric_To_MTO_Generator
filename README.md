# Isometric Drawing to Automated MTO Generator

A full-stack AI engineering assessment project that converts **one piping isometric drawing** (`PNG`, `JPG`, or `PDF`) into a structured **Material Take-Off (MTO)** using a FastAPI backend, a pluggable Gemini vision pipeline, and a Next.js frontend.

The app is intentionally designed so evaluators can run it without an AI key. If `GEMINI_API_KEY` is missing, the backend returns a clearly labelled mock MTO while keeping the full upload → process → table → CSV flow working.

---

## 1. Project overview + architecture

```text
+----------------------+         multipart upload         +----------------------+
|                      |  POST /api/upload -> {job_id}   |                      |
|   Next.js Frontend   +--------------------------------->+   FastAPI Backend    |
|   App Router + TS    |                                  |   Python + Pydantic  |
|                      |  GET /api/mto/{job_id}           |                      |
|  - drag/drop upload  +<---------------------------------+  - file validation   |
|  - drawing preview   |                                  |  - job store         |
|  - MTO table         |  GET /api/mto/{job_id}/csv       |  - CSV export        |
|  - CSV export        +<---------------------------------+  - Swagger /docs     |
+----------+-----------+                                  +----------+-----------+
           |                                                         |
           |                                                         v
           |                                           +--------------------------+
           |                                           | AI Extraction Pipeline   |
           |                                           |                          |
           |                                           | 1. PDF/image normalize   |
           |                                           | 2. Gemini vision prompt  |
           |                                           | 3. Gemini JSON output    |
           |                                           | 4. Pydantic validation   |
           |                                           | 5. MTO post-processing   |
           |                                           | 6. Mock fallback         |
           |                                           +--------------------------+
```

### Main design choice

The backend uses an **asynchronous job-style API**:

- `POST /api/upload` creates a job and starts processing in the background.
- `GET /api/mto/{job_id}` lets the frontend poll for status and result.
- `GET /api/mto/{job_id}/csv` exports the validated MTO.

This is slightly more code than a single synchronous `/extract` endpoint, but it represents the real workflow better because vision AI calls can be slow, fail, or be replaced later by a queue worker.

---

## 2. Exact setup steps

### Version requirements

- Python: **3.11+**
- Node.js: **20+** recommended
- npm: **10+** recommended

### Step A: clone/unzip the project

```bash
unzip Saurabh_Prajapati_isometric_mto.zip
cd isometric_mto_project
```

### Step B: environment variables

Create `.env` from the sample file:

```bash
cp .env.example .env
```

For mock mode, no changes are required.

For live Gemini extraction, edit `.env` and set:

```env
GEMINI_API_KEY=your_google_ai_studio_key_here
GEMINI_MODEL=gemini-2.5-flash-lite
USE_MOCK_PIPELINE=false
FALLBACK_TO_MOCK_ON_LLM_ERROR=true
AI_JOB_TIMEOUT_SECONDS=420
```

`gemini-2.5-flash-lite` is recommended for dense scanned assessment PDFs because it usually responds faster. You can switch to `gemini-2.5-flash` if you want a stronger but sometimes slower extraction run.

### Step C: run backend

```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1

# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Open FastAPI docs:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/api/health
```

### Step D: run frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

### Step E: run backend tests

```bash
cd backend
pytest -q
```

### Step F: test the company scanned PDF

A company-style marked scanned isometric sample is included at:

```text
samples/company_marked_isometric.pdf
```

For live Gemini testing, use the `.env` values shown above and keep the backend terminal open so you can see any Gemini/API error details.

---

## 3. Environment variables

See `.env.example`.

| Variable | Required | Default | Purpose |
|---|---:|---|---|
| `GEMINI_API_KEY` | No | empty | Google AI Studio key. If absent, mock pipeline is used. |
| `GEMINI_MODEL` | No | `gemini-2.5-flash-lite` | Vision model name. Flash-Lite is recommended for faster assessment/demo runs. |
| `USE_MOCK_PIPELINE` | No | `false` | Force mock extraction even if an API key exists. |
| `FALLBACK_TO_MOCK_ON_LLM_ERROR` | No | `true` | If Gemini fails, return a labelled mock result instead of crashing. |
| `AI_JOB_TIMEOUT_SECONDS` | No | `420` | Hard timeout for live AI extraction jobs. Dense scanned drawings can take several minutes. |
| `MAX_UPLOAD_SIZE_MB` | No | `20` | Server-side upload size limit. |
| `NEXT_PUBLIC_API_BASE_URL` | No | `http://localhost:8000/api` | Frontend API base URL. |

No real API key is committed.

---

## 4. How the AI pipeline works

The pipeline code lives in:

```text
backend/app/pipeline/
```

### 4.1 Pre-processing

`preprocess.py` converts all supported inputs into an optimized **multi-view image packet** for Gemini:

- `PNG` / `JPG` files are opened with Pillow.
- `PDF` files are rendered from page 1 using PyMuPDF at higher resolution.
- Scanner whitespace is cropped automatically.
- A full enhanced page is generated for overall context.
- A blue-grid-suppressed view is generated for marked/scanned isometrics drawn on graph paper.
- A title/header crop is generated for metadata.
- The image packet is kept compact so the live Gemini call is less likely to time out.

This optimization was added because dense scanned assessment PDFs can time out if the model receives only one noisy full-page image. The drawing dimensions are **not measured from pixels** because piping isometrics are not to scale. Lengths must come from dimension text or the BOM table.

### 4.2 Extraction

`gemini_pipeline.py` sends the optimized image views and prompt to Gemini. It first uses JSON MIME mode for a fast structured extraction. If that fails, it retries with the stored JSON schema.

The prompt is stored in:

```text
backend/app/pipeline/prompt.py
```

The prompt tells the model to behave like a piping MTO engineer and to extract:

- title block metadata: drawing number, revision, line number, NPS, material class, service
- MTO rows: pipe, fittings, flanges, valves, gaskets, bolts, supports
- engineering fields: size, schedule/rating, material spec, end type, quantity, unit, length, remarks, confidence

### 4.3 Structured output schema

The JSON schema is stored in `prompt.py` and the prompt includes the exact output structure. The pipeline uses Gemini JSON output and can retry with schema-guided output. The output is validated again using Pydantic models in:

```text
backend/app/models/mto.py
```

The application does **not** trust free-text LLM output directly. It follows this path:

```text
Vision LLM JSON -> Pydantic validation -> post-processing -> API response
```

### 4.4 Post-processing and derived items

`postprocess.py` normalizes and enriches the extracted MTO:

- categories are normalized to uppercase engineering families
- item numbers are re-numbered safely
- pipe length is summarized in metres
- counts are computed by category
- if flanged components are found but gasket/bolt rows are missing, gasket and stud-bolt rows are added using a transparent heuristic

Heuristic used:

```text
flanged_joint_count = max(number of flange items, number of flanged valve items × 2)
```

This is conservative for an assessment project and is explained in `remarks` on derived rows.

### 4.5 Mock fallback

If no Gemini key is configured, the backend uses `mock_pipeline.py`. This returns a realistic sample MTO with:

- pipe by length
- fittings by count
- flanges and valve
- gasket and bolt sets
- title block metadata
- confidence values
- warnings explaining that the result is a mock fallback

This makes the complete evaluation flow runnable on a fresh machine.

---

## 5. Assumptions and known limitations

### Assumptions

1. The app processes **one isometric per upload**.
2. For PDFs, only the **first page** is processed. Multi-sheet PDF processing is a possible bonus extension.
3. The drawing contains readable text for dimensions, BOM, and title block.
4. Pipe length is extracted from dimension text/BOM, not from pixel geometry.
5. If the BOM table exists, the prompt asks the model to prefer BOM rows over symbol counting.
6. Gasket and bolt-set derivation is heuristic and marked in remarks.

### Known limitations

- Dense isometrics may have overlapping callouts and rotated text that a vision model can miss.
- Hand-drawn or low-resolution scans may reduce extraction accuracy.
- Vision LLMs may confuse similar symbols such as globe/check/gate valves without a clear legend.
- The mock fallback is for engineering flow demonstration, not real extraction accuracy.
- In-memory job storage is fine for this assessment but would not survive server restart.
- BackgroundTasks are acceptable here; production should use Redis/Celery/RQ or a durable queue.

---

## 6. What I would improve with more time

1. Add OCR-first BOM table extraction using PaddleOCR or Tesseract, then reconcile it with Gemini symbol extraction.
2. Add bounding-box overlays for detected symbols and title-block fields.
3. Add Excel export with formatted worksheets.
4. Add multi-page PDF and multi-sheet job processing.
5. Add human-in-the-loop correction UI for low-confidence rows.
6. Add persistent storage with SQLite/Postgres.
7. Add confidence visualization per item and per drawing region.
8. Add a production queue worker and object storage for uploaded drawings.
9. Add automated comparison tests against labelled sample isometrics.

---

## 7. API contract

### `GET /api/health`

Returns backend status and selected pipeline.

### `POST /api/upload`

Accepts one multipart file.

Allowed:

- `image/png`
- `image/jpeg`
- `application/pdf`

Rejects files larger than `MAX_UPLOAD_SIZE_MB`.

Response:

```json
{
  "job_id": "uuid",
  "status": "queued"
}
```

### `GET /api/mto/{job_id}`

Response while processing:

```json
{
  "job_id": "uuid",
  "status": "processing",
  "filename": "sample.png",
  "result": null,
  "error": null
}
```

Response when completed:

```json
{
  "job_id": "uuid",
  "status": "completed",
  "filename": "sample.png",
  "result": {
    "drawing_meta": {},
    "items": [],
    "summary": {},
    "extraction_info": {}
  },
  "error": null
}
```

### `GET /api/mto/{job_id}/csv`

Downloads the MTO items as CSV.

---

## 8. Repository structure

```text
isometric_mto_project/
├── README.md
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/routes/
│   │   ├── core/
│   │   ├── models/
│   │   ├── pipeline/
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/
│   ├── components/
│   ├── lib/
│   ├── package.json
│   └── Dockerfile
├── samples/
│   ├── sample_isometric_01.png
│   └── sample_isometric_02.png
└── screenshots/
    ├── app_upload.png
    └── app_results.png
```

---

## 9. Submission packaging

The submitted ZIP excludes:

- `node_modules/`
- `.next/`
- `dist/`
- `venv/` / `.venv/`
- `__pycache__/`
- `.git/`
- real API keys

## 10. Demo

**Made by:** Saurabh Prajapati  
**Email:** saurabhcsecsvtu@gmail.com
**Demo Video:** https://youtu.be/mYAcE7cPuOo  

The main design principle of this project is that the LLM is not treated as a complete solution by itself. Instead, it is wrapped inside an engineering pipeline: input validation, image/PDF preprocessing, structured prompting, schema validation, post-processing, fallback handling, and user-facing export. This makes the system easier to debug, explain, and extend.
