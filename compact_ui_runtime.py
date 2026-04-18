import os
import tkinter as tk

import customtkinter as ctk


def compact_title(model, friendly_item_display_name, title_separator="  â€¢  "):
    if not model:
        return "Item"
    name = str(model.get("name", "") or "Item").strip() or "Item"
    raw_type = str(model.get("type", "") or "").strip()
    friendly = friendly_item_display_name(raw_type) if raw_type else ""
    if friendly and friendly.lower() != name.lower():
        return f"{name}{title_separator}{friendly}"
    return name


def compact_summary(model, flat_stat_map, preview_joiner=" Â· "):
    if not model:
        return ""
    quality = str(model.get("quality", "normal") or "normal").strip().title()
    stats = list(model.get("stats", []) or [])
    adv = list(model.get("advanced_clauses", []) or [])
    extras = list(model.get("base_extra_conditions", []) or [])
    bits = [quality]
    preview_stats = []
    for key, op, val in stats[:3]:
        key_text = flat_stat_map.get(str(key).lower(), str(key))
        preview_stats.append(f"{key_text} {op} {val}")
    if preview_stats:
        bits.append(preview_joiner.join(preview_stats))
    if len(stats) > 3:
        bits.append(f"+{len(stats)-3} more stats")
    if adv:
        bits.append(f"{len(adv)} advanced")
    if extras:
        bits.append(f"{len(extras)} extra condition{'s' if len(extras) != 1 else ''}")
    if model.get("is_disabled"):
        bits.append("Disabled")
    return "   |   ".join([b for b in bits if b])


class CompactCommentCard(ctk.CTkFrame):
    def __init__(self, parent, model, app_ref, model_index):
        super().__init__(parent, fg_color="#101010", border_width=1, border_color="#3a3a3a", corner_radius=10)
        self.app_ref = app_ref
        self.model = model or {}
        self._model_index = model_index
        self.is_comment = True
        self.hide_in_ui = bool(self.model.get("hide_in_ui", False))
        self.display_name = str(self.model.get("name", "") or "Section")
        self.grid_columnconfigure(0, weight=1)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=10, pady=8)
        row.grid_columnconfigure(0, weight=1)

        label_text = self.display_name or "Section"
        self.name_label = ctk.CTkLabel(
            row,
            text=f"// {label_text}",
            anchor="w",
            font=(getattr(app_ref, "d2_font_name", "Segoe UI"), 16, "bold"),
            text_color="#c9a063",
        )
        self.name_label.grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")
        self.edit_btn = ctk.CTkButton(btns, text="EDIT", width=64, height=30, fg_color="#2c3e50", hover_color="#3d566e", command=self.open_editor)
        self.edit_btn.pack(side="left", padx=3)
        self.up_btn = ctk.CTkButton(btns, text="â†‘", width=36, height=30, fg_color="#3a3a3a", hover_color="#505050", command=lambda: self.app_ref.move_card_up(self))
        self.up_btn.pack(side="left", padx=3)
        self.down_btn = ctk.CTkButton(btns, text="â†“", width=36, height=30, fg_color="#3a3a3a", hover_color="#505050", command=lambda: self.app_ref.move_card_down(self))
        self.down_btn.pack(side="left", padx=3)
        self.del_btn = ctk.CTkButton(btns, text="DEL", width=56, height=30, fg_color="#7a1f1f", hover_color="#922b2b", command=lambda: self.app_ref.del_card(self))
        self.del_btn.pack(side="left", padx=3)

        for widget in (self, row, self.name_label):
            try:
                widget.bind("<Button-1>", lambda e, s=self: self.app_ref.set_active(s))
            except Exception:
                pass

    def set_active(self, is_active):
        try:
            self.configure(border_color="#f1c40f" if is_active else "#3a3a3a")
        except Exception:
            pass

    def open_editor(self):
        try:
            self.app_ref.open_compact_editor(self)
        except Exception:
            pass


class CompactItemCard(ctk.CTkFrame):
    def __init__(self, parent, model, app_ref, model_index, *, title_builder, summary_builder):
        super().__init__(parent, fg_color="#111111", border_width=1, border_color="#333333", corner_radius=10)
        self.app_ref = app_ref
        self.model = model or {}
        self._model_index = model_index
        self.is_comment = False
        self.is_collapsed = True
        self._is_hydrated = True
        self.raw_line = self.model.get("raw_line", "")
        self.display_name = str(self.model.get("name", "") or "Item")
        self.type_field = str(self.model.get("type_field", "name") or "name")
        self.is_disabled = bool(self.model.get("is_disabled", False))
        self.base_extra_conditions = list(self.model.get("base_extra_conditions", []) or [])
        self.grid_columnconfigure(0, weight=1)

        row = ctk.CTkFrame(self, fg_color="transparent")
        row.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        row.grid_columnconfigure(0, weight=1)

        title = title_builder(self.model)
        title_color = "#a8d8ff" if not self.is_disabled else "#888888"
        self.name_label = ctk.CTkLabel(
            row,
            text=title,
            anchor="w",
            font=(getattr(app_ref, "d2_font_name", "Segoe UI"), 16, "bold"),
            text_color=title_color,
        )
        self.name_label.grid(row=0, column=0, sticky="w")

        btns = ctk.CTkFrame(row, fg_color="transparent")
        btns.grid(row=0, column=1, sticky="e")
        self.edit_btn = ctk.CTkButton(btns, text="EDIT", width=64, height=30, fg_color="#2c3e50", hover_color="#3d566e", command=self.open_editor)
        self.edit_btn.pack(side="left", padx=3)
        self.clone_btn = ctk.CTkButton(btns, text="COPY", width=64, height=30, fg_color="#375a2c", hover_color="#44753a", command=lambda: self.app_ref.clone(self))
        self.clone_btn.pack(side="left", padx=3)
        self.up_btn = ctk.CTkButton(btns, text="â†‘", width=36, height=30, fg_color="#3a3a3a", hover_color="#505050", command=lambda: self.app_ref.move_card_up(self))
        self.up_btn.pack(side="left", padx=3)
        self.down_btn = ctk.CTkButton(btns, text="â†“", width=36, height=30, fg_color="#3a3a3a", hover_color="#505050", command=lambda: self.app_ref.move_card_down(self))
        self.down_btn.pack(side="left", padx=3)
        self.del_btn = ctk.CTkButton(btns, text="DEL", width=56, height=30, fg_color="#7a1f1f", hover_color="#922b2b", command=lambda: self.app_ref.del_card(self))
        self.del_btn.pack(side="left", padx=3)

        self.summary_label = ctk.CTkLabel(
            self,
            text=summary_builder(self.model),
            anchor="w",
            justify="left",
            font=(getattr(app_ref, "d2_font_name", "Segoe UI"), 13),
            text_color="#b8b8b8",
        )
        self.summary_label.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

        for widget in (self, row, self.name_label, self.summary_label):
            try:
                widget.bind("<Button-1>", lambda e, s=self: self.app_ref.set_active(s))
                widget.bind("<Double-Button-1>", lambda e, s=self: self.app_ref.open_compact_editor(s))
            except Exception:
                pass

    def set_active(self, is_active):
        try:
            self.configure(border_color="#f1c40f" if is_active else "#333333")
        except Exception:
            pass

    def open_editor(self):
        try:
            self.app_ref.open_compact_editor(self)
        except Exception:
            pass


class _PerfCompactRowBase(tk.Frame):
    def __init__(self, parent, model, app_ref, model_index, *, bg, border_color, active_border_color, title, title_color, summary=""):
        super().__init__(
            parent,
            bg=bg,
            bd=0,
            highlightthickness=1,
            highlightbackground=border_color,
            highlightcolor=border_color,
            cursor="hand2",
            takefocus=1,
        )
        self.app_ref = app_ref
        self.model = model or {}
        self._model_index = model_index
        self._bg = bg
        self._border_color = border_color
        self._active_border_color = active_border_color
        self._actions_menu = None
        self.raw_line = self.model.get("raw_line", "")

        self.name_label = tk.Label(
            self,
            text=title,
            anchor="w",
            justify="left",
            font=(getattr(app_ref, "d2_font_name", "Segoe UI"), 15, "bold"),
            fg=title_color,
            bg=bg,
            cursor="hand2",
        )
        self.name_label.pack(fill="x", padx=10, pady=(8, 0))

        self.summary_label = None
        if summary:
            self.summary_label = tk.Label(
                self,
                text=summary,
                anchor="w",
                justify="left",
                font=(getattr(app_ref, "d2_font_name", "Segoe UI"), 12),
                fg="#b8b8b8",
                bg=bg,
                cursor="hand2",
            )
            self.summary_label.pack(fill="x", padx=10, pady=(3, 8))
        else:
            self.name_label.configure(pady=8)

        self._bind_row_events(self, self.name_label, self.summary_label)

    def _bind_row_events(self, *widgets):
        for widget in widgets:
            if widget is None:
                continue
            try:
                widget.bind("<Button-1>", self._select_card, add="+")
                widget.bind("<Double-Button-1>", self._open_from_event, add="+")
                widget.bind("<Button-3>", self._show_actions_menu, add="+")
            except Exception:
                pass

    def _select_card(self, event=None):
        try:
            self.focus_set()
        except Exception:
            pass
        try:
            self.app_ref.set_active(self)
        except Exception:
            pass
        return "break"

    def _open_from_event(self, event=None):
        self._select_card(event)
        self.open_editor()
        return "break"

    def _menu_actions(self):
        return []

    def _build_actions_menu(self):
        menu = tk.Menu(self, tearoff=False, bg="#181818", fg="#f3f3f3", activebackground="#2c3e50", activeforeground="#ffffff")
        menu.add_command(label="Edit", command=self.open_editor)
        for label, callback in self._menu_actions():
            if label == "-":
                menu.add_separator()
            else:
                menu.add_command(label=label, command=callback)
        return menu

    def _show_actions_menu(self, event=None):
        self._select_card(event)
        menu = self._actions_menu
        if menu is None:
            menu = self._build_actions_menu()
            self._actions_menu = menu
        try:
            x = event.x_root if event is not None else self.winfo_rootx() + 24
            y = event.y_root if event is not None else self.winfo_rooty() + 24
            menu.tk_popup(x, y)
        finally:
            try:
                menu.grab_release()
            except Exception:
                pass
        return "break"

    def set_active(self, is_active):
        border = self._active_border_color if is_active else self._border_color
        try:
            self.configure(highlightbackground=border, highlightcolor=border)
        except Exception:
            pass

    def open_editor(self):
        try:
            self.app_ref.open_compact_editor(self)
        except Exception:
            pass

    def destroy(self):
        menu = getattr(self, "_actions_menu", None)
        if menu is not None:
            try:
                menu.destroy()
            except Exception:
                pass
            self._actions_menu = None
        super().destroy()


class PerfCompactCommentRow(_PerfCompactRowBase):
    def __init__(self, parent, model, app_ref, model_index):
        self.model = model or {}
        self.is_comment = True
        self.hide_in_ui = bool(self.model.get("hide_in_ui", False))
        self.display_name = str(self.model.get("name", "") or "Section")
        super().__init__(
            parent,
            self.model,
            app_ref,
            model_index,
            bg="#101010",
            border_color="#3a3a3a",
            active_border_color="#f1c40f",
            title=f"// {self.display_name or 'Section'}",
            title_color="#c9a063",
            summary="",
        )

    def _menu_actions(self):
        return [
            ("Move Up", lambda: self.app_ref.move_card_up(self)),
            ("Move Down", lambda: self.app_ref.move_card_down(self)),
            ("-", None),
            ("Delete", lambda: self.app_ref.del_card(self)),
        ]


class PerfCompactItemRow(_PerfCompactRowBase):
    def __init__(self, parent, model, app_ref, model_index, *, title_builder, summary_builder):
        self.model = model or {}
        self.is_comment = False
        self.is_collapsed = True
        self._is_hydrated = True
        self.display_name = str(self.model.get("name", "") or "Item")
        self.type_field = str(self.model.get("type_field", "name") or "name")
        self.is_disabled = bool(self.model.get("is_disabled", False))
        self.base_extra_conditions = list(self.model.get("base_extra_conditions", []) or [])
        super().__init__(
            parent,
            self.model,
            app_ref,
            model_index,
            bg="#111111",
            border_color="#333333",
            active_border_color="#f1c40f",
            title=title_builder(self.model),
            title_color="#888888" if self.is_disabled else "#a8d8ff",
            summary=summary_builder(self.model),
        )

    def _menu_actions(self):
        return [
            ("Copy", lambda: self.app_ref.clone(self)),
            ("Move Up", lambda: self.app_ref.move_card_up(self)),
            ("Move Down", lambda: self.app_ref.move_card_down(self)),
            ("-", None),
            ("Delete", lambda: self.app_ref.del_card(self)),
        ]


CompactItemCard.qual_menu = property(lambda self: type("X", (), {"get": lambda s: str((self.model.get("quality") or "normal")).strip().lower()})())
PerfCompactItemRow.qual_menu = property(lambda self: type("X", (), {"get": lambda s: str((self.model.get("quality") or "normal")).strip().lower()})())


def build_full_editor_card(
    app,
    parent,
    model,
    model_index,
    *,
    comment_rule_card_cls,
    item_rule_card_cls,
    flat_stat_map,
    apply_rune_state_to_card,
):
    if model.get("is_comment"):
        card = comment_rule_card_cls(
            parent,
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
            parent,
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
            apply_rune_state_to_card(card)
            card.is_disabled = model.get("is_disabled", False)
            card.refresh_power_button()
            card.base_extra_conditions = list(model.get("base_extra_conditions", []) or [])
            for sk, op, val in list(model.get("stats", []) or []):
                stat_name = flat_stat_map.get(str(sk).lower(), sk)
                card.add_stat_visually(sk, stat_name, op, val)
            for clause in list(model.get("advanced_clauses", []) or []):
                card.add_advanced_clause(clause)
        finally:
            card._suspend_unsaved_mark = False
        card._last_saved_name = card.display_name
    card._model_index = model_index
    return card


def refresh_after_model_change(app, paged_cache_clear, paged_cache_rebuild_filtered_indices, preserve_page=True):
    app._model_search_cache = {}
    try:
        paged_cache_clear(app, destroy=True, keep_current=False)
    except Exception:
        pass
    current_page = int(getattr(app, "current_page_index", 0) or 0)
    paged_cache_rebuild_filtered_indices(app)
    if preserve_page:
        total = len(getattr(app, "filtered_model_indices", []) or [])
        pages = max(1, ((total - 1) // max(1, int(getattr(app, "page_size", 50) or 50))) + 1) if total else 1
        app.current_page_index = min(max(0, current_page), pages - 1)
    app.render_current_page()


def open_compact_editor(
    app,
    card,
    *,
    messagebox_module,
    configure_dialog_window,
    destroy_window_safely,
    compact_editor_builder,
    compact_editor_refresh,
    model_from_card,
    serialize_model_to_line,
):
    idx = getattr(card, "_model_index", None)
    if idx is None or idx < 0 or idx >= len(getattr(app, "all_file_data", []) or []):
        return
    model = dict(app.all_file_data[idx])
    top = ctk.CTkToplevel(app)
    top.title("Rule Editor")
    top.geometry("1220x860")
    top.minsize(900, 620)
    top.configure(fg_color="#0b0b0b")
    configure_dialog_window(top, app, modal=True)
    top.grid_columnconfigure(0, weight=1)
    top.grid_rowconfigure(1, weight=1)

    hdr = ctk.CTkFrame(top, fg_color="transparent")
    hdr.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
    hdr.grid_columnconfigure(0, weight=1)
    ctk.CTkLabel(hdr, text="Full Rule Editor", font=("Segoe UI", 22, "bold"), text_color="#f1c40f").grid(row=0, column=0, sticky="w")
    ctk.CTkLabel(
        hdr,
        text="Performance Mode uses compact rows. Use this editor when you need full controls for one rule.",
        font=("Segoe UI", 12),
        text_color="#bbbbbb",
    ).grid(row=1, column=0, sticky="w", pady=(3, 0))

    body = ctk.CTkScrollableFrame(top, fg_color="#0f0f0f", border_width=1, border_color="#333333")
    body.grid(row=1, column=0, sticky="nsew", padx=14, pady=8)
    body.grid_columnconfigure(0, weight=1)

    editor_card = compact_editor_builder(app, body, model, idx)
    editor_card.pack(fill="x", padx=12, pady=12)
    try:
        if not getattr(editor_card, "is_comment", False):
            app.set_active(editor_card)
    except Exception:
        pass

    btns = ctk.CTkFrame(top, fg_color="transparent")
    btns.grid(row=2, column=0, sticky="e", padx=14, pady=(0, 12))

    def _save_close():
        try:
            new_model = model_from_card(app, editor_card)
            new_model["raw_line"] = serialize_model_to_line(app, new_model)
            app.all_file_data[idx] = new_model
            app.mark_unsaved()
            destroy_window_safely(top, app)
            compact_editor_refresh(app, preserve_page=True)
        except Exception as exc:
            messagebox_module.showerror("Save Failed", f"Could not save this rule editor:\n\n{exc}", parent=top)

    ctk.CTkButton(btns, text="Save Changes", width=130, fg_color="#27ae60", hover_color="#2ecc71", text_color="#000000", command=_save_close).pack(side="left", padx=6)
    ctk.CTkButton(btns, text="Cancel", width=110, fg_color="#5a1a1a", hover_color="#8a1a1a", command=lambda: destroy_window_safely(top, app)).pack(side="left", padx=6)


def build_compact_card_from_model(app, model, model_index, *, title_builder, summary_builder):
    if model.get("is_comment"):
        return PerfCompactCommentRow(app.card_scroll, model, app, model_index)
    return PerfCompactItemRow(app.card_scroll, model, app, model_index, title_builder=title_builder, summary_builder=summary_builder)


def render_current_page(app, standard_render_current_page, runtime_get_compact_card):
    perf = bool(getattr(getattr(app, "performance_mode", None), "get", lambda: False)())
    if not perf:
        return standard_render_current_page(app)

    indices = list(getattr(app, "filtered_model_indices", []) or [])
    size = max(1, int(getattr(app, "page_size", 25) or 25))
    start = app.current_page_index * size
    end = start + size
    page_indices = indices[start:end]
    target_key = ("compact", int(getattr(app, "_filter_revision", 0) or 0), int(size), int(app.current_page_index))

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
        for model_index in page_indices:
            model = app.all_file_data[model_index]
            card = runtime_get_compact_card(app, model_index, model)
            cards.append(card)
        entry = {"frame": None, "cards": cards, "page_indices": list(page_indices), "dirty": False, "compact": True}
        cache[target_key] = entry
        app._page_widget_cache = cache

    app.rule_cards = list(entry.get("cards", []) or [])
    if getattr(app, "active_card", None) not in app.rule_cards:
        app.active_card = None
    for card in app.rule_cards:
        try:
            card.pack(fill="x", pady=6, padx=10)
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
            text=f"Editing: {os.path.basename(app.current_file) if app.current_file else 'No file'} ({loaded} visible / {total} matched / {full} total) [Compact]"
        )
    try:
        app.after_idle(app.update_status_bar)
    except Exception:
        app.update_status_bar()
