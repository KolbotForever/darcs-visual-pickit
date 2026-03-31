import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk


def _setup_dialog(window, parent=None, apply_window_icon=None, configure_dialog_window=None, modal=True):
    if callable(apply_window_icon):
        try:
            apply_window_icon(window, force=True)
        except Exception:
            try:
                apply_window_icon(window)
            except Exception:
                pass
    if callable(configure_dialog_window):
        configure_dialog_window(window, parent, modal=modal)


class LoadingDialog:
    def __init__(self, master):
        self.master = master
        self._closed = False
        self.container = ctk.CTkFrame(master, fg_color="#0d0d0d", border_width=1, border_color="#333333", corner_radius=10)
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        self.container.lift()
        try:
            self.container.configure(width=420, height=165)
        except Exception:
            pass

        self.label = ctk.CTkLabel(
            self.container,
            text="Please Wait\nLoading NIP File...",
            font=("Constantia", 22, "bold"),
            text_color="#c9a063",
        )
        self.label.pack(padx=24, pady=(18, 10))

        self.prog = ctk.CTkProgressBar(
            self.container,
            width=300,
            fg_color="#1a1a1a",
            progress_color="#27ae60",
        )
        self.prog.pack(pady=(4, 10), padx=20)
        self.prog.set(0)

        self.sub = ctk.CTkLabel(
            self.container,
            text="Loading...",
            font=("Segoe UI", 12),
            text_color="#9a9a9a",
        )
        self.sub.pack(padx=20, pady=(0, 14))
        self._last_progress_text = None

    def winfo_exists(self):
        try:
            return int(self.container.winfo_exists())
        except Exception:
            return 0

    def update_idletasks(self):
        return

    def lift(self):
        try:
            self.container.lift()
        except Exception:
            pass

    def focus_force(self):
        try:
            self.master.focus_force()
        except Exception:
            pass

    def grab_set(self):
        return

    def grab_release(self):
        return

    def geometry(self, *_args, **_kwargs):
        return

    def update_progress(self, current, total):
        if self._closed:
            return
        if total > 0:
            try:
                self.prog.set(current / total)
            except Exception:
                pass
        msg = f"Loaded {current} of {total}"
        if msg != self._last_progress_text:
            try:
                self.sub.configure(text=msg)
            except Exception:
                pass
            self._last_progress_text = msg

    def safe_close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.container.place_forget()
        except Exception:
            pass
        try:
            self.container.destroy()
        except Exception:
            pass


class SnippetImportDialog(ctk.CTkToplevel):
    def __init__(
        self,
        master,
        target_card,
        app_ref,
        parse_rule_line,
        flat_stat_map,
        apply_window_icon=None,
        configure_dialog_window=None,
    ):
        super().__init__(master)
        self.title("Import NIP Snippet")
        self.geometry("700x350")
        self.configure(fg_color="#0d0d0d")
        self.target_card = target_card
        self.app_ref = app_ref
        self.parse_rule_line = parse_rule_line
        self.flat_stat_map = flat_stat_map
        _setup_dialog(self, master, apply_window_icon=apply_window_icon, configure_dialog_window=configure_dialog_window, modal=True)
        ctk.CTkLabel(self, text=f"IMPORT TO: {target_card.display_name.upper()}", font=app_ref.d2_font, text_color="#c9a063").pack(pady=15)
        self.textbox = ctk.CTkTextbox(self, height=150, font=app_ref.item_font, fg_color="#000", border_color="#333", border_width=1)
        self.textbox.pack(fill="both", expand=True, padx=20, pady=10)
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=15)
        ctk.CTkButton(btn_row, text="Update Card", command=self.process_import, fg_color="#27ae60", text_color="#000", font=app_ref.item_font).pack(side="left", padx=10)
        ctk.CTkButton(btn_row, text="Cancel", command=self.destroy, fg_color="#5a1a1a", font=app_ref.item_font).pack(side="left", padx=10)

    def process_import(self):
        text = self.textbox.get("1.0", "end").strip()
        if not text:
            return
        clean = text.split("\n")[0].strip()
        info = self.parse_rule_line(clean)
        if not info or info.get("is_comment"):
            messagebox.showerror("Import Error", "Invalid NIP syntax.", parent=self)
            return
        self.target_card.display_name = info["name"]
        self.target_card.name_label.configure(text=info["name"])
        self.target_card.qual_menu.set(info["quality"])
        self.target_card.update_color(info["quality"])
        self.target_card.set_type(info["type"] or "item")
        self.target_card.type_field = info.get("type_field", "name")
        self.target_card.is_disabled = info.get("is_disabled", False)
        self.target_card.refresh_power_button()
        self.target_card.base_extra_conditions = list(info.get("base_extra_conditions", []))
        self.target_card.clear_all_conditions()
        for sk, op, val in info.get("stats", []):
            stat_name = self.flat_stat_map.get(sk.lower(), sk)
            self.target_card.add_stat_visually(sk, stat_name, op, val)
        for clause in info.get("advanced_clauses", []):
            self.target_card.add_advanced_clause(clause)
        if self.app_ref and not getattr(self, "_suspend_unsaved_mark", False):
            self.app_ref.mark_unsaved()
        self.destroy()


class ShortcutDialog(ctk.CTkToplevel):
    def __init__(self, master, app_ref, extract_shortcut_bindings, apply_window_icon=None, configure_dialog_window=None):
        super().__init__(master)
        self.title("Keyboard Shortcuts")
        self.geometry("600x600")
        self.configure(fg_color="#0d0d0d")
        self.app_ref = app_ref
        self.extract_shortcut_bindings = extract_shortcut_bindings
        _setup_dialog(self, master, apply_window_icon=apply_window_icon, configure_dialog_window=configure_dialog_window, modal=True)
        ctk.CTkLabel(self, text="CUSTOM KEYBOARD SHORTCUTS", font=app_ref.d2_font, text_color="#c9a063").pack(pady=20)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#000", corner_radius=0)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self.rows = []
        for action, key in self.extract_shortcut_bindings(app_ref.shortcuts).items():
            self.create_shortcut_row(action, key)
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=10)
        ctk.CTkButton(btn_row, text="+ Add Custom", command=self.add_blank_shortcut, fg_color="#1a2a3a").pack(side="left", padx=10)
        ctk.CTkButton(btn_row, text="Save & Bind", command=self.save_keys, fg_color="#27ae60", text_color="#000").pack(side="left", padx=10)

    def create_shortcut_row(self, action, key):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=5)
        is_fixed = action in ["save", "new_rule", "syntax_check", "load_folder", "undo"]
        name_entry = ctk.CTkEntry(row, font=self.app_ref.item_font, width=180)
        name_entry.insert(0, action)
        if is_fixed:
            name_entry.configure(state="disabled", text_color="#777")
        name_entry.pack(side="left", padx=10)
        key_entry = ctk.CTkEntry(row, placeholder_text="e.g. <Control-s>", font=self.app_ref.item_font, width=150)
        key_entry.insert(0, key)
        key_entry.pack(side="left", padx=10)
        if not is_fixed:
            del_img, del_txt = self.app_ref.card_icons["delete"]
            fnt = ("Segoe UI Emoji", 24) if not del_img else None
            ctk.CTkButton(
                row,
                image=del_img,
                text=del_txt if not del_img else "",
                font=fnt,
                fg_color="#5a1a1a",
                hover_color="#8a1a1a",
                width=46,
                height=46,
                corner_radius=6,
                anchor="center",
                command=lambda r=row: self.remove_row(r),
            ).pack(side="right", padx=10)
        self.rows.append((name_entry, key_entry, row))

    def add_blank_shortcut(self):
        self.create_shortcut_row("custom_action", "")

    def remove_row(self, row_obj):
        for i, (_n, _k, row) in enumerate(self.rows):
            if row == row_obj:
                row.destroy()
                self.rows.pop(i)
                break

    def save_keys(self):
        new_shortcuts = {}
        for n_entry, k_entry, _ in self.rows:
            name = n_entry.get().strip()
            key = k_entry.get().strip()
            if name and key:
                new_shortcuts[name] = key
        existing = dict(getattr(self.app_ref, "shortcuts", {}) or {})
        for action in list(self.extract_shortcut_bindings(existing).keys()):
            existing.pop(action, None)
        existing.update(new_shortcuts)
        self.app_ref.shortcuts = existing
        self.app_ref.save_config()
        self.app_ref.rebind_shortcuts()
        self.destroy()


class BackupHistoryDialog(ctk.CTkToplevel):
    def __init__(self, master, app_ref, apply_window_icon=None, configure_dialog_window=None):
        super().__init__(master)
        self.title("Backup History")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.configure(fg_color="#0d0d0d")
        self.app_ref = app_ref
        _setup_dialog(self, master, apply_window_icon=apply_window_icon, configure_dialog_window=configure_dialog_window, modal=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="BACKUP HISTORY", font=app_ref.d2_font, text_color="#c9a063").grid(row=0, column=0, sticky="w", padx=22, pady=(18, 8))

        settings = ctk.CTkFrame(self, fg_color="#101010", border_width=1, border_color="#333333", corner_radius=8)
        settings.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        settings.grid_columnconfigure(0, weight=1)

        row1 = ctk.CTkFrame(settings, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 6))
        row1.grid_columnconfigure(3, weight=1)

        ctk.CTkCheckBox(row1, text="Enable Auto-Snapshot on Save", variable=app_ref.backup_active, font=app_ref.item_font, command=app_ref.save_config).grid(row=0, column=0, sticky="w", padx=(0, 20))
        ctk.CTkLabel(row1, text="Keep Backups For", font=app_ref.item_font).grid(row=0, column=1, sticky="w", padx=(0, 8))

        self.days_menu = ctk.CTkOptionMenu(row1, values=["1 Day", "1 Week", "1 Month"], command=self.set_interval, width=150)
        self.days_menu.set("1 Week" if app_ref.backup_days.get() == 7 else ("1 Day" if app_ref.backup_days.get() == 1 else "1 Month"))
        self.days_menu.grid(row=0, column=2, sticky="w", padx=(0, 8))

        row2 = ctk.CTkFrame(settings, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        row2.grid_columnconfigure(2, weight=1)

        ctk.CTkCheckBox(row2, text="Warn Before Cleanup", variable=app_ref.backup_warn, font=app_ref.item_font, command=app_ref.save_config).grid(row=0, column=0, sticky="w", padx=(0, 20))
        ctk.CTkButton(row2, text="Create Snapshot Now", fg_color="#1f6aa5", hover_color="#2b7db8", width=180, command=self.create_snapshot_now).grid(row=0, column=1, sticky="w", padx=(0, 12))

        self.count_var = tk.StringVar(value="")
        ctk.CTkLabel(row2, textvariable=self.count_var, font=("Segoe UI", 12), text_color="#bbbbbb", anchor="e").grid(row=0, column=2, sticky="e")

        body = ctk.CTkFrame(self, fg_color="#101010", border_width=1, border_color="#333333", corner_radius=8)
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 10))
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)
        self.summary_var = tk.StringVar(value="")
        ctk.CTkLabel(body, textvariable=self.summary_var, font=("Segoe UI", 12), text_color="#bbbbbb", anchor="w", wraplength=1080, justify="left").grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 6))

        self.listbox = tk.Listbox(body, bg="#0d0d0d", fg="#f0f0f0", selectbackground="#1f6aa5", selectforeground="#ffffff", relief="flat", font=("Consolas", 13))
        self.listbox.grid(row=1, column=0, sticky="nsew", padx=(12, 0), pady=(0, 12))
        sb = tk.Scrollbar(body, orient="vertical", command=self.listbox.yview)
        sb.grid(row=1, column=1, sticky="ns", padx=(0, 12), pady=(0, 12))
        self.listbox.configure(yscrollcommand=sb.set)

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 16))
        btns.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkButton(btns, text="Open Backup Folder", fg_color="#2c3e50", hover_color="#34495e", width=180, command=self.open_backup_folder).grid(row=0, column=0, padx=8, sticky="ew")
        ctk.CTkButton(btns, text="Restore Selected", fg_color="#6c4aa1", hover_color="#845cc5", width=180, command=self.restore_selected).grid(row=0, column=1, padx=8, sticky="ew")
        ctk.CTkButton(btns, text="Refresh", fg_color="#262626", hover_color="#333333", width=180, command=self.refresh).grid(row=0, column=2, padx=8, sticky="ew")
        ctk.CTkButton(btns, text="Close", fg_color="#5a1a1a", hover_color="#8a1a1a", width=180, command=self.destroy).grid(row=0, column=3, padx=8, sticky="ew")
        self.refresh()

    def set_interval(self, val):
        self.app_ref.backup_days.set(1 if val == "1 Day" else 7 if val == "1 Week" else 30)
        self.app_ref.save_config()

    def _selected_path(self):
        sel = self.listbox.curselection()
        if not sel:
            return None
        items = self.app_ref.get_backup_history()
        if hasattr(self, "count_var"):
            self.count_var.set(f"Backups Found: {len(items)}")
        idx = sel[0]
        if idx < 0 or idx >= len(items):
            return None
        return items[idx].get("path")

    def create_snapshot_now(self):
        created = self.app_ref.create_backup_snapshot(reason="Manual Snapshot")
        self.refresh()
        if created:
            messagebox.showinfo("Backup Snapshot", f"Snapshot created:\n{os.path.basename(created)}", parent=self)

    def open_backup_folder(self):
        folder = self.app_ref.get_backup_dir(create=True)
        try:
            os.startfile(folder)
        except Exception:
            messagebox.showinfo("Backup Folder", folder, parent=self)

    def restore_selected(self):
        path = self._selected_path()
        if not path:
            messagebox.showinfo("Restore Backup", "Select a backup first.", parent=self)
            return
        self.app_ref.restore_backup_from_history(path, parent=self)
        self.refresh()

    def refresh(self):
        self.listbox.delete(0, "end")
        items = self.app_ref.get_backup_history()
        if not items:
            self.listbox.insert("end", "No backups found yet.")
            self.summary_var.set("Snapshots appear here after manual snapshots, saves, or updates.")
            return
        self.summary_var.set(f"{len(items)} backup snapshot(s) in {self.app_ref.get_backup_dir(create=True)}")
        for item in items:
            stamp = item.get("timestamp_display", "Unknown time")
            reason = item.get("reason", "Snapshot")
            size = item.get("size_label", "")
            name = item.get("name", os.path.basename(item.get("path", "")))
            self.listbox.insert("end", f"{stamp}  |  {reason}  |  {name}  {size}")


class EntriesSettingsDialog(ctk.CTkToplevel):
    def __init__(self, master, app_ref, loading_dialog_cls=LoadingDialog, apply_window_icon=None, configure_dialog_window=None):
        super().__init__(master)
        self.title("Entries Limit")
        self.geometry("300x350")
        self.configure(fg_color="#0d0d0d")
        self.app_ref = app_ref
        self.loading_dialog_cls = loading_dialog_cls
        _setup_dialog(self, master, apply_window_icon=apply_window_icon, configure_dialog_window=configure_dialog_window, modal=True)
        ctk.CTkLabel(self, text="LOAD ENTRIES LIMIT", font=app_ref.d2_font, text_color="#c9a063").pack(pady=20)
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(pady=10)

        def apply_limit():
            limit_str = app_ref.load_limit.get()
            if limit_str == "Load All Entries":
                app_ref.target_count = len(app_ref.all_file_data)
            else:
                try:
                    app_ref.target_count = int("".join(filter(str.isdigit, limit_str)))
                except ValueError:
                    app_ref.target_count = 50
            app_ref.target_count = min(app_ref.target_count, len(app_ref.all_file_data))
            if app_ref.loaded_count < app_ref.target_count:
                if not app_ref.loading_modal or not app_ref.loading_modal.winfo_exists():
                    app_ref.loading_modal = self.loading_dialog_cls(app_ref)
                    app_ref.loading_modal.update_idletasks()
                app_ref.load_next_segment()
            self.destroy()

        for opt in ["Load 50", "Load 100", "Load 150", "Load 200", "Load All Entries"]:
            ctk.CTkRadioButton(frame, text=opt, variable=app_ref.load_limit, value=opt, font=app_ref.item_font, fg_color="#27ae60", hover_color="#2ecc71").pack(anchor="w", pady=8, padx=20)
        ctk.CTkButton(self, text="Done", command=apply_limit, fg_color="#262626").pack(pady=20)


class StatSearchDialog(ctk.CTkToplevel):
    def __init__(self, master, font_data, on_select_callback, stat_library, skill_library, apply_window_icon=None, configure_dialog_window=None):
        super().__init__(master)
        self.title("Search and Add Attribute")
        self.geometry("500x650")
        self.configure(fg_color="#0d0d0d")
        self.on_select = on_select_callback
        _setup_dialog(self, master, apply_window_icon=apply_window_icon, configure_dialog_window=configure_dialog_window, modal=True)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_stats)
        ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Search", font=font_data["item"], height=45, corner_radius=8, fg_color="#1a1a1a").pack(fill="x", padx=15, pady=15)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#000", corner_radius=0)
        self.scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.all_stats = [(k, v) for _cat, stats in stat_library.items() for k, v in stats.items()]
        self.all_stats += [(k, v) for _cls, skills in skill_library.items() for k, v in skills.items()]
        self.stat_buttons = []
        for key, name in self.all_stats:
            btn = ctk.CTkButton(
                self.scroll,
                text=name,
                font=font_data["item"],
                height=40,
                anchor="w",
                fg_color="#1a1a1a",
                hover_color="#262626",
                corner_radius=4,
                command=lambda stat_key=key, stat_name=name: self.select_stat(stat_key, stat_name),
            )
            btn.pack(fill="x", pady=2)
            self.stat_buttons.append((btn, name.lower(), key.lower()))

    def filter_stats(self, *args):
        q = self.search_var.get().lower()
        for btn, name_lower, key_lower in self.stat_buttons:
            if q in name_lower or q in key_lower:
                btn.pack(fill="x", pady=2)
            else:
                btn.pack_forget()

    def select_stat(self, key, name):
        self.on_select(key, name)
        self.destroy()


class StatCopyDialog(ctk.CTkToplevel):
    def __init__(self, master, stats, font_data, on_confirm_callback, inv_op_map, apply_window_icon=None, configure_dialog_window=None):
        super().__init__(master)
        self.title("Select Attributes to Copy")
        self.geometry("400x500")
        self.configure(fg_color="#0d0d0d")
        self.on_confirm = on_confirm_callback
        self.inv_op_map = inv_op_map
        _setup_dialog(self, master, apply_window_icon=apply_window_icon, configure_dialog_window=configure_dialog_window, modal=True)
        ctk.CTkLabel(self, text="Choose attributes:", font=font_data["item"], text_color="#c9a063").pack(pady=10)
        scroll = ctk.CTkScrollableFrame(self, fg_color="#000", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        self.vars = []
        for stat in stats:
            var = tk.BooleanVar(value=True)
            ctk.CTkCheckBox(scroll, text=stat.stat_key, variable=var, font=font_data["item"], fg_color="#c9a063", hover_color="#e0b87d").pack(fill="x", pady=5, padx=5)
            self.vars.append((var, stat))
        ctk.CTkButton(self, text="Copy Selected", command=self.confirm, font=font_data["item"], fg_color="#c9a063", text_color="#000").pack(pady=10)

    def confirm(self):
        selected = [
            {"key": stat.stat_key, "op": self.inv_op_map.get(stat.op_menu.get(), ">="), "val": stat.val_entry.get()}
            for var, stat in self.vars
            if var.get()
        ]
        self.on_confirm(selected)
        self.destroy()


class TypeSearchDialog(ctk.CTkToplevel):
    def __init__(self, master, font_data, on_select_callback, all_item_types, apply_window_icon=None, configure_dialog_window=None):
        super().__init__(master)
        self.title("Search Item Type")
        self.geometry("450x600")
        self.configure(fg_color="#0d0d0d")
        self.on_select = on_select_callback
        _setup_dialog(self, master, apply_window_icon=apply_window_icon, configure_dialog_window=configure_dialog_window, modal=True)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_types)
        ctk.CTkEntry(self, textvariable=self.search_var, placeholder_text="Search", font=font_data["item"], height=45, corner_radius=8, fg_color="#1a1a1a").pack(fill="x", padx=15, pady=15)
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="#000", corner_radius=0)
        self.scroll.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.type_buttons = []
        for item_type in all_item_types:
            btn = ctk.CTkButton(
                self.scroll,
                text=item_type,
                font=font_data["item"],
                height=40,
                anchor="w",
                fg_color="#1a1a1a",
                hover_color="#262626",
                corner_radius=4,
                command=lambda val=item_type: self.select_type(val),
            )
            btn.pack(fill="x", pady=2)
            self.type_buttons.append((btn, item_type.lower()))

    def filter_types(self, *args):
        q = self.search_var.get().lower()
        for btn, name_lower in self.type_buttons:
            if q in name_lower:
                btn.pack(fill="x", pady=2)
            else:
                btn.pack_forget()

    def select_type(self, val):
        self.on_select(val)
        self.destroy()
