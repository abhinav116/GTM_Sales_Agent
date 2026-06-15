# GTM Sales Call Intelligence Agent

A full-stack agentic AI pipeline that ingests sales call transcripts, extracts structured deal intelligence using an LLM, scores confidence, and routes runs through a three-tier human review workflow before pushing to CRM.

Built as a take-home assignment for the **Agentic AI Manager** role at RAAPID INC.

---

## What It Does

1. Upload a sales call transcript (audio or `.txt`)
2. The agent extracts BANT fields, stakeholders, pain points, objections, and next steps
3. Confidence is scored per field and averaged across the run
4. The run is routed based on a three-tier confidence gate:
   - **≥ 0.8** → Auto-approved, CRM push triggered
   - **0.5 – 0.79** → Routed to AE review queue
   - **< 0.5** → Auto-rejected, nothing reaches CRM
5. AE can inspect flagged fields, edit values, and approve or reject from the UI
6. All runs are persisted to Supabase and visible in the Previous Runs dashboard

---

## Stack

| Layer | Technology |
|---|---|
| LLM | Groq (LLaMA 3.3-70b) via OpenAI-compatible client |
| Backend | FastAPI + Python |
| Transcription | OpenAI Whisper (for audio uploads) |
| Frontend | React + Vite |
| Database | Supabase (PostgreSQL via REST API) |
| Prompt versioning | Single `prompts/prompt.v1.txt` with section headers |

---

## Project Structure

```
raapid_agent/
├── agent.py                  # 9-step intelligence pipeline
├── backend.py                # FastAPI server
├── prompts/
│   └── prompt.v1.txt         # System, extraction, summary, email prompts
├── runs/                     # Local JSON fallback for run persistence
├── sample-transcripts/       # 10 sample transcripts with varying confidence
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── UploadPage.jsx
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── RunsPage.jsx
│   │   │   └── ReviewPage.jsx
│   │   └── components/
│   │       └── Sidebar.jsx
│   └── dist/                 # Built frontend served by FastAPI
├── supabase_schema.sql       # Supabase table definition
├── package.json              # Root-level dev runner (concurrently)
└── .env                      # API keys (not committed)
```

---

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/abhinav116/GTM_Sales_Agent.git
cd GTM_Sales_Agent
```

### 2. Create a `.env` file

```
GROQ_API_KEY=your_groq_api_key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key
```

Get a free Groq API key at [console.groq.com](https://console.groq.com).

### 3. Install Python dependencies

```bash
pip install fastapi uvicorn python-dotenv openai whisper
```

### 4. Install frontend dependencies

```bash
npm install
cd frontend && npm install && cd ..
```

### 5. Set up Supabase

Run `supabase_schema.sql` in your Supabase SQL editor to create the `runs` table.

---

## Running the App

### Development (both servers together)

```bash
npm run dev
```

This starts:
- Backend: `http://localhost:8000`
- Frontend: `http://localhost:5173`

### Production

```bash
cd frontend && npm run build && cd ..
uvicorn backend:app --port 8000
```

The built frontend is served statically by FastAPI at `http://localhost:8000`.

---

## Agent Pipeline

| Step | Description |
|---|---|
| 1 | Input validation — reject transcripts under 100 characters |
| 2 | Load prompt from `prompts/prompt.v1.txt` |
| 3 | LLM extraction — BANT, stakeholders, pain points, objections, next steps |
| 4 | Confidence scoring — average across BANT fields |
| 5 | Three-tier gate — auto-approve / review queue / auto-reject |
| 6 | Deal summary generation |
| 7 | Follow-up email draft |
| 8 | Supabase persist |
| 9 | Return results to frontend |

---

## Three-Tier Confidence Gate

| Confidence | Outcome | CRM | Email |
|---|---|---|---|
| ≥ 0.8 | Auto Approved | Written | Generated |
| 0.5 – 0.79 | Human Review Required | Blocked until AE approves | Blocked |
| < 0.5 | Auto Rejected | Blocked | Blocked |

After AE review, outcome is either **Approved after Review** or **Rejected after Review**.

---

## Guardrails

- **No fact invention** — extraction-only system prompt; agent cannot surface anything not in the transcript
- **Confidence gate** — three-tier routing prevents low-confidence data from reaching CRM
- **JSON schema enforcement** — up to 3 retries on parse failure; run halts if all fail
- **HITL** — AE owns the final approve/reject decision on all review-queue runs
- **No PHI** — agent operates exclusively on sales call transcripts

---

## Sample Transcripts

Ten sample transcripts are included in `sample-transcripts/` covering the full confidence range:

| File | Company | Expected Confidence |
|---|---|---|
| 01_humana... | Humana | ~95% |
| 02_caremore... | CareMore | ~78% |
| 03_scott_white... | Scott & White | ~65% |
| 04_friday_health... | Friday Health | ~52% |
| 05_anthem... | Anthem | ~92% |
| 06_independence... | Independence BC | ~70% |
| 07_kaiser... | Kaiser | ~60% |
| 08_wellcare... | WellCare | ~40% |
| 09_elevance... | Elevance | ~55% |
| 10_molina... | Molina | ~20% |

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/runs` | List all runs |
| GET | `/api/runs/{run_id}` | Get single run detail |
| POST | `/api/analyze` | Upload and analyze transcript |
| POST | `/api/runs/{run_id}/approve` | AE approves a review-queue run |
| POST | `/api/runs/{run_id}/reject` | AE rejects a review-queue run |

---

## Assignment Context

This project is **Task 1** of the RAAPID Agentic AI Manager take-home assignment.

- **Task 1**: Build a functioning agentic workflow (this repo)
- **Task 2**: Agentic AI Product Vision Memo (separate document)

Architecture note and product vision memo are available separately.
