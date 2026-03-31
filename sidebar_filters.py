from typing import Callable


def filter_sidebar_sections(
    app,
    widgets,
    query,
    cache_attr,
    after_attr,
    *,
    refresh_delay=25,
    body_limit=36,
    display_label: Callable[[str], str],
):
    q = str(query or "").lower().strip()
    cache = getattr(app, cache_attr, None)
    if cache == q:
        return
    setattr(app, cache_attr, q)

    try:
        pending = getattr(app, after_attr, None)
        if pending:
            app.after_cancel(pending)
    except Exception:
        pass
    setattr(app, after_attr, None)

    widgets = list(widgets or [])
    total = len(widgets)
    idx = 0

    def _apply_section(entry):
        if len(entry) == 3:
            header_btn, item_btns, cat_name = entry
        else:
            header_btn, item_btns, cat_name, _icon = entry
        section = header_btn.master
        cat_label = str(cat_name).lower()
        if not q:
            section.pack(fill="x", expand=False)
            if getattr(section, "_body_visible", False):
                for btn in item_btns[:body_limit]:
                    try:
                        btn.pack_forget()
                    except Exception:
                        pass
            section._body_visible = False
            try:
                header_btn.configure(text=display_label(cat_name))
            except Exception:
                pass
            return

        matches = []
        for btn in item_btns:
            label_cache = getattr(btn, "_perf76_label_lower", None)
            if label_cache is None:
                try:
                    label_cache = btn.cget("text").strip().lower()
                except Exception:
                    label_cache = ""
                btn._perf76_label_lower = label_cache
            if q in label_cache or q in cat_label:
                matches.append(btn)

        if matches:
            section.pack(fill="x", expand=False)
            for btn in item_btns:
                try:
                    btn.pack_forget()
                except Exception:
                    pass
            for btn in matches[:body_limit]:
                try:
                    btn.pack(fill="x", pady=1)
                except Exception:
                    pass
            section._body_visible = True
            try:
                header_btn.configure(text=display_label(cat_name))
            except Exception:
                pass
        else:
            for btn in item_btns:
                try:
                    btn.pack_forget()
                except Exception:
                    pass
            try:
                section.pack_forget()
            except Exception:
                pass
            section._body_visible = False

    def _step():
        nonlocal idx
        end = min(idx + 8, total)
        while idx < end:
            try:
                _apply_section(widgets[idx])
            except Exception:
                pass
            idx += 1
        if idx < total:
            try:
                setattr(app, after_attr, app.after(1, _step))
            except Exception:
                _step()
        else:
            setattr(app, after_attr, None)
            try:
                app.after(refresh_delay, app._refresh_sidebars)
            except Exception:
                pass

    _step()


def filter_catalog(app, display_label: Callable[[str], str]):
    return filter_sidebar_sections(
        app,
        getattr(app, "catalog_widgets", []),
        app.cat_search_var.get() if hasattr(app, "cat_search_var") else "",
        "_perf76_last_catalog_query",
        "_perf76_catalog_after_id",
        refresh_delay=20,
        body_limit=40,
        display_label=display_label,
    )


def filter_library(app, display_label: Callable[[str], str]):
    return filter_sidebar_sections(
        app,
        getattr(app, "library_widgets", []),
        app.lib_search_var.get() if hasattr(app, "lib_search_var") else "",
        "_perf76_last_library_query",
        "_perf76_library_after_id",
        refresh_delay=20,
        body_limit=32,
        display_label=display_label,
    )
