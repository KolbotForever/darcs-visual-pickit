import re


SIMPLE_STAT_CLAUSE_RE = re.compile(r"^\s*\[([\w-]+)\]\s*([><=!]+)\s*(-?\d+)\s*$")
BASE_TYPE_CLAUSE_RE = re.compile(r"^\s*\[(name|type)\]\s*==\s*([\w-]+)\s*$", re.I)
BASE_QUALITY_CLAUSE_RE = re.compile(r"^\s*\[quality\]\s*([><=!]+)\s*([\w-]+)\s*$", re.I)
RESIST_COLOR_MAP = {
    "fireresist": "#ff6b6b",
    "lightresist": "#f1c40f",
    "coldresist": "#5dade2",
    "poisonresist": "#2ecc71",
}
RESIST_ALIAS_TEXT = {
    "all_res": "ALL RES",
    "tri_res": "TRI RES",
    "dual_res": "DUAL RES",
}


def split_top_level_and(expr: str):
    parts, buf, depth, i = [], [], 0, 0
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if depth == 0 and expr[i : i + 2] == "&&":
            part = "".join(buf).strip()
            if part:
                parts.append(part)
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    part = "".join(buf).strip()
    if part:
        parts.append(part)
    return parts


def split_rule_and_comment(text_line: str):
    if "//" not in text_line:
        return text_line.strip(), ""
    left, right = text_line.rsplit("//", 1)
    return left.strip(), right.strip()


def classify_comment_line(comment_text: str):
    s = (comment_text or "").strip()
    if not s:
        return {"kind": "blank", "name": ""}
    compact = s.replace("\t", " ").strip()
    punctuation_only = re.sub(r"[=\-_/\\|:*#\s]+", "", compact)
    if not punctuation_only:
        return {"kind": "separator", "name": ""}

    header = re.sub(r"^[=\-_/\\|:*#\s]+", "", compact)
    header = re.sub(r"[=\-_/\\|:*#\s]+$", "", header).strip()
    if header and "[" not in header and "]" not in header and "#" not in header:
        return {"kind": "section", "name": header}

    return {"kind": "comment", "name": compact}


def parse_simple_stat_clause(clause: str):
    m = SIMPLE_STAT_CLAUSE_RE.match(clause or "")
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3)


def is_rune_type_value(value):
    s = str(value or "").strip().lower()
    return s.endswith("rune") or s == "rune"


def rule_uses_rune_name(type_text="", type_field="name", quality="", display_name="", raw_line=""):
    type_field_s = str(type_field or "name").strip().lower() or "name"
    if type_field_s == "name":
        if is_rune_type_value(type_text) or is_rune_type_value(display_name):
            return True
    raw_lower = str(raw_line or "").lower()
    return "[name]" in raw_lower and "rune" in raw_lower


def parse_nip_rule_line(raw_line: str, friendly_item_display_name):
    clean = (raw_line or "").strip()
    if not clean:
        return None

    original = clean
    disabled = False
    working = clean
    if working.startswith("//"):
        disabled = True
        working = working[2:].strip()

    comment_meta = classify_comment_line(working)
    if comment_meta["kind"] == "separator":
        return {
            "is_comment": True,
            "name": "",
            "raw_line": original,
            "hide_in_ui": True,
        }
    if comment_meta["kind"] == "section":
        return {
            "is_comment": True,
            "name": comment_meta["name"] or "Section",
            "raw_line": original,
            "comment_kind": "section",
        }
    if comment_meta["kind"] in ("blank", "comment") and "[" not in working and "#" not in working:
        return {
            "is_comment": True,
            "name": comment_meta["name"] or original.lstrip("/").strip(),
            "raw_line": original,
            "comment_kind": comment_meta["kind"],
        }

    if working.startswith("---"):
        name = working.replace("---", "").strip("- ").strip() or "Section"
        return {"is_comment": True, "name": name, "raw_line": original, "comment_kind": "section"}

    if working.startswith("--"):
        working = working[2:].strip()

    rule_part, display_comment = split_rule_and_comment(working)
    if not rule_part:
        return {"is_comment": True, "name": display_comment or original.lstrip("/").strip(), "raw_line": original}

    if "[" not in rule_part and "#" not in rule_part:
        return {"is_comment": True, "name": display_comment or rule_part, "raw_line": original}

    line_err = []
    if rule_part.count("[") != rule_part.count("]"):
        line_err.append("Unbalanced brackets [ ].")

    lhs, rhs = (rule_part.split("#", 1) + [""])[:2]
    lhs = lhs.strip()
    rhs = rhs.strip()

    item_type = ""
    type_field = "name"
    quality = ""
    base_extra_conditions = []

    for clause in split_top_level_and(lhs):
        m_type = BASE_TYPE_CLAUSE_RE.match(clause or "")
        if m_type:
            type_field = m_type.group(1).lower()
            item_type = m_type.group(2)
            continue
        m_quality = BASE_QUALITY_CLAUSE_RE.match(clause or "")
        if m_quality:
            if m_quality.group(1) == "==":
                quality = m_quality.group(2)
            else:
                base_extra_conditions.append(clause)
            continue
        if clause:
            base_extra_conditions.append(clause)

    simple_stats = []
    advanced_clauses = []
    if rhs:
        for clause in split_top_level_and(rhs):
            clean_clause = (clause or "").strip()
            while clean_clause.startswith("#"):
                clean_clause = clean_clause[1:].strip()
            if not clean_clause:
                continue
            parsed = parse_simple_stat_clause(clean_clause)
            if parsed:
                simple_stats.append(parsed)
            else:
                advanced_clauses.append(clean_clause)

    display_name = display_comment or friendly_item_display_name(item_type) or "Item"
    info = {
        "is_comment": False,
        "name": display_name,
        "type": item_type,
        "type_field": type_field,
        "quality": quality,
        "stats": simple_stats,
        "advanced_clauses": advanced_clauses,
        "base_extra_conditions": base_extra_conditions,
        "is_disabled": disabled,
        "display_comment": display_comment,
        "error": " ".join(line_err) if line_err else None,
        "raw_line": original,
    }
    if rule_uses_rune_name(item_type, type_field=type_field, quality=quality, display_name=display_name, raw_line=original):
        info["quality"] = "rune"
    if not item_type and not simple_stats and not advanced_clauses and not base_extra_conditions and not info["error"]:
        info["error"] = "Invalid NIP line formatting."
    return info


def parse_advanced_alias(expression: str):
    expr = (expression or "").strip()
    m = re.match(r"^\s*((?:\[[\w-]+\]\s*(?:\+\s*)?)+)\s*([><=!]+)\s*(-?\d+)\s*$", expr, re.I)
    if not m:
        return None
    stat_expr, op, val = m.groups()
    stats = re.findall(r"\[([\w-]+)\]", stat_expr, re.I)
    stats = [s.lower() for s in stats]
    if not stats or len(set(stats)) != len(stats):
        return None
    if not all(s in RESIST_COLOR_MAP for s in stats):
        return None
    unique = set(stats)
    if len(unique) == 4:
        alias_type = "all_res"
    elif len(unique) == 3:
        alias_type = "tri_res"
    elif len(unique) == 2:
        alias_type = "dual_res"
    else:
        return None
    return {
        "kind": alias_type,
        "stats": stats,
        "op": op,
        "val": val,
        "raw": expr,
    }


def build_advanced_alias_expression(alias_info, op: str, value: str):
    stats = list(alias_info.get("stats", []))
    stat_expr = "+".join(f"[{s}]" for s in stats)
    return f"{stat_expr} {op} {value}".strip()


def split_top_level_boolean(expr: str):
    parts = []
    buf = []
    paren = 0
    bracket = 0
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "[":
            bracket += 1
            buf.append(ch)
            i += 1
            continue
        if ch == "]":
            bracket = max(0, bracket - 1)
            buf.append(ch)
            i += 1
            continue
        if ch == "(" and bracket == 0:
            paren += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ")" and bracket == 0:
            paren = max(0, paren - 1)
            buf.append(ch)
            i += 1
            continue
        if bracket == 0 and paren == 0 and expr[i : i + 2] in ("&&", "||"):
            parts.append(("".join(buf).strip(), expr[i : i + 2]))
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    parts.append(("".join(buf).strip(), None))
    return parts


def unwrap_outer_group(expr: str) -> str:
    s = (expr or "").strip()
    while s.startswith("(") and s.endswith(")"):
        depth = 0
        ok = True
        for idx, ch in enumerate(s):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and idx != len(s) - 1:
                    ok = False
                    break
        if not ok or depth != 0:
            break
        s = s[1:-1].strip()
    return s


def is_atomic_advanced_clause(expr: str) -> bool:
    s = unwrap_outer_group((expr or "").strip())
    if not s:
        return False
    if "#" in s:
        return False
    if split_top_level_boolean(s)[0][1] is not None:
        return False
    return bool(re.search(r"(==|!=|>=|<=|>|<)", s))


def find_invalid_comparison_operators(text: str):
    text = text or ""
    bad = []
    bracket_depth = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "[":
            bracket_depth += 1
            i += 1
            continue
        if ch == "]":
            bracket_depth = max(0, bracket_depth - 1)
            i += 1
            continue
        if bracket_depth == 0 and ch in "<>!=":
            j = i
            while j < len(text) and text[j] in "<>!=":
                j += 1
            op_run = text[i:j]
            if op_run not in ("==", "!=", ">=", "<=", ">", "<"):
                bad.append((op_run, i + 1))
            i = j
            continue
        i += 1
    return bad


def analyze_advanced_expression(expression: str):
    expr = (expression or "").strip()
    if not expr:
        return "error", "Expression is empty."

    paren_stack = []
    bracket_stack = []
    for i, ch in enumerate(expr):
        if ch == "(":
            paren_stack.append(i)
        elif ch == ")":
            if not paren_stack:
                return "error", f"Unexpected ')' near position {i + 1}."
            paren_stack.pop()
        elif ch == "[":
            bracket_stack.append(i)
        elif ch == "]":
            if not bracket_stack:
                return "error", f"Unexpected ']' near position {i + 1}."
            bracket_stack.pop()
    if paren_stack:
        return "error", f"Missing ')' for '(' near position {paren_stack[-1] + 1}."
    if bracket_stack:
        return "error", f"Missing ']' for '[' near position {bracket_stack[-1] + 1}."

    if "[]" in expr:
        return "error", "Empty [] token detected."
    if "#" in expr:
        return "error", "Advanced editor expects one clause only; remove # from this field."

    invalid_ops = find_invalid_comparison_operators(expr)
    if invalid_ops:
        bad_op, pos = invalid_ops[0]
        return "error", f"Invalid comparison operator '{bad_op}' near position {pos}."

    if re.search(r"\+\s*(?:[><=!]=?|$)", expr):
        return "error", "A + operator is not followed by another stat token."

    stripped = expr.strip()
    if stripped.startswith("&&") or stripped.startswith("||") or stripped.endswith("&&") or stripped.endswith("||"):
        return "error", "Expression starts or ends with a dangling && or || connector."
    if re.search(r"(?:&&|\|\|)\s*(?:&&|\|\|)", expr):
        return "error", "Expression has consecutive boolean connectors."

    top_parts = split_top_level_boolean(expr)
    connectors = [conn for _, conn in top_parts if conn]
    if connectors:
        for clause, _ in top_parts:
            if not clause:
                return "error", "Expression contains an empty clause around a boolean connector."
        for clause, _ in top_parts:
            if clause and not is_atomic_advanced_clause(clause):
                inner = unwrap_outer_group(clause)
                inner_parts = split_top_level_boolean(inner)
                if inner_parts[0][1] is None and not re.search(r"(==|!=|>=|<=|>|<)", inner):
                    return "warning", "Complex grouped expression detected. Validation is limited for this pattern."
        return "ok", "Expression looks valid."

    if not re.search(r"(==|!=|>=|<=|>|<)", expr):
        return "warning", "Complex expression detected, but no top-level comparison operator was found."

    return "ok", "Expression looks valid."


def validate_advanced_expression(expression: str):
    level, msg = analyze_advanced_expression(expression)
    return level != "error", msg


def extract_numeric_stat_ids(expression: str):
    return sorted(set(re.findall(r"\[(\d+)\]", expression or "")), key=lambda x: int(x))


def summarize_advanced_expression(expression: str) -> str:
    expr = (expression or "").strip()
    if not expr:
        return "Empty advanced expression"

    alias = parse_advanced_alias(expr)
    if alias:
        return f"Recognized as {RESIST_ALIAS_TEXT.get(alias['kind'], 'ADVANCED')} {alias['op']} {alias['val']}"

    refs = re.findall(r"\[([\w-]+)\]", expr)
    connectors = []
    if "&&" in expr:
        connectors.append("AND")
    if "||" in expr:
        connectors.append("OR")
    grouped = "grouped expression" if ("(" in expr or ")" in expr) else "flat expression"
    desc = [grouped]
    if connectors:
        desc.append("/".join(connectors))
    if refs:
        desc.append(f"{len(refs)} stat reference{'s' if len(refs) != 1 else ''}")
    else:
        desc.append("no bracketed stat refs detected")
    return " - ".join(desc)
