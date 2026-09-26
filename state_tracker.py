# state_tracker.py
import json
import anthropic

client = anthropic.Anthropic()

class LectureStateTracker:
    def __init__(self, knowledge_base_path="code_knowledge.json"):
        with open(knowledge_base_path) as f:
            self.knowledge_base = json.load(f)

        self.current_location = None
        self.history = []

    def build_prompt(self, transcript_chunk, recent_context):
        # Give the LLM the rich semantic summary, not raw code
        kb_summary = "\n".join(
            f"- `{item['name']}` ({item['type']}): {item['purpose']} "
            f"[key concepts: {', '.join(item['key_concepts'])}] "
            f"[likely phrases: {', '.join(item['likely_phrases'])}]"
            for item in self.knowledge_base
        )

        return f"""You are tracking which part of a codebase a lecturer is currently explaining, based on their live speech.

CODE KNOWLEDGE BASE:
{kb_summary}

PREVIOUS LOCATION: {self.current_location or "none yet"}
RECENT TRANSCRIPT CONTEXT: {recent_context}
NEW TRANSCRIPT CHUNK: "{transcript_chunk}"

Match the new transcript chunk to the most relevant item in the knowledge base, using purpose, key concepts, and likely phrases as clues — the lecturer may paraphrase rather than say exact names. Stay on the previous location unless the new text clearly signals a move to something else. If nothing matches (e.g. small talk, intro), say "none".

Respond ONLY with JSON, no other text:
{{
  "location": "<name from knowledge base, or 'none'>",
  "confidence": "<high|medium|low>",
  "reasoning": "<one short sentence>"
}}"""

    def update(self, transcript_chunk, timestamp):
        recent_context = " ".join(h["transcript"] for h in self.history[-2:])
        prompt = self.build_prompt(transcript_chunk, recent_context)

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {"location": self.current_location, "confidence": "low", "reasoning": "parse error"}

        if result["location"] != "none":
            self.current_location = result["location"]

        # attach the matched code snippet for display purposes
        matched_entry = next(
            (item for item in self.knowledge_base if item["name"] == result["location"]), None
        )

        entry = {
            "timestamp": timestamp,
            "transcript": transcript_chunk,
            "location": result["location"],
            "confidence": result["confidence"],
            "reasoning": result["reasoning"],
            "code": matched_entry["code"] if matched_entry else None,
            "purpose": matched_entry["purpose"] if matched_entry else None
        }
        self.history.append(entry)

        with open("lecture_state_log.json", "w") as f:
            json.dump(self.history, f, indent=2)

        return entry