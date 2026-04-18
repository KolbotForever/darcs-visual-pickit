def clear_compact_card_cache(app, destroy=True):
    try:
        pending = getattr(app, "_compact_prewarm_after", None)
        if pending:
            app.after_cancel(pending)
    except Exception:
        pass
    app._compact_prewarm_after = None
    app._compact_prewarm_queue = []
    cache = dict(getattr(app, "_compact_card_cache", {}) or {})
    for entry in cache.values():
        card = entry.get("card")
        if card is None:
            continue
        try:
            card.pack_forget()
        except Exception:
            pass
        if destroy:
            try:
                card.destroy()
            except Exception:
                pass
    app._compact_card_cache = {}


def get_compact_card(app, model_index, model, *, model_signature, base_compact_card_builder):
    cache = getattr(app, "_compact_card_cache", None)
    if cache is None:
        cache = {}
        app._compact_card_cache = cache
    sig = model_signature(model)
    entry = cache.get(model_index)
    card = entry.get("card") if isinstance(entry, dict) else None
    if card is not None:
        try:
            alive = not hasattr(card, "winfo_exists") or bool(card.winfo_exists())
        except Exception:
            alive = False
        if alive and entry.get("sig") == sig and bool(getattr(card, "is_comment", False)) == bool(model.get("is_comment")):
            card._model_index = model_index
            return card
        try:
            card.destroy()
        except Exception:
            pass
    card = base_compact_card_builder(app, model, model_index)
    cache[model_index] = {"sig": sig, "card": card}
    return card


def schedule_compact_prewarm(
    app,
    *,
    runtime_perf_enabled,
    runtime_get_compact_card,
    page_hint=None,
    page_span=1,
    chunk_size=3,
):
    if not runtime_perf_enabled(app):
        return
    try:
        if getattr(app, "_compact_prewarm_after", None):
            app.after_cancel(app._compact_prewarm_after)
    except Exception:
        pass
    app._compact_prewarm_after = None
    indices = list(getattr(app, "filtered_model_indices", []) or [])
    if not indices:
        app._compact_prewarm_queue = []
        return
    try:
        size = max(1, int(getattr(app, "page_size", 10) or 10))
    except Exception:
        size = 10
    if page_hint is None:
        page_hint = int(getattr(app, "current_page_index", 0) or 0) + 1
    targets = []
    seen = set()
    for page_index in range(max(0, page_hint), max(0, page_hint) + max(1, int(page_span))):
        start = page_index * size
        for idx in indices[start : start + size]:
            if idx not in seen:
                targets.append(idx)
                seen.add(idx)
    app._compact_prewarm_queue = targets

    def _step():
        queue = list(getattr(app, "_compact_prewarm_queue", []) or [])
        if not queue:
            app._compact_prewarm_after = None
            return
        batch = queue[: max(1, int(chunk_size))]
        app._compact_prewarm_queue = queue[max(1, int(chunk_size)) :]
        for idx in batch:
            try:
                if idx < 0 or idx >= len(getattr(app, "all_file_data", []) or []):
                    continue
                runtime_get_compact_card(app, idx, app.all_file_data[idx])
            except Exception:
                pass
        try:
            app._compact_prewarm_after = app.after(1, _step)
        except Exception:
            app._compact_prewarm_after = None

    try:
        app._compact_prewarm_after = app.after(1, _step)
    except Exception:
        app._compact_prewarm_after = None


def prime_visible_models(
    app,
    *,
    runtime_perf_enabled,
    visible_model_cache_prime,
    runtime_schedule_compact_prewarm,
    chunk_size=120,
):
    if not runtime_perf_enabled(app):
        return
    try:
        app.after(
            5,
            lambda s=app, chunk=chunk_size: visible_model_cache_prime(
                s,
                page_hint=getattr(s, "current_page_index", 0),
                chunk_size=chunk,
            ),
        )
    except Exception:
        pass
    try:
        app.after(
            15,
            lambda s=app: runtime_schedule_compact_prewarm(
                s,
                page_hint=getattr(s, "current_page_index", 0) + 1,
                page_span=1,
                chunk_size=3,
            ),
        )
    except Exception:
        pass
