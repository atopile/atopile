import os
import ast
import collections
import sys

def find_duplicate_tests(root_dir):
    test_functions = collections.defaultdict(list)
    
    # skip these directories
    skip_dirs = {'.venv', '.git', 'build', '__pycache__', 'node_modules', '.uv-cache', 'artifacts', 'site-packages'}

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Modify dirnames in-place to skip directories
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
                
            filepath = os.path.join(dirpath, filename)
            
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    try:
                        tree = ast.parse(f.read(), filename=filepath)
                    except SyntaxError:
                        # Skip files with syntax errors
                        continue
                        
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.name.startswith("test_"):
                            test_functions[node.name].append((filepath, node.lineno))
                            
            except Exception as e:
                print(f"Error processing {filepath}: {e}", file=sys.stderr)

    duplicates = {k: v for k, v in test_functions.items() if len(v) > 1}
    
    return duplicates

def main():
    root_dir = os.getcwd()
    duplicates = find_duplicate_tests(root_dir)
    
    if not duplicates:
        print("No duplicate test functions found.")
        return

    print(f"Found {len(duplicates)} duplicate test function names:\n")
    
    for name, locations in sorted(duplicates.items()):
        print(f"{name}:")
        for path, lineno in locations:
            rel_path = os.path.relpath(path, root_dir)
            print(f"  - {rel_path}:{lineno}")
        print()

if __name__ == "__main__":
    main()

