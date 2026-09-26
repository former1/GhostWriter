# live_annotator.py
import json
import anthropic
import requests

SERVER_URL = "http://localhost:8000"

client = anthropic.Anthropic()

class LiveAnnotator:
    def __init__(self, source_path="example_code.py",
                 knowledge_path="code_knowledge.json",
                 output_path="example_code_annotated.py"):
        self.source_path = source_path
        self.output_path = output_path

        with open(knowledge_path) as f:
            self.knowledge_base = json.load(f)

        with open(source_path) as f:
            self.original_lines = f.readlines()

        # location -> {relative_line_offset: comment_text}
        self.line_comments = {}
        # location -> short one-line purpose comment (set once, on first mention)
        self.function_intro = {}

        self._rebuild_annotated_file()

    def _locate_line(self, name, code, transcript_chunk):
        numbered_code = "\n".join(
            f"{i}: {line}" for i, line in enumerate(code.split("\n"))
        )

        prompt = f"""A lecturer is live-explaining this function. Decide if their latest sentence refers to ONE specific line of code, or is a general/overview statement.

FUNCTION CODE (numbered from 0):
{numbered_code}

LECTURER JUST SAID: "{transcript_chunk}"

If this clearly refers to one specific line's operation, respond with that line's number and a very short comment (under 10 words, plain language, corrected for speech-to-text errors).
If it's general/overview/unclear, respond with line -1.

Respond ONLY with JSON:
{{"line": <number or -1>, "comment": "<short comment or empty string>"}}"""

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=100,
            messages=[{"role": "user", "content": prompt}]
        )

        raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"line": -1, "comment": ""}

    def update(self, location, transcript_chunk):
        if not location or location == "none":
            return None

        matched = next((item for item in self.knowledge_base if item["name"] == location), None)
        if not matched:
            return None

        if location not in self.function_intro:
            self.function_intro[location] = f"# {matched['purpose']}"
            try:
                requests.post(f"{SERVER_URL}/comment", json={
                    "location": location,
                    "line": None,
                    "comment": matched["purpose"]
                }, timeout=2)
            except requests.exceptions.RequestException as e:
                print(f"[WARN] Failed to post comment: {e}")

        result = self._locate_line(location, matched["code"], transcript_chunk)

        if result["line"] >= 0 and result["comment"]:
            self.line_comments.setdefault(location, {})[result["line"]] = result["comment"]
            try:
                requests.post(f"{SERVER_URL}/comment", json={
                    "location": location,
                    "line": result["line"],
                    "comment": result["comment"]
                }, timeout=2)
            except requests.exceptions.RequestException as e:
                print(f"[WARN] Failed to post comment: {e}")
            self._rebuild_annotated_file()

        return result

    def _rebuild_annotated_file(self):
        lines = list(self.original_lines)

        insertions = []

        for item in self.knowledge_base:
            name = item["name"]

            if name in self.function_intro:
                insertions.append((item["line_start"], self.function_intro[name]))

            if name in self.line_comments:
                for rel_line, comment in self.line_comments[name].items():
                    abs_line = item["line_start"] + rel_line
                    insertions.append((abs_line, f"    # {comment}"))

        insertions.sort(key=lambda x: x[0], reverse=True)

        for line_num, comment_text in insertions:
            target_line = lines[line_num - 1] if line_num - 1 < len(lines) else lines[-1]
            indent = target_line[:len(target_line) - len(target_line.lstrip())]
            comment_line = f"{indent}{comment_text.lstrip('#').strip() and '# ' + comment_text.lstrip('#').strip()}\n"
            lines[line_num - 1:line_num - 1] = [comment_line]

        with open(self.output_path, "w") as f:
            f.writelines(lines)