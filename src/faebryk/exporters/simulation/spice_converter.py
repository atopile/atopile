"""PSpice/LTspice → ngspice converter.

Pure text processing, no graph dependencies. Converts common PSpice/LTspice
constructs to ngspice-compatible syntax so manufacturer .LIB files can be
included directly in ngspice netlists.

Main entry point:
    convert_pspice_to_ngspice(text) -> str

Helpers:
    parse_subcircuit_pins(text, subckt_name) -> list[str]
    parse_subcircuit_params(text, subckt_name) -> dict[str, str]
"""

from __future__ import annotations

import re


def convert_pspice_to_ngspice(text: str) -> str:
    """Convert PSpice/LTspice model text to ngspice-compatible syntax."""
    lines = text.splitlines()

    # 1. Join continuation lines (+ prefix) to previous line
    joined: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("+") and joined:
            # Append continuation (strip the '+' prefix) to previous line
            joined[-1] = joined[-1] + " " + stripped[1:].strip()
        else:
            joined.append(line)
    lines = joined

    result: list[str] = []
    for line in lines:
        stripped = line.strip()

        # Skip comment-only lines (preserve them)
        if stripped.startswith("*"):
            result.append(line)
            continue

        # Skip empty lines
        if not stripped:
            result.append(line)
            continue

        processed = _process_line(stripped)
        if processed is not None:
            result.append(processed)

    # Multi-line pass: break self-referencing B source algebraic loops
    result = _break_algebraic_loops(result)

    return "\n".join(result)


def _process_line(line: str) -> str:
    """Process a single non-comment line."""
    # Strip PSpice inline comments (semicolon to end of line)
    line = re.sub(r";.*$", "", line).rstrip()

    # 2. Strip TC=0,0 from R and C lines (ngspice doesn't support inline TC)
    first_char = line.split()[0][0].upper() if line.split() else ""
    if first_char in ("R", "C"):
        line = re.sub(r"\s+TC=[\d.,]+", "", line)

    # 3. Convert E/G sources with value={expr} → B sources
    line = _convert_controlled_sources(line)

    # 8. Convert PARAMS: in .SUBCKT declarations and X lines
    line = _convert_params_keyword(line)

    # 4. Remove {} curly braces ONLY from B source expressions.
    # Component values like C1 a b {DELAY*1.3} need braces for ngspice.
    line = _remove_curly_braces_from_behavioral(line)

    # 4b. Convert XOR (^) between comparison sub-expressions in B sources.
    # Must run BEFORE IF→ternary (XOR appears inside IF conditions) and
    # BEFORE exponentiation (so ^ used as XOR isn't converted to **).
    line = _convert_xor_in_behavioral(line)

    # 5. Convert IF(cond, true, false) → ternary (in B source expressions)
    line = _convert_if_functions(line)

    # 5b. Convert PSpice boolean operators | and & to ngspice-compatible
    # arithmetic in B source expressions. Must run AFTER IF→ternary so the
    # boolean ops are in the ternary condition, not breaking IF() arguments.
    # Uses (a) + (b) for OR, (a) * (b) for AND — works because comparison
    # operators return 0/1 and ternary ? : treats non-zero as true.
    line = _convert_boolean_ops(line)

    # 6. Convert ^ → ** (exponentiation) only in arithmetic contexts
    line = _convert_exponentiation(line)

    # 6b. Strip PSpice source value suffixes (Vdc, Vac, Adc, Aac)
    line = _strip_pspice_source_suffixes(line)

    # 7. Convert LIMIT(x, lo, hi) → min(max(x,lo),hi)
    line = _convert_limit_functions(line)

    # 9. Convert VSWITCH → SW in .model lines
    if re.match(r"\.model\b", line, re.IGNORECASE) and "VSWITCH" in line.upper():
        line = re.sub(r"\bVSWITCH\b", "SW", line, flags=re.IGNORECASE)

    # 10. Convert SW model VON/VOFF → VT/VH (ngspice uses different params)
    if re.match(r"\.model\b", line, re.IGNORECASE) and re.search(
        r"\bSW\b", line, re.IGNORECASE
    ):
        line = _convert_sw_params(line)

    # 11. Relax extreme diode ideality factors for ngspice convergence
    if re.match(r"\.model\b", line, re.IGNORECASE) and re.search(
        r"\bd\b", line, re.IGNORECASE
    ):
        line = _relax_diode_ideality(line)

    return line


def _convert_controlled_sources(line: str) -> str:
    """Convert E/G sources with VALUE to B sources.

    Standard linear E (VCVS) and G (VCCS) without VALUE are kept as-is.
    E with VALUE → B with V =
    G with VALUE → B with I =

    Handles both PSpice forms:
        E name n+ n- VALUE = { expr }
        E name n+ n- VALUE { expr }
    """
    # Match E or G source lines with VALUE (with or without =)
    match = re.match(
        r"^(E\S*|G\S*)\s+(\S+)\s+(\S+)\s+(?:(\S+)\s+(\S+)\s+)?value\s*=?\s*(.+)$",
        line,
        re.IGNORECASE,
    )
    if not match:
        return line

    name = match.group(1)
    node_p = match.group(2)
    node_n = match.group(3)
    expr = match.group(6).strip()

    prefix = name[0].upper()
    # Replace E→B or G→B in name
    new_name = "B_" + name[1:] if name[1:] else "B" + name

    if prefix == "E":
        return f"{new_name} {node_p} {node_n} V = {expr}"
    else:  # G
        return f"{new_name} {node_p} {node_n} I = {expr}"


def _convert_params_keyword(line: str) -> str:
    """Remove PARAMS: keyword from .SUBCKT and X lines, keep key=value pairs."""
    # .SUBCKT line: remove PARAMS: keyword
    line = re.sub(r"\s+PARAMS:\s*", " ", line, flags=re.IGNORECASE)
    return line


def _convert_boolean_ops(line: str) -> str:
    """Convert PSpice boolean operators | and & to ngspice equivalents.

    ngspice B source expressions don't support | (OR) or & (AND).
    For boolean (0/1) operands (e.g. from comparison operators):
        a | b  →  (a) + (b)
        a & b  →  (a) * (b)

    Only applies to B source expression lines.
    """
    m = re.match(r"^(B\S*\s+\S+\s+\S+\s+[VI]\s*=\s*)(.*)", line, re.IGNORECASE)
    if not m:
        return line

    prefix = m.group(1)
    expr = m.group(2)

    if " | " not in expr and " & " not in expr:
        return line

    # Process & (AND) first — higher precedence than |
    expr = _replace_bool_op(expr, " & ", " * ")
    # Process | (OR) — lowest precedence boolean operator
    expr = _replace_bool_op(expr, " | ", " + ")

    return prefix + expr


def _replace_bool_op(expr: str, op: str, arith_op: str) -> str:
    """Replace boolean operator with arithmetic equivalent.

    PSpice | and & are never valid in ngspice, so convert all occurrences.
    Uses (a) + (b) for OR, (a) * (b) for AND — works because comparison
    operators return 0/1 and ternary ? : treats non-zero as true.
    """
    parts = expr.split(op)
    if len(parts) <= 1:
        return expr

    # Parenthesize each operand and join with arithmetic operator
    wrapped = [f"({p.strip()})" for p in parts]
    return arith_op.join(wrapped)


def _remove_curly_braces_from_behavioral(line: str) -> str:
    """Remove {} curly braces only from B source expressions.

    In PSpice, {param} is used in both behavioral expressions and component
    values. ngspice component values support {expr} syntax, but B source
    expressions should not have curly braces around parameter references.
    """
    # Only strip braces from B source expression parts (after V = or I =)
    m = re.match(r"^(B\S*\s+\S+\s+\S+\s+[VI]\s*=\s*)(.*)", line, re.IGNORECASE)
    if m:
        prefix = m.group(1)
        expr = m.group(2).replace("{", "").replace("}", "")
        return prefix + expr
    return line


def _convert_if_functions(line: str) -> str:
    """Convert IF(cond, true_val, false_val) → ((cond) ? (true_val) : (false_val)).

    Handles nested parentheses via recursive paren matching.
    """
    while True:
        match = re.search(r"\bIF\s*\(", line, re.IGNORECASE)
        if not match:
            break

        start = match.start()
        paren_start = match.end() - 1  # position of '('

        # Find the matching closing paren
        args = _extract_paren_args(line, paren_start)
        if args is None or len(args) != 3:
            break  # malformed, skip

        end = _find_matching_paren(line, paren_start) + 1
        cond, true_val, false_val = args

        replacement = f"(({cond}) ? ({true_val}) : ({false_val}))"
        line = line[:start] + replacement + line[end:]

    return line


def _convert_limit_functions(line: str) -> str:
    """Convert LIMIT(x, lo, hi) → min(max(x,lo),hi)."""
    while True:
        match = re.search(r"\bLIMIT\s*\(", line, re.IGNORECASE)
        if not match:
            break

        start = match.start()
        paren_start = match.end() - 1

        args = _extract_paren_args(line, paren_start)
        if args is None or len(args) != 3:
            break

        end = _find_matching_paren(line, paren_start) + 1
        x, lo, hi = args

        replacement = f"min(max({x},{lo}),{hi})"
        line = line[:start] + replacement + line[end:]

    return line


def _convert_exponentiation(line: str) -> str:
    """Convert ^ to ** for exponentiation, but skip boolean XOR contexts.

    PSpice uses ^ for both exponentiation (2^3) and XOR (a > 0.5 ^ b > 0.5).
    We convert ^ to ** only when it appears in arithmetic context (preceded by
    a number, closing paren, or variable name — NOT a comparison operator).
    """
    # If line doesn't contain ^, nothing to do
    if "^" not in line:
        return line

    result = []
    i = 0
    while i < len(line):
        if line[i] == "^":
            # Check context: is this arithmetic (exponentiation) or boolean (XOR)?
            # Look at what precedes ^: if it's a digit, ), or letter → exponentiation
            # If preceded by a comparison result (> < = !) → XOR
            pre = line[:i].rstrip()
            if pre and pre[-1] in "0123456789.)":
                result.append("**")
            elif pre and pre[-1].isalpha():
                result.append("**")
            else:
                # Likely XOR context — keep as ^ (ngspice doesn't have ^,
                # but it appears inside subcircuit defs that may not be called)
                result.append("^")
            i += 1
        else:
            result.append(line[i])
            i += 1
    return "".join(result)


def _convert_sw_params(line: str) -> str:
    """Convert PSpice SW model VON/VOFF to ngspice VT/VH.

    PSpice: .MODEL name SW RON=r ROFF=r VON=v1 VOFF=v2
    ngspice: .MODEL name SW RON=r ROFF=r VT=threshold VH=hysteresis
    where VT = (VON+VOFF)/2, VH = (VON-VOFF)/2

    Also caps Roff at 1e6 to avoid extreme Roff/Ron ratios that cause
    convergence issues in ngspice.
    """
    von_m = re.search(r"\bVON\s*=\s*([\d.eE+-]+)", line, re.IGNORECASE)
    voff_m = re.search(r"\bVOFF\s*=\s*([\d.eE+-]+)", line, re.IGNORECASE)
    if not von_m or not voff_m:
        return line

    von = float(von_m.group(1))
    voff = float(voff_m.group(1))
    vt = (von + voff) / 2
    vh = abs(von - voff) / 2

    # Remove VON and VOFF
    line = re.sub(r"\bVON\s*=\s*[\d.eE+-]+", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\bVOFF\s*=\s*[\d.eE+-]+", "", line, flags=re.IGNORECASE)

    # Cap Roff/Ron ratio at 1e6 to reduce matrix conditioning issues
    roff_m = re.search(r"\bRoff\s*=\s*([\d.eE+-]+)", line, re.IGNORECASE)
    ron_m = re.search(r"\bRon\s*=\s*([\d.eE+-]+)", line, re.IGNORECASE)
    if roff_m:
        roff = float(roff_m.group(1))
        ron = float(ron_m.group(1)) if ron_m else 1.0
        max_roff = max(ron * 1e6, 1.0)  # ratio-based cap, minimum 1 ohm
        if roff > max_roff:
            line = re.sub(
                r"\bRoff\s*=\s*[\d.eE+-]+",
                f"Roff={max_roff:g}",
                line,
                flags=re.IGNORECASE,
            )

    # Clean up double spaces
    line = re.sub(r"  +", " ", line).rstrip()
    # Add VT and VH
    line += f" VT={vt:g} VH={vh:g}"
    return line


def _relax_diode_ideality(line: str) -> str:
    """Relax extreme diode ideality factors for ngspice convergence.

    PSpice models often use n=0.01 or n=0.1 to approximate ideal diodes.
    ngspice has trouble converging with such extreme values. Clamp to
    n=0.5 (compromise between ideal and standard), raise is to 1e-12,
    and ensure rs >= 0.1 for convergence.
    """
    m = re.search(r"\bn\s*=\s*([\d.eE+-]+)", line, re.IGNORECASE)
    if not m:
        return line
    n_val = float(m.group(1))
    if n_val < 0.5:
        line = re.sub(
            r"\bn\s*=\s*[\d.eE+-]+", "n=0.5", line, flags=re.IGNORECASE,
        )
    # Raise is if extremely small (< 1e-12)
    is_m = re.search(r"\bis\s*=\s*([\d.eE+-]+)", line, re.IGNORECASE)
    if is_m:
        is_val = float(is_m.group(1))
        if is_val < 1e-12:
            line = re.sub(
                r"\bis\s*=\s*[\d.eE+-]+", "is=1e-12", line, flags=re.IGNORECASE,
            )
    # Add or fix rs for convergence (minimum 0.1)
    rs_m = re.search(r"\brs\s*=\s*([\d.eE+-]+)", line, re.IGNORECASE)
    if rs_m:
        rs_val = float(rs_m.group(1))
        if rs_val < 0.01:
            line = re.sub(
                r"\brs\s*=\s*[\d.eE+-]+", "rs=0.1", line, flags=re.IGNORECASE,
            )
    else:
        # No rs parameter — add rs=0.1 before the closing paren or at end
        line = line.rstrip()
        line += " rs=0.1"
    return line


def _convert_xor_in_behavioral(line: str) -> str:
    """Convert XOR (^) between comparison sub-expressions in B source lines.

    PSpice uses ^ for both exponentiation and XOR. In B source expressions,
    when ^ appears between two comparison expressions like:
        V(A) > VTHRESH ^ V(B) > VTHRESH
    it's XOR. Convert to arithmetic equivalent:
        ((a) + (b) - 2*(a)*(b))

    Uses targeted regex to match comparison_expr ^ comparison_expr
    without splitting across IF() arguments or other structures.
    Must run BEFORE IF→ternary and BEFORE the exponentiation pass.
    """
    m = re.match(r"^(B\S*\s+\S+\s+\S+\s+[VI]\s*=\s*)(.*)", line, re.IGNORECASE)
    if not m:
        return line

    prefix = m.group(1)
    expr = m.group(2)

    if "^" not in expr:
        return line

    # Match: comparison_a ^ comparison_b
    # A comparison is: <operand> <comp_op> <operand>
    # <operand> is: V(X), I(X), number, or parameter name
    # (NOT a general pattern like [\w.()] which would eat IF() function names)
    # Number pattern (\d...) must come before \w+ so "0.5" isn't split as "0"+".5"
    operand = (
        r"(?:[VI]\([^)]*\)|\d[\d.eE+-]*|\w+)"
        r"(?:\s*[*/]\s*(?:[VI]\([^)]*\)|\d[\d.eE+-]*|\w+))*"
    )
    comp_op = r"[><=!]+"
    comparison = rf"({operand}\s*{comp_op}\s*{operand})"

    def xor_replace(match: re.Match) -> str:
        a = match.group(1).strip()
        b = match.group(2).strip()
        return f"(({a}) + ({b}) - 2*({a})*({b}))"

    expr = re.sub(
        rf"{comparison}\s*\^\s*{comparison}",
        xor_replace,
        expr,
    )
    return prefix + expr


def _break_algebraic_loops(lines: list[str]) -> list[str]:
    """Break self-referencing B source algebraic loops.

    PSpice models use patterns like:
        E name OUT 0 VALUE {IF(V(OUT)>0.5, ...)}
    After conversion to B sources, the output node appears in the expression,
    creating an algebraic loop that ngspice can't resolve.

    Fix: Insert an RC filter to break the loop:
        B_name OUT_drv 0 V = expr_using_V(OUT)
        R_name_fb OUT_drv OUT 1
        C_name_fb OUT 0 1n

    The 1ns time constant matches the existing RC delays used in gate subcircuits.
    """
    result: list[str] = []
    for line in lines:
        m = re.match(
            r"^(B\S+)\s+(\S+)\s+(\S+)\s+([VI]\s*=\s*)(.*)",
            line,
            re.IGNORECASE,
        )
        if not m:
            result.append(line)
            continue

        b_name = m.group(1)
        out_node = m.group(2)
        ref_node = m.group(3)
        mode = m.group(4)
        expr = m.group(5)

        # Check if the output node appears in the expression as V(node) or I(node)
        # Use word boundary to avoid false matches (e.g. OUT matching OUTPUT)
        pattern = re.compile(
            r"\b[VI]\(\s*" + re.escape(out_node) + r"\s*\)",
            re.IGNORECASE,
        )
        if not pattern.search(expr):
            result.append(line)
            continue

        # Self-referencing detected — break the loop with RC filter
        drv_node = out_node + "_drv"
        # Sanitize name for R/C (remove B_ prefix if present)
        base_name = b_name[2:] if b_name.upper().startswith("B_") else b_name[1:]
        r_name = f"R_{base_name}_fb"
        c_name = f"C_{base_name}_fb"

        result.append(f"{b_name} {drv_node} {ref_node} {mode}{expr}")
        result.append(f"{r_name} {drv_node} {out_node} 1")
        result.append(f"{c_name} {out_node} {ref_node} 1n")

    return result


def _strip_pspice_source_suffixes(line: str) -> str:
    """Strip PSpice source value suffixes (Vdc, Vac, Adc, Aac).

    PSpice uses forms like '0Vdc', '1.7Vdc', '0Adc' which ngspice
    doesn't recognize. Strip the suffix, keeping the numeric value.
    """
    return re.sub(
        r"(\d)\s*(Vdc|Vac|Adc|Aac)\b",
        r"\1",
        line,
        flags=re.IGNORECASE,
    )


def _find_matching_paren(text: str, pos: int) -> int:
    """Find the position of the matching closing parenthesis."""
    depth = 0
    for i in range(pos, len(text)):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _extract_paren_args(text: str, paren_pos: int) -> list[str] | None:
    """Extract comma-separated arguments from parenthesized expression.

    Handles nested parentheses correctly.
    """
    close = _find_matching_paren(text, paren_pos)
    if close == -1:
        return None

    inner = text[paren_pos + 1 : close]

    # Split on commas, respecting nested parens
    args: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in inner:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    args.append("".join(current).strip())

    return args


def parse_subcircuit_pins(text: str, subckt_name: str) -> list[str]:
    """Extract pin names in declaration order from a .SUBCKT line.

    Args:
        text: Full model file text (may contain multiple subcircuits).
        subckt_name: Name of the subcircuit to find.

    Returns:
        List of pin names in the order they appear in the .SUBCKT declaration.
    """
    # Join continuation lines first
    joined_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("+") and joined_lines:
            joined_lines[-1] = joined_lines[-1] + " " + stripped[1:].strip()
        else:
            joined_lines.append(line)

    for line in joined_lines:
        stripped = line.strip()
        # Match .SUBCKT <name> <pins...> [PARAMS: ...]
        match = re.match(
            rf"\.SUBCKT\s+{re.escape(subckt_name)}\s+(.+)",
            stripped,
            re.IGNORECASE,
        )
        if not match:
            continue

        rest = match.group(1)

        # Remove PARAMS: section and everything after
        params_match = re.search(r"\bPARAMS:\s*", rest, re.IGNORECASE)
        if params_match:
            rest = rest[: params_match.start()]

        # Remove key=value pairs (default params without PARAMS: keyword)
        # These look like NAME=VALUE at the end
        tokens = rest.split()
        pins: list[str] = []
        for token in tokens:
            if "=" in token:
                break  # Hit parameter defaults, stop
            pins.append(token)

        return pins

    return []


def parse_subcircuit_params(text: str, subckt_name: str) -> dict[str, str]:
    """Extract default parameter values from a .SUBCKT declaration.

    Args:
        text: Full model file text.
        subckt_name: Name of the subcircuit to find.

    Returns:
        Dict of parameter name → default value string.
    """
    # Join continuation lines first
    joined_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("+") and joined_lines:
            joined_lines[-1] = joined_lines[-1] + " " + stripped[1:].strip()
        else:
            joined_lines.append(line)

    for line in joined_lines:
        stripped = line.strip()
        match = re.match(
            rf"\.SUBCKT\s+{re.escape(subckt_name)}\s+(.+)",
            stripped,
            re.IGNORECASE,
        )
        if not match:
            continue

        rest = match.group(1)

        # Find all KEY=VALUE pairs
        params: dict[str, str] = {}
        for m in re.finditer(r"(\w+)\s*=\s*(\S+)", rest):
            params[m.group(1)] = m.group(2)

        return params

    return {}


def extract_subcircuit_block(text: str, subckt_name: str) -> str | None:
    """Extract a complete .SUBCKT...ENDS block by name.

    Returns the block text including .SUBCKT and .ENDS lines, or None if not found.
    """
    lines = text.splitlines()
    result: list[str] = []
    capturing = False

    for line in lines:
        stripped = line.strip()
        if not capturing:
            if re.match(
                rf"\.SUBCKT\s+{re.escape(subckt_name)}\b",
                stripped,
                re.IGNORECASE,
            ):
                capturing = True
                result.append(line)
        else:
            result.append(line)
            if re.match(r"\.ENDS\b", stripped, re.IGNORECASE):
                capturing = False
                break

    return "\n".join(result) if result else None


def extract_all_subcircuits_and_models(text: str) -> str:
    """Extract all .SUBCKT/.ENDS blocks and .model lines from text.

    Returns them concatenated, suitable for inclusion in a SPICE netlist.
    """
    lines = text.splitlines()
    result: list[str] = []
    in_subckt = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("*"):
            # Keep comments that are inside subcircuits
            if in_subckt:
                result.append(line)
            continue

        if re.match(r"\.SUBCKT\b", stripped, re.IGNORECASE):
            in_subckt = True
            result.append(line)
        elif re.match(r"\.ENDS\b", stripped, re.IGNORECASE):
            result.append(line)
            in_subckt = False
        elif in_subckt:
            result.append(line)
        elif re.match(r"\.model\b", stripped, re.IGNORECASE):
            result.append(line)

    return "\n".join(result)
