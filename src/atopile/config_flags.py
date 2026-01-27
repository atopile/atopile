"""
ConfigFlag discovery utilities.

AST-based discovery of ConfigFlag definitions in Python source files.
Used by both the CLI (`ato dev flags`) and the server API (`/api/tests/flags`).
"""

import ast
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ConfigFlagDef:
    """A discovered ConfigFlag definition."""

    env_name: str  # The raw env var name (without FBRK_ prefix)
    kind: str  # ConfigFlag, ConfigFlagInt, ConfigFlagFloat, ConfigFlagString, ConfigFlagEnum
    python_name: str | None  # The Python variable name
    file: Path  # Source file path
    line: int  # Line number in source
    default: str | None  # Default value as string
    descr: str | None  # Description text

    @property
    def full_env_name(self) -> str:
        """The full environment variable name with FBRK_ prefix."""
        return f"FBRK_{self.env_name}"

    @property
    def current_value(self) -> str:
        """Get the current value from the environment."""
        return os.getenv(self.full_env_name, "")


def _iter_python_files(*roots: Path) -> list[Path]:
    """Iterate over all Python files in the given root directories."""
    out: list[Path] = []
    for r in roots:
        if not r.exists():
            continue
        out.extend(p for p in r.rglob("*.py") if p.is_file())
    return out


def _format_ast_target(target) -> str | None:
    """Format an AST assignment target as a string."""
    match target:
        case ast.Name(id=name):
            return name
        case ast.Attribute(value=base, attr=attr):
            base_s = _format_ast_target(base)
            if base_s is None:
                return attr
            return f"{base_s}.{attr}"
        case _:
            return None


def _extract_str_constant(node) -> str | None:
    """Extract a string constant from an AST node."""
    match node:
        case ast.Constant(value=str_val) if isinstance(str_val, str):
            return str_val
        case _:
            return None


def _extract_literal_repr(node) -> str | None:
    """Extract a literal value representation from an AST node."""
    match node:
        case ast.Constant(value=v):
            return repr(v)
        case ast.Name(id=name):
            return name
        case ast.Attribute(value=ast.Name(id=obj_name), attr=attr_name):
            return f"{obj_name}.{attr_name}"
        case ast.UnaryOp(op=ast.USub(), operand=ast.Constant(value=v)) if isinstance(
            v, (int, float)
        ):
            return repr(-v)
        case _:
            return None


def _is_configflag_ctor(call) -> str | None:
    """Return the constructor name if `call` looks like ConfigFlag*(...) or None."""
    if not isinstance(call, ast.Call):
        return None

    fn = call.func
    name = None
    if isinstance(fn, ast.Name):
        name = fn.id
    elif isinstance(fn, ast.Attribute):
        name = fn.attr

    if name in {
        "ConfigFlag",
        "ConfigFlagInt",
        "ConfigFlagFloat",
        "ConfigFlagString",
        "ConfigFlagEnum",
    }:
        return name
    return None


def _find_configflags_in_assignment(
    value, *, file: Path, line: int, python_name: str
) -> list[ConfigFlagDef]:
    """Find ConfigFlag definitions in an assignment value."""
    found: list[ConfigFlagDef] = []
    for node in ast.walk(value):
        if not isinstance(node, ast.Call):
            continue
        ctor = _is_configflag_ctor(node)
        if ctor is None:
            continue

        env_name = _extract_str_constant(node.args[0]) if node.args else None
        if not env_name:
            continue

        default: str | None = None
        descr: str | None = None
        for kw in node.keywords:
            if kw.arg == "default":
                default = _extract_literal_repr(kw.value)
            elif kw.arg == "descr":
                descr = _extract_str_constant(kw.value) or _extract_literal_repr(
                    kw.value
                )

        # Common positional patterns used in this repo:
        # - ConfigFlag("NAME", False, "descr")
        # - ConfigFlag("NAME", False)
        if default is None and len(node.args) >= 2:
            default = _extract_literal_repr(node.args[1])
        if descr is None and len(node.args) >= 3:
            descr = _extract_str_constant(node.args[2]) or _extract_literal_repr(
                node.args[2]
            )

        found.append(
            ConfigFlagDef(
                env_name=env_name,
                kind=ctor,
                python_name=python_name,
                file=file,
                line=line,
                default=default,
                descr=descr,
            )
        )

    return found


def discover_configflags(*roots: Path) -> list[ConfigFlagDef]:
    """
    Discover ConfigFlags in the given root directories using AST analysis.

    This is intentionally best-effort and repo-local:
    - Discovery is AST-based (no imports, no side effects)
    - Returns a deduplicated, sorted list of ConfigFlagDef objects
    """
    flags: list[ConfigFlagDef] = []
    for path in _iter_python_files(*roots):
        try:
            src = path.read_text(encoding="utf-8")
        except Exception:
            continue
        try:
            tree = ast.parse(src, filename=str(path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if not node.targets:
                    continue
                python_name = _format_ast_target(node.targets[0])
                if python_name is None:
                    continue
                flags.extend(
                    _find_configflags_in_assignment(
                        node.value,
                        file=path,
                        line=node.lineno,
                        python_name=python_name,
                    )
                )
            elif isinstance(node, ast.AnnAssign):
                python_name = _format_ast_target(node.target)
                if python_name is None or node.value is None:
                    continue
                flags.extend(
                    _find_configflags_in_assignment(
                        node.value,
                        file=path,
                        line=node.lineno,
                        python_name=python_name,
                    )
                )

    # Dedupe exact duplicates (same env/type/location/name)
    uniq: dict[tuple[str, str, str, int, str | None], ConfigFlagDef] = {}
    for f in flags:
        k = (f.env_name, f.kind, str(f.file), f.line, f.python_name)
        uniq[k] = f
    return sorted(
        uniq.values(), key=lambda f: (f.env_name, f.kind, str(f.file), f.line)
    )


def get_default_roots() -> list[Path]:
    """Get the default root directories for ConfigFlag discovery."""
    cwd = Path.cwd()
    roots = []

    # Look for src directories relative to cwd
    for candidate in [cwd, cwd.parent, cwd.parent.parent]:
        atopile_src = candidate / "src" / "atopile"
        faebryk_src = candidate / "src" / "faebryk"
        if atopile_src.is_dir() or faebryk_src.is_dir():
            if atopile_src.is_dir():
                roots.append(atopile_src)
            if faebryk_src.is_dir():
                roots.append(faebryk_src)
            break

    return roots
