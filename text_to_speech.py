import whisper
import json
import sys

def transcribe(audio_path, output_path="transcript.json"):
    # "base" is a good speed/accuracy tradeoff for a hackathon.
    # Options: tiny, base, small, medium, large (bigger = slower, more accurate)
    model = whisper.load_model("base")

    result = model.transcribe(audio_path, word_timestamps=True)

    # Keep it simple: list of segments with start/end time + text
    segments = [
        {
            "start": round(seg["start"], 2),
            "end": round(seg["end"], 2),
            "text": seg["text"].strip()
        }
        for seg in result["segments"]
    ]

    with open(output_path, "w") as f:
        json.dump(segments, f, indent=2)

    print(f"Saved {len(segments)} segments to {output_path}")
    return segments

if __name__ == "__main__":
    audio_file = sys.argv[1] if len(sys.argv) > 1 else "2024-09-25 19-28-16.mov"
    transcribe(audio_file)