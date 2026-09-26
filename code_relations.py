import ast
import json

def extract_relations(file_path):
    with open(file_path) as f:
        source = f.read()

    tree = ast.parse(source)
    nodes = []
    edges = []
    class_of = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            nodes.append({"id": node.name, "type": "class"})
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    nodes.append({"id": f"{node.name}.{child.name}", "type": "method"})
                    edges.append({"source": node.name, "target": f"{node.name}.{child.name}",
                                  "type": "contains", "label": ""})
                    class_of[child.name] = node.name

    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            nodes.append({"id": node.name, "type": "function"})

    known_names = {n["id"].split(".")[-1]: n["id"] for n in nodes}

    def resolve_call_name(call_node):
        if isinstance(call_node.func, ast.Name):
            return call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            return call_node.func.attr
        return None

    def scan_body(body_node, owner_id):
        for stmt in ast.walk(body_node):
            if isinstance(stmt, ast.Assign):
                if isinstance(stmt.value, ast.Call):
                    called_name = resolve_call_name(stmt.value)
                    if called_name in known_names and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                        var_name = stmt.targets[0].id
                        target_id = known_names[called_name]
                        if target_id != owner_id:
                            edges.append({"source": target_id, "target": owner_id,
                                          "type": "data_flow", "label": var_name})
            elif isinstance(stmt, ast.Call):
                called_name = resolve_call_name(stmt)
                if called_name in known_names:
                    target_id = known_names[called_name]
                    if target_id != owner_id:
                        already_have = any(
                            e["source"] == target_id and e["target"] == owner_id and e["type"] == "data_flow"
                            for e in edges
                        )
                        if not already_have:
                            edges.append({"source": owner_id, "target": target_id,
                                          "type": "calls", "label": ""})

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, ast.FunctionDef):
                    scan_body(child, f"{node.name}.{child.name}")
        elif isinstance(node, ast.FunctionDef) and node in tree.body:
            scan_body(node, node.name)

    seen = set()
    unique_edges = []
    for e in edges:
        key = (e["source"], e["target"], e["type"], e["label"])
        if key not in seen:
            seen.add(key)
            unique_edges.append(e)

    return {"nodes": nodes, "edges": unique_edges}


if __name__ == "__main__":
    graph = extract_relations("example_code.py")
    with open("code_graph.json", "w") as f:
        json.dump(graph, f, indent=2)
    print(json.dumps(graph, indent=2))