import whisper
import numpy as np
import sounddevice as sd
import queue
import json
import time
from state_tracker import LectureStateTracker
from live_annotator import LiveAnnotator
import requests

SERVER_URL = "http://localhost:8000"

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3

model = whisper.load_model("base")
audio_queue = queue.Queue()
transcript_log = []


def annotated_path_for(source_filename):
    """Mirrors server.py's naming so /download-annotated finds this file."""
    stem, dot, ext = source_filename.rpartition(".")
    if not dot:
        return f"{source_filename}_annotated"
    return f"{stem}_annotated.{ext}"


def get_current_source():
    """Ask the server which file was uploaded via the browser, so this
    script annotates the same file the viewer is showing — instead of a
    hardcoded filename that could silently drift from whatever was uploaded."""
    resp = requests.get(f"{SERVER_URL}/knowledge", timeout=5)
    resp.raise_for_status()
    return resp.json()["name"]


def audio_callback(indata, frames, time_info, status):
    audio_queue.put(indata.copy())


def live_transcribe(tracker, annotator):
    print("Listening... (Ctrl+C to stop)")
    start_time = time.time()

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1,
                         callback=audio_callback, dtype='float32'):
        buffer = np.zeros((0,), dtype=np.float32)

        while True:
            chunk = audio_queue.get()
            buffer = np.concatenate([buffer, chunk.flatten()])

            if len(buffer) >= SAMPLE_RATE * CHUNK_SECONDS:
                elapsed = round(time.time() - start_time, 2)
                peak = float(np.abs(buffer).max())
                print(f"[{elapsed}s] chunk received, peak amplitude={peak:.5f}"
                      + (" (near-silent — check mic/input device)" if peak < 0.01 else ""))

                result = model.transcribe(buffer, fp16=False)
                text = result["text"].strip()

                if text:
                    entry = {"time": elapsed, "text": text}
                    transcript_log.append(entry)
                    requests.post(f"{SERVER_URL}/transcript", json={"time": elapsed, "text": text})
                    print(f"[{elapsed}s] {text}")

                    with open("live_transcript.json", "w") as f:
                        json.dump(transcript_log, f, indent=2)

                    state = tracker.update(text, elapsed)
                    requests.post(f"{SERVER_URL}/location", json={
                        "time": elapsed,
                        "location": state["location"],
                        "confidence": state["confidence"],
                        "reasoning": state["reasoning"]
                    })
                    print(f"[{elapsed}s] Location: {state['location']} "
                          f"({state['confidence']}) — {state['reasoning']}")

                    if state["location"] != "none" and state["confidence"] in ("high", "medium"):
                        annotator.update(state["location"], text)
                        print(f"[{elapsed}s] Updated comment for `{state['location']}`")

                buffer = np.zeros((0,), dtype=np.float32)


if __name__ == "__main__":
    source_name = get_current_source()
    print(f"Annotating: {source_name}")

    tracker = LectureStateTracker("code_knowledge.json")
    annotator = LiveAnnotator(
        source_path=source_name,
        output_path=annotated_path_for(source_name)
    )

    try:
        live_transcribe(tracker, annotator)
    except KeyboardInterrupt:
        print("\nStopped. Transcript saved to live_transcript.json")