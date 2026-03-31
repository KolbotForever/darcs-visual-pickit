def add_blank(
    app,
    *,
    ctk_module,
    parse_nip_rule_line,
    serialize_model_to_line,
    active_insert_index,
    runtime_clear_compact_card_cache,
    runtime_clear_standard_card_pool,
    insert_model_at,
    paged_cache_rebuild_filtered_indices,
):
    dialog = ctk_module.CTkInputDialog(text="Enter custom name for this item:", title="New Item")
    custom_name = dialog.get_input()
    if custom_name is None:
        return
    final_name = custom_name.strip() or "New Rule"
    model = parse_nip_rule_line(f"[name] == {final_name} && [quality] == unique // {final_name}")
    model["raw_line"] = serialize_model_to_line(app, model)
    insert_at = active_insert_index(app, fallback_to_page_start=True)
    app._sync_current_page_to_models()
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    insert_model_at(app, model, insert_at)
    paged_cache_rebuild_filtered_indices(app)
    app.current_page_index = insert_at // max(1, app.page_size)
    app.render_current_page()
    app.mark_unsaved()


def add_comment(
    app,
    name=None,
    *,
    ctk_module,
    runtime_clear_compact_card_cache,
    runtime_clear_standard_card_pool,
    insert_model_at,
    paged_cache_rebuild_filtered_indices,
):
    if name is None:
        dialog = ctk_module.CTkInputDialog(text="Enter section header text:", title="New Comment Divider")
        custom_name = dialog.get_input()
        if custom_name is None:
            return
        name = custom_name.strip() or "Section"
    model = {
        "is_comment": True,
        "name": name,
        "raw_line": f"// --- {name} ---",
        "comment_kind": "section",
        "hide_in_ui": False,
    }
    app._sync_current_page_to_models()
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    insert_model_at(app, model, len(app.all_file_data))
    paged_cache_rebuild_filtered_indices(app)
    app.current_page_index = max(0, ((len(app.filtered_model_indices) - 1) // max(1, app.page_size))) if app.filtered_model_indices else 0
    app.render_current_page()
    app.mark_unsaved()


def add_from_cat(
    app,
    name,
    category=None,
    *,
    parse_nip_rule_line,
    serialize_model_to_line,
    active_insert_index,
    runtime_clear_compact_card_cache,
    runtime_clear_standard_card_pool,
    insert_model_at,
    paged_cache_rebuild_filtered_indices,
):
    active = getattr(app, "active_card", None)
    if active and not getattr(active, "is_comment", False) and hasattr(active, "set_type") and hasattr(active, "name_label"):
        active.display_name = name
        active.name_label.configure(text=name)
        active.set_type(name)
        app.mark_unsaved()
        return
    model = parse_nip_rule_line(f"[name] == {name} && [quality] == unique // {name}")
    model["raw_line"] = serialize_model_to_line(app, model)
    app._sync_current_page_to_models()
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    insert_at = 0 if category == "Most Wanted Items" else active_insert_index(app, fallback_to_page_start=False)
    insert_model_at(app, model, insert_at)
    paged_cache_rebuild_filtered_indices(app)
    max_page = max(0, ((len(app.filtered_model_indices) - 1) // max(1, app.page_size))) if app.filtered_model_indices else 0
    app.current_page_index = min(insert_at // max(1, app.page_size), max_page)
    app.render_current_page()
    app.mark_unsaved()


def del_card(app, card, *, runtime_clear_compact_card_cache, runtime_clear_standard_card_pool, paged_cache_rebuild_filtered_indices):
    idx = getattr(card, "_model_index", None)
    if idx is None or idx < 0 or idx >= len(app.all_file_data):
        return
    app._sync_current_page_to_models()
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    app.deleted_stack.append({"model": app.all_file_data[idx], "idx": idx})
    app.all_file_data.pop(idx)
    app._model_search_cache = {}
    app.active_card = None
    paged_cache_rebuild_filtered_indices(app)
    total_pages = max(1, ((len(app.filtered_model_indices) - 1) // max(1, app.page_size)) + 1) if app.filtered_model_indices else 1
    app.current_page_index = min(app.current_page_index, total_pages - 1)
    app.render_current_page()
    app.mark_unsaved()


def clone_card(
    app,
    old,
    *,
    serialize_model_to_line,
    runtime_clear_compact_card_cache,
    runtime_clear_standard_card_pool,
    paged_cache_rebuild_filtered_indices,
):
    idx = getattr(old, "_model_index", None)
    if idx is None:
        return
    app._sync_current_page_to_models()
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    model = dict(app.all_file_data[idx])
    if not model.get("is_comment"):
        model["name"] = str(model.get("name", "Item")) + " (Copy)"
        model["display_comment"] = model["name"]
        model["raw_line"] = serialize_model_to_line(app, model)
    app.all_file_data.insert(idx + 1, model)
    app._model_search_cache = {}
    paged_cache_rebuild_filtered_indices(app)
    app.current_page_index = (idx + 1) // max(1, app.page_size)
    app.render_current_page()
    app.mark_unsaved()


def move_card_up(app, card, *, runtime_clear_compact_card_cache, runtime_clear_standard_card_pool, paged_cache_rebuild_filtered_indices):
    idx = getattr(card, "_model_index", None)
    if idx is None or idx <= 0:
        return
    app._sync_current_page_to_models()
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    app.all_file_data[idx - 1], app.all_file_data[idx] = app.all_file_data[idx], app.all_file_data[idx - 1]
    app._model_search_cache = {}
    paged_cache_rebuild_filtered_indices(app)
    app.current_page_index = (idx - 1) // max(1, app.page_size)
    app.render_current_page()
    app.mark_unsaved()


def move_card_down(app, card, *, runtime_clear_compact_card_cache, runtime_clear_standard_card_pool, paged_cache_rebuild_filtered_indices):
    idx = getattr(card, "_model_index", None)
    if idx is None or idx >= len(app.all_file_data) - 1:
        return
    app._sync_current_page_to_models()
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    app.all_file_data[idx + 1], app.all_file_data[idx] = app.all_file_data[idx], app.all_file_data[idx + 1]
    app._model_search_cache = {}
    paged_cache_rebuild_filtered_indices(app)
    app.current_page_index = (idx + 1) // max(1, app.page_size)
    app.render_current_page()
    app.mark_unsaved()


def undo_delete(app, *, messagebox_module, runtime_clear_compact_card_cache, runtime_clear_standard_card_pool, paged_cache_rebuild_filtered_indices):
    if not app.deleted_stack:
        messagebox_module.showinfo("Undo", "Nothing to undo.", parent=app)
        return
    data = app.deleted_stack.pop()
    model = data.get("model")
    idx = min(int(data.get("idx", len(app.all_file_data))), len(app.all_file_data))
    runtime_clear_compact_card_cache(app, destroy=True)
    runtime_clear_standard_card_pool(app, destroy=True)
    app.all_file_data.insert(idx, model)
    app._model_search_cache = {}
    paged_cache_rebuild_filtered_indices(app)
    app.current_page_index = idx // max(1, app.page_size)
    app.render_current_page()
    app.mark_unsaved()
