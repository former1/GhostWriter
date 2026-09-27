# GhostWriter

A live coding lecture assistant for Deaf and hard-of-hearing (DHH) learners.

## The problem

Following a programming lecture while Deaf or hard-of-hearing usually means splitting attention between a live transcript and the code on screen at the same time — reading a scrolling wall of text while also trying to track which function or line the lecturer is actually pointing at. That split-attention cost makes live coding lectures far more demanding to follow than they need to be.

## The idea

Instead of handing the learner a raw transcript to read alongside the code, GhostWriter listens to the lecture, figures out which part of the codebase is currently being discussed, and writes that understanding directly into the code — as short, corrected, plain-language comments that appear right where the lecturer is talking about them. The learner watches meaning accumulate inside the code itself, along with a live map of how functions and classes relate to each other, instead of reading two things at once.

## How it works

**Setup (once per file):**
1. A `.py` file is uploaded through the browser.
2. `code_parser.py` walks the file's AST to find every function and class, with line ranges.
3. `code_analyzer.py` sends each one to Claude to get a plain-language purpose, key concepts, and phrases a lecturer might plausibly say about it.
4. `code_relations.py` walks the AST again to map calls and data flow between functions/methods, powering the code map view.

**Live (while the lecture is running):**
1. `live_transcribe.py` records the microphone in 3-second chunks and transcribes them locally with Whisper.
2. `state_tracker.py` asks Claude to match each transcript chunk against the knowledge base's purposes/concepts/phrases to figure out which function is currently being discussed — staying on the previous location unless the lecturer clearly moves on.
3. `live_annotator.py` asks Claude whether that specific sentence points to one exact line, and generates a short corrected comment if so.
4. `server.py` collects all of this as a stream of events; `viewer.html` polls it and types the comments into place next to the code in real time, highlights the current function, and reveals it on the code relationship map.

There's also an offline path (`comment_generator.py`) that, after a full session, groups the whole transcript by function and asks Claude to write one clean, consolidated comment per function — useful for producing a tidier final annotated file than the incremental live version.
![Example Screenshot](https://github.com/former1/GhostWriter/blob/main/PHOTO-2026-09-26-16-34-28.jpg)
## Project structure

```
server.py                FastAPI backend: upload, live events, start/stop transcription, downloads
viewer.html               Browser UI: transcript panel, live-annotated code panel, code map
code_parser.py            Extracts functions/classes from a .py file via ast
code_analyzer.py          Claude calls to build the semantic knowledge base for a file
code_relations.py         Builds the function/class call & data-flow graph
state_tracker.py          Matches live transcript chunks to a location in the code
live_annotator.py         Generates and posts live inline comments
live_transcribe.py        Captures mic audio, runs Whisper, drives the live loop
comment_generator.py      Offline: one consolidated comment per function after a session
text_to_speech.py         Transcribes a pre-recorded audio/video file with Whisper
example_codes/            Sample source files and their annotated output, for demoing
```

## Setup

Requires Python 3.10+ and `ffmpeg` installed as a system binary (Whisper uses it to decode audio files):

```bash
brew install ffmpeg        # macOS
# or: sudo apt install ffmpeg   # Linux
```

Then, from the project root:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

You'll need an [Anthropic API key](https://console.anthropic.com/).

## Running it

In one terminal:

```bash
source venv/bin/activate
export ANTHROPIC_API_KEY="your-key-here"
uvicorn server:app --reload --port 8000
```

Then, in a second terminal, serve `viewer.html` over HTTP instead of opening it directly as a file — some browsers block `fetch()` requests made from a page loaded via `file://`, which can make the page look broken even though the backend is working fine:

```bash
python3 -m http.server 5500
```

Open `http://localhost:5500/viewer.html` in your browser.

1. Click **Upload code** and choose a `.py` file — this analyzes it and builds the knowledge base.
2. Click **Start transcription** and begin talking through the code. Comments will appear inline as you speak, and the code map (bottom bar) fills in as topics come up.
3. Click **Stop transcription** when you're done.
4. Click **Download commented file** to save the annotated version of the source file.

The first run of `live_transcribe.py` will download the Whisper "base" model (~140MB); this only happens once.
## Privacy and Limitations
1. Audio transcription runs locally through Whisper. However, transcript text and relevant code context are sent to the Anthropic API to identify the code being discussed and generate annotations.

2. Avoid using sensitive conversations or proprietary source code unless sharing that data with the configured API is permitted.

3. Generated comments may be incomplete or inaccurate. They should be treated as learning aids and reviewed before being used as technical documentation.

4. Session state is stored in memory and resets when the server restarts or a new file is uploaded.
## Notes

- Microphone permission is required for whichever terminal app or process is capturing audio. On macOS, grant this under **System Settings → Privacy & Security → Microphone**.
- This is a single-session, single-file-at-a-time hackathon build: lecture state lives in memory and resets when the server restarts or a new file is uploaded.
