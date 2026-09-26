# code_analyzer.py
import json
import anthropic
from code_parser import extract_structure

client = anthropic.Anthropic()

def analyze_chunk(chunk):
    prompt = f"""Analyze this code chunk and describe it for someone tracking a live lecture about this code.

CODE ({chunk['type']} `{chunk['name']}`, lines {chunk['line_start']}-{chunk['line_end']}):
{chunk['code']}

Respond ONLY with JSON, no other text:
{{
  "purpose": "<one sentence: what this does, in plain language>",
  "key_concepts": ["<important variable/method names or concepts someone might say out loud when explaining this>"],
  "likely_phrases": ["<3-5 short phrases a lecturer might plausibly say when talking about this part, e.g. 'check the balance', 'verify funds', 'constructor'>"]
}}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = response.content[0].text.strip().replace("```json", "").replace("```", "").strip()

    try:
        analysis = json.loads(raw)
    except json.JSONDecodeError:
        analysis = {"purpose": "", "key_concepts": [], "likely_phrases": []}

    return analysis


def build_code_knowledge_base(file_path, output_path="code_knowledge.json"):
    structure = extract_structure(file_path)
    knowledge_base = []

    for chunk in structure:
        print(f"Analyzing {chunk['type']} `{chunk['name']}`...")
        analysis = analyze_chunk(chunk)

        entry = {
            "name": chunk["name"],
            "type": chunk["type"],
            "line_start": chunk["line_start"],
            "line_end": chunk["line_end"],
            "code": chunk["code"],
            "purpose": analysis["purpose"],
            "key_concepts": analysis["key_concepts"],
            "likely_phrases": analysis["likely_phrases"]
        }
        knowledge_base.append(entry)

    with open(output_path, "w") as f:
        json.dump(knowledge_base, f, indent=2)

    print(f"\nSaved knowledge base with {len(knowledge_base)} entries to {output_path}")
    return knowledge_base


if __name__ == "__main__":
    build_code_knowledge_base("example_code.py")