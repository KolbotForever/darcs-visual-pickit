from typing import Callable


def stat_preview_parts(stats, flat_stat_map, limit=3):
    parts = []
    for key, op, val in list(stats or [])[:limit]:
        key_l = str(key).lower()
        label = flat_stat_map.get(key_l, str(key))
        if label in ("Faster Cast Rate", "Increased Attack Speed", "Faster Hit Recovery", "Faster Run/Walk"):
            short = {
                "Faster Cast Rate": "FCR",
                "Increased Attack Speed": "IAS",
                "Faster Hit Recovery": "FHR",
                "Faster Run/Walk": "FRW",
            }.get(label, label)
            parts.append(f"{val} {short}")
        elif "Resist" in label:
            parts.append(f"{label} {op} {val}")
        elif "Skills" in label or key_l.startswith("sk"):
            parts.append(f"+{val} {label}" if str(op) == "==" else f"{label} {op} {val}")
        else:
            if str(op) == "==":
                parts.append(f"{label} {val}")
            else:
                parts.append(f"{label} {op} {val}")
    return parts


def model_signature(model):
    if not model:
        return ""
    return repr(
        (
            model.get("is_comment"),
            model.get("hide_in_ui"),
            model.get("name"),
            model.get("type"),
            model.get("type_field"),
            model.get("quality"),
            tuple(model.get("stats", []) or []),
            tuple(model.get("advanced_clauses", []) or []),
            tuple(model.get("base_extra_conditions", []) or []),
            model.get("is_disabled"),
            model.get("raw_line"),
        )
    )


def build_model_cache(
    app,
    idx,
    model,
    *,
    flat_stat_map,
    friendly_item_display_name: Callable[[str], str],
    extract_numeric_stat_ids: Callable[[str], list[str]],
    runtime_model_is_rune: Callable[[dict], bool],
    title_separator: str,
    preview_joiner: str,
):
    if model is None:
        return {"title": "Item", "summary": "", "search_blob": ""}
    sig = model_signature(model)
    cache = model.get("_perf68_cache") if isinstance(model, dict) else None
    if isinstance(cache, dict) and cache.get("sig") == sig:
        if idx is not None:
            app._model_search_cache[idx] = cache.get("search_blob", "")
        return cache

    if model.get("is_comment"):
        name = str(model.get("name", "") or "Section").strip() or "Section"
        title = f"// {name}"
        summary = "Comment section"
        search_parts = [name, str(model.get("raw_line", "") or "")]
    else:
        name = str(model.get("name", "") or "Item").strip() or "Item"
        raw_type = str(model.get("type", "") or "").strip()
        friendly = friendly_item_display_name(raw_type) if raw_type else ""
        title = f"{name}{title_separator}{friendly}" if friendly and friendly.lower() != name.lower() else name

        quality = str(model.get("quality", "normal") or "normal").strip().title()
        stats = list(model.get("stats", []) or [])
        adv = list(model.get("advanced_clauses", []) or [])
        extras = list(model.get("base_extra_conditions", []) or [])
        bits = [quality] if quality else []
        preview_stats = stat_preview_parts(stats, flat_stat_map, limit=3)
        if preview_stats:
            bits.append(preview_joiner.join(preview_stats))
        if len(stats) > 3:
            bits.append(f"+{len(stats)-3} more")
        if adv:
            bits.append(f"{len(adv)} adv")
        if extras:
            bits.append(f"{len(extras)} extra")
        if model.get("is_disabled"):
            bits.append("Disabled")
        summary = "   |   ".join([b for b in bits if b])

        search_parts = [
            name,
            title,
            summary,
            str(model.get("raw_line", "") or ""),
            raw_type,
            friendly,
            str(model.get("type_field", "") or ""),
            str(model.get("quality", "") or ""),
        ]
        for extra in extras:
            search_parts.append(str(extra))
        for key, op, val in stats:
            search_parts.extend([str(key), str(op), str(val), flat_stat_map.get(str(key).lower(), str(key))])
        for expr in adv:
            search_parts.append(str(expr))
            search_parts.extend(extract_numeric_stat_ids(str(expr)))
        if runtime_model_is_rune(model):
            search_parts.extend(["rune", "runes"])

    search_blob = " ".join(p for p in search_parts if p).lower()
    cache = {"sig": sig, "title": title, "summary": summary, "search_blob": search_blob}
    if isinstance(model, dict):
        model["_perf68_cache"] = cache
    if idx is not None:
        app._model_search_cache[idx] = search_blob
    return cache


def get_model_search_blob(app, idx, model, model_cache_func):
    cached = app._model_search_cache.get(idx)
    if cached is not None:
        return cached
    return model_cache_func(app, idx, model).get("search_blob", "")


def compact_title(model, friendly_item_display_name: Callable[[str], str], title_separator: str):
    cache = model.get("_perf68_cache") if isinstance(model, dict) else None
    if isinstance(cache, dict) and cache.get("title"):
        return cache["title"]
    name = str(model.get("name", "") or "Item").strip() or "Item"
    raw_type = str(model.get("type", "") or "").strip()
    friendly = friendly_item_display_name(raw_type) if raw_type else ""
    return f"{name}{title_separator}{friendly}" if friendly and friendly.lower() != name.lower() else name


def compact_summary(model, base_compact_summary):
    cache = model.get("_perf68_cache") if isinstance(model, dict) else None
    if isinstance(cache, dict) and "summary" in cache:
        return cache["summary"]
    return base_compact_summary(model)


def prime_model_caches(app, model_cache_func, page_hint=None, chunk_size=80):
    try:
        all_data = list(getattr(app, "all_file_data", []) or [])
    except Exception:
        all_data = []
    if not all_data:
        return
    priority = []
    seen = set()
    try:
        size = max(1, int(getattr(app, "page_size", 25) or 25))
        if page_hint is None:
            page_hint = int(getattr(app, "current_page_index", 0) or 0)
        indices = list(getattr(app, "filtered_model_indices", []) or range(len(all_data)))
        for page_index in (page_hint, page_hint + 1):
            start = max(0, page_index) * size
            for idx in indices[start : start + size]:
                if idx not in seen:
                    priority.append(idx)
                    seen.add(idx)
    except Exception:
        pass
    work = priority + [i for i in range(len(all_data)) if i not in seen]
    app._perf68_cache_queue = work
    if getattr(app, "_perf68_cache_after_id", None):
        try:
            app.after_cancel(app._perf68_cache_after_id)
        except Exception:
            pass
        app._perf68_cache_after_id = None

    def _step():
        queue = list(getattr(app, "_perf68_cache_queue", []) or [])
        if not queue:
            app._perf68_cache_after_id = None
            return
        batch = queue[:chunk_size]
        app._perf68_cache_queue = queue[chunk_size:]
        for idx in batch:
            try:
                model = app.all_file_data[idx]
                model_cache_func(app, idx, model)
            except Exception:
                pass
        app._perf68_cache_after_id = app.after(1, _step)

    app._perf68_cache_after_id = app.after(1, _step)
