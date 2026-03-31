def start_render_paged(
    app,
    data_list,
    rid,
    errors,
    *,
    page_size_value,
    perf68_model_cache,
    perf68_prime_model_caches,
    paged_profile_mark,
    paged_profile_finish,
):
    if rid != app.load_id:
        return
    app.all_file_data = list(data_list or [])
    app.loaded_count = len(app.all_file_data)
    app.pending_errors = errors
    app.page_size = page_size_value(app)
    app.current_page_index = 0
    app._model_search_cache = {}
    app._perf68_cache_queue = []
    app._rebuild_filtered_model_indices()
    try:
        size = max(1, int(getattr(app, "page_size", 25) or 25))
        visible = list(getattr(app, "filtered_model_indices", []) or [])[:size]
        for idx in visible:
            perf68_model_cache(app, idx, app.all_file_data[idx])
    except Exception:
        pass
    app.render_current_page()
    try:
        app.after(5, lambda s=app: perf68_prime_model_caches(s, page_hint=getattr(s, "current_page_index", 0), chunk_size=120))
    except Exception:
        pass
    app._is_loading = False
    app.validation_state = "Not checked"
    app.mark_saved()
    paged_profile_mark(app, "render_done")
    paged_profile_finish(app, total_rules=len(app.all_file_data), rendered_cards=len(app.rule_cards))
    if app.loading_modal:
        try:
            app.loading_modal.safe_close()
        except Exception:
            pass
        app.loading_modal = None
    if app.pending_errors:
        app.syntax_errors = app.pending_errors
        app.pending_errors = []


def render_current_page(app, *, perf67_render_current_page, perf68_prime_model_caches):
    perf67_render_current_page(app)
    if bool(getattr(getattr(app, "performance_mode", None), "get", lambda: False)()):
        try:
            current_page = int(getattr(app, "current_page_index", 0) or 0)
            if getattr(app, "_perf68_prefetch_page", None) != current_page:
                app._perf68_prefetch_page = current_page
                app.after(10, lambda s=app: perf68_prime_model_caches(s, page_hint=min(getattr(s, "current_page_index", 0) + 1, 999999), chunk_size=80))
        except Exception:
            pass


def perf_enabled(app):
    try:
        return bool(app.performance_mode.get())
    except Exception:
        return bool((getattr(app, "shortcuts", {}) or {}).get("performance_mode", True))


def _page_choice_size(choice):
    raw = str(choice or "").strip().lower()
    if raw == "all":
        return 10**9
    digits = "".join(ch for ch in raw if ch.isdigit())
    try:
        return max(1, int(digits or "50"))
    except Exception:
        return 50


def _standard_page_soft_cap(app):
    total = len(getattr(app, "filtered_model_indices", []) or getattr(app, "all_file_data", []) or [])
    if total >= 400:
        return 10
    if total >= 120:
        return 25
    return None


def _coerce_standard_page_choice(app, choice, valid_choices):
    choice = str(choice or "25 / page")
    if choice not in valid_choices:
        choice = "25 / page"
    cap = _standard_page_soft_cap(app)
    if cap is None or _page_choice_size(choice) <= cap:
        return choice
    return f"{cap} / page"


def perf_page_size_choice(app, enabled, valid_choices):
    if enabled:
        choice = str(getattr(app, "performance_page_size_choice", "10 / page") or "10 / page")
        if choice not in valid_choices or choice == "All":
            choice = "10 / page"
            app.performance_page_size_choice = choice
        return choice
    choice = str(getattr(app, "_runtime_prev_page_size", "25 / page") or "25 / page")
    return _coerce_standard_page_choice(app, choice, valid_choices)


def sync_perf_button(app, perf_enabled_func):
    btn = getattr(app, "performance_mode_bottom_button", None)
    if btn is None:
        return
    enabled = perf_enabled_func(app)
    try:
        if enabled:
            btn.configure(
                text="PERFORMANCE ON",
                text_color="#000000",
                border_width=2,
                border_color="#8ef0a8",
                fg_color="#16a34a",
                hover_color="#22c55e",
            )
        else:
            btn.configure(
                text="PERFORMANCE OFF",
                text_color="#ffffff",
                border_width=2,
                border_color="#6f8aa3",
                fg_color="#2c3e50",
                hover_color="#3d566e",
            )
    except Exception:
        pass


def update_status_bar(app, app_version, status_rule_count_paged, perf_enabled_func, validation_state=None):
    if validation_state is not None:
        app.validation_state = validation_state
    file_name = app.current_file.split("\\")[-1] if app.current_file else "No file loaded"
    page_txt = ""
    try:
        page_txt = f" [ {app.page_status_var.get()} ]"
    except Exception:
        pass
    prof = f" [ {app.last_profile_summary} ]" if getattr(app, "last_profile_summary", "") else ""
    mode_txt = "Performance" if perf_enabled_func(app) else "Standard"
    text = (
        f"[ File: {file_name} ] [ {app._status_save_text()} ] "
        f"[ Rules: {status_rule_count_paged(app)} ]{page_txt} [ Mode: {mode_txt} ] "
        f"[ {app.validation_state} ] [ {app_version} ]{prof}"
    )
    if hasattr(app, "status_label") and app.status_label.winfo_exists():
        status_color = "#c9a063"
        if app.unsaved_changes:
            status_color = "#f1c40f"
        if str(app.validation_state).lower() in {"error", "partial load"}:
            status_color = "#ff7675"
        app.status_label.configure(text=text, text_color=status_color)


def change_page_size(
    app,
    *,
    perf_enabled_func,
    valid_choices,
    page_size_value,
    paged_cache_clear,
    paged_cache_rebuild_filtered_indices,
    runtime_prime_visible_models,
):
    current_choice = ""
    try:
        current_choice = str(app.page_size_var.get() or "")
    except Exception:
        pass
    if perf_enabled_func(app):
        if current_choice in valid_choices and current_choice != "All":
            app.performance_page_size_choice = current_choice
    elif current_choice in valid_choices:
        app._runtime_prev_page_size = current_choice
        coerced_choice = _coerce_standard_page_choice(app, current_choice, valid_choices)
        if coerced_choice != current_choice:
            current_choice = coerced_choice
            try:
                app.page_size_var.set(current_choice)
            except Exception:
                pass
    app.page_size = page_size_value(app)
    app.current_page_index = 0
    app._sync_current_page_to_models()
    app._filter_revision = int(getattr(app, "_filter_revision", 0) or 0) + 1
    paged_cache_clear(app, destroy=True, keep_current=False)
    paged_cache_rebuild_filtered_indices(app)
    app.render_current_page()
    runtime_prime_visible_models(app)


def apply_performance_mode(
    app,
    *,
    perf_enabled_func,
    perf_page_size_choice_func,
    valid_choices,
    sync_perf_button_func,
    runtime_change_page_size,
    paged_cache_rebuild_filtered_indices,
    runtime_clear_compact_card_cache,
    runtime_prime_visible_models,
    refresh=True,
    persist=True,
    force_rebuild=False,
):
    enabled = perf_enabled_func(app)
    current_choice = ""
    try:
        current_choice = str(app.page_size_var.get() or "")
    except Exception:
        pass
    if enabled and current_choice in valid_choices and current_choice != getattr(app, "performance_page_size_choice", "10 / page"):
        app._runtime_prev_page_size = current_choice
    target_choice = perf_page_size_choice_func(app, enabled)
    changed = False
    try:
        if str(app.page_size_var.get() or "") != target_choice:
            app.page_size_var.set(target_choice)
            changed = True
    except Exception:
        pass
    try:
        if hasattr(app, "shortcuts") and isinstance(app.shortcuts, dict):
            app.shortcuts["performance_mode"] = enabled
            app.shortcuts["performance_page_size"] = str(getattr(app, "performance_page_size_choice", "10 / page") or "10 / page")
    except Exception:
        pass
    sync_perf_button_func(app)
    if persist:
        try:
            app.save_config()
        except Exception:
            pass
    if refresh:
        if force_rebuild:
            try:
                runtime_clear_compact_card_cache(app, destroy=True)
            except Exception:
                pass
        if changed:
            runtime_change_page_size(app)
        elif force_rebuild:
            paged_cache_rebuild_filtered_indices(app)
            app.render_current_page()
            runtime_prime_visible_models(app)
        else:
            app.render_current_page()
            runtime_prime_visible_models(app)
    else:
        try:
            app.update_status_bar()
        except Exception:
            pass


def toggle_performance(app, *, perf_enabled_func, runtime_apply_performance_mode):
    try:
        app.performance_mode.set(not perf_enabled_func(app))
    except Exception:
        return
    runtime_apply_performance_mode(app, refresh=True, persist=True, force_rebuild=True)


def go_prev_page(app, *, runtime_prime_visible_models):
    if app.current_page_index <= 0:
        return
    app._sync_current_page_to_models()
    app.current_page_index -= 1
    app.render_current_page()
    runtime_prime_visible_models(app, chunk_size=80)


def go_next_page(app, *, runtime_prime_visible_models):
    total = len(getattr(app, "filtered_model_indices", []) or [])
    size = max(1, int(getattr(app, "page_size", 50) or 50))
    pages = max(1, ((total - 1) // size) + 1) if total else 1
    if app.current_page_index >= pages - 1:
        return
    app._sync_current_page_to_models()
    app.current_page_index += 1
    app.render_current_page()
    runtime_prime_visible_models(app, chunk_size=80)


def filter_rule_cards(app, *, paged_cache_rebuild_filtered_indices, runtime_prime_visible_models):
    app.current_page_index = 0
    paged_cache_rebuild_filtered_indices(app)
    app.render_current_page()
    runtime_prime_visible_models(app)


def repack_cards(app, *, runtime_prime_visible_models):
    app.render_current_page()
    runtime_prime_visible_models(app, chunk_size=80)


def schedule_rule_filter(app, *, runtime_filter_rule_cards):
    try:
        if getattr(app, "_rule_filter_after", None):
            app.after_cancel(app._rule_filter_after)
    except Exception:
        pass
    query = app.rule_search_var.get().strip() if hasattr(app, "rule_search_var") else ""
    delay = 90 if query else 20
    try:
        app._rule_filter_after = app.after(delay, lambda s=app: runtime_filter_rule_cards(s))
    except Exception:
        runtime_filter_rule_cards(app)


def run_rule_filter(app, *, runtime_filter_rule_cards):
    app._rule_filter_after = None
    runtime_filter_rule_cards(app)


def init_runtime(app, paged_cache_init, valid_choices, runtime_apply_performance_mode, *args, **kwargs):
    paged_cache_init(app, *args, **kwargs)
    shortcuts = dict(getattr(app, "shortcuts", {}) or {})
    import tkinter as tk

    app.performance_mode = tk.BooleanVar(value=bool(shortcuts.get("performance_mode", True)))
    perf_page_choice = str(shortcuts.get("performance_page_size", "") or "").strip()
    if perf_page_choice in {"", "25 / page"}:
        perf_page_choice = "10 / page"
    app.performance_page_size_choice = perf_page_choice
    try:
        current_choice = str(app.page_size_var.get() or "").strip()
    except Exception:
        current_choice = ""
    if current_choice not in valid_choices or current_choice == "50 / page":
        current_choice = "25 / page"
    app._runtime_prev_page_size = current_choice
    try:
        app.after_idle(lambda s=app: runtime_apply_performance_mode(s, refresh=False, persist=False))
    except Exception:
        runtime_apply_performance_mode(app, refresh=False, persist=False)


def start_render(app, data_list, rid, errors, *, runtime_clear_compact_card_cache, runtime_clear_standard_card_pool, paged_runtime_start_render):
    runtime_clear_compact_card_cache(app, destroy=True)
    try:
        runtime_clear_standard_card_pool(app, destroy=True)
    except Exception:
        pass
    return paged_runtime_start_render(app, data_list, rid, errors)
