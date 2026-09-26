# comment_generator.py
import json
import anthropic

client = anthropic.Anthropic()

def group_transcript_by_location(log_path="lecture_state_log.json"):
    with open(log_path) as f:
        log = json.load(f)

    grouped = {}
    for entry in log:
        loc = entry["location"]
        if loc and loc != "none":
            grouped.setdefault(loc, []).append(entry["transcript"])

    return grouped


def generate_comment(name, purpose, spoken_chunks):
    spoken_text = " ".join(spoken_chunks)

    prompt = f"""A lecturer explained this part of the code out loud. Write a short, clear explanatory comment for a student reviewing the code later.

CODE ELEMENT: {name}
CODE'S ACTUAL PURPOSE: {purpose}
WHAT THE LECTURER SAID (raw, may include speech-to-text errors or filler): "{spoken_text}"

Write a comment that:
- explains what this code does and why, in plain language
- corrects any obvious speech-to-text errors using the code's actual purpose as ground truth
- is concise (2-4 lines max)
- does NOT just repeat the lecturer's words verbatim

Respond ONLY with the comment text, no quotes, no markdown, no "Comment:" prefix. Each line should be ready to prefix with '#'."""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text.strip()


def annotate_source(
    source_path="example_code.py",
    knowledge_path="code_knowledge.json",
    log_path="lecture_state_log.json",
    output_path="example_code_annotated.py"
):
    with open(knowledge_path) as f:
        knowledge_base = json.load(f)

    grouped_transcripts = group_transcript_by_location(log_path)

    with open(source_path) as f:
        lines = f.readlines()

    # build list of (line_start, comment_text) for every item that was actually discussed
    insertions = []
    for item in knowledge_base:
        name = item["name"]
        if name in grouped_transcripts:
            print(f"Generating comment for `{name}`...")
            comment = generate_comment(name, item["purpose"], grouped_transcripts[name])
            insertions.append((item["line_start"], comment))

    # sort by line number descending so inserting doesn't shift earlier line numbers
    insertions.sort(key=lambda x: x[0], reverse=True)

    for line_start, comment in insertions:
        # match the indentation of the target line
        target_line = lines[line_start - 1]
        indent = target_line[:len(target_line) - len(target_line.lstrip())]

        comment_lines = [f"{indent}# {line}\n" for line in comment.split("\n") if line.strip()]
        insert_at = line_start - 1  # insert directly above the def/class line

        lines[insert_at:insert_at] = comment_lines

    with open(output_path, "w") as f:
        f.writelines(lines)

    print(f"\nAnnotated source saved to {output_path}")


if __name__ == "__main__":
    annotate_source()