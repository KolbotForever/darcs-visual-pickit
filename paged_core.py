def update_page_controls(app):
    total = len(getattr(app, "filtered_model_indices", []) or [])
    size = max(1, int(getattr(app, "page_size", 50) or 50))
    pages = max(1, ((total - 1) // size) + 1) if total else 1
    current = min(app.current_page_index + 1, pages)
    start = (current - 1) * size + 1 if total else 0
    end = min((current - 1) * size + size, total) if total else 0
    if hasattr(app, "page_status_var"):
        app.page_status_var.set(f"Page {current}/{pages}  ({start}-{end} of {total})")
    try:
        app.page_prev_btn.configure(state="normal" if current > 1 else "disabled")
        app.page_next_btn.configure(state="normal" if current < pages else "disabled")
    except Exception:
        pass


def build_card_from_model(
    app,
    model,
    model_index,
    *,
    comment_rule_card_cls,
    item_rule_card_cls,
    flat_stat_map,
    runtime_apply_rune_state_to_card,
):
    if model.get("is_comment"):
        card = comment_rule_card_cls(
            app.card_scroll,
            model.get("name", "Section"),
            app.del_card,
            app.move_card_up,
            app.move_card_down,
            app,
            raw_line=model.get("raw_line"),
            hide_in_ui=model.get("hide_in_ui", False),
        )
    else:
        card = item_rule_card_cls(
            app.card_scroll,
            model.get("name", "Item"),
            (model.get("quality") or "normal"),
            app.del_card,
            app.clone,
            app.set_active,
            app.font_data,
            app,
            app.move_card_up,
            app.move_card_down,
        )
        card._suspend_unsaved_mark = True
        try:
            card.raw_line = model.get("raw_line")
            if model.get("type"):
                card.set_type(model.get("type"))
            if model.get("error"):
                card.highlight_error(True)
            card.type_field = model.get("type_field", "name")
            runtime_apply_rune_state_to_card(card)
            card.is_disabled = model.get("is_disabled", False)
            card.refresh_power_button()
            card.base_extra_conditions = list(model.get("base_extra_conditions", []) or [])
            stats_payload = list(model.get("stats", []) or [])
            advanced_payload = list(model.get("advanced_clauses", []) or [])
            eager_indices = set(getattr(app, "_standard_render_eager_indices", set()) or ())
            if model_index in eager_indices:
                for sk, op, val in stats_payload:
                    stat_name = flat_stat_map.get(str(sk).lower(), sk)
                    card.add_stat_visually(sk, stat_name, op, val)
                for clause in advanced_payload:
                    card.add_advanced_clause(clause)
            else:
                card.set_pending_conditions(stats_payload, advanced_payload, mark_unsaved=False)
            card._last_saved_name = card.display_name
        finally:
            card._suspend_unsaved_mark = False
    card._model_index = model_index
    return card


def insert_model_at(app, model, idx):
    idx = max(0, min(int(idx), len(app.all_file_data)))
    app.all_file_data.insert(idx, model)
    app._model_search_cache = {}
    app.filtered_model_indices = []


def active_insert_index(app, fallback_to_page_start=True):
    if app.active_card is not None and getattr(app.active_card, "_model_index", None) is not None:
        return int(app.active_card._model_index)
    if fallback_to_page_start and getattr(app, "filtered_model_indices", None):
        size = max(1, int(getattr(app, "page_size", 50) or 50))
        start = app.current_page_index * size
        if start < len(app.filtered_model_indices):
            return int(app.filtered_model_indices[start])
    return len(app.all_file_data)


def status_rule_count(app):
    if getattr(app, "filtered_model_indices", None):
        return len(app.filtered_model_indices)
    if getattr(app, "all_file_data", None):
        return sum(1 for model in app.all_file_data if not model.get("hide_in_ui", False))
    return sum(1 for card in getattr(app, "rule_cards", []) if not getattr(card, "hide_in_ui", False))
