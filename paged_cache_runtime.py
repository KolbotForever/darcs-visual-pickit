import os


def init_runtime(app, base_editor_init, *args, **kwargs):
    base_editor_init(app, *args, **kwargs)
    app._page_widget_cache = {}
    app._compact_card_cache = {}
    app._standard_card_pool = {}
    app._standard_card_pool_order = []
    app._standard_card_pool_limit = 180
    app._rendered_page_key = None
    app._filter_revision = 0
    app._page_nav_after = None


def standard_card_signature(model):
    if not isinstance(model, dict):
        return ("unknown", repr(model))
    if model.get("is_comment"):
        return (
            "comment",
            str(model.get("raw_line", "") or ""),
            str(model.get("name", "") or ""),
            bool(model.get("hide_in_ui", False)),
        )
    raw_line = str(model.get("raw_line", "") or "")
    if raw_line:
        return ("item", raw_line, str(model.get("error", "") or ""))
    return (
        "item",
        str(model.get("name", "") or ""),
        str(model.get("type", "") or ""),
        str(model.get("type_field", "name") or "name"),
        str(model.get("quality", "") or ""),
        bool(model.get("is_disabled", False)),
        str(model.get("error", "") or ""),
    )


def _trim_standard_card_pool(app):
    pool = getattr(app, "_standard_card_pool", {}) or {}
    order = list(getattr(app, "_standard_card_pool_order", []) or [])
    try:
        limit = max(0, int(getattr(app, "_standard_card_pool_limit", 180) or 180))
    except Exception:
        limit = 180
    while len(order) > limit:
        victim = order.pop(0)
        entry = pool.pop(victim, None)
        card = entry.get("card") if isinstance(entry, dict) else None
        if card is not None:
            try:
                card.destroy()
            except Exception:
                pass
    app._standard_card_pool = pool
    app._standard_card_pool_order = order


def _cache_standard_card(app, model_index, model, card):
    if card is None:
        return False
    try:
        if hasattr(card, "winfo_exists") and not card.winfo_exists():
            return False
    except Exception:
        return False
    try:
        key = int(model_index)
    except Exception:
        return False
    try:
        if hasattr(card, "set_active") and not getattr(card, "is_comment", False):
            card.set_active(False)
    except Exception:
        pass
    pool = dict(getattr(app, "_standard_card_pool", {}) or {})
    order = list(getattr(app, "_standard_card_pool_order", []) or [])
    if key in order:
        order = [idx for idx in order if idx != key]
    previous = pool.get(key)
    previous_card = previous.get("card") if isinstance(previous, dict) else None
    if previous_card is not None and previous_card is not card:
        try:
            previous_card.destroy()
        except Exception:
            pass
    pool[key] = {"card": card, "signature": standard_card_signature(model)}
    order.append(key)
    app._standard_card_pool = pool
    app._standard_card_pool_order = order
    _trim_standard_card_pool(app)
    return True


def _take_standard_card(app, model_index, model):
    pool = dict(getattr(app, "_standard_card_pool", {}) or {})
    order = list(getattr(app, "_standard_card_pool_order", []) or [])
    try:
        key = int(model_index)
    except Exception:
        return None
    entry = pool.pop(key, None)
    if entry is None:
        return None
    order = [idx for idx in order if idx != key]
    app._standard_card_pool = pool
    app._standard_card_pool_order = order
    card = entry.get("card") if isinstance(entry, dict) else None
    if card is None:
        return None
    try:
        if hasattr(card, "winfo_exists") and not card.winfo_exists():
            return None
    except Exception:
        return None
    if entry.get("signature") != standard_card_signature(model):
        try:
            card.destroy()
        except Exception:
            pass
        return None
    return card


def clear_standard_card_pool(app, destroy=True):
    pool = dict(getattr(app, "_standard_card_pool", {}) or {})
    app._standard_card_pool = {}
    app._standard_card_pool_order = []
    if not destroy:
        return
    for entry in pool.values():
        card = entry.get("card") if isinstance(entry, dict) else None
        if card is not None:
            try:
                card.destroy()
            except Exception:
                pass


def page_cache_key(app, page_index=None):
    if page_index is None:
        page_index = int(getattr(app, "current_page_index", 0) or 0)
    return (
        int(getattr(app, "_filter_revision", 0) or 0),
        int(getattr(app, "page_size", 50) or 50),
        int(page_index),
    )


def standard_eager_count(app, page_indices):
    # Standard mode now keeps inactive cards in an intentional summary state and
    # prebuilds full controls in the background. Avoid inline card hydration here
    # so the page paint stays quick and visually stable.
    return 0


def clear_page_cache(app, destroy=True, keep_current=False):
    current_key = getattr(app, "_rendered_page_key", None)
    cache = dict(getattr(app, "_page_widget_cache", {}) or {})
    compact_cache = getattr(app, "_compact_card_cache", {}) or {}
    preserved_ids = {id(entry.get("card")) for entry in compact_cache.values() if entry.get("card") is not None}
    new_cache = {}
    for key, entry in cache.items():
        if keep_current and key == current_key:
            new_cache[key] = entry
            continue
        page_frame = entry.get("frame")
        if page_frame is not None:
            try:
                page_frame.pack_forget()
            except Exception:
                pass
        for card in list(entry.get("cards", []) or []):
            try:
                card.pack_forget()
            except Exception:
                pass
            preserve_compact = bool(entry.get("compact")) and id(card) in preserved_ids
            pooled = False
            if destroy and not preserve_compact and not entry.get("compact"):
                idx = getattr(card, "_model_index", None)
                models = getattr(app, "all_file_data", []) or []
                if idx is not None and 0 <= idx < len(models):
                    pooled = _cache_standard_card(app, idx, models[idx], card)
            if destroy and not preserve_compact and not pooled:
                try:
                    card.destroy()
                except Exception:
                    pass
        if destroy and page_frame is not None:
            try:
                page_frame.destroy()
            except Exception:
                pass
    app._page_widget_cache = new_cache
    if not keep_current:
        app._rendered_page_key = None


def sync_cached_entry(app, key, entry, model_from_card):
    if not entry or not entry.get("dirty"):
        return
    for card in list(entry.get("cards", []) or []):
        idx = getattr(card, "_model_index", None)
        if idx is None or idx < 0 or idx >= len(getattr(app, "all_file_data", []) or []):
            continue
        try:
            if hasattr(card, "winfo_exists") and not card.winfo_exists():
                continue
        except Exception:
            continue
        try:
            app.all_file_data[idx] = model_from_card(app, card)
            app._model_search_cache.pop(idx, None)
        except Exception:
            continue
    entry["dirty"] = False


def sync_current_page_to_models(app, model_from_card):
    if getattr(app, "_page_sync_in_progress", False):
        return
    app._page_sync_in_progress = True
    try:
        cache = getattr(app, "_page_widget_cache", {}) or {}
        current_key = getattr(app, "_rendered_page_key", None)
        entry = cache.get(current_key)
        if entry is not None:
            sync_cached_entry(app, current_key, entry, model_from_card)
        elif getattr(app, "rule_cards", None):
            for card in list(app.rule_cards or []):
                idx = getattr(card, "_model_index", None)
                if idx is None or idx < 0 or idx >= len(getattr(app, "all_file_data", []) or []):
                    continue
                try:
                    if hasattr(card, "winfo_exists") and not card.winfo_exists():
                        continue
                except Exception:
                    continue
                try:
                    app.all_file_data[idx] = model_from_card(app, card)
                    app._model_search_cache.pop(idx, None)
                except Exception:
                    continue
    finally:
        app._page_sync_in_progress = False


def mark_unsaved(app, base_mark_unsaved):
    try:
        key = getattr(app, "_rendered_page_key", None)
        if key is not None:
            entry = (getattr(app, "_page_widget_cache", {}) or {}).get(key)
            if entry is not None:
                entry["dirty"] = True
    except Exception:
        pass
    base_mark_unsaved(app)


def mark_saved(app, base_mark_saved):
    try:
        for entry in (getattr(app, "_page_widget_cache", {}) or {}).values():
            entry["dirty"] = False
    except Exception:
        pass
    base_mark_saved(app)


def rebuild_filtered_model_indices(app, get_model_search_blob, clear_page_cache_func):
    app._sync_current_page_to_models()
    q = str(app.rule_search_var.get() or "").lower().strip()
    indices = []
    for idx, model in enumerate(getattr(app, "all_file_data", []) or []):
        if model.get("is_comment") and model.get("hide_in_ui"):
            continue
        if not q or q in get_model_search_blob(app, idx, model):
            indices.append(idx)
    app.filtered_model_indices = indices
    page_count = max(1, ((len(indices) - 1) // max(1, app.page_size)) + 1) if indices else 1
    app.current_page_index = min(max(0, app.current_page_index), page_count - 1)
    app._filter_revision = int(getattr(app, "_filter_revision", 0) or 0) + 1
    clear_page_cache_func(app, destroy=True, keep_current=False)


def render_current_page(app, ctk_module, build_card_from_model, page_cache_key_func):
    indices = list(getattr(app, "filtered_model_indices", []) or [])
    size = max(1, int(getattr(app, "page_size", 50) or 50))
    start = app.current_page_index * size
    end = start + size
    page_indices = indices[start:end]
    target_key = page_cache_key_func(app)

    current_key = getattr(app, "_rendered_page_key", None)
    current_entry = (getattr(app, "_page_widget_cache", {}) or {}).get(current_key)
    if current_entry and current_key != target_key:
        old_frame = current_entry.get("frame")
        if old_frame is not None:
            try:
                old_frame.pack_forget()
            except Exception:
                pass
        for card in list(current_entry.get("cards", []) or []):
            try:
                card.pack_forget()
            except Exception:
                pass

    cache = getattr(app, "_page_widget_cache", {}) or {}
    entry = cache.get(target_key)
    if entry is None:
        cards = []
        eager_count = standard_eager_count(app, page_indices)
        app._standard_render_eager_indices = set(page_indices[:eager_count])
        try:
            for model_index in page_indices:
                model = app.all_file_data[model_index]
                card = _take_standard_card(app, model_index, model)
                if card is None:
                    card = build_card_from_model(app, model, model_index)
                else:
                    card._model_index = model_index
                cards.append(card)
                if not getattr(card, "is_comment", False):
                    try:
                        card._last_saved_name = card.display_name
                    except Exception:
                        pass
        finally:
            app._standard_render_eager_indices = set()
        entry = {"frame": None, "cards": cards, "page_indices": list(page_indices), "dirty": False}
        cache[target_key] = entry
        app._page_widget_cache = cache

    app.rule_cards = list(entry.get("cards", []) or [])
    app.active_card = app.active_card if app.active_card in app.rule_cards else None
    for card in app.rule_cards:
        try:
            if hasattr(card, "set_active") and not getattr(card, "is_comment", False):
                card.set_active(card is app.active_card)
        except Exception:
            pass
    for card in app.rule_cards:
        try:
            card.pack(fill="x", pady=8, padx=12)
        except Exception:
            pass
    app._rendered_page_key = target_key
    app._update_empty_state(len(page_indices))
    app._update_page_controls()
    loaded = len(app.rule_cards)
    total = len(indices)
    full = len(app.all_file_data)
    if hasattr(app, "header"):
        app.header.configure(
            text=f"Editing: {os.path.basename(app.current_file) if app.current_file else 'No file'} ({loaded} visible / {total} matched / {full} total)"
        )
    try:
        visible_items = [card for card in app.rule_cards if not getattr(card, "is_comment", False)]
        eager_count = standard_eager_count(app, page_indices)
        app._schedule_deferred_hydration(visible_items[:eager_count], reset=True, prioritize=True)
        app._schedule_deferred_hydration(visible_items[eager_count:])
    except Exception:
        pass
    try:
        app.after_idle(app.update_status_bar)
    except Exception:
        app.update_status_bar()


def profile_finish(app, total_rules=0, rendered_cards=0):
    lp = getattr(app, "last_profile", {}) or {}
    start = lp.get("start")
    parse_done = lp.get("parse_done")
    render_done = lp.get("render_done")
    bits = []
    if start and parse_done:
        bits.append(f"parse {((parse_done - start) * 1000):.0f} ms")
    if parse_done and render_done:
        bits.append(f"paint {((render_done - parse_done) * 1000):.0f} ms")
    bits.append(f"rules {int(total_rules)}")
    bits.append(f"page {int(rendered_cards)}")
    app.last_profile_summary = " | ".join(bits)
    print(f"[chatgpt58] {app.last_profile_summary}")
