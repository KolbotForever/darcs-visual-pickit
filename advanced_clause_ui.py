import re
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from nip_parser import (
    extract_numeric_stat_ids,
    summarize_advanced_expression,
    validate_advanced_expression,
)


DEFAULT_NUMERIC_STAT_ID_MAP = {
    "2": "Dexterity (verify)",
    "45": "All Resist (verify)",
    "79": "Gold Find (verify)",
    "80": "Magic Find (verify)",
}


def _setup_dialog(window, parent=None, configure_dialog_window=None, modal=True):
    if callable(configure_dialog_window):
        configure_dialog_window(window, parent, modal=modal)
        return
    if parent is not None:
        try:
            window.transient(parent)
        except Exception:
            pass
    if modal:
        try:
            window.grab_set()
        except Exception:
            pass


def get_numeric_stat_id_map(app_ref=None):
    merged = dict(DEFAULT_NUMERIC_STAT_ID_MAP)
    if app_ref is not None:
        try:
            merged.update(getattr(app_ref, "numeric_stat_id_map", {}) or {})
        except Exception:
            pass
    return merged


def format_numeric_stat_id_lines(expression: str, app_ref=None):
    ids = extract_numeric_stat_ids(expression)
    if not ids:
        return []
    current_map = get_numeric_stat_id_map(app_ref)
    lines = []
    for sid in ids:
        label = current_map.get(sid)
        if label:
            lines.append(f"{sid} \u2192 {label}")
        else:
            lines.append(f"{sid} \u2192 Unknown numeric stat id")
    return lines


def format_numeric_stat_id_summary(expression: str, app_ref=None):
    lines = format_numeric_stat_id_lines(expression, app_ref)
    if not lines:
        return ""
    return "Numeric stat ids:\n" + "\n".join(lines)


class RawLineInspectorDialog(ctk.CTkToplevel):
    def __init__(self, parent, title_text, original_line, current_line=None, configure_dialog_window=None):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("1000x560")
        self.minsize(760, 420)
        self.configure(fg_color="#0b0b0b")
        _setup_dialog(self, parent, configure_dialog_window=configure_dialog_window, modal=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text=title_text, font=("Segoe UI", 22, "bold"), text_color="#f1c40f").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text="Original loaded line and current generated line.", font=("Segoe UI", 12), text_color="#bbbbbb").grid(row=1, column=0, sticky="w", pady=(3, 0))

        body = ctk.CTkFrame(self, fg_color="#111111", border_width=1, border_color="#333333")
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(1, weight=1)
        body.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(body, text="Original line", font=("Segoe UI", 14, "bold"), text_color="#c9a063").grid(row=0, column=0, sticky="w", padx=12, pady=(10, 4))
        self.original_box = ctk.CTkTextbox(body, font=("Consolas", 16), wrap="word", fg_color="#0b0b0b", border_width=1, border_color="#333333")
        self.original_box.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.original_box.insert("1.0", original_line or "")
        self.original_box.configure(state="disabled")

        ctk.CTkLabel(body, text="Current generated line", font=("Segoe UI", 14, "bold"), text_color="#c9a063").grid(row=2, column=0, sticky="w", padx=12, pady=(0, 4))
        self.current_box = ctk.CTkTextbox(body, font=("Consolas", 16), wrap="word", fg_color="#0b0b0b", border_width=1, border_color="#333333")
        self.current_box.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))
        self.current_box.insert("1.0", current_line or original_line or "")
        self.current_box.configure(state="disabled")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="e", padx=16, pady=(0, 14))
        ctk.CTkButton(btns, text="Close", width=110, fg_color="#2c3e50", hover_color="#34495e", command=self.destroy).pack(side="left", padx=6)


class ValidationReportDialog(ctk.CTkToplevel):
    def __init__(self, parent, results, on_continue_save=None, save_plan_text="", configure_dialog_window=None):
        super().__init__(parent)
        self.results = results or {"errors": [], "warnings": [], "duplicates": []}
        self.on_continue_save = on_continue_save
        self.save_plan_text = save_plan_text or ""
        self.title("Validation Report")
        self.geometry("1100x700")
        self.minsize(860, 520)
        self.configure(fg_color="#0b0b0b")
        _setup_dialog(self, parent, configure_dialog_window=configure_dialog_window, modal=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        hdr.grid_columnconfigure(0, weight=1)
        err_count = len(self.results.get("errors", []))
        warn_count = len(self.results.get("warnings", []))
        dup_count = len(self.results.get("duplicates", []))
        title_color = "#ff7675" if err_count else ("#f1c40f" if warn_count or dup_count else "#2ecc71")
        ctk.CTkLabel(hdr, text="Validate File", font=("Segoe UI", 22, "bold"), text_color=title_color).grid(row=0, column=0, sticky="w")
        summary = f"Errors: {err_count}    Warnings: {warn_count}    Duplicates: {dup_count}"
        if self.save_plan_text:
            summary += f"    |    {self.save_plan_text}"
        ctk.CTkLabel(hdr, text=summary, font=("Segoe UI", 13), text_color="#dddddd", wraplength=980, justify="left").grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.report = ctk.CTkTextbox(self, font=("Consolas", 15), wrap="word", fg_color="#0f0f0f", border_width=1, border_color="#333333")
        self.report.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self.report.insert("1.0", self._build_report_text())
        self.report.configure(state="disabled")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="e", padx=16, pady=(0, 14))
        if self.on_continue_save is not None:
            label = "Save Anyway" if err_count else "Continue Save"
            ctk.CTkButton(btns, text=label, width=130, fg_color="#27ae60", hover_color="#2ecc71", text_color="#000", command=self._continue).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Close", width=110, fg_color="#2c3e50", hover_color="#34495e", command=self.destroy).pack(side="left", padx=6)

    def _build_report_text(self):
        lines = []
        errs = self.results.get("errors", [])
        warns = self.results.get("warnings", [])
        dups = self.results.get("duplicates", [])
        if errs:
            lines.append("ERRORS")
            lines.append("-" * 72)
            for msg in errs:
                lines.append(msg)
            lines.append("")
        if warns:
            lines.append("WARNINGS")
            lines.append("-" * 72)
            for msg in warns:
                lines.append(msg)
            lines.append("")
        if dups:
            lines.append("DUPLICATES")
            lines.append("-" * 72)
            for msg in dups:
                lines.append(msg)
            lines.append("")
        if self.save_plan_text:
            lines.append("SAVE PLAN")
            lines.append("-" * 72)
            lines.append(self.save_plan_text)
            lines.append("")
        if not lines:
            lines = ["No validation issues found."]
        return "\n".join(lines)

    def _continue(self):
        try:
            self.destroy()
        finally:
            if self.on_continue_save is not None:
                self.on_continue_save()


class DiffPreviewDialog(ctk.CTkToplevel):
    def __init__(self, parent, diff_entries, on_continue_save=None, save_plan_text="", configure_dialog_window=None):
        super().__init__(parent)
        self.diff_entries = diff_entries or []
        self.on_continue_save = on_continue_save
        self.save_plan_text = save_plan_text or ""
        self.title("Save Diff Preview")
        self.geometry("1180x760")
        self.minsize(920, 560)
        self.configure(fg_color="#0b0b0b")
        _setup_dialog(self, parent, configure_dialog_window=configure_dialog_window, modal=True)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        hdr.grid_columnconfigure(0, weight=1)
        changed = len(self.diff_entries)
        ctk.CTkLabel(hdr, text="Save Diff Preview", font=("Segoe UI", 22, "bold"), text_color="#f1c40f").grid(row=0, column=0, sticky="w")
        diff_summary = f"Changed lines: {changed}. Review the original and generated output before writing the file."
        if self.save_plan_text:
            diff_summary += f"  {self.save_plan_text}"
        ctk.CTkLabel(hdr, text=diff_summary, font=("Segoe UI", 12), text_color="#bbbbbb", wraplength=1080, justify="left").grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.report = ctk.CTkTextbox(self, font=("Consolas", 15), wrap="word", fg_color="#0f0f0f", border_width=1, border_color="#333333")
        self.report.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self.report.insert("1.0", self._build_report_text())
        self.report.configure(state="disabled")

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="e", padx=16, pady=(0, 14))
        if self.on_continue_save is not None:
            ctk.CTkButton(btns, text="Save File", width=120, fg_color="#27ae60", hover_color="#2ecc71", text_color="#000000", command=self._continue).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Cancel", width=110, fg_color="#5a1a1a", hover_color="#8a1a1a", command=self.destroy).pack(side="left", padx=6)

    def _build_report_text(self):
        if not self.diff_entries:
            return "No changed lines detected."
        chunks = []
        if self.save_plan_text:
            chunks.extend(["SAVE PLAN", "-" * 84, self.save_plan_text, "", ""])
        for entry in self.diff_entries:
            chunks.append(f"Line {entry['line_no']} - {entry['name']}")
            chunks.append("-" * 84)
            chunks.append("ORIGINAL:")
            chunks.append(entry.get("original", ""))
            chunks.append("")
            chunks.append("NEW:")
            chunks.append(entry.get("current", ""))
            chunks.append("")
            chunks.append("")
        return "\n".join(chunks).rstrip()

    def _continue(self):
        try:
            self.destroy()
        finally:
            if self.on_continue_save is not None:
                self.on_continue_save()


class NumericStatIdMappingDialog(ctk.CTkToplevel):
    def __init__(self, parent, stat_ids, app_ref=None, on_save=None, configure_dialog_window=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.on_save = on_save
        self.stat_ids = [str(s) for s in stat_ids if str(s).strip()]
        self.title("Numeric Stat ID Mapping")
        self.geometry("620x420")
        self.minsize(520, 320)
        self.configure(fg_color="#0b0b0b")
        _setup_dialog(self, parent, configure_dialog_window=configure_dialog_window, modal=True)
        self.entries = {}
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Numeric Stat ID Mappings", font=("Segoe UI", 22, "bold"), text_color="#f1c40f").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(hdr, text="Review or edit friendly labels for numeric stat ids used by this clause or card.", font=("Segoe UI", 12), text_color="#bbbbbb").grid(row=1, column=0, sticky="w", pady=(3, 0))

        body = ctk.CTkScrollableFrame(self, fg_color="#0f0f0f", border_width=1, border_color="#333333", corner_radius=8)
        body.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        body.grid_columnconfigure(1, weight=1)

        current_map = get_numeric_stat_id_map(app_ref)
        if not self.stat_ids:
            ctk.CTkLabel(body, text="No numeric stat ids detected in this expression.", font=("Segoe UI", 13), text_color="#bbbbbb").grid(row=0, column=0, sticky="w", padx=12, pady=12)
        else:
            for r, sid in enumerate(self.stat_ids):
                ctk.CTkLabel(body, text=sid, width=80, anchor="w", font=("Consolas", 16), text_color="#f5c16c").grid(row=r, column=0, sticky="w", padx=(12, 8), pady=6)
                entry = ctk.CTkEntry(body, font=("Segoe UI", 14), fg_color="#141414", border_color="#444444")
                entry.grid(row=r, column=1, sticky="ew", padx=(0, 12), pady=6)
                entry.insert(0, current_map.get(sid, ""))
                self.entries[sid] = entry

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="e", padx=16, pady=(0, 14))
        ctk.CTkButton(btns, text="Save Mappings", width=130, fg_color="#27ae60", hover_color="#2ecc71", text_color="#000000", command=self._save).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Cancel", width=110, fg_color="#5a1a1a", hover_color="#8a1a1a", command=self.destroy).pack(side="left", padx=6)

    def _save(self):
        if self.app_ref is None:
            self.destroy()
            return
        updated = dict(getattr(self.app_ref, "numeric_stat_id_map", {}) or {})
        for sid, entry in self.entries.items():
            val = entry.get().strip()
            if val:
                updated[sid] = val
            elif sid in updated:
                updated.pop(sid, None)
        self.app_ref.numeric_stat_id_map = updated
        try:
            self.app_ref.save_config()
        except Exception:
            pass
        if callable(self.on_save):
            self.on_save()
        self.destroy()


class AdvancedClauseEditor(ctk.CTkToplevel):
    def __init__(self, parent, expression, on_save, app_ref=None, all_card_numeric_ids=None, configure_dialog_window=None):
        super().__init__(parent)
        self.on_save = on_save
        self.app_ref = app_ref
        self.all_card_numeric_ids = [str(x) for x in (all_card_numeric_ids or []) if str(x).strip()]
        self._configure_dialog_window = configure_dialog_window
        self.title("Advanced Clause Editor")
        self.geometry("980x520")
        self.minsize(760, 420)
        self.configure(fg_color="#0b0b0b")
        _setup_dialog(self, parent, configure_dialog_window=configure_dialog_window, modal=True)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="Advanced Pickit Clause", font=("Segoe UI", 22, "bold"), text_color="#f1c40f").grid(row=0, column=0, sticky="w")
        helper_msg = "Edit the raw clause, validate it, then save it back to the card."
        if self.all_card_numeric_ids:
            helper_msg += f"  Card numeric ids: {', '.join(self.all_card_numeric_ids)}"
        ctk.CTkLabel(hdr, text=helper_msg, font=("Segoe UI", 12), text_color="#bbbbbb", wraplength=900, justify="left").grid(row=1, column=0, sticky="w", pady=(3, 0))

        self.textbox = ctk.CTkTextbox(self, font=("Consolas", 18), wrap="word", fg_color="#0f0f0f", border_width=1, border_color="#333333")
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self.textbox.insert("1.0", (expression or "").strip())

        info = ctk.CTkFrame(self, fg_color="#111111", border_width=1, border_color="#333333", corner_radius=8)
        info.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 8))
        info.grid_columnconfigure(0, weight=1)
        self.status_var = tk.StringVar(value="Checking syntax...")
        self.preview_var = tk.StringVar(value="")
        self.status_lbl = ctk.CTkLabel(info, textvariable=self.status_var, font=("Segoe UI", 13, "bold"), anchor="w")
        self.status_lbl.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 2))
        self.preview_lbl = ctk.CTkLabel(info, textvariable=self.preview_var, font=("Segoe UI", 12), justify="left", anchor="w", wraplength=900)
        self.preview_lbl.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))

        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="e", padx=16, pady=(0, 14))
        ctk.CTkButton(btns, text="Map IDs", width=110, fg_color="#6c4aa1", hover_color="#845cc5", command=self.open_mapping_dialog).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Validate", width=110, fg_color="#1f6aa5", hover_color="#2b7db8", command=self.run_validation).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Save", width=110, fg_color="#27ae60", hover_color="#2ecc71", text_color="#000000", command=self.save_and_close).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Cancel", width=110, fg_color="#5a1a1a", hover_color="#8a1a1a", command=self.destroy).pack(side="left", padx=6)

        try:
            self.textbox._textbox.tag_config("numeric_id", foreground="#f5c16c")
        except Exception:
            pass
        self._after_id = None
        self.textbox.bind("<KeyRelease>", self._on_text_changed)
        self.run_validation()

    def _get_text(self):
        return self.textbox.get("1.0", "end").strip()

    def _on_text_changed(self, event=None):
        if self._after_id:
            try:
                self.after_cancel(self._after_id)
            except Exception:
                pass
        self._after_id = self.after(180, self.run_validation)

    def _highlight_numeric_ids(self):
        try:
            tb = self.textbox._textbox
            tb.tag_remove("numeric_id", "1.0", "end")
            content = tb.get("1.0", "end-1c")
            for match in re.finditer(r"\[(\d+)\]", content):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                tb.tag_add("numeric_id", start, end)
        except Exception:
            pass

    def open_mapping_dialog(self):
        ids = extract_numeric_stat_ids(self._get_text())
        merged = []
        for sid in list(ids) + list(self.all_card_numeric_ids):
            sid = str(sid).strip()
            if sid and sid not in merged:
                merged.append(sid)
        NumericStatIdMappingDialog(
            self,
            merged,
            app_ref=self.app_ref,
            on_save=self.run_validation,
            configure_dialog_window=self._configure_dialog_window,
        )

    def run_validation(self):
        expr = self._get_text()
        valid, msg = validate_advanced_expression(expr)
        numeric_ids = extract_numeric_stat_ids(expr)
        preview = "Preview: " + summarize_advanced_expression(expr)
        mapped_lines = format_numeric_stat_id_lines(expr, self.app_ref)
        if mapped_lines:
            preview += "\nNumeric stat ids:\n" + "\n".join(mapped_lines)
        elif numeric_ids:
            preview += f"\nUnknown / numeric stat id(s): {', '.join(numeric_ids)}"
        if self.all_card_numeric_ids:
            preview += f"\nCard numeric ids available for mapping: {', '.join(self.all_card_numeric_ids)}"
        self.status_var.set(("\u2713 " if valid else "\u26a0 ") + msg)
        self.status_lbl.configure(text_color=("#2ecc71" if valid else "#ff7675"))
        self.preview_var.set(preview)
        self._highlight_numeric_ids()
        return valid

    def save_and_close(self):
        expr = self._get_text()
        valid, msg = validate_advanced_expression(expr)
        if not valid:
            keep = messagebox.askyesno("Save with warning?", f"{msg}\n\nSave this clause anyway?", parent=self)
            if not keep:
                return
        self.on_save(expr)
        self.destroy()
