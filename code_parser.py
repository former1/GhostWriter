# code_parser.py
import ast
import json

def extract_structure(file_path):
    with open(file_path) as f:
        source = f.read()

    tree = ast.parse(source)
    lines = source.splitlines()
    structure = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            structure.append({
                "name": node.name,
                "type": "class" if isinstance(node, ast.ClassDef) else "function",
                "line_start": node.lineno,
                "line_end": node.end_lineno,
                "code": "\n".join(lines[node.lineno-1:node.end_lineno])
            })

    return structure

if __name__ == "__main__":
    structure = extract_structure("example_code.py")
    with open("code_structure.json", "w") as f:
        json.dump(structure, f, indent=2)
    print(f"Found {len(structure)} functions/classes")