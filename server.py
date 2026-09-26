# server.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import json
import os
import shutil
import signal
import subprocess
import sys

from code_analyzer import build_code_knowledge_base
from code_relations import extract_relations

app = FastAPI()

# allow the HTML viewer (running in browser) to call this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory shared state
state = {
    "transcript_log": [],      # list of {time, text}
    "current_location": None,
    "events": []                # list of comment events, in order, for the frontend to replay/type out
}

# path to whatever source file is currently loaded — None until someone
# uploads a file via /upload; there is no default demo file anymore
CURRENT_SOURCE = None

# handle on the live_transcribe.py subprocess, if one is running
TRANSCRIBE_PROC = None


def annotated_path_for(source_filename):
    """example_code.py -> example_code_annotated.py. Keeps the annotated
    output next to (and named after) whatever file was actually uploaded,
    instead of a hardcoded filename."""
    stem, dot, ext = source_filename.rpartition(".")
    if not dot:
        return f"{source_filename}_annotated"
    return f"{stem}_annotated.{ext}"


def _stop_transcription_if_running():
    global TRANSCRIBE_PROC
    if TRANSCRIBE_PROC is not None and TRANSCRIBE_PROC.poll() is None:
        TRANSCRIBE_PROC.send_signal(signal.SIGINT)
        try:
            TRANSCRIBE_PROC.wait(timeout=5)
        except subprocess.TimeoutExpired:
            TRANSCRIBE_PROC.kill()
    TRANSCRIBE_PROC = None


class TranscriptEvent(BaseModel):
    time: float
    text: str


class LocationEvent(BaseModel):
    time: float
    location: str
    confidence: str
    reasoning: str


class CommentEvent(BaseModel):
    location: str
    line: Optional[int] = None   # None = function-level intro comment, else a specific line
    comment: str


@app.post("/transcript")
def post_transcript(event: TranscriptEvent):
    state["transcript_log"].append(event.dict())
    state["events"].append({"type": "transcript", **event.dict()})  # NEW
    return {"ok": True}


@app.post("/location")
def post_location(event: LocationEvent):
    state["current_location"] = event.location
    state["events"].append({"type": "location", **event.dict()})
    return {"ok": True}


@app.post("/comment")
def post_comment(event: CommentEvent):
    state["events"].append({"type": "comment", **event.dict()})
    return {"ok": True}


@app.get("/state")
def get_state():
    return state


@app.get("/events")
def get_events(since: int = 0):
    """Frontend polls this with the index it last saw, gets only new events."""
    return {"events": state["events"][since:], "total": len(state["events"])}

# add to server.py

@app.get("/code")
def get_code():
    if CURRENT_SOURCE is None:
        raise HTTPException(status_code=404, detail="No source code uploaded yet")
    with open(CURRENT_SOURCE) as f:
        source_lines = f.readlines()
    with open("code_knowledge.json") as f:
        knowledge_base = json.load(f)
    return {"source_lines": source_lines, "knowledge_base": knowledge_base}
    
@app.get("/knowledge")
def get_knowledge():
    if CURRENT_SOURCE is None:
        raise HTTPException(status_code=404, detail="No source code uploaded yet")
    with open(CURRENT_SOURCE) as f:
        source = f.read()
    with open("code_knowledge.json") as f:
        knowledge_base = json.load(f)
    # 0-indexed line of each function's `def` line, matching source.split("\n") indexing
    functions = {item["name"]: item["line_start"] - 1 for item in knowledge_base}
    return {"source": source, "functions": functions, "name": CURRENT_SOURCE}

@app.get("/graph")
def get_graph():
    if CURRENT_SOURCE is None:
        raise HTTPException(status_code=404, detail="No source code uploaded yet")
    with open("code_graph.json") as f:
        return json.load(f)


@app.post("/upload")
def upload_source(file: UploadFile = File(...)):
    """Accepts a .py file from the browser, saves it, and runs the same
    analysis that used to be triggered by hand from the terminal:
    code_analyzer -> code_knowledge.json, code_relations -> code_graph.json."""
    global CURRENT_SOURCE

    _stop_transcription_if_running()

    filename = os.path.basename(file.filename or "uploaded_code.py")
    if not filename.endswith(".py"):
        raise HTTPException(status_code=400, detail="Please upload a .py file")

    with open(filename, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        build_code_knowledge_base(filename, output_path="code_knowledge.json")
        graph = extract_relations(filename)
        with open("code_graph.json", "w") as f:
            json.dump(graph, f, indent=2)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    CURRENT_SOURCE = filename

    # fresh lecture state for the newly uploaded file
    state["transcript_log"] = []
    state["current_location"] = None
    state["events"] = []

    return {"ok": True, "source": filename}


@app.post("/start-transcription")
def start_transcription():
    """Launches `live_transcribe.py` the same way you'd run it by hand —
    as a subprocess that inherits this server's environment (so an
    ANTHROPIC_API_KEY exported before starting the server carries through)."""
    global TRANSCRIBE_PROC

    if CURRENT_SOURCE is None:
        raise HTTPException(status_code=400, detail="Upload a source file first")

    if TRANSCRIBE_PROC is not None and TRANSCRIBE_PROC.poll() is None:
        raise HTTPException(status_code=409, detail="Transcription is already running")

    TRANSCRIBE_PROC = subprocess.Popen(
        [sys.executable, "live_transcribe.py"],
        env=os.environ.copy(),
    )
    return {"ok": True, "pid": TRANSCRIBE_PROC.pid}


@app.post("/stop-transcription")
def stop_transcription():
    """Sends SIGINT (same as Ctrl+C) so live_transcribe.py exits through its
    own KeyboardInterrupt handler and closes the mic stream cleanly."""
    _stop_transcription_if_running()
    return {"ok": True, "running": False}


@app.get("/transcription-status")
def transcription_status():
    running = TRANSCRIBE_PROC is not None and TRANSCRIBE_PROC.poll() is None
    return {"running": running}


@app.get("/download-annotated")
def download_annotated():
    if CURRENT_SOURCE is None:
        raise HTTPException(status_code=404, detail="No source code uploaded yet")

    path = annotated_path_for(CURRENT_SOURCE)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="No annotated file yet — start transcription first")

    return FileResponse(path, media_type="text/x-python", filename=os.path.basename(path))