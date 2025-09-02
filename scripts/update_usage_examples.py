import ast
import re
from pathlib import Path

LIB_DIR = Path(__file__).resolve().parents[1] / "src" / "faebryk" / "library"


def find_usage_example_targets(py_path: Path) -> list[tuple[str, bool]]:
    """
    Parse a file and return a list of (class_name, is_interface) that define
    a 'usage_example = L.f_field(F.has_usage_example)(...)' at class scope.
    is_interface is True when the class inherits from ModuleInterface.
    """
    text = py_path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(py_path))
    out: list[tuple[str, bool]] = []

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            bases = {getattr(b, "id", getattr(getattr(b, "attr", None), "id", None)) for b in node.bases}
            is_interface = "ModuleInterface" in bases
            # scan assignments in class body
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    if any(isinstance(t, ast.Name) and t.id == "usage_example" for t in stmt.targets):
                        out.append((node.name, is_interface))
                        break

    return out


def build_example_for(class_name: str, is_interface: bool) -> str:
    indent = "        "
    if is_interface:
        # Minimal, generic interface usage: connect two instances of same interface
        body = f"""
{indent}#pragma experiment("BRIDGE_CONNECT")
{indent}import {class_name}

{indent}module UsageExample:
{indent}    a = new {class_name}
{indent}    b = new {class_name}
{indent}    a ~ b
{indent}"""
    else:
        # Generic module usage: bridge between two Electrical nets
        body = f"""
{indent}#pragma experiment("BRIDGE_CONNECT")
{indent}import {class_name}
{indent}import Electrical

{indent}module UsageExample:
{indent}    electrical1 = new Electrical
{indent}    electrical2 = new Electrical
{indent}    device = new {class_name}
{indent}    electrical1 ~> device ~> electrical2
{indent}"""

    # Trim leading newline from f-string
    return body.lstrip("\n")


def replace_example_block(text: str, new_example: str) -> str:
    """
    Replace the content of the example="""...""" argument inside the usage_example
    initializer call. We keep the surrounding language argument as-is.
    """
    # matches example="""...""" with non-greedy capture
    pattern = re.compile(
        r"(usage_example\s*=\s*L\.f_field\(F\.has_usage_example\)\(\s*example\s*=\s*)([\"\']{3})([\s\S]*?)(\2)",
        re.MULTILINE,
    )

    def repl(match: re.Match[str]) -> str:
        prefix = match.group(1)
        quote = match.group(2)
        # Ensure example ends with a newline for readability
        replacement = prefix + quote + new_example + quote
        return replacement

    new_text, n = pattern.subn(repl, text, count=1)
    if n == 0:
        raise ValueError("example string not found for replacement")
    return new_text


def process_file(py_path: Path) -> bool:
    targets = find_usage_example_targets(py_path)
    if not targets:
        return False

    text = py_path.read_text(encoding="utf-8")

    # Only handle first target per file (library files define a single primary class)
    class_name, is_interface = targets[0]
    example = build_example_for(class_name, is_interface)
    updated = replace_example_block(text, example)
    if updated != text:
        py_path.write_text(updated, encoding="utf-8")
        return True
    return False


def main():
    changed = 0
    for py in sorted(LIB_DIR.glob("*.py")):
        if py.name in {"_F.py", "has_usage_example.py"}:
            continue
        try:
            if process_file(py):
                changed += 1
                print(f"Updated: {py}")
        except Exception as e:
            print(f"Failed to update {py}: {e}")

    print(f"Done. Files updated: {changed}")


if __name__ == "__main__":
    main()


