"""
RAAPID Sales Call Intelligence Agent - FastAPI Backend
Accepts audio files (mp3, wav, m4a, etc.) OR plain text transcripts (.txt).
"""
import json
import os
import sys
import io
import tempfile
import logging
import traceback
from pathlib import Path
from contextlib import redirect_stdout

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("raapid")

# Load .env from the project root
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Force UTF-8 stdout/stderr so Windows cp1252 doesn't break agent print() calls
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="RAAPID Sales Intelligence API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS_DIR = Path(__file__).parent / "runs"
RUNS_DIR.mkdir(exist_ok=True)

# File extensions treated as plain text (no transcription needed)
TEXT_EXTENSIONS = {".txt", ".text", ".transcript"}

# File extensions treated as audio (run through Whisper)
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac", ".wma", ".mp4"}

_whisper_model = None

def get_whisper():
    global _whisper_model
    if _whisper_model is None:
        import whisper
        _whisper_model = whisper.load_model("base")
    return _whisper_model


def is_text_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in TEXT_EXTENSIONS


def is_audio_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in AUDIO_EXTENSIONS


@app.get("/api/health")
def health():
    return {"status": "ok"}


def _supabase_request(method: str, path: str, params: dict = None):
    """Make a Supabase REST API call. Returns parsed JSON or None if not configured."""
    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not sb_url or not sb_key:
        return None
    import urllib.request, urllib.parse
    url = f"{sb_url}/rest/v1/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method=method, headers={
        "apikey":        sb_key,
        "Authorization": f"Bearer {sb_key}",
        "Content-Type":  "application/json",
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except Exception as e:
        logger.error(f"Supabase {method} {path} failed: {e}")
        return None


@app.get("/api/runs")
def get_runs():
    # Try Supabase first
    rows = _supabase_request("GET", "runs", {
        "select": "run_id,prospect_company,call_date,avg_confidence,pain_points_count,flags_count,started_at,input_type,human_review_outcome",
        "order":  "started_at.desc",
        "limit":  "50",
    })
    if rows is not None:
        return [
            {
                "run_id":            r.get("run_id", ""),
                "company":           r.get("prospect_company", "Unknown"),
                "call_date":         r.get("call_date", ""),
                "confidence":        r.get("avg_confidence", 0),
                "pain_points_count": r.get("pain_points_count", 0),
                "flags_count":       r.get("flags_count", 0),
                "started_at":        r.get("started_at", ""),
                "input_type":        r.get("input_type", "audio"),
                "outcome":           r.get("human_review_outcome", ""),
            }
            for r in rows
        ]

    # Fallback: local JSON files
    runs = []
    for f in sorted(RUNS_DIR.glob("run_*.json"), reverse=True)[:20]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            intel = data.get("intel", {})
            bant  = intel.get("bant", {})
            scores = [bant.get(k, {}).get("confidence", 0) for k in ["budget", "authority", "need", "timeline"]]
            avg_conf = round(sum(scores) / len(scores), 2) if scores else 0
            runs.append({
                "run_id":            data.get("run_meta", {}).get("run_id", ""),
                "company":           intel.get("metadata", {}).get("prospect_company", "Unknown"),
                "call_date":         intel.get("metadata", {}).get("call_date", ""),
                "confidence":        avg_conf,
                "pain_points_count": len(intel.get("pain_points", [])),
                "flags_count":       len(data.get("flags", [])),
                "started_at":        data.get("run_meta", {}).get("started_at", ""),
                "input_type":        data.get("input_type", "audio"),
                "outcome":           data.get("human_review", {}).get("outcome", ""),
            })
        except Exception:
            pass
    return runs


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    # Try Supabase first
    rows = _supabase_request("GET", "runs", {
        "select":  "*",
        "run_id":  f"eq.{run_id}",
        "limit":   "1",
    })
    if rows:
        row = rows[0]
        # Parse JSONB fields back to objects
        for field in ["stakeholders", "pain_points", "objections", "next_steps", "flags"]:
            if isinstance(row.get(field), str):
                row[field] = json.loads(row[field])
        # Rebuild structure expected by frontend
        return {
            "run_meta":     {"run_id": row.get("run_id"), "started_at": row.get("started_at")},
            "input_type":   row.get("input_type"),
            "transcript":   row.get("transcript", ""),
            "deal_summary": row.get("deal_summary", ""),
            "email_draft":  row.get("email_draft", ""),
            "flags":        row.get("flags", []),
            "human_review": {
                "required": row.get("human_review_required", False),
                "outcome":  row.get("human_review_outcome", ""),
            },
            "intel": {
                "metadata": {
                    "prospect_company": row.get("prospect_company"),
                    "call_date":        row.get("call_date"),
                    "duration_minutes": row.get("duration_minutes"),
                },
                "bant": {
                    "budget":    {"value": row.get("budget"),    "confidence": row.get("budget_confidence", 0)},
                    "authority": {"value": row.get("authority"), "confidence": row.get("authority_confidence", 0)},
                    "need":      {"value": row.get("need"),      "confidence": row.get("need_confidence", 0)},
                    "timeline":  {"value": row.get("timeline"),  "confidence": row.get("timeline_confidence", 0)},
                },
                "stakeholders":    row.get("stakeholders", []),
                "pain_points":     row.get("pain_points", []),
                "objections":      row.get("objections", []),
                "next_steps":      row.get("next_steps", []),
                "competitive_intel": {
                    "current_vendor":  row.get("current_vendor"),
                    "contract_renewal": row.get("contract_renewal"),
                    "confidence":      0,
                },
            },
        }

    # Fallback: local JSON file
    f = RUNS_DIR / f"run_{run_id}.json"
    if not f.exists():
        raise HTTPException(status_code=404, detail="Run not found")
    return json.loads(f.read_text(encoding="utf-8"))


@app.post("/api/runs/{run_id}/approve")
async def approve_run(run_id: str, request: Request):
    """
    Human approves a pending_review run.
    Body: { "bant_edits": { "budget": "...", "authority": "...", ... } }
    Updates Supabase and marks outcome as human_approved.
    """
    body = await request.json()
    bant_edits = body.get("bant_edits", {})

    update = {
        "human_review_required": False,
        "human_review_outcome":  "human_approved",
    }
    for field, value in bant_edits.items():
        if field in ("budget", "authority", "need", "timeline"):
            update[field] = value

    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not sb_url or not sb_key:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    import urllib.request as _urllib
    payload = json.dumps(update).encode("utf-8")
    req = _urllib.Request(
        f"{sb_url}/rest/v1/runs?run_id=eq.{run_id}",
        data=payload, method="PATCH",
        headers={
            "Content-Type":  "application/json",
            "apikey":        sb_key,
            "Authorization": f"Bearer {sb_key}",
            "Prefer":        "return=representation",
        }
    )
    try:
        with _urllib.urlopen(req) as resp:
            updated = json.loads(resp.read())
        return {"status": "approved", "run_id": run_id, "updated": updated}
    except Exception as e:
        logger.error(f"Approve failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/runs/{run_id}/reject")
async def reject_run(run_id: str):
    """AE rejects a pending_review run — marks outcome as human_rejected, no CRM push."""
    sb_url = os.environ.get("SUPABASE_URL")
    sb_key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not sb_url or not sb_key:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    import urllib.request as _urllib
    payload = json.dumps({
        "human_review_required": False,
        "human_review_outcome":  "human_rejected",
    }).encode("utf-8")
    req = _urllib.Request(
        f"{sb_url}/rest/v1/runs?run_id=eq.{run_id}",
        data=payload, method="PATCH",
        headers={
            "Content-Type":  "application/json",
            "apikey":        sb_key,
            "Authorization": f"Bearer {sb_key}",
            "Prefer":        "return=representation",
        }
    )
    try:
        with _urllib.urlopen(req) as resp:
            updated = json.loads(resp.read())
        return {"status": "rejected", "run_id": run_id, "updated": updated}
    except Exception as e:
        logger.error(f"Reject failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    filename = file.filename or "upload.wav"
    suffix = Path(filename).suffix.lower()
    content = await file.read()

    # ── Determine input type and get transcript ──────────────────────────────

    if is_text_file(filename):
        # Plain text — decode and use directly, no Whisper needed
        try:
            transcript = content.decode("utf-8").strip()
        except UnicodeDecodeError:
            transcript = content.decode("latin-1").strip()
        input_type = "text"

    elif is_audio_file(filename):
        # Audio — write to temp file and transcribe with Whisper
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            whisper_model = get_whisper()
            result = whisper_model.transcribe(tmp_path)
            transcript = result["text"].strip()
        finally:
            os.unlink(tmp_path)
        input_type = "audio"

    else:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Upload an audio file (mp3, wav, m4a) or a text transcript (.txt)."
        )

    # ── Validate transcript ──────────────────────────────────────────────────

    if len(transcript) < 100:
        raise HTTPException(
            status_code=422,
            detail="Transcript too short. Please upload a longer recording or transcript."
        )

    # ── Run agent ────────────────────────────────────────────────────────────

    sys.path.insert(0, str(Path(__file__).parent))
    from agent import SalesCallAgent

    try:
        live = bool(os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))
        agent = SalesCallAgent(transcript, demo_mode=not live)
        agent.results["input_type"] = input_type
        with redirect_stdout(io.StringIO()):
            agent.run()
    except Exception as e:
        logger.error("Agent failed:\n" + traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

    results = dict(agent.results)
    results["transcript"] = transcript
    results["input_type"] = input_type

    # ── Persist run ──────────────────────────────────────────────────────────

    try:
        run_id = results.get("run_meta", {}).get("run_id", "unknown")
        run_file = RUNS_DIR / f"run_{run_id}.json"
        run_file.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    except Exception as e:
        logger.error("Failed to persist run:\n" + traceback.format_exc())

    return results


# Serve React frontend (must be last)
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
