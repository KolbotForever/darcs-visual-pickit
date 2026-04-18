from nip_parser import BASE_QUALITY_CLAUSE_RE, parse_nip_rule_line, rule_uses_rune_name


def _card_quality(card, default="unique"):
    getter = getattr(card, "get_quality_value", None)
    if callable(getter):
        try:
            value = str(getter() or "").strip().lower()
            if value:
                return value
        except Exception:
            pass
    qual_menu = getattr(card, "qual_menu", None)
    if qual_menu is not None and hasattr(qual_menu, "get"):
        try:
            value = str(qual_menu.get() or "").strip().lower()
            if value:
                return value
        except Exception:
            pass
    return str(default or "unique").strip().lower() or "unique"


def serialize_rule_card(app, card, hydrate=True):
    type_text = app._card_raw_item_type(card)
    if not type_text or type_text.lower() == "item":
        type_text = getattr(card, "display_name", "item") or "item"
    quality = _card_quality(card, default="unique")
    is_rune = rule_uses_rune_name(
        type_text,
        type_field=getattr(card, "type_field", "name"),
        quality=quality,
        display_name=getattr(card, "display_name", ""),
        raw_line=getattr(card, "raw_line", ""),
    )
    type_field = "name" if is_rune else (getattr(card, "type_field", "name") or "name")

    lhs_parts = [f"[{type_field}] == {type_text}"]
    if not is_rune:
        lhs_parts.append(f"[quality] == {quality}")
    for extra in getattr(card, "base_extra_conditions", []) or []:
        extra = (extra or "").strip()
        if extra and not (is_rune and BASE_QUALITY_CLAUSE_RE.match(extra)):
            lhs_parts.append(extra)

    if hydrate and hasattr(card, "ensure_hydrated"):
        try:
            card.ensure_hydrated()
        except Exception:
            pass

    rhs_parts = []
    for key, op, val in app._get_card_stat_tuples(card):
        key = getattr(key, "strip", lambda: str(key))().strip() if hasattr(key, "strip") else str(key).strip()
        if key:
            rhs_parts.append(f"[{key}] {op} {val}")
    for expr in app._get_card_advanced_expressions(card):
        expr = str(expr).strip()
        if expr:
            rhs_parts.append(expr)

    line = " && ".join(lhs_parts)
    if rhs_parts:
        line += " # " + " && ".join(rhs_parts)

    display_comment = getattr(card, "display_name", "") or ""
    if display_comment:
        line += f" // {display_comment}"

    if getattr(card, "is_disabled", False):
        line = "// " + line
    return line


def serialize_model_to_line(app, model):
    if not model:
        return ""
    if model.get("is_comment"):
        raw = str(model.get("raw_line", "") or "")
        if raw.strip():
            return raw
        name = str(model.get("name", "") or "Section").strip()
        if model.get("hide_in_ui"):
            return "//"
        return f"// --- {name} ---"

    type_text = str(model.get("type", "") or "").strip()
    display_name = str(model.get("name", "") or "Item").strip() or "Item"
    if not type_text or type_text.lower() == "item":
        type_text = display_name
    quality = str(model.get("quality", "unique") or "unique").strip().lower() or "unique"
    is_rune = rule_uses_rune_name(
        type_text,
        type_field=model.get("type_field", "name"),
        quality=quality,
        display_name=display_name,
        raw_line=model.get("raw_line", ""),
    )
    type_field = "name" if is_rune else (str(model.get("type_field", "name") or "name").strip() or "name")
    lhs_parts = [f"[{type_field}] == {type_text}"]
    if not is_rune:
        lhs_parts.append(f"[quality] == {quality}")
    for extra in list(model.get("base_extra_conditions", []) or []):
        extra = str(extra or "").strip()
        if extra and not (is_rune and BASE_QUALITY_CLAUSE_RE.match(extra)):
            lhs_parts.append(extra)

    rhs_parts = []
    for key, op, val in list(model.get("stats", []) or []):
        key = str(key or "").strip()
        op = str(op or ">=").strip() or ">="
        val = str(val or "0").strip() or "0"
        if key:
            rhs_parts.append(f"[{key}] {op} {val}")
    for expr in list(model.get("advanced_clauses", []) or []):
        expr = str(expr or "").strip()
        if expr:
            rhs_parts.append(expr)

    line = " && ".join(lhs_parts)
    if rhs_parts:
        line += " # " + " && ".join(rhs_parts)
    if display_name:
        line += f" // {display_name}"
    if model.get("is_disabled"):
        line = "// " + line
    return line


def model_from_card(app, card, apply_rune_state, friendly_item_display_name):
    if getattr(card, "is_comment", False):
        name = str(getattr(card, "display_name", "") or "").strip() or "Section"
        raw_line = f"// --- {name} ---"
        return {
            "is_comment": True,
            "name": name,
            "raw_line": raw_line,
            "comment_kind": "section",
            "hide_in_ui": bool(getattr(card, "hide_in_ui", False)),
        }

    try:
        apply_rune_state(card)
    except Exception:
        pass

    model = {
        "is_comment": False,
        "name": str(getattr(card, "display_name", "") or "Item"),
        "type": app._card_raw_item_type(card),
        "type_field": getattr(card, "type_field", "name"),
        "quality": _card_quality(card, default="unique"),
        "stats": list(app._get_card_stat_tuples(card)),
        "advanced_clauses": list(app._get_card_advanced_expressions(card)),
        "base_extra_conditions": list(getattr(card, "base_extra_conditions", []) or []),
        "is_disabled": bool(getattr(card, "is_disabled", False)),
        "display_comment": str(getattr(card, "display_name", "") or ""),
        "error": None,
        "raw_line": "",
    }
    line = serialize_model_to_line(app, model)
    parsed = parse_nip_rule_line(line, friendly_item_display_name) or model
    if not parsed.get("is_comment"):
        parsed["raw_line"] = line
    return parsed
