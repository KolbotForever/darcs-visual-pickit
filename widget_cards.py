import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from advanced_clause_ui import (
    AdvancedClauseEditor,
    NumericStatIdMappingDialog,
    RawLineInspectorDialog,
    format_numeric_stat_id_lines,
)
from editor_dialogs import SnippetImportDialog, StatSearchDialog, TypeSearchDialog
from nip_parser import (
    RESIST_ALIAS_TEXT,
    RESIST_COLOR_MAP,
    build_advanced_alias_expression,
    extract_numeric_stat_ids,
    parse_advanced_alias,
    summarize_advanced_expression,
    validate_advanced_expression,
)


_RUNTIME = {}


def configure_widget_cards_runtime(**deps):
    _RUNTIME.update(deps)


def _dep(name):
    if name not in _RUNTIME:
        raise RuntimeError(f"widget_cards dependency '{name}' has not been configured")
    return _RUNTIME[name]


class ToolTip:
    def __init__(self, widget, text, app_ref):
        self.widget = widget
        self.text = text
        self.app_ref = app_ref
        self.tip_win = None
        self._id = None
        widget.bind("<Enter>", self.schedule)
        widget.bind("<Leave>", self.hide)
        widget.bind("<Motion>", self.update_pos)
        widget.bind("<ButtonPress>", self.hide, add="+")

    def update_pos(self, event):
        if self.tip_win:
            self.tip_win.wm_geometry(f"+{event.x_root + 20}+{event.y_root + 20}")

    def schedule(self, event=None):
        self.hide()
        if not self.app_ref.tooltips_enabled.get():
            return
        if event:
            self.update_pos(event)
        self._id = self.widget.after(300, self.show)

    def show(self):
        if self.tip_win or not self.text or not self.widget.winfo_exists():
            return
        self.tip_win = tw = tk.Toplevel(self.widget)
        txt = self.text() if callable(self.text) else self.text
        tw.title("Hint")
        tw.resizable(False, False)
        try:
            tw.transient(self.widget.winfo_toplevel())
        except Exception:
            pass
        _dep("apply_window_icon")(tw)
        tk.Label(
            tw,
            text=txt,
            justify="left",
            background="#1a1a1a",
            foreground="#d4d4d4",
            relief="solid",
            borderwidth=1,
            font=("Arial", 11),
        ).pack(ipadx=6, ipady=3)
        tw.update_idletasks()
        tw.wm_geometry(
            f"+{self.widget.winfo_rootx() + 20}+{self.widget.winfo_rooty() + self.widget.winfo_height() + 5}"
        )
        _dep("nudge_window_paint")(tw)

    def hide(self, event=None):
        if self._id:
            self.widget.after_cancel(self._id)
            self._id = None
        if self.tip_win:
            _dep("destroy_window_safely")(self.tip_win, self.widget.winfo_toplevel())
            self.tip_win = None


class StatWidget(ctk.CTkFrame):
    def __init__(
        self,
        master,
        stat_key,
        stat_name,
        op=">=",
        val="0",
        delete_callback=None,
        font_data=None,
        app_ref=None,
        auto_pack=True,
    ):
        super().__init__(master, fg_color="#1a1a1a", height=55, corner_radius=6)
        stat_colors = _dep("stat_colors")
        stat_hints = _dep("stat_hints")
        op_map = _dep("op_map")

        self.stat_key = stat_key
        self.app_ref = app_ref
        text_color = "#d4d4d4"
        for key, color in stat_colors.items():
            if key in stat_key.lower() or key in stat_name.lower():
                text_color = color
                break
        stat_lbl = ctk.CTkLabel(self, text=stat_name, width=280, anchor="w", font=font_data["item"], text_color=text_color)
        stat_lbl.pack(side="left", padx=10)
        hint = stat_hints.get(stat_key.lower(), "")
        ToolTip(stat_lbl, (f"Attribute: {stat_name}\n{hint}" if hint else f"Attribute: {stat_name}"), app_ref)
        display_op = op_map.get(op, "Equal or Higher")
        self.op_menu = ctk.CTkComboBox(
            self,
            values=list(op_map.values()),
            width=240,
            height=36,
            font=font_data["item"],
            dropdown_font=font_data["d2"],
            state="readonly",
            corner_radius=4,
            dropdown_fg_color="#1a1a1a",
            dropdown_hover_color="#333",
            dropdown_text_color="#fff",
        )
        self.op_menu.set(display_op)
        self.op_menu.pack(side="left", padx=5)
        self.op_menu.configure(command=lambda v: app_ref.mark_unsaved())
        self.val_entry = ctk.CTkEntry(self, width=80, height=36, font=font_data["item"], corner_radius=4, fg_color="#0d0d0d")
        self.val_entry.insert(0, val)
        self.val_entry.pack(side="left", padx=5)
        self.val_entry.bind("<KeyRelease>", lambda e: app_ref.mark_unsaved())
        del_img, del_txt = app_ref.card_icons["delete"]
        font = ("Segoe UI Emoji", 24) if not del_img else None
        ctk.CTkButton(
            self,
            image=del_img,
            text=del_txt if not del_img else "",
            font=font,
            fg_color="#5a1a1a",
            hover_color="#8a1a1a",
            width=46,
            height=46,
            corner_radius=6,
            anchor="center",
            command=lambda: delete_callback(self),
        ).pack(side="right", padx=10)
        if auto_pack:
            self.pack(fill="x", pady=2, padx=4)


class AdvancedStatWidget(ctk.CTkFrame):
    def __init__(self, master, expression, delete_callback=None, font_data=None, app_ref=None, auto_pack=True):
        super().__init__(master, fg_color="#101010", height=55, corner_radius=6, border_width=1, border_color="#333333")
        self.expression = (expression or "").strip()
        self.delete_callback = delete_callback
        self.font_data = font_data
        self.app_ref = app_ref
        self.alias_info = None
        self.main = ctk.CTkFrame(self, fg_color="transparent")
        self.main.pack(fill="x", expand=True, padx=10, pady=4)
        self.rebuild_ui()
        if auto_pack:
            self.pack(fill="x", pady=2, padx=4)

    def rebuild_ui(self):
        for child in self.main.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass
        self.alias_info = parse_advanced_alias(self.expression)
        if self.alias_info:
            self._build_alias_ui()
        else:
            self._build_raw_ui()

    def _make_action_button(self, parent, text, command, width=92, fg="#2c3e50", hover="#34495e", text_color="#ffffff"):
        return ctk.CTkButton(
            parent,
            text=text,
            width=width,
            height=36,
            corner_radius=6,
            fg_color=fg,
            hover_color=hover,
            text_color=text_color,
            font=self.font_data["item"],
            command=command,
        )

    def _open_editor(self):
        self.expression = (self.expression or "").strip()
        while self.expression.startswith("#"):
            self.expression = self.expression[1:].strip()
        card_ids = []
        if hasattr(self, "master") and hasattr(self.master, "winfo_children"):
            for child in self.master.winfo_children():
                if isinstance(child, AdvancedStatWidget):
                    for sid in extract_numeric_stat_ids(child.get_expression()):
                        sid = str(sid).strip()
                        if sid and sid not in card_ids:
                            card_ids.append(sid)
        AdvancedClauseEditor(
            self.winfo_toplevel(),
            self.expression,
            self._save_expression_from_editor,
            self.app_ref,
            all_card_numeric_ids=card_ids,
            configure_dialog_window=_dep("configure_dialog_window"),
        )

    def _open_mapping_dialog(self):
        ids = []
        for sid in extract_numeric_stat_ids(self.expression):
            sid = str(sid).strip()
            if sid and sid not in ids:
                ids.append(sid)
        if hasattr(self, "master") and hasattr(self.master, "winfo_children"):
            for child in self.master.winfo_children():
                if isinstance(child, AdvancedStatWidget):
                    for sid in extract_numeric_stat_ids(child.get_expression()):
                        sid = str(sid).strip()
                        if sid and sid not in ids:
                            ids.append(sid)
        NumericStatIdMappingDialog(
            self.winfo_toplevel(),
            ids,
            app_ref=self.app_ref,
            on_save=self.rebuild_ui,
            configure_dialog_window=_dep("configure_dialog_window"),
        )

    def _save_expression_from_editor(self, new_expression: str):
        self.expression = (new_expression or "").strip()
        self.rebuild_ui()
        self.app_ref.mark_unsaved()

    def _build_alias_ui(self):
        flat_stat_map = _dep("flat_stat_map")
        display_label = _dep("display_label")
        op_map = _dep("op_map")

        left = ctk.CTkFrame(self.main, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(left, text="ADVANCED", width=110, anchor="w", font=self.font_data["item"], text_color="#f1c40f").pack(side="left", padx=(0, 8))

        badge = ctk.CTkFrame(left, fg_color="#141414", corner_radius=8, border_width=1, border_color="#444444")
        badge.pack(side="left", padx=(0, 10), pady=2)

        dots = ctk.CTkFrame(badge, fg_color="transparent")
        dots.pack(side="left", padx=(10, 6), pady=6)
        for stat in self.alias_info["stats"]:
            ctk.CTkLabel(dots, text="\u25a0", width=10, font=("Segoe UI", 12, "bold"), text_color=RESIST_COLOR_MAP.get(stat, "#cccccc")).pack(side="left", padx=1)

        self.alias_label = ctk.CTkLabel(
            badge,
            text=RESIST_ALIAS_TEXT.get(self.alias_info["kind"], "ADVANCED"),
            font=self.font_data["item"],
            text_color="#f5e6a6",
            anchor="w",
        )
        self.alias_label.pack(side="left", padx=(0, 10), pady=6)

        tooltip_label = " + ".join(display_label(flat_stat_map.get(stat, stat)) for stat in self.alias_info["stats"])
        ToolTip(self.alias_label, f"Friendly advanced alias for: {tooltip_label}", self.app_ref)

        display_op = op_map.get(self.alias_info["op"], "Equal or Higher")
        self.op_menu = ctk.CTkComboBox(
            left,
            values=list(op_map.values()),
            width=200,
            height=36,
            font=self.font_data["item"],
            dropdown_font=self.font_data["d2"],
            state="readonly",
            corner_radius=4,
            dropdown_fg_color="#1a1a1a",
            dropdown_hover_color="#333",
            dropdown_text_color="#fff",
        )
        self.op_menu.set(display_op)
        self.op_menu.pack(side="left", padx=5)
        self.op_menu.configure(command=lambda v: self.app_ref.mark_unsaved())

        self.val_entry = ctk.CTkEntry(left, width=90, height=36, font=self.font_data["item"], corner_radius=4, fg_color="#0d0d0d")
        self.val_entry.insert(0, self.alias_info["val"])
        self.val_entry.pack(side="left", padx=5)
        self.val_entry.bind("<KeyRelease>", lambda e: self.app_ref.mark_unsaved())

        btns = ctk.CTkFrame(self.main, fg_color="transparent")
        btns.pack(side="right", padx=(8, 10))
        expand_btn = self._make_action_button(btns, "Expand", self._open_editor, width=92, fg="#3a2f5c", hover="#51397e")
        expand_btn.pack(side="left", padx=5)
        ToolTip(expand_btn, "Open the advanced clause editor", self.app_ref)

        del_img, del_txt = self.app_ref.card_icons["delete"]
        font = ("Segoe UI Emoji", 24) if not del_img else None
        ctk.CTkButton(
            btns,
            image=del_img,
            text=del_txt if not del_img else "",
            font=font,
            fg_color="#5a1a1a",
            hover_color="#8a1a1a",
            width=46,
            height=46,
            corner_radius=6,
            anchor="center",
            command=lambda: self.delete_callback(self),
        ).pack(side="left", padx=5)

    def _build_raw_ui(self):
        left = ctk.CTkFrame(self.main, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True, padx=0)
        ctk.CTkLabel(left, text="ADVANCED", width=110, anchor="w", font=self.font_data["item"], text_color="#f1c40f").pack(side="left", padx=(0, 8))

        preview_box = ctk.CTkFrame(left, fg_color="#0d0d0d", border_width=1, border_color="#333333", corner_radius=6)
        preview_box.pack(side="left", fill="x", expand=True, padx=(0, 8))
        preview_text = self.expression if len(self.expression) <= 95 else self.expression[:92] + "..."
        self.preview_label = ctk.CTkLabel(preview_box, text=preview_text, anchor="w", justify="left", font=self.font_data["item"], text_color="#d9d9d9")
        self.preview_label.pack(fill="x", expand=True, padx=10, pady=(6, 2))

        valid, msg = validate_advanced_expression(self.expression)
        self.status_label = ctk.CTkLabel(
            preview_box,
            text=(("\u2713 " if valid else "\u26a0 ") + summarize_advanced_expression(self.expression)),
            anchor="w",
            justify="left",
            font=("Segoe UI", 11),
            text_color=("#2ecc71" if valid else "#ff7675"),
        )
        self.status_label.pack(fill="x", expand=True, padx=10, pady=(0, 3))
        numeric_map_lines = format_numeric_stat_id_lines(self.expression, self.app_ref)
        if numeric_map_lines:
            first = numeric_map_lines[0]
            more = "" if len(numeric_map_lines) == 1 else f" (+{len(numeric_map_lines) - 1} more)"
            self.unknown_label = ctk.CTkLabel(
                preview_box,
                text=f"Numeric stat ids: {first}{more}",
                anchor="w",
                justify="left",
                font=("Segoe UI", 10),
                text_color="#f5c16c",
            )
            self.unknown_label.pack(fill="x", expand=True, padx=10, pady=(0, 6))
            ToolTip(self.unknown_label, "\n".join(numeric_map_lines), self.app_ref)
        ToolTip(self.preview_label, self.expression, self.app_ref)

        btns = ctk.CTkFrame(self.main, fg_color="transparent")
        btns.pack(side="right", padx=(8, 10))
        expand_btn = self._make_action_button(btns, "Expand", self._open_editor, width=92, fg="#3a2f5c", hover="#51397e")
        expand_btn.pack(side="left", padx=5)
        ToolTip(expand_btn, "Open the advanced clause editor", self.app_ref)

        del_img, del_txt = self.app_ref.card_icons["delete"]
        font = ("Segoe UI Emoji", 24) if not del_img else None
        ctk.CTkButton(
            btns,
            image=del_img,
            text=del_txt if not del_img else "",
            font=font,
            fg_color="#5a1a1a",
            hover_color="#8a1a1a",
            width=46,
            height=46,
            corner_radius=6,
            anchor="center",
            command=lambda: self.delete_callback(self),
        ).pack(side="left", padx=5)

    def get_expression(self):
        inv_op_map = _dep("inv_op_map")
        if self.alias_info and hasattr(self, "op_menu") and hasattr(self, "val_entry"):
            op = inv_op_map.get(self.op_menu.get(), self.alias_info.get("op", ">="))
            value = self.val_entry.get().strip() or self.alias_info.get("val", "0")
            return build_advanced_alias_expression(self.alias_info, op, value)
        return (self.expression or "").strip()


class CommentRuleCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        display_name,
        delete_rule_callback,
        move_up_cb,
        move_down_cb,
        app_ref,
        raw_line=None,
        hide_in_ui=False,
    ):
        super().__init__(master, fg_color="#1a1a1a", border_width=1, border_color="#444", corner_radius=10)
        self.is_comment = True
        self.app_ref = app_ref
        self.stats = []
        self.is_collapsed = False
        self.raw_line = raw_line
        self.hide_in_ui = hide_in_ui

        row = ctk.CTkFrame(self, fg_color="transparent", height=40)
        row.pack(fill="x", pady=5, padx=10)
        ctk.CTkLabel(row, text="// ---", font=("Constantia", 18, "bold"), text_color="#7f8c8d").pack(side="left", padx=(0, 5))
        self.name_var = tk.StringVar(value=display_name)
        self.name_var.trace("w", lambda *a: app_ref.mark_unsaved())
        self.name_entry = ctk.CTkEntry(
            row,
            textvariable=self.name_var,
            font=("Constantia", 18, "bold"),
            fg_color="#0d0d0d",
            text_color="#7f8c8d",
        )
        self.name_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(row, text="---", font=("Constantia", 18, "bold"), text_color="#7f8c8d").pack(side="left", padx=(5, 10))

        btn_w, btn_h = 46, 46
        icon_font = ("Segoe UI Emoji", 24)
        del_img, del_txt = app_ref.card_icons["delete"]
        down_img, down_txt = app_ref.card_icons["down"]
        up_img, up_txt = app_ref.card_icons["up"]
        undo_img, undo_txt = app_ref.card_icons["undo"]

        ctk.CTkButton(
            row,
            image=del_img,
            text=del_txt if not del_img else "",
            font=icon_font if not del_img else None,
            fg_color="#5a1a1a",
            hover_color="#8a1a1a",
            width=btn_w,
            height=btn_h,
            corner_radius=6,
            anchor="center",
            command=lambda: delete_rule_callback(self),
        ).pack(side="right", padx=10)
        ctk.CTkButton(
            row,
            image=down_img,
            text=down_txt if not down_img else "",
            font=icon_font if not down_img else None,
            fg_color="#2c3e50",
            width=btn_w,
            height=btn_h,
            anchor="center",
            command=lambda: move_down_cb(self),
        ).pack(side="right", padx=4)
        ctk.CTkButton(
            row,
            image=up_img,
            text=up_txt if not up_img else "",
            font=icon_font if not up_img else None,
            fg_color="#2c3e50",
            width=btn_w,
            height=btn_h,
            anchor="center",
            command=lambda: move_up_cb(self),
        ).pack(side="right", padx=4)

        raw_btn = ctk.CTkButton(
            row,
            text="Raw",
            width=58,
            height=btn_h,
            fg_color="#6c5ce7",
            hover_color="#7d6ef0",
            command=self.open_raw_view,
        )
        raw_btn.pack(side="right", padx=6)
        ToolTip(raw_btn, "Inspect original raw line", app_ref)

        undo_btn = ctk.CTkButton(
            row,
            image=undo_img,
            text=undo_txt if not undo_img else "",
            font=icon_font if not undo_img else None,
            fg_color="#8e44ad",
            hover_color="#9b59b6",
            width=btn_w,
            height=btn_h,
            anchor="center",
            command=app_ref.undo_delete,
        )
        undo_btn.pack(side="right", padx=6)
        ToolTip(undo_btn, "Undo last deletion", app_ref)

    def open_raw_view(self):
        configure_dialog_window = _dep("configure_dialog_window")
        original = self.raw_line or f"// --- {self.display_name} ---"
        RawLineInspectorDialog(
            self.winfo_toplevel(),
            "Raw Comment Inspector",
            original,
            original,
            configure_dialog_window=configure_dialog_window,
        )

    @property
    def display_name(self):
        return self.name_var.get()

    def highlight_error(self, err):
        pass

    def set_active(self, active):
        pass

    def toggle_collapse(self):
        pass


class ItemRuleCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        display_name,
        quality,
        delete_rule_callback,
        clone_callback,
        set_active_callback,
        font_data=None,
        app_ref=None,
        move_up_cb=None,
        move_down_cb=None,
    ):
        quality_colors = _dep("quality_colors")
        parse_rule_line = _dep("parse_rule_line")
        flat_stat_map = _dep("flat_stat_map")
        apply_window_icon = _dep("apply_window_icon")
        configure_dialog_window = _dep("configure_dialog_window")

        self.base_color = quality_colors.get(quality.lower(), "#444")
        self.app_ref = app_ref
        self._delete_rule_callback = delete_rule_callback
        self._clone_callback = clone_callback
        self._move_up_cb = move_up_cb
        self._move_down_cb = move_down_cb
        self.display_name = display_name
        self.raw_line = None
        self.font_data = font_data
        self.is_collapsed = False
        super().__init__(master, fg_color="#121212", border_width=1, border_color="#262626", corner_radius=10)
        self.stats = []
        self.advanced_clauses = []
        self.pending_stats_data = []
        self.pending_advanced_data = []
        self._summary_stat_count = 0
        self._summary_advanced_count = 0
        self._is_hydrated = True
        self._deferred_hint = None
        self._deferred_summary_frame = None
        self._deferred_summary_var = tk.StringVar(value="")
        self._deferred_summary_hint = None
        self._hover_hydration_after = None
        self._hover_hydration_delay_ms = 220
        self._suspend_unsaved_mark = False
        self.base_extra_conditions = []
        self.is_disabled = False
        self.type_field = "name"
        self.current_type_raw = "item"
        self._quality_value = str(quality or "normal").strip().lower() or "normal"
        self._quality_locked = False
        self._header_controls_active = False
        self._header_row = None
        self.type_btn = None
        self.qual_menu = None
        self._type_summary_label = None
        self._quality_summary_label = None
        self._conditions_revealed = False
        self._user_revealed_conditions = False
        self._actions_tray = None
        self._actions_visible = False

        self.indicator = ctk.CTkFrame(self, width=6, fg_color=self.base_color, corner_radius=0)
        self.indicator.pack(side="left", fill="y")

        row = ctk.CTkFrame(self, fg_color="transparent", height=55)
        row.pack(fill="x", pady=8, padx=(10, 5))
        self._header_row = row

        self.toggle_btn = ctk.CTkButton(
            row,
            text="\u25bc",
            width=30,
            height=40,
            font=("Arial", 12),
            fg_color="#1a1a1a",
            hover_color="#333",
            command=self.toggle_collapse,
        )
        self.toggle_btn.pack(side="left", padx=5)

        self.name_label = ctk.CTkLabel(
            row,
            text=display_name,
            font=("Constantia", 18, "bold"),
            text_color=self.base_color,
            width=120,
            anchor="w",
        )
        self.name_label.pack(side="left", padx=5)
        ToolTip(self.name_label, lambda: f"Item rule: {self.display_name}", app_ref)
        self._build_header_summaries()

        btn_w, btn_h = 46, 46

        self.power_btn = ctk.CTkButton(
            row,
            text="\u23fb",
            width=btn_w,
            height=btn_h,
            corner_radius=6,
            font=("Segoe UI Symbol", 20, "bold"),
            command=self.toggle_disabled_state,
        )
        self.power_btn.pack(side="right", padx=6)
        ToolTip(self.power_btn, "Toggle commented out / active state", app_ref)

        self.actions_btn = ctk.CTkButton(
            row,
            text="Actions",
            width=96,
            height=btn_h,
            fg_color="#2c3e50",
            hover_color="#3d566e",
            command=self.open_actions_menu,
        )
        self.actions_btn.pack(side="right", padx=(10, 6))
        ToolTip(self.actions_btn, "Open card actions", app_ref)

        self.stats_area = ctk.CTkFrame(self, fg_color="transparent")
        self.stats_area.pack(fill="x", pady=2, padx=10)
        self.actions_host = ctk.CTkFrame(self.stats_area, fg_color="transparent")
        self.conditions_host = ctk.CTkFrame(self.stats_area, fg_color="transparent")
        self._show_deferred_hint(False)

        def on_enter(event):
            if self.app_ref.active_card != self:
                self.configure(border_color="#555555")

        def on_leave(event):
            self._cancel_hover_hydration()
            if self.app_ref.active_card != self:
                self.configure(border_color="#262626")

        def make_active(event):
            set_active_callback(self)

        def hydrate_on_hover(event):
            self._schedule_hover_hydration()

        self.bind("<Enter>", on_enter)
        self.bind("<Enter>", hydrate_on_hover, add="+")
        self.bind("<Leave>", on_leave)
        self.bind("<Button-1>", make_active)
        row.bind("<Button-1>", make_active)
        self.name_label.bind("<Button-1>", make_active)
        self.stats_area.bind("<Button-1>", make_active)
        self.refresh_power_button()

    def _cancel_hover_hydration(self):
        after_id = getattr(self, "_hover_hydration_after", None)
        if after_id is not None:
            try:
                self.after_cancel(after_id)
            except Exception:
                pass
        self._hover_hydration_after = None

    def _schedule_hover_hydration(self):
        if getattr(self, "_is_hydrated", True):
            return
        self._cancel_hover_hydration()
        try:
            self._hover_hydration_after = self.after(self._hover_hydration_delay_ms, self.ensure_hydrated)
        except Exception:
            self._hover_hydration_after = None

    def get_quality_value(self):
        qual_menu = getattr(self, "qual_menu", None)
        if qual_menu is not None and hasattr(qual_menu, "get"):
            try:
                value = str(qual_menu.get() or "").strip().lower()
                if value:
                    self._quality_value = value
            except Exception:
                pass
        return str(getattr(self, "_quality_value", "normal") or "normal").strip().lower() or "normal"

    def _set_quality_value(self, value):
        value = str(value or "normal").strip().lower() or "normal"
        self._quality_value = value
        qual_menu = getattr(self, "qual_menu", None)
        if qual_menu is not None:
            try:
                current = str(qual_menu.get() or "").strip().lower()
            except Exception:
                current = ""
            if current != value:
                try:
                    qual_menu.set(value)
                except Exception:
                    pass
        summary = getattr(self, "_quality_summary_label", None)
        if summary is not None:
            try:
                summary.configure(text=value.upper())
            except Exception:
                pass

    def _set_quality_locked(self, locked):
        self._quality_locked = bool(locked)
        qual_menu = getattr(self, "qual_menu", None)
        if qual_menu is not None:
            try:
                qual_menu.configure(state="disabled" if locked else "readonly")
            except Exception:
                try:
                    qual_menu.configure(state="disabled" if locked else "normal")
                except Exception:
                    pass
        summary = getattr(self, "_quality_summary_label", None)
        if summary is not None:
            try:
                summary.configure(fg="#9c9c9c" if locked else "#f0f0f0")
            except Exception:
                pass

    def _header_type_text(self):
        display_val = self.app_ref._display_item_type(getattr(self, "current_type_raw", "item") or "item")
        return display_val or "item"

    def _activate_from_header_summary(self, target=None):
        if self.app_ref:
            try:
                self.app_ref.set_active(self)
            except Exception:
                pass
        if target == "type":
            try:
                self.after_idle(self.open_type_search)
            except Exception:
                self.open_type_search()

    def _destroy_header_summaries(self):
        for attr in ("_type_summary_label", "_quality_summary_label"):
            widget = getattr(self, attr, None)
            if widget is not None:
                try:
                    widget.destroy()
                except Exception:
                    pass
                setattr(self, attr, None)

    def _destroy_header_editors(self):
        qual_menu = getattr(self, "qual_menu", None)
        if qual_menu is not None:
            try:
                value = str(qual_menu.get() or "").strip().lower()
                if value:
                    self._quality_value = value
            except Exception:
                pass
            try:
                qual_menu.destroy()
            except Exception:
                pass
        type_btn = getattr(self, "type_btn", None)
        if type_btn is not None:
            try:
                type_btn.destroy()
            except Exception:
                pass
        self.qual_menu = None
        self.type_btn = None
        self._header_controls_active = False

    def _build_header_summaries(self):
        if getattr(self, "_header_controls_active", False):
            self._destroy_header_editors()
        self._destroy_header_summaries()
        row = getattr(self, "_header_row", None)
        if row is None:
            return
        item_font = self.font_data["item"]
        self._type_summary_label = tk.Label(
            row,
            text=self._header_type_text(),
            font=item_font,
            fg="#f0f0f0",
            bg="#1a1a1a",
            bd=1,
            relief="solid",
            padx=10,
            pady=8,
            cursor="hand2",
        )
        self._type_summary_label.pack(side="left", padx=4)
        ToolTip(self._type_summary_label, "Activate this rule to edit item type/base", self.app_ref)
        self._type_summary_label.bind("<Button-1>", lambda e: self._activate_from_header_summary("type"))

        self._quality_summary_label = tk.Label(
            row,
            text=self.get_quality_value().upper(),
            font=item_font,
            fg="#f0f0f0",
            bg="#2b2b2b",
            bd=1,
            relief="solid",
            padx=10,
            pady=8,
            cursor="hand2",
        )
        self._quality_summary_label.pack(side="left", padx=4)
        ToolTip(self._quality_summary_label, "Activate this rule to edit quality", self.app_ref)
        self._quality_summary_label.bind("<Button-1>", lambda e: self._activate_from_header_summary())
        self._set_quality_locked(getattr(self, "_quality_locked", False))

    def _ensure_header_editors(self):
        if getattr(self, "_header_controls_active", False) and self.type_btn is not None and self.qual_menu is not None:
            return
        self._destroy_header_summaries()
        row = getattr(self, "_header_row", None)
        quality_colors = _dep("quality_colors")
        self.type_btn = ctk.CTkButton(
            row,
            text=self._header_type_text() + " \u25bc",
            width=90,
            height=40,
            font=self.font_data["item"],
            fg_color="#1a1a1a",
            hover_color="#333",
            border_width=1,
            border_color="#333",
            anchor="w",
            command=self.open_type_search,
        )
        self.type_btn.pack(side="left", padx=4)
        ToolTip(self.type_btn, "Change item type/base", self.app_ref)

        self.qual_menu = ctk.CTkComboBox(
            row,
            values=list(quality_colors.keys()),
            width=130,
            height=40,
            font=self.font_data["item"],
            dropdown_font=self.font_data["d2"],
            state="readonly",
            command=self.update_color,
            dropdown_fg_color="#1a1a1a",
            dropdown_hover_color="#333",
            dropdown_text_color="#fff",
        )
        self.qual_menu.set(self.get_quality_value())
        self.qual_menu.pack(side="left", padx=4)
        ToolTip(self.qual_menu, "Select item quality color", self.app_ref)
        self._header_controls_active = True
        try:
            _dep("apply_rune_state_to_card")(self)
        except Exception:
            pass

    def _collapse_header_editors(self):
        if not getattr(self, "_header_controls_active", False):
            return
        self._destroy_header_editors()
        self._build_header_summaries()

    def refresh_power_button(self):
        if not hasattr(self, "power_btn"):
            return
        if getattr(self, "is_disabled", False):
            self.power_btn.configure(fg_color="#7a1f1f", hover_color="#a32626", text_color="#ffdddd")
        else:
            self.power_btn.configure(fg_color="#1f7a3d", hover_color="#26a65b", text_color="#eaffea")

    def toggle_disabled_state(self):
        self.is_disabled = not getattr(self, "is_disabled", False)
        self.refresh_power_button()
        if getattr(self, "app_ref", None):
            self.app_ref.mark_unsaved()

    def toggle_collapse(self):
        if self.is_collapsed:
            self.ensure_hydrated()
            if self.app_ref:
                self.app_ref._preload_neighbor_cards(self)
            self.stats_area.pack(fill="x", pady=2, padx=10)
            self.toggle_btn.configure(text="\u25bc")
        else:
            self.stats_area.pack_forget()
            self.toggle_btn.configure(text="\u25b2")
        self.is_collapsed = not self.is_collapsed

    def set_active(self, is_active):
        if is_active:
            self._cancel_hover_hydration()
            self._ensure_header_editors()
            self._show_action_tray()
            self.ensure_hydrated()
            self._show_full_conditions(user_initiated=True)
            if self.app_ref:
                self.app_ref._preload_neighbor_cards(self)
            self.configure(border_color="#00ffff", border_width=2)
        else:
            self._collapse_header_editors()
            self._hide_action_tray()
            if not getattr(self, "_user_revealed_conditions", False):
                self._show_summary_conditions()
            self.indicator.configure(fg_color=self.base_color)
            self.name_label.configure(text_color=self.base_color)
            self.configure(border_width=1, border_color="#262626")

    def highlight_error(self, is_error):
        self.configure(border_color="#ff0000" if is_error else "#262626", border_width=3 if is_error else 1)

    def update_color(self, val):
        quality_colors = _dep("quality_colors")
        self.base_color = quality_colors.get(val.lower(), "#444")
        self.indicator.configure(fg_color=self.base_color)
        self.name_label.configure(text_color=self.base_color)
        if self.app_ref and not getattr(self, "_suspend_unsaved_mark", False):
            self.app_ref.mark_unsaved()

    def open_type_search(self):
        self._ensure_header_editors()
        TypeSearchDialog(
            self.winfo_toplevel(),
            self.font_data,
            self.set_type,
            all_item_types=_dep("all_item_types"),
            apply_window_icon=_dep("apply_window_icon"),
            configure_dialog_window=_dep("configure_dialog_window"),
        )

    def set_type(self, val):
        raw_val = self.app_ref._raw_item_type(val)
        self.current_type_raw = raw_val if raw_val else "item"
        display_val = self.app_ref._display_item_type(self.current_type_raw)
        if self.type_btn is not None:
            self.type_btn.configure(text=display_val + " \u25bc")
        if self._type_summary_label is not None:
            try:
                self._type_summary_label.configure(text=display_val)
            except Exception:
                pass
        self.app_ref.mark_unsaved()

    def open_actions_menu(self):
        if self.app_ref and self.app_ref.active_card is not self:
            try:
                self.app_ref.set_active(self)
            except Exception:
                pass
        if getattr(self, "_actions_visible", False):
            self._hide_action_tray()
        else:
            self._show_action_tray()

    def _build_deferred_summary_text(self):
        stat_count = int(getattr(self, "_summary_stat_count", 0) or 0)
        advanced_count = int(getattr(self, "_summary_advanced_count", 0) or 0)
        parts = []
        if stat_count:
            parts.append(f"{stat_count} stat{'s' if stat_count != 1 else ''}")
        if advanced_count:
            parts.append(f"{advanced_count} advanced rule{'s' if advanced_count != 1 else ''}")
        if not parts:
            parts.append("Ready to edit")
        return " \u00b7 ".join(parts)

    def _show_deferred_hint(self, visible):
        frame = getattr(self, "_deferred_summary_frame", None)
        if not visible:
            if frame is not None:
                try:
                    frame.pack_forget()
                except Exception:
                    pass
            self._deferred_summary_var.set("")
            return
        if frame is None or not frame.winfo_exists():
            frame = tk.Frame(self.stats_area, bg="#101010", highlightthickness=1, highlightbackground="#2f2f2f")
            frame.bind("<Button-1>", lambda e: self._activate_from_header_summary())
            frame.bind("<Double-Button-1>", lambda e: self._activate_from_header_summary())
            summary = tk.Label(
                frame,
                textvariable=self._deferred_summary_var,
                anchor="w",
                justify="left",
                font=("Segoe UI", 11, "bold"),
                fg="#c9a063",
                bg="#101010",
                cursor="hand2",
            )
            summary.pack(fill="x", padx=10, pady=(8, 2))
            hint = tk.Label(
                frame,
                text="Click a rule to open full controls.",
                anchor="w",
                justify="left",
                font=("Segoe UI", 10),
                fg="#9a9a9a",
                bg="#101010",
                cursor="hand2",
            )
            hint.pack(fill="x", padx=10, pady=(0, 8))
            summary.bind("<Button-1>", lambda e: self._activate_from_header_summary())
            summary.bind("<Double-Button-1>", lambda e: self._activate_from_header_summary())
            hint.bind("<Button-1>", lambda e: self._activate_from_header_summary())
            hint.bind("<Double-Button-1>", lambda e: self._activate_from_header_summary())
            self._deferred_summary_frame = frame
            self._deferred_summary_hint = hint
        self._deferred_summary_var.set(self._build_deferred_summary_text())
        try:
            frame.pack(fill="x", pady=(2, 4), padx=4)
        except Exception:
            pass

    def _show_full_conditions(self, user_initiated=False):
        if user_initiated:
            self._user_revealed_conditions = True
        frame = getattr(self, "_deferred_summary_frame", None)
        if frame is not None:
            try:
                frame.pack_forget()
            except Exception:
                pass
        host = getattr(self, "conditions_host", None)
        if host is None:
            return
        try:
            if not host.winfo_manager():
                host.pack(fill="x")
        except Exception:
            try:
                host.pack(fill="x")
            except Exception:
                pass
        self._conditions_revealed = True

    def _show_summary_conditions(self):
        host = getattr(self, "conditions_host", None)
        if host is not None:
            try:
                host.pack_forget()
            except Exception:
                pass
        self._conditions_revealed = False
        self._show_deferred_hint(True)

    def _make_tray_button(self, parent, text, command, *, width=118, fg="#25384c", hover="#35506d", text_color="#f4f4f4"):
        return ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            corner_radius=8,
            fg_color=fg,
            hover_color=hover,
            text_color=text_color,
            font=self.font_data["item"],
        )

    def _build_action_tray(self):
        if self._actions_tray is not None:
            return self._actions_tray
        parse_rule_line = _dep("parse_rule_line")
        flat_stat_map = _dep("flat_stat_map")
        apply_window_icon = _dep("apply_window_icon")
        configure_dialog_window = _dep("configure_dialog_window")

        tray = ctk.CTkFrame(self.actions_host, fg_color="#0f141a", corner_radius=10, border_width=1, border_color="#2a3a4d")
        title_row = ctk.CTkFrame(tray, fg_color="transparent")
        title_row.pack(fill="x", padx=10, pady=(8, 4))
        ctk.CTkLabel(
            title_row,
            text="Rule Actions",
            font=("Constantia", 15, "bold"),
            text_color="#c9a063",
        ).pack(side="left")
        ctk.CTkLabel(
            title_row,
            text="Quick tools for the active rule",
            font=("Segoe UI", 10),
            text_color="#8f9baa",
        ).pack(side="right")

        row1 = ctk.CTkFrame(tray, fg_color="transparent")
        row1.pack(fill="x", padx=8, pady=(0, 4))
        row2 = ctk.CTkFrame(tray, fg_color="transparent")
        row2.pack(fill="x", padx=8, pady=(0, 8))

        btn = self._make_tray_button(row1, "Add Attribute", self.open_stat_search, fg="#1f6f54", hover="#28896a")
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Open the attribute picker for this rule", self.app_ref)

        btn = self._make_tray_button(
            row1,
            "Import Snippet",
            lambda: SnippetImportDialog(
                self.winfo_toplevel(),
                self,
                self.app_ref,
                parse_rule_line=parse_rule_line,
                flat_stat_map=flat_stat_map,
                apply_window_icon=apply_window_icon,
                configure_dialog_window=configure_dialog_window,
            ),
            fg="#31507a",
            hover="#446b9f",
        )
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Import a prepared stat snippet into this rule", self.app_ref)

        btn = self._make_tray_button(row1, "Copy", self.copy_stats, width=88, fg="#3b4d63", hover="#506783")
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Copy this rule's attributes", self.app_ref)

        btn = self._make_tray_button(row1, "Paste", self.paste_stats, width=88, fg="#3b4d63", hover="#506783")
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Paste copied attributes into this rule", self.app_ref)

        btn = self._make_tray_button(row1, "Clone Rule", lambda: self._clone_callback(self), fg="#5a3e7a", hover="#73509d")
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Duplicate this rule", self.app_ref)

        move_up_btn = self._make_tray_button(
            row2,
            "Move Up",
            (lambda: self._move_up_cb(self)) if self._move_up_cb else (lambda: None),
            width=98,
            fg="#35414d",
            hover="#4b5a69",
        )
        move_up_btn.pack(side="left", padx=4)
        if not self._move_up_cb:
            move_up_btn.configure(state="disabled")
        ToolTip(move_up_btn, "Move this rule upward", self.app_ref)

        move_down_btn = self._make_tray_button(
            row2,
            "Move Down",
            (lambda: self._move_down_cb(self)) if self._move_down_cb else (lambda: None),
            width=108,
            fg="#35414d",
            hover="#4b5a69",
        )
        move_down_btn.pack(side="left", padx=4)
        if not self._move_down_cb:
            move_down_btn.configure(state="disabled")
        ToolTip(move_down_btn, "Move this rule downward", self.app_ref)

        btn = self._make_tray_button(row2, "Raw Inspector", self.open_raw_view, fg="#2d4f63", hover="#416d86")
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Inspect the generated raw rule line", self.app_ref)

        btn = self._make_tray_button(row2, "Undo Delete", self.app_ref.undo_delete, fg="#6b5a1f", hover="#8a7429")
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Restore the most recently deleted rule", self.app_ref)

        btn = self._make_tray_button(row2, "Delete Rule", lambda: self._delete_rule_callback(self), fg="#7a2626", hover="#983232")
        btn.pack(side="left", padx=4)
        ToolTip(btn, "Delete this rule", self.app_ref)

        self._actions_tray = tray
        return tray

    def _show_action_tray(self):
        tray = self._build_action_tray()
        host = getattr(self, "actions_host", None)
        frame = getattr(self, "_deferred_summary_frame", None)
        target = frame if frame is not None and frame.winfo_exists() else getattr(self, "conditions_host", None)
        try:
            if host is not None and not host.winfo_manager():
                if target is not None:
                    host.pack(fill="x", before=target)
                else:
                    host.pack(fill="x")
        except Exception:
            try:
                if host is not None and not host.winfo_manager():
                    host.pack(fill="x")
            except Exception:
                pass
        try:
            tray.pack_forget()
        except Exception:
            pass
        try:
            tray.pack(fill="x", pady=(0, 6), padx=4)
        except Exception:
            try:
                tray.pack(fill="x")
            except Exception:
                pass
        self._actions_visible = True
        try:
            self.actions_btn.configure(text="Hide Tools")
        except Exception:
            pass

    def _hide_action_tray(self):
        tray = getattr(self, "_actions_tray", None)
        host = getattr(self, "actions_host", None)
        if tray is not None:
            try:
                tray.pack_forget()
            except Exception:
                pass
        if host is not None:
            try:
                host.pack_forget()
            except Exception:
                pass
        self._actions_visible = False
        try:
            self.actions_btn.configure(text="Actions")
        except Exception:
            pass

    def set_pending_conditions(self, stats_data=None, advanced_data=None, mark_unsaved=False):
        self._cancel_hover_hydration()
        self.clear_all_conditions()
        self.pending_stats_data = [(key, op, val) for key, op, val in list(stats_data or [])]
        self.pending_advanced_data = [str(expr or "").strip() for expr in list(advanced_data or []) if str(expr or "").strip()]
        self._summary_stat_count = len(self.pending_stats_data)
        self._summary_advanced_count = len(self.pending_advanced_data)
        self._is_hydrated = not (self.pending_stats_data or self.pending_advanced_data)
        self._user_revealed_conditions = False
        if self._is_hydrated and (self.app_ref and self.app_ref.active_card is self):
            self._show_full_conditions(user_initiated=True)
        else:
            self._show_summary_conditions()
        if mark_unsaved and self.app_ref:
            self.app_ref.mark_unsaved()

    def ensure_hydrated(self):
        flat_stat_map = _dep("flat_stat_map")
        self._cancel_hover_hydration()
        if getattr(self, "_is_hydrated", True):
            return
        stats_payload = list(self.pending_stats_data or [])
        advanced_payload = list(self.pending_advanced_data or [])
        self.pending_stats_data = []
        self.pending_advanced_data = []
        self._show_deferred_hint(False)
        self._suspend_unsaved_mark = True
        created_widgets = []
        try:
            for key, op, val in stats_payload:
                name = flat_stat_map.get(str(key).lower(), key)
                widget = self.add_stat_visually(key, name, op, val, auto_pack=False, suppress_hint=True)
                if widget is not None:
                    created_widgets.append(widget)
            for expr in advanced_payload:
                widget = self.add_advanced_clause(expr, auto_pack=False, suppress_hint=True)
                if widget is not None:
                    created_widgets.append(widget)
        finally:
            self._suspend_unsaved_mark = False
        for widget in created_widgets:
            try:
                widget.pack(fill="x", pady=2, padx=4)
            except Exception:
                pass
        self._is_hydrated = True
        if self.app_ref and self.app_ref.active_card is self:
            self._show_full_conditions(user_initiated=True)
        elif getattr(self, "_user_revealed_conditions", False):
            self._show_full_conditions()
        else:
            self._show_summary_conditions()

    def open_stat_search(self):
        self.ensure_hydrated()
        self._show_full_conditions(user_initiated=True)
        StatSearchDialog(
            self.winfo_toplevel(),
            self.font_data,
            self.add_stat_visually,
            stat_library=_dep("stat_library"),
            skill_library=_dep("skill_library"),
            apply_window_icon=_dep("apply_window_icon"),
            configure_dialog_window=_dep("configure_dialog_window"),
        )

    def add_stat_visually(self, key, name, op=">=", val="0", auto_pack=True, suppress_hint=False):
        if not suppress_hint:
            self._show_full_conditions(user_initiated=True)
        sw = StatWidget(
            self.conditions_host,
            key,
            name,
            op,
            val,
            self.remove_stat,
            self.font_data,
            self.app_ref,
            auto_pack=auto_pack,
        )
        self.stats.append(sw)
        self._is_hydrated = True
        if self.app_ref and not getattr(self, "_suspend_unsaved_mark", False):
            self.app_ref.mark_unsaved()
        return sw

    def add_advanced_clause(self, expression, auto_pack=True, suppress_hint=False):
        expression = (expression or "").strip()
        while expression.startswith("#"):
            expression = expression[1:].strip()
        if not expression:
            return None
        if not suppress_hint:
            self._show_full_conditions(user_initiated=True)
        aw = AdvancedStatWidget(
            self.conditions_host,
            expression,
            self.remove_advanced_clause,
            self.font_data,
            self.app_ref,
            auto_pack=auto_pack,
        )
        self.advanced_clauses.append(aw)
        self._is_hydrated = True
        if self.app_ref and not getattr(self, "_suspend_unsaved_mark", False):
            self.app_ref.mark_unsaved()
        return aw

    def clear_all_conditions(self):
        for stat in list(self.stats):
            try:
                stat.destroy()
            except Exception:
                pass
        self.stats = []
        for clause in list(self.advanced_clauses):
            try:
                clause.destroy()
            except Exception:
                pass
        self.advanced_clauses = []
        self.pending_stats_data = []
        self.pending_advanced_data = []
        self._summary_stat_count = 0
        self._summary_advanced_count = 0
        self._is_hydrated = True
        self._show_summary_conditions()

    def remove_stat(self, widget):
        try:
            widget.destroy()
        except Exception:
            pass
        if widget in self.stats:
            self.stats.remove(widget)
        self.app_ref.mark_unsaved()

    def remove_advanced_clause(self, widget):
        try:
            widget.destroy()
        except Exception:
            pass
        if widget in self.advanced_clauses:
            self.advanced_clauses.remove(widget)
        self.app_ref.mark_unsaved()

    def build_current_line(self):
        return self.app_ref.serialize_rule_card(self) if self.app_ref else ""

    def open_raw_view(self):
        RawLineInspectorDialog(
            self.winfo_toplevel(),
            f"Raw Rule Inspector - {self.display_name}",
            self.raw_line or self.build_current_line(),
            self.build_current_line(),
            configure_dialog_window=_dep("configure_dialog_window"),
        )

    def copy_stats(self):
        flat_stat_map = _dep("flat_stat_map")
        stats_payload = self.app_ref._get_card_stat_tuples(self) if self.app_ref else []
        advanced_payload = self.app_ref._get_card_advanced_expressions(self) if self.app_ref else []
        if not stats_payload and not advanced_payload:
            messagebox.showinfo("Copy", "No attributes to copy.", parent=self.winfo_toplevel())
            return
        copied = {
            "stats": [
                {"key": key, "name": flat_stat_map.get(str(key).lower(), key), "op": op, "val": val}
                for key, op, val in stats_payload
            ],
            "advanced": list(advanced_payload),
        }
        self.finalize_copy(copied)

    def finalize_copy(self, data):
        self.app_ref.stat_clipboard = data

    def paste_stats(self):
        clip = self.app_ref.stat_clipboard or {}
        for stat in clip.get("stats", []):
            self.add_stat_visually(stat["key"], stat.get("name") or stat["key"], stat["op"], stat["val"])
        for expr in clip.get("advanced", []):
            self.add_advanced_clause(expr)
