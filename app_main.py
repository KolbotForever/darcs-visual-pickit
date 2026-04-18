# Created by: Darcvigilante
import os
import sys
import re
import threading
import queue
import ctypes
import webbrowser
import shutil
import time
import json
import subprocess
import tempfile
import traceback
import urllib.request
import urllib.error
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import font as tkfont
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
from release_metadata import APP_BUILD_DATE, APP_SLUG, APP_USER_MODEL_ID, APP_VENDOR, APP_VERSION, GITHUB_LATEST_RELEASE_API, GITHUB_RELEASES_PAGE, GITHUB_REPO, PUBLIC_RELEASE_VERSION
from advanced_clause_ui import DiffPreviewDialog, ValidationReportDialog
from compact_ui_runtime import CompactCommentCard, CompactItemCard, PerfCompactCommentRow, PerfCompactItemRow, build_compact_card_from_model as _compact_build_card_impl, build_full_editor_card as _compact_build_full_editor_card_impl, compact_summary as _compact_legacy_summary_impl, compact_title as _compact_legacy_title_impl, open_compact_editor as _compact_open_editor_impl, refresh_after_model_change as _compact_refresh_after_model_change_impl, render_current_page as _compact_render_current_page_impl
from compact_card_runtime import clear_compact_card_cache as _compact_clear_card_cache_impl, get_compact_card as _compact_get_card_impl, prime_visible_models as _compact_prime_visible_models_impl, schedule_compact_prewarm as _compact_schedule_prewarm_impl
from compact_model_cache import build_model_cache as _compact_build_model_cache_impl, compact_summary as _compact_summary_impl, compact_title as _compact_title_impl, get_model_search_blob as _compact_get_model_search_blob_impl, model_signature as _compact_model_signature_impl, prime_model_caches as _compact_prime_model_caches_impl, stat_preview_parts as _compact_stat_preview_parts_impl
from editor_dialogs import BackupHistoryDialog, EntriesSettingsDialog, LoadingDialog, ShortcutDialog
from nip_parser import BASE_QUALITY_CLAUSE_RE, RESIST_ALIAS_TEXT, RESIST_COLOR_MAP, analyze_advanced_expression as _nip_analyze_advanced_expression_impl, build_advanced_alias_expression as _nip_build_advanced_alias_expression_impl, extract_numeric_stat_ids as _nip_extract_numeric_stat_ids_impl, find_invalid_comparison_operators as _nip_find_invalid_comparison_operators_impl, is_rune_type_value as _nip_is_rune_type_value_impl, parse_advanced_alias as _nip_parse_advanced_alias_impl, parse_nip_rule_line as _nip_parse_nip_rule_line_impl, rule_uses_rune_name as _nip_rule_uses_rune_name_impl, summarize_advanced_expression as _nip_summarize_advanced_expression_impl, validate_advanced_expression as _nip_validate_advanced_expression_impl
from paged_cache_runtime import clear_page_cache as _paged_cache_clear_impl, clear_standard_card_pool as _paged_cache_clear_standard_pool_impl, init_runtime as _paged_cache_init_impl, mark_saved as _paged_cache_mark_saved_impl, mark_unsaved as _paged_cache_mark_unsaved_impl, page_cache_key as _paged_cache_page_key_impl, profile_finish as _paged_cache_profile_finish_impl, rebuild_filtered_model_indices as _paged_cache_rebuild_filtered_indices_impl, render_current_page as _paged_cache_render_current_page_impl, sync_current_page_to_models as _paged_cache_sync_current_page_to_models_impl
from paged_validation import build_output_lines as _paged_build_output_lines_impl, collect_diff_entries as _paged_collect_diff_entries_impl, collect_validation_results as _paged_collect_validation_results_impl, validate_loaded_file as _paged_validate_loaded_file_impl
from paged_core import active_insert_index as _paged_active_insert_index_impl, build_card_from_model as _paged_build_card_from_model_impl, insert_model_at as _paged_insert_model_at_impl, status_rule_count as _paged_status_rule_count_impl, update_page_controls as _paged_update_page_controls_impl
from rule_model_runtime import model_from_card as _rule_model_from_card_impl, serialize_model_to_line as _rule_model_serialize_model_to_line_impl, serialize_rule_card as _rule_model_serialize_card_impl
from runtime_controller import apply_performance_mode as _runtime_controller_apply_performance_mode_impl, change_page_size as _runtime_controller_change_page_size_impl, filter_rule_cards as _runtime_controller_filter_rule_cards_impl, go_next_page as _runtime_controller_go_next_page_impl, go_prev_page as _runtime_controller_go_prev_page_impl, init_runtime as _runtime_controller_init_runtime_impl, perf_enabled as _runtime_controller_perf_enabled_impl, perf_page_size_choice as _runtime_controller_perf_page_size_choice_impl, render_current_page as _runtime_controller_render_current_page_impl, repack_cards as _runtime_controller_repack_cards_impl, run_rule_filter as _runtime_controller_run_rule_filter_impl, schedule_rule_filter as _runtime_controller_schedule_rule_filter_impl, start_render as _runtime_controller_start_render_impl, start_render_paged as _runtime_controller_start_render_paged_impl, sync_perf_button as _runtime_controller_sync_perf_button_impl, toggle_performance as _runtime_controller_toggle_performance_impl, update_status_bar as _runtime_controller_update_status_bar_impl
from runtime_wiring import bind_pickit_runtime
from runtime_mutations import add_blank as _runtime_mutations_add_blank_impl, add_comment as _runtime_mutations_add_comment_impl, add_from_cat as _runtime_mutations_add_from_cat_impl, clone_card as _runtime_mutations_clone_impl, del_card as _runtime_mutations_del_card_impl, move_card_down as _runtime_mutations_move_card_down_impl, move_card_up as _runtime_mutations_move_card_up_impl, undo_delete as _runtime_mutations_undo_delete_impl
from sidebar_filters import filter_catalog as _sidebar_filter_catalog_impl, filter_library as _sidebar_filter_library_impl
from widget_cards import AdvancedStatWidget, CommentRuleCard, ItemRuleCard, StatWidget, ToolTip, configure_widget_cards_runtime

def _display_label(name: str) -> str:
    return str(name).replace("*", "").replace("#", "").replace("\u25b7", "").replace("\u25bc", "").strip()

ITEM_CODE_DISPLAY_OVERRIDES = {
    "cm3": "Paladin Shield",
}

RAW_TO_FRIENDLY_ITEM_TYPE = {}
FRIENDLY_TO_RAW_ITEM_TYPE = {}

def _friendly_item_display_name(item_type: str) -> str:
    raw = str(item_type or "").strip()
    if not raw:
        return ""
    key = raw.lower()
    if key in ITEM_CODE_DISPLAY_OVERRIDES:
        return ITEM_CODE_DISPLAY_OVERRIDES[key]
    if key.startswith("cm") and len(key) <= 4:
        return "Paladin Shield"
    return raw

def _friendly_item_type_option(value: str) -> str:
    return _friendly_item_display_name(value) or str(value or "").strip()

def _normalize_version(v: str) -> tuple:
    cleaned = re.sub(r"[^0-9.]", "", str(v or ""))
    parts = [int(p) for p in cleaned.split(".") if p.isdigit()]
    return tuple(parts) if parts else (0,)


def _numeric_version_text(v: str) -> str:
    return re.sub(r"[^0-9.]", "", str(v or "")).strip(".")


def _extract_embedded_versions(text: str) -> list[tuple]:
    matches = re.findall(r"v?\d+(?:\.\d+)+", str(text or "").lower())
    versions = []
    for match in matches:
        versions.append(_normalize_version(match))
    return versions


def _parse_iso_datetime(value: str):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            local_tz = datetime.now().astimezone().tzinfo
            if local_tz is not None:
                dt = dt.replace(tzinfo=local_tz)
        return dt
    except Exception:
        return None


def _extract_release_build_date(text: str) -> str:
    if not text:
        return ""
    match = re.search(r"(?im)^(?:Build-Date|Build Date|Updater Build ID)\s*:\s*(.+?)\s*$", str(text or ""))
    return str(match.group(1)).strip() if match else ""


def _clean_release_notes_text(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"(?im)^(?:Build-Date|Build Date|Updater Build ID)\s*:\s*.+?\s*$", "", str(text or ""))
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _format_update_timestamp(value: str, fallback: str = "Never") -> str:
    dt = _parse_iso_datetime(str(value or "").strip())
    if not dt:
        return fallback
    try:
        local = dt.astimezone()
    except Exception:
        local = dt
    try:
        return local.strftime("%b %d, %Y %I:%M %p")
    except Exception:
        return str(value or fallback)


def _format_release_published(value: str, fallback: str = "Unknown") -> str:
    dt = _parse_iso_datetime(str(value or "").strip())
    if not dt:
        return fallback
    try:
        local = dt.astimezone()
    except Exception:
        local = dt
    try:
        return local.strftime("%b %d, %Y")
    except Exception:
        return str(value or fallback)


def _find_app_icon_paths():
    # Canonical runtime icon name going forward is darc.ico.
    ico_candidates = [
        "darc.ico",
        "darc_release.ico",
        "darc.icon",
        "darc pic.ico",
    ]
    png_candidates = [
        "darc.png",
        "darc_release.png",
    ]
    ico_path = None
    png_path = None
    for name in ico_candidates:
        path = resource_path(name)
        if os.path.exists(path):
            ico_path = path
            break
    for name in png_candidates:
        path = resource_path(name)
        if os.path.exists(path):
            png_path = path
            break
    return ico_path, png_path


def _current_process_image_path():
    try:
        if getattr(sys, "frozen", False):
            return sys.executable
    except Exception:
        pass
    try:
        return os.path.abspath(sys.executable)
    except Exception:
        return None


_WINDOW_ICON_PHOTO = None


def _load_window_icon_photo(ico_path=None, png_path=None):
    global _WINDOW_ICON_PHOTO
    if _WINDOW_ICON_PHOTO is not None:
        return _WINDOW_ICON_PHOTO
    image_source = None
    try:
        if png_path and os.path.exists(png_path):
            image_source = Image.open(png_path)
        elif ico_path and os.path.exists(ico_path):
            image_source = Image.open(ico_path)
        if image_source is None:
            return None
        if image_source.mode != 'RGBA':
            image_source = image_source.convert('RGBA')
        _WINDOW_ICON_PHOTO = ImageTk.PhotoImage(image_source)
    except Exception:
        _WINDOW_ICON_PHOTO = None
    return _WINDOW_ICON_PHOTO


def apply_window_icon(window, force=False):
    try:
        if not force and getattr(window, '_window_icon_applied', False):
            return
    except Exception:
        pass
    try:
        allow_native = bool(getattr(window, "_allow_native_icon", True))
    except Exception:
        allow_native = True
    ico_path, png_path = _find_app_icon_paths()
    applied = False
    if ico_path and os.path.exists(ico_path):
        try:
            window.iconbitmap(ico_path)
            applied = True
        except Exception:
            pass
        try:
            window.wm_iconbitmap(ico_path)
            applied = True
        except Exception:
            pass
    icon_photo = _load_window_icon_photo(ico_path=ico_path, png_path=png_path)
    if icon_photo is not None:
        try:
            window.iconphoto(True, icon_photo)
            applied = True
        except Exception:
            pass
        try:
            window.wm_iconphoto(True, icon_photo)
            applied = True
        except Exception:
            pass
        try:
            window._window_icon_photo_ref = icon_photo
        except Exception:
            pass
    if allow_native:
        try:
            force_native_window_icon(window, force=force)
        except Exception:
            pass
    if applied:
        try:
            window._window_icon_applied = True
        except Exception:
            pass


def set_windows_app_id(app_id=APP_USER_MODEL_ID):
    if sys.platform.startswith('win'):
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass


def force_native_window_icon(window, force=False):
    if not sys.platform.startswith("win"):
        return

    try:
        set_windows_app_id()
    except Exception:
        pass

    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
    except Exception:
        return
    try:
        if not force and getattr(window, '_native_icon_applied_hwnd', None) == hwnd:
            return
    except Exception:
        pass

    try:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x00000010
        LR_DEFAULTSIZE = 0x00000040
        LR_SHARED = 0x00008000
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        GCL_HICON = -14
        GCL_HICONSM = -34

        if ctypes.sizeof(ctypes.c_void_p) == 8:
            SetClassLongPtr = user32.SetClassLongPtrW
            SetClassLongPtr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
            SetClassLongPtr.restype = ctypes.c_void_p
        else:
            SetClassLongPtr = user32.SetClassLongW
            SetClassLongPtr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
            SetClassLongPtr.restype = ctypes.c_long

        LoadImageW = user32.LoadImageW
        LoadImageW.argtypes = [
            ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint
        ]
        LoadImageW.restype = ctypes.c_void_p

        SendMessageW = user32.SendMessageW
        SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        SendMessageW.restype = ctypes.c_void_p

        GetParent = user32.GetParent
        GetParent.argtypes = [ctypes.c_void_p]
        GetParent.restype = ctypes.c_void_p

        hicon_small = None
        hicon_big = None

        ico_path, _ = _find_app_icon_paths()
        if ico_path and os.path.exists(ico_path):
            hicon_small = LoadImageW(None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE | LR_DEFAULTSIZE)
            hicon_big = LoadImageW(None, ico_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_DEFAULTSIZE)

        if not hicon_small or not hicon_big:
            try:
                module_handle = kernel32.GetModuleHandleW(None)
            except Exception:
                module_handle = None

            process_image = _current_process_image_path()
            if process_image and os.path.exists(process_image):
                if not hicon_small:
                    hicon_small = LoadImageW(None, process_image, IMAGE_ICON, 16, 16, LR_LOADFROMFILE | LR_DEFAULTSIZE)
                if not hicon_big:
                    hicon_big = LoadImageW(None, process_image, IMAGE_ICON, 32, 32, LR_LOADFROMFILE | LR_DEFAULTSIZE)

            if module_handle:
                if not hicon_small:
                    hicon_small = LoadImageW(module_handle, ctypes.c_wchar_p(1), IMAGE_ICON, 16, 16, LR_DEFAULTSIZE | LR_SHARED)
                if not hicon_big:
                    hicon_big = LoadImageW(module_handle, ctypes.c_wchar_p(1), IMAGE_ICON, 32, 32, LR_DEFAULTSIZE | LR_SHARED)

        if not hicon_small and not hicon_big:
            return

        hwnds = [hwnd]
        try:
            parent_hwnd = GetParent(hwnd)
            if parent_hwnd and parent_hwnd not in hwnds:
                hwnds.append(parent_hwnd)
        except Exception:
            pass

        for target_hwnd in hwnds:
            if hicon_small:
                SendMessageW(target_hwnd, WM_SETICON, ICON_SMALL, hicon_small)
                SetClassLongPtr(target_hwnd, GCL_HICONSM, hicon_small)
            if hicon_big:
                SendMessageW(target_hwnd, WM_SETICON, ICON_BIG, hicon_big)
                SetClassLongPtr(target_hwnd, GCL_HICON, hicon_big)

        try:
            window._hicon_small = hicon_small
            window._hicon_big = hicon_big
            window._native_icon_applied_hwnd = hwnd
        except Exception:
            pass

    except Exception:
        pass


def nudge_window_paint(window):
    try:
        window.update_idletasks()
    except Exception:
        return
    if sys.platform.startswith('win'):
        try:
            window.attributes('-alpha', 0.99)
            window.after(20, lambda w=window: w.wm_attributes('-alpha', 1.0) if w.winfo_exists() else None)
        except Exception:
            pass


def set_windows_dark_title_bar(window):
    if not sys.platform.startswith("win"):
        return
    try:
        hwnd = int(window.winfo_id())
    except Exception:
        return
    try:
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            20,  # DWMWA_USE_IMMERSIVE_DARK_MODE
            ctypes.byref(value),
            ctypes.sizeof(value),
        )
    except Exception:
        try:
            value = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                ctypes.c_void_p(hwnd),
                19,  # older Windows builds
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
        except Exception:
            pass


def set_windows_rounded_corners(window):
    if not sys.platform.startswith("win"):
        return
    try:
        hwnd = int(window.winfo_id())
    except Exception:
        return
    try:
        preference = ctypes.c_int(2)  # DWMWCP_ROUND
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            33,  # DWMWA_WINDOW_CORNER_PREFERENCE
            ctypes.byref(preference),
            ctypes.sizeof(preference),
        )
    except Exception:
        pass


def center_window(window, parent=None):
    try:
        window.update_idletasks()
        width = max(200, int(window.winfo_width() or window.winfo_reqwidth() or 200))
        height = max(120, int(window.winfo_height() or window.winfo_reqheight() or 120))
        if parent is not None and parent.winfo_exists():
            parent.update_idletasks()
            px = int(parent.winfo_rootx())
            py = int(parent.winfo_rooty())
            pw = max(width, int(parent.winfo_width()))
            ph = max(height, int(parent.winfo_height()))
            x = px + max(0, (pw - width) // 2)
            y = py + max(0, (ph - height) // 2)
        else:
            sw = int(window.winfo_screenwidth())
            sh = int(window.winfo_screenheight())
            x = max(0, (sw - width) // 2)
            y = max(0, (sh - height) // 2)
        window.geometry(f"+{x}+{y}")
    except Exception:
        pass


def polish_window(window, parent=None, modal=False, center=False, refresh=False):
    try:
        window.update_idletasks()
    except Exception:
        pass
    try:
        apply_window_icon(window, force=refresh)
    except Exception:
        pass
    try:
        set_windows_dark_title_bar(window)
    except Exception:
        pass
    try:
        set_windows_rounded_corners(window)
    except Exception:
        pass
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
    try:
        window.lift()
    except Exception:
        pass
    if center:
        try:
            center_window(window, parent=parent)
        except Exception:
            pass
    try:
        window.after(10, lambda w=window, p=parent, c=center: center_window(w, parent=p) if c and w.winfo_exists() else None)
        window.after(15, lambda w=window: nudge_window_paint(w) if w.winfo_exists() else None)
        window.after(120, lambda w=window, r=refresh: apply_window_icon(w, force=r) if w.winfo_exists() else None)
        if bool(getattr(window, "_allow_native_icon", True)):
            window.after(220, lambda w=window: force_native_window_icon(w, force=False) if w.winfo_exists() else None)
        window.after(140, lambda w=window: set_windows_dark_title_bar(w) if w.winfo_exists() else None)
        window.after(160, lambda w=window: set_windows_rounded_corners(w) if w.winfo_exists() else None)
    except Exception:
        pass


def configure_dialog_window(window, parent=None, modal=False):
    # Dialog windows use a safer single-pass icon path; repeated native icon
    # reapplication has been prone to destabilizing packaged Tk builds.
    try:
        window._allow_native_icon = False
    except Exception:
        pass
    polish_window(window, parent=parent, modal=modal, center=True, refresh=False)


def destroy_window_safely(window, parent=None):
    try:
        window.update_idletasks()
    except Exception:
        pass
    try:
        window.grab_release()
    except Exception:
        pass
    try:
        window.withdraw()
        window.update_idletasks()
    except Exception:
        pass
    try:
        window.destroy()
    except Exception:
        pass
    if parent is not None:
        try:
            parent.update_idletasks()
        except Exception:
            pass


_NATIVE_DROP_WNDPROCS = {}


def install_native_file_drop(window, callback):
    if not sys.platform.startswith("win"):
        return False
    try:
        window.update_idletasks()
        hwnd = int(window.winfo_id())
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        WM_DROPFILES = 0x0233
        GWL_WNDPROC = -4
        if ctypes.sizeof(ctypes.c_void_p) == 8:
            SetWindowLongPtr = user32.SetWindowLongPtrW
            GetWindowLongPtr = user32.GetWindowLongPtrW
        else:
            SetWindowLongPtr = user32.SetWindowLongW
            GetWindowLongPtr = user32.GetWindowLongW
        SetWindowLongPtr.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        SetWindowLongPtr.restype = ctypes.c_void_p
        GetWindowLongPtr.argtypes = [ctypes.c_void_p, ctypes.c_int]
        GetWindowLongPtr.restype = ctypes.c_void_p
        CallWindowProc = user32.CallWindowProcW
        CallWindowProc.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        CallWindowProc.restype = ctypes.c_void_p
        shell32.DragAcceptFiles(hwnd, True)
        old_proc = GetWindowLongPtr(hwnd, GWL_WNDPROC)
        if not old_proc:
            return False
        WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)

        def _wndproc(hWnd, msg, wParam, lParam):
            if msg == WM_DROPFILES:
                files = []
                try:
                    count = shell32.DragQueryFileW(wParam, 0xFFFFFFFF, None, 0)
                    for i in range(count):
                        length = shell32.DragQueryFileW(wParam, i, None, 0)
                        buf = ctypes.create_unicode_buffer(length + 1)
                        shell32.DragQueryFileW(wParam, i, buf, length + 1)
                        files.append(buf.value)
                except Exception:
                    files = []
                finally:
                    try:
                        shell32.DragFinish(wParam)
                    except Exception:
                        pass
                if files:
                    try:
                        window.after(0, lambda vals=tuple(files): callback(list(vals)))
                    except Exception:
                        pass
                return 0
            return CallWindowProc(old_proc, hWnd, msg, wParam, lParam)

        proc_ref = WNDPROC(_wndproc)
        prev = SetWindowLongPtr(hwnd, GWL_WNDPROC, proc_ref)
        _NATIVE_DROP_WNDPROCS[hwnd] = {"proc": proc_ref, "old": prev or old_proc}
        return True
    except Exception:
        return False

def _compare_versions_and_dates(current_version: str, latest_version: str, current_build_date: str = None, latest_published_at: str = None):
    """Return (cmp, reason). cmp: 1 if latest is newer, 0 if same, -1 if current is newer."""
    current_v = _normalize_version(current_version)
    latest_v = _normalize_version(latest_version)
    if latest_v > current_v:
        return 1, "version"
    if latest_v < current_v:
        return -1, "version"
    current_dt = _parse_iso_datetime(str(current_build_date or "").strip())
    latest_dt = _parse_iso_datetime(str(latest_published_at or "").strip())
    if current_dt and latest_dt:
        try:
            delta_seconds = (latest_dt.astimezone() - current_dt.astimezone()).total_seconds()
        except Exception:
            try:
                delta_seconds = (latest_dt - current_dt).total_seconds()
            except Exception:
                delta_seconds = 0
        if delta_seconds > 1:
            return 1, "build"
        if delta_seconds < -1:
            return -1, "build"
    return 0, "same"


class UpdateProgressWindow(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self._parent = parent
        self.title("Updating Darc's Visual Pickit")
        self.geometry("760x320")
        self.resizable(False, False)
        configure_dialog_window(self, parent, modal=True)
        self.grid_columnconfigure(0, weight=1)

        self.header = ctk.CTkLabel(self, text="Updater", font=("Segoe UI", 24, "bold"))
        self.header.grid(row=0, column=0, padx=20, pady=(18, 8), sticky="w")

        self.status_var = tk.StringVar(value="Preparing update check...")
        self.detail_var = tk.StringVar(value="")

        self.status_lbl = ctk.CTkLabel(self, textvariable=self.status_var, font=("Segoe UI", 18, "bold"), wraplength=700, justify="left", anchor="w")
        self.status_lbl.grid(row=1, column=0, padx=20, pady=(4, 2), sticky="w")

        self.detail_lbl = ctk.CTkLabel(self, textvariable=self.detail_var, font=("Segoe UI", 13), justify="left", anchor="w", wraplength=700)
        self.detail_lbl.grid(row=2, column=0, padx=20, pady=(0, 10), sticky="ew")

        self.bar = ctk.CTkProgressBar(self)
        self.bar.grid(row=3, column=0, padx=20, pady=(6, 8), sticky="ew")
        self.bar.set(0)

        self.substatus = ctk.CTkLabel(self, text="", font=("Segoe UI", 12), justify="left", anchor="w", wraplength=700)
        self.substatus.grid(row=4, column=0, padx=20, pady=(0, 10), sticky="w")

        self.close_btn = ctk.CTkButton(self, text="Close", state="disabled", command=lambda: destroy_window_safely(self, parent), width=120)
        self.close_btn.grid(row=5, column=0, padx=20, pady=(4, 18), sticky="e")

        self.protocol("WM_DELETE_WINDOW", lambda: None)

    def set_status(self, status: str, detail: str = "", progress: float = None, substatus: str = ""):
        self.status_var.set(status)
        self.detail_var.set(detail)
        self.substatus.configure(text=substatus)
        if progress is not None:
            try:
                self.bar.set(max(0.0, min(1.0, float(progress))))
            except Exception:
                pass
        self.update_idletasks()

    def allow_close(self):
        self.close_btn.configure(state="normal")
        self.protocol("WM_DELETE_WINDOW", lambda: destroy_window_safely(self, self._parent))
        self.update_idletasks()


class UpdateCenterDialog(ctk.CTkToplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("Update Center")
        self.geometry("940x760")
        self.minsize(860, 660)
        configure_dialog_window(self, parent=parent, modal=False)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.status_var = tk.StringVar(value="Ready to check for updates.")
        self.summary_var = tk.StringVar(value="")
        self.current_var = tk.StringVar(value="")
        self.latest_var = tk.StringVar(value="Not checked yet")
        self.published_var = tk.StringVar(value="Published: Unknown")
        self.asset_var = tk.StringVar(value="Installer: Not available")
        self.last_checked_var = tk.StringVar(value="Last checked: Never")
        self.skip_var = tk.StringVar(value="Skipped version: None")
        self.install_mode_var = tk.StringVar(value="")
        self.auto_check_var = tk.BooleanVar(value=bool(getattr(app, "auto_check_updates", True)))
        self.interval_var = tk.StringVar(value=self._interval_label(getattr(app, "update_check_interval_hours", 24)))

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(18, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Update Center",
            font=("Segoe UI", 28, "bold"),
            text_color="#d4b072",
        ).grid(row=0, column=0, sticky="w")
        self.status_lbl = ctk.CTkLabel(
            header,
            textvariable=self.status_var,
            font=("Segoe UI", 15, "bold"),
            text_color="#dfe7ef",
            anchor="w",
            justify="left",
        )
        self.status_lbl.grid(row=1, column=0, sticky="w", pady=(6, 2))
        ctk.CTkLabel(
            header,
            textvariable=self.summary_var,
            font=("Segoe UI", 12),
            text_color="#94a3b8",
            anchor="w",
            justify="left",
        ).grid(row=2, column=0, sticky="w")

        status_card = ctk.CTkFrame(self, fg_color="#11161d", corner_radius=12, border_width=1, border_color="#293445")
        status_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        for idx in range(2):
            status_card.grid_columnconfigure(idx, weight=1)

        ctk.CTkLabel(status_card, text="Current Build", font=("Segoe UI", 14, "bold"), text_color="#c9a063").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 4)
        )
        ctk.CTkLabel(status_card, textvariable=self.current_var, font=("Segoe UI", 13), anchor="w", justify="left").grid(
            row=1, column=0, sticky="w", padx=16, pady=(0, 12)
        )

        ctk.CTkLabel(status_card, text="Latest Release", font=("Segoe UI", 14, "bold"), text_color="#c9a063").grid(
            row=0, column=1, sticky="w", padx=16, pady=(14, 4)
        )
        latest_block = ctk.CTkFrame(status_card, fg_color="transparent")
        latest_block.grid(row=1, column=1, sticky="ew", padx=16, pady=(0, 12))
        ctk.CTkLabel(latest_block, textvariable=self.latest_var, font=("Segoe UI", 13, "bold"), anchor="w", justify="left").pack(anchor="w")
        ctk.CTkLabel(latest_block, textvariable=self.published_var, font=("Segoe UI", 12), text_color="#94a3b8", anchor="w", justify="left").pack(anchor="w", pady=(2, 0))
        ctk.CTkLabel(latest_block, textvariable=self.asset_var, font=("Segoe UI", 12), text_color="#94a3b8", anchor="w", justify="left").pack(anchor="w", pady=(2, 0))

        settings_card = ctk.CTkFrame(self, fg_color="#101318", corner_radius=12, border_width=1, border_color="#293445")
        settings_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        settings_card.grid_columnconfigure(1, weight=1)
        settings_card.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(settings_card, text="Auto Check", font=("Segoe UI", 13, "bold"), text_color="#c9a063").grid(
            row=0, column=0, sticky="w", padx=(16, 8), pady=(14, 6)
        )
        self.auto_check_switch = ctk.CTkSwitch(
            settings_card,
            text="Enable automatic update checks",
            variable=self.auto_check_var,
            command=self._on_auto_toggle,
        )
        self.auto_check_switch.grid(row=0, column=1, sticky="w", padx=(0, 16), pady=(14, 6))

        ctk.CTkLabel(settings_card, text="Interval", font=("Segoe UI", 13, "bold"), text_color="#c9a063").grid(
            row=0, column=2, sticky="e", padx=(8, 8), pady=(14, 6)
        )
        self.interval_menu = ctk.CTkOptionMenu(
            settings_card,
            values=["6 hours", "12 hours", "24 hours", "48 hours", "72 hours", "168 hours"],
            variable=self.interval_var,
            width=150,
            command=self._on_interval_change,
        )
        self.interval_menu.grid(row=0, column=3, sticky="w", padx=(0, 16), pady=(14, 6))

        ctk.CTkLabel(settings_card, textvariable=self.last_checked_var, font=("Segoe UI", 12), text_color="#94a3b8").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 12)
        )
        ctk.CTkLabel(settings_card, textvariable=self.skip_var, font=("Segoe UI", 12), text_color="#94a3b8").grid(
            row=1, column=2, columnspan=2, sticky="w", padx=16, pady=(0, 12)
        )
        ctk.CTkLabel(settings_card, textvariable=self.install_mode_var, font=("Segoe UI", 12), text_color="#94a3b8").grid(
            row=2, column=0, columnspan=4, sticky="w", padx=16, pady=(0, 14)
        )

        notes_card = ctk.CTkFrame(self, fg_color="#0f1217", corner_radius=12, border_width=1, border_color="#293445")
        notes_card.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 10))
        notes_card.grid_columnconfigure(0, weight=1)
        notes_card.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(notes_card, text="Release Notes", font=("Segoe UI", 15, "bold"), text_color="#c9a063").grid(
            row=0, column=0, sticky="w", padx=16, pady=(14, 8)
        )
        self.notes_box = ctk.CTkTextbox(notes_card, wrap="word", font=("Segoe UI", 12))
        self.notes_box.grid(row=1, column=0, sticky="nsew", padx=16, pady=(0, 14))
        self.notes_box.insert("1.0", "Check for updates to load release notes here.")
        self.notes_box.configure(state="disabled")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 18))
        footer.grid_columnconfigure(0, weight=1)

        left_actions = ctk.CTkFrame(footer, fg_color="transparent")
        left_actions.grid(row=0, column=0, sticky="w")
        self.check_btn = ctk.CTkButton(left_actions, text="Check Now", width=120, command=self._check_now)
        self.check_btn.pack(side="left", padx=(0, 8))
        self.open_page_btn = ctk.CTkButton(
            left_actions,
            text="Open Release Page",
            width=150,
            fg_color="#31507a",
            hover_color="#446b9f",
            command=self._open_release_page,
        )
        self.open_page_btn.pack(side="left", padx=(0, 8))
        self.clear_skip_btn = ctk.CTkButton(
            left_actions,
            text="Clear Skipped Version",
            width=170,
            fg_color="#5b4c1b",
            hover_color="#7a6624",
            command=self._clear_skip,
        )
        self.clear_skip_btn.pack(side="left")

        right_actions = ctk.CTkFrame(footer, fg_color="transparent")
        right_actions.grid(row=0, column=1, sticky="e")
        self.skip_btn = ctk.CTkButton(
            right_actions,
            text="Skip This Version",
            width=150,
            fg_color="#5b4c1b",
            hover_color="#7a6624",
            command=self._skip_version,
        )
        self.skip_btn.pack(side="left", padx=(0, 8))
        self.install_btn = ctk.CTkButton(
            right_actions,
            text="Download && Install",
            width=170,
            fg_color="#1f6f8b",
            hover_color="#2d8fb3",
            command=self._install_update,
        )
        self.install_btn.pack(side="left", padx=(0, 8))
        self.close_btn = ctk.CTkButton(
            right_actions,
            text="Close",
            width=110,
            fg_color="#4b5563",
            hover_color="#64748b",
            command=self._close,
        )
        self.close_btn.pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self._close)
        self.refresh_from_app()

    def _close(self):
        self.app.update_center_window = None
        destroy_window_safely(self, self.app)

    def _interval_label(self, hours):
        try:
            value = max(1, int(hours or 24))
        except Exception:
            value = 24
        return f"{value} hours"

    def _interval_hours(self, label):
        match = re.search(r"(\d+)", str(label or ""))
        if not match:
            return 24
        try:
            return max(1, int(match.group(1)))
        except Exception:
            return 24

    def _set_notes(self, text):
        self.notes_box.configure(state="normal")
        self.notes_box.delete("1.0", "end")
        self.notes_box.insert("1.0", text)
        self.notes_box.configure(state="disabled")

    def _set_checking(self, checking):
        state = "disabled" if checking else "normal"
        for btn in (self.check_btn, self.open_page_btn, self.install_btn, self.skip_btn, self.clear_skip_btn):
            try:
                btn.configure(state=state)
            except Exception:
                pass
        try:
            self.auto_check_switch.configure(state=state)
            self.interval_menu.configure(state=state)
        except Exception:
            pass

    def _check_now(self):
        try:
            self.app.start_update_check(auto=False, force=True, source="dialog")
        except Exception as exc:
            self.app._handle_update_ui_exception("Check Now", exc, parent=self)

    def _open_release_page(self):
        try:
            self.app.open_latest_release_page(parent=self)
        except Exception as exc:
            self.app._handle_update_ui_exception("Open Release Page", exc, parent=self)

    def _clear_skip(self):
        try:
            self.app.clear_skipped_update()
        except Exception as exc:
            self.app._handle_update_ui_exception("Clear Skipped Version", exc, parent=self)

    def _skip_version(self):
        try:
            self.app.skip_latest_update()
        except Exception as exc:
            self.app._handle_update_ui_exception("Skip This Version", exc, parent=self)

    def _install_update(self):
        try:
            self.app.download_and_install_latest_release(parent_window=self)
        except Exception as exc:
            self.app._handle_update_ui_exception("Download && Install", exc, parent=self)

    def _on_auto_toggle(self):
        try:
            self.app.auto_check_updates = bool(self.auto_check_var.get())
            self.app.save_config()
            self.refresh_from_app()
        except Exception as exc:
            self.app._handle_update_ui_exception("Update Auto Check Setting", exc, parent=self)

    def _on_interval_change(self, value):
        try:
            self.app.update_check_interval_hours = self._interval_hours(value)
            self.app.save_config()
            self.refresh_from_app()
        except Exception as exc:
            self.app._handle_update_ui_exception("Update Check Interval", exc, parent=self)

    def refresh_from_app(self, checking=False, auto=False):
        try:
            app = self.app
            release = getattr(app, "_latest_release_info", None)
            error = getattr(app, "_latest_update_error", None)
            cmp_result = int(getattr(app, "_latest_release_cmp_result", 0) or 0)
            reason = str(getattr(app, "_latest_release_cmp_reason", "same") or "same")
            latest_label = str(getattr(app, "_latest_release_label", "") or "").strip()
            asset = getattr(app, "_latest_release_asset", None)
            asset_name = str((asset or {}).get("name") or "Not available")

            self.auto_check_var.set(bool(getattr(app, "auto_check_updates", True)))
            self.interval_var.set(self._interval_label(getattr(app, "update_check_interval_hours", 24)))
            self.last_checked_var.set(f"Last checked: {_format_update_timestamp(getattr(app, 'last_update_check_utc', ''))}")
            skipped = str(getattr(app, "skipped_update_version", "") or "").strip() or "None"
            self.skip_var.set(f"Skipped version: {skipped}")
            install_mode = "Installed EXE build" if is_likely_installed() else ("Portable EXE build" if is_frozen() else "Source / development run")
            self.install_mode_var.set(f"Install mode: {install_mode}")
            self.current_var.set(f"{APP_VERSION}  |  Built {_format_release_published(APP_BUILD_DATE, fallback=APP_BUILD_DATE)}")

            if checking:
                self.status_var.set("Checking for updates...")
                self.summary_var.set("Contacting GitHub for the latest release information.")
                self._set_checking(True)
            else:
                self._set_checking(False)
                if error is not None:
                    self.status_var.set("Update check failed")
                    self.summary_var.set(str(error))
                elif not release:
                    self.status_var.set("Ready to check for updates.")
                    self.summary_var.set("No release information has been loaded yet.")
                elif cmp_result > 0:
                    if reason == "build":
                        self.status_var.set("A refreshed build is available.")
                        self.summary_var.set("The version tag matches, but GitHub has a newer build than this installed copy.")
                    else:
                        self.status_var.set("A newer version is available.")
                        self.summary_var.set("Review the release notes below, then download the installer when you're ready.")
                elif cmp_result < 0:
                    if reason == "build":
                        self.status_var.set("This build is newer than the published build.")
                        self.summary_var.set("GitHub has the same version tag, but this installed build is newer than the published build metadata.")
                    else:
                        self.status_var.set("This build is newer than the latest published release.")
                        self.summary_var.set("GitHub latest is behind this local build, so no update is available yet.")
                else:
                    self.status_var.set("You're up to date.")
                    self.summary_var.set("This build is current based on the latest published release.")

            self.latest_var.set(latest_label or "Not checked yet")
            published = _format_release_published(str((release or {}).get("published_at") or ""))
            self.published_var.set(f"Published: {published}")
            self.asset_var.set(f"Installer: {asset_name}")

            notes = _clean_release_notes_text(str((release or {}).get("body") or "").strip())
            if not notes:
                if error is not None:
                    notes = "The update check failed before release notes could be loaded."
                elif not release:
                    notes = "Check for updates to load release notes here."
                else:
                    notes = "This release does not include release notes."
            self._set_notes(notes)

            has_release_url = bool(str((release or {}).get("html_url") or GITHUB_RELEASES_PAGE).strip())
            has_newer = bool(release) and cmp_result > 0
            has_skipped = str(getattr(app, "skipped_update_version", "") or "").strip() != ""
            has_asset = bool(asset)

            try:
                self.open_page_btn.configure(state="normal" if has_release_url and not checking else "disabled")
                self.install_btn.configure(state="normal" if has_newer and has_asset and not checking else "disabled")
                self.skip_btn.configure(state="normal" if has_newer and latest_label and not checking else "disabled")
                self.clear_skip_btn.configure(state="normal" if has_skipped and not checking else "disabled")
            except Exception:
                pass
        except Exception as exc:
            self.app._handle_update_ui_exception("Refresh Update Center", exc, parent=self, show_dialog=False)

# --- 1. PRE-COMPILED REGEX ---
DEFAULT_SHORTCUT_ACTIONS = {
    "save",
    "new_rule",
    "syntax_check",
    "load_folder",
    "undo",
}


def _looks_like_tk_binding(value) -> bool:
    return isinstance(value, str) and value.startswith("<") and value.endswith(">")


def _extract_shortcut_bindings(config):
    bindings = {}
    for action, key in dict(config or {}).items():
        action_name = str(action or "").strip()
        key_text = key.strip() if isinstance(key, str) else ""
        if not action_name or not key_text:
            continue
        if action_name in DEFAULT_SHORTCUT_ACTIONS or _looks_like_tk_binding(key_text):
            bindings[action_name] = key_text
    return bindings
def parse_advanced_alias(expression: str):
    return _nip_parse_advanced_alias_impl(expression)

def build_advanced_alias_expression(alias_info, op: str, value: str):
    return _nip_build_advanced_alias_expression_impl(alias_info, op, value)

def analyze_advanced_expression(expression: str):
    return _nip_analyze_advanced_expression_impl(expression)


def find_invalid_comparison_operators(text: str):
    return _nip_find_invalid_comparison_operators_impl(text)

def summarize_advanced_expression(expression: str) -> str:
    return _nip_summarize_advanced_expression_impl(expression)


def validate_advanced_expression(expression: str):
    return _nip_validate_advanced_expression_impl(expression)


def extract_numeric_stat_ids(expression: str):
    return _nip_extract_numeric_stat_ids_impl(expression)



def _is_rune_type_value(value):
    return _nip_is_rune_type_value_impl(value)


def _rule_uses_rune_name(type_text='', type_field='name', quality='', display_name='', raw_line=''):
    return _nip_rule_uses_rune_name_impl(
        type_text=type_text,
        type_field=type_field,
        quality=quality,
        display_name=display_name,
        raw_line=raw_line,
    )


def parse_nip_rule_line(raw_line: str):
    return _nip_parse_nip_rule_line_impl(raw_line, _friendly_item_display_name)


# --- 2. RESOURCE PATH HELPER ---
def is_frozen():
    return bool(getattr(sys, "frozen", False))

def install_base_dir():
    if is_frozen():
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def is_likely_installed():
    if not is_frozen():
        return False
    try:
        exe_dir = os.path.abspath(install_base_dir()).lower()
        local_appdata = os.path.abspath(os.environ.get("LOCALAPPDATA", "")).lower()
        program_files = [
            os.path.abspath(os.environ.get("ProgramFiles", "")).lower(),
            os.path.abspath(os.environ.get("ProgramFiles(x86)", "")).lower(),
        ]
        if local_appdata and exe_dir.startswith(os.path.join(local_appdata, "programs").lower()):
            return True
        for root in program_files:
            if root and exe_dir.startswith(root):
                return True
    except Exception:
        pass
    return False

def app_data_root():
    if is_frozen() and is_likely_installed():
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or install_base_dir()
        target = os.path.join(base, APP_VENDOR, APP_SLUG)
        os.makedirs(target, exist_ok=True)
        return target
    return install_base_dir()

def app_base_dir():
    """Writable app data folder for config/backups/logs."""
    return app_data_root()

def resource_path(relative_path):
    """Read-only bundled resource path (works for source and PyInstaller)."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = install_base_dir()
    return os.path.join(base_path, relative_path)

def user_data_path(relative_path):
    """Writable path for config/backups/logs; uses LocalAppData when installed."""
    base = app_data_root()
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, relative_path)

def load_icon(icon_name, fallback_text):

    icon_path = resource_path(f"icons/{icon_name}.png")
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path)
            return ctk.CTkImage(light_image=img, dark_image=img, size=(32, 32)), ""
        except:
            pass
    return None, fallback_text
# --- 3. DATA LIBRARIES ---
OP_MAP = {
    ">=": "Equal or Higher",
    "==": "Equal to",
    "<=": "Equal or Lower",
    ">": "More than",
    "<": "Less than",
    "!=": "Not equal to"
}
INV_OP_MAP = {v: k for k, v in OP_MAP.items()}
STAT_LIBRARY = {
    "Attributes": {
        "strength": "Strength", "dexterity": "Dexterity", "vitality": "Vitality", "energy": "Energy",
        "stats": "All Stats", "maxhp": "Life", "maxmana": "Mana", "itemhp-perlevel": "Life / Lvl",
        "itemstr-perlevel": "Str / Lvl", "itemdex-perlevel": "Dex / Lvl", "itemvit-perlevel": "Vit / Lvl",
        "manarecovery": "Mana Regen", "manarecoverybonus": "Mana Regen %", "staminarecoverybonus": "Stam Regen %"
    },
    "Resistances & Absorb": {
        "resall": "All Resistances", "fireresist": "Fire Resist", "lightresist": "Light Resist",
        "coldresist": "Cold Resist", "poisonresist": "Poison Resist", "maxfireresist": "Max Fire Res",
        "fireabsorb": "Fire Absorb", "lightabsorb": "Light Absorb", "coldabsorb": "Cold Absorb",
        "magicabsorb": "Magic Absorb", "fireabsorbpercent": "Fire Absorb %",
        "lightabsorbpercent": "Light Absorb %", "coldabsorbpercent": "Cold Absorb %"
    },
    "Combat & Speed": {
        "fcr": "Faster Cast Rate", "ias": "Increased Attack Speed", "fhr": "Faster Hit Recovery",
        "frw": "Faster Run/Walk", "tohit": "Attack Rating", "itemar-perlevel": "AR / Lvl (Visionary)",
        "enhanceddamage": "Enhanced Damage", "itemmaxdamage-perlevel": "Max Dam / Lvl",
        "deadlystrike": "Deadly Strike", "crushingblow": "Crushing Blow", "openwounds": "Open Wounds",
        "toblock": "Chance to Block", "defense": "Defense", "enhanceddefense": "Enhanced Defense",
        "ignoretargetar": "Ignore Target AC"
    },
    "Leech & Regeneration": {
        "manasteal": "Mana Leech", "lifesteal": "Life Leech", "lifedrain-perlevel": "Life Leech / Lvl",
        "manadrain-perlevel": "Mana Leech / Lvl", "hpregen": "Replenish Life",
        "laek": "Life After Kill", "maek": "Mana After Kill"
    },
    "Magic & Utility": {
        "itemmagicbonus": "Magic Find %", "itemgoldbonus": "Gold Find %", "sockets": "Sockets",
        "reduceddamagepercent": "Damage Reduced %", "magicdmgreduce": "Magic DR",
        "itemlevelreq": "Level Req", "indestructible": "Indestructible", "ethereal": "Ethereal",
        "rep-durability": "Replenish Durability", "cannotbefrozen": "Cannot be Frozen"
    }
}
SKILL_LIBRARY = {
    "Amazon": {
        "sk6": "Inner Sight", "sk7": "Magic Arrow", "sk8": "Fire Arrow", "sk9": "Multiple Shot",
        "sk10": "Jab", "sk11": "Power Strike", "sk12": "Poison Javelin", "sk13": "Exploding Arrow",
        "sk14": "Slow Missiles", "sk15": "Avoid", "sk16": "Impale", "sk17": "Lightning Bolt",
        "sk18": "Ice Arrow", "sk19": "Guided Arrow", "sk20": "Penetrate", "sk21": "Charged Strike",
        "sk22": "Plague Javelin", "sk23": "Strafe", "sk24": "Immolation Arrow", "sk25": "Decoy",
        "sk26": "Evade", "sk27": "Fend", "sk28": "Freezing Arrow", "sk29": "Valkyrie",
        "sk30": "Pierce", "sk31": "Lightning Strike", "sk32": "Lightning Fury"
    },
    "Assassin": {
        "sk251": "Fire Blast", "sk252": "Claw Mastery", "sk253": "Psychic Hammer",
        "sk254": "Tiger Strike", "sk255": "Burst of Speed", "sk256": "Shock Web",
        "sk257": "Dragon Talon", "sk258": "Weapon Block", "sk259": "Fists of Fire",
        "sk260": "Cloak of Shadows", "sk261": "Charged Bolt Sentry", "sk262": "Wake of Fire",
        "sk263": "Dragon Claw", "sk265": "Cobra Strike", "sk266": "Blade Fury", "sk267": "Fade",
        "sk268": "Shadow Warrior", "sk269": "Claws of Thunder", "sk270": "Dragon Tail",
        "sk271": "Lightning Sentry", "sk272": "Wake of Inferno", "sk273": "Mind Blast",
        "sk274": "Blades of Ice", "sk275": "Dragon Flight", "sk276": "Death Sentry",
        "sk277": "Blade Shield", "sk278": "Venom", "sk279": "Shadow Master", "sk280": "Phoenix Strike"
    },
    "Barbarian": {
        "sk126": "Bash", "sk127": "Sword Mastery", "sk128": "Axe Mastery", "sk129": "Mace Mastery",
        "sk130": "Howl", "sk131": "Find Potion", "sk132": "Leap", "sk133": "Double Swing",
        "sk134": "Polearm Mastery", "sk135": "Throwing Mastery", "sk136": "Spear Mastery",
        "sk137": "Taunt", "sk138": "Shout", "sk139": "Stun", "sk140": "Leap Attack",
        "sk141": "Increased Stamina", "sk142": "Find Item", "sk143": "Double Throw",
        "sk144": "Concentrate", "sk145": "Iron Skin", "sk146": "Battle Cry", "sk147": "Frenzy",
        "sk148": "Increased Speed", "sk149": "Battle Orders", "sk150": "Grim Ward",
        "sk151": "Whirlwind", "sk152": "Berserk", "sk153": "Natural Resistance",
        "sk154": "War Cry", "sk155": "Battle Command"
    },
    "Druid": {
        "sk221": "Raven", "sk222": "Poison Creeper", "sk223": "Werewolf", "sk224": "Lycanthropy",
        "sk225": "Firestorm", "sk226": "Oak Sage", "sk227": "Summon Spirit Wolf", "sk228": "Werebear",
        "sk229": "Molten Boulder", "sk230": "Arctic Blast", "sk231": "Carrion Vine",
        "sk232": "Feral Rage", "sk233": "Maul", "sk234": "Fissure", "sk235": "Cyclone Armor",
        "sk236": "Heart of Wolverine", "sk237": "Summon Dire Wolf", "sk238": "Rabies",
        "sk239": "Fire Claws", "sk240": "Twister", "sk241": "Spirit of Barbs",
        "sk242": "Summon Grizzly", "sk243": "Volcano", "sk244": "Tornado",
        "sk245": "Solar Creeper", "sk246": "Hunger", "sk247": "Shock Wave",
        "sk248": "Hurricane", "sk249": "Armageddon", "sk250": "Fury"
    },
    "Necromancer": {
        "sk66": "Amplify Damage", "sk67": "Teeth", "sk68": "Bone Armor",
        "sk69": "Skeleton Mastery", "sk70": "Raise Skeleton", "sk71": "Dim Vision",
        "sk72": "Weaken", "sk73": "Poison Dagger", "sk74": "Corpse Explosion",
        "sk75": "Clay Golem", "sk76": "Iron Maiden", "sk77": "Terror", "sk78": "Bone Wall",
        "sk79": "Golem Mastery", "sk80": "Raise Skeletal Mage", "sk81": "Confuse",
        "sk82": "Life Tap", "sk83": "Poison Explosion", "sk84": "Bone Spear",
        "sk85": "Blood Golem", "sk86": "Attract", "sk87": "Decrepify", "sk88": "Bone Prison",
        "sk89": "Summon Resist", "sk90": "Iron Golem", "sk91": "Lower Resist",
        "sk92": "Poison Nova", "sk93": "Bone Spirit", "sk94": "Fire Golem", "sk95": "Revive"
    },
    "Paladin": {
        "sk96": "Sacrifice", "sk97": "Smite", "sk98": "Might", "sk99": "Prayer",
        "sk100": "Resist Fire", "sk101": "Holy Bolt", "sk102": "Holy Fire", "sk103": "Thorns",
        "sk104": "Defiance", "sk105": "Resist Cold", "sk106": "Zeal", "sk107": "Charge",
        "sk108": "Blessed Aim", "sk109": "Cleansing", "sk110": "Resist Lightning",
        "sk111": "Vengeance", "sk112": "Blessed Hammer", "sk113": "Concentration",
        "sk114": "Holy Freeze", "sk115": "Vigor", "sk116": "Conversion", "sk117": "Holy Shield",
        "sk118": "Holy Shock", "sk119": "Sanctuary", "sk120": "Meditation",
        "sk121": "Fist of the Heavens", "sk122": "Fanaticism", "sk123": "Conviction",
        "redemption": "Redemption", "sk125": "Salvation"
    },
    "Sorceress": {
        "sk36": "Fire Bolt", "sk37": "Warmth", "sk38": "Charged Bolt", "sk39": "Ice Bolt",
        "sk40": "Frozen Armor", "sk41": "Inferno", "sk42": "Static Field", "sk43": "Telekinesis",
        "sk44": "Frost Nova", "sk45": "Ice Blast", "sk46": "Blaze", "sk47": "Fire Ball",
        "sk48": "Nova", "sk49": "Lightning", "sk50": "Shiver Armor", "sk51": "Fire Wall",
        "sk52": "Enchant", "sk53": "Chain Lightning", "sk54": "Teleport", "sk55": "Glacial Spike",
        "sk56": "Meteor", "sk57": "Thunder Storm", "sk58": "Energy Shield", "sk59": "Blizzard",
        "sk60": "Chilling Armor", "sk61": "Fire Mastery", "sk62": "Hydra",
        "sk63": "Lightning Mastery", "sk64": "Frozen Orb", "sk65": "Cold Mastery"
    }
}
# Flat lookup: stat/skill key -> friendly display name
FLAT_STAT_MAP = {}
for _cat, _stats in STAT_LIBRARY.items():
    FLAT_STAT_MAP.update({k.lower(): v for k, v in _stats.items()})
for _cat, _skills in SKILL_LIBRARY.items():
    FLAT_STAT_MAP.update({k.lower(): v for k, v in _skills.items()})
ITEM_CATALOG = {
    "Most Wanted Items": [
        "jah rune", "ber rune", "lo rune", "sur rune", "zod rune", "shako", "diadem",
        "spiderweb sash", "swirling crystal", "dimensional shard", "monarch", "archonplate",
        "berserker axe", "phase blade", "ring", "amulet", "smallcharm", "grandcharm", "jewel"
    ],
    "Headgear": [
        "cap", "skullcap", "helm", "fullhelm", "greathelm", "mask", "crown",
        "bonehelm", "shako", "coronet", "tiara", "diadem"
    ],
    "Body Armor": [
        "quiltedarmor", "leatherarmor", "breastplate", "mageplate", "duskshroud", "archonplate"
    ],
    "Shields": ["buckler", "kiteshield", "towershield", "monarch", "aegis", "ward"],
    "Weapons": [
        "phase blade", "berserker axe", "war scepter", "dimensional shard", "swirling crystal",
        "colossus blade", "war pike", "hydra bow", "matriarchal bow"
    ],
    "Jewelry & Misc": ["ring", "amulet", "jewel", "smallcharm", "grandcharm", "largecharm"],
    "Runes": [
        "el rune", "eld rune", "tir rune", "nef rune", "eth rune", "ith rune",
        "tal rune", "ral rune", "ort rune", "thul rune", "amn rune", "sol rune",
        "shael rune", "dol rune", "hel rune", "io rune", "lum rune", "ko rune",
        "fal rune", "lem rune", "pul rune", "um rune", "mal rune", "ist rune",
        "gul rune", "vex rune", "ohm rune", "lo rune", "sur rune", "ber rune",
        "jah rune", "cham rune", "zod rune"
    ]
}
ALL_ITEM_TYPES = sorted([
    "ring", "amulet", "jewel", "smallcharm", "grandcharm", "largecharm", "rune", "gold",
    "cap", "skullcap", "helm", "fullhelm", "greathelm", "mask", "crown", "bonehelm",
    "shako", "coronet", "tiara", "diadem",
    "quiltedarmor", "leatherarmor", "hardleatherarmor", "studdedleather", "ringmail",
    "scalemail", "breastplate", "chainmail", "splintmail", "lightplate", "fieldplate",
    "platemail", "gothicplate", "fullplatemail", "ancientarmor", "mageplate",
    "duskshroud", "archonplate",
    "buckler", "smallshield", "largeshield", "kiteshield", "towershield", "gothicshield",
    "roundshield", "pavis", "monarch", "aegis", "ward",
    "handaxe", "axe", "doubleaxe", "militarypick", "waraxe", "largeaxe", "broadaxe",
    "battleaxe", "greataxe", "giantaxe", "berserkeraxe",
    "club", "spikedclub", "mace", "morningstar", "warhammer", "maul", "greatmaul",
    "dagger", "dirk", "kris", "blade", "shortsword", "scimitar", "sabre", "falchion",
    "broadsword", "longsword", "twohandedsword", "claymore", "giantsword", "bastardsword",
    "flamberge", "greatsword", "phaseblade", "colossussword", "colossalblade",
    "javelin", "pilum", "shortspear", "glaive", "throwingknife", "throwingspear",
    "spear", "trident", "brandistock", "spetum", "pike",
    "scepter", "grandscepter", "warscepter", "divinerscepter", "archonscepter",
    "shortstaff", "longstaff", "gnarledstaff", "battlestaff", "warstaff",
    "orb", "swirlingcrystal", "dimensionalshard",
    "shortbow", "hunterbow", "longbow", "compositebow", "shortbattlebow", "longbattlebow",
    "shortwarbow", "longwarbow", "hydrabow", "matriarchalbow", "wardbow",
    "lightcrossbow", "crossbow", "heavycrossbow", "repeatingcrossbow",
    "elrune", "eldrune", "tirrune", "nefrune", "ethrune", "ithrune",
    "talrune", "ralrune", "ortrune", "thulrune", "amnrune", "solrune",
    "shaelrune", "dolrune", "helrune", "iorune", "lumrune", "korune",
    "falrune", "lemrune", "pulrune", "umrune", "malrune", "istrune",
    "gulrune", "vexrune", "ohmrune", "lorune", "surrune", "berrune",
    "jahrune", "chamrune", "zodrune"
])
FRIENDLY_ITEM_TYPE_TO_RAW = {}
FRIENDLY_ALL_ITEM_TYPE_OPTIONS = []
_seen_friendly_item_types = set()
for _raw_item_type in ALL_ITEM_TYPES:
    _friendly_item_type = _friendly_item_type_option(_raw_item_type)
    RAW_TO_FRIENDLY_ITEM_TYPE[_raw_item_type] = _friendly_item_type
    FRIENDLY_ITEM_TYPE_TO_RAW.setdefault(_friendly_item_type, _raw_item_type)
    if _friendly_item_type not in _seen_friendly_item_types:
        FRIENDLY_ALL_ITEM_TYPE_OPTIONS.append(_friendly_item_type)
        _seen_friendly_item_types.add(_friendly_item_type)

QUALITY_COLORS = {
    "unique": "#a59263",
    "set": "#00ff00",
    "rare": "#ffff00",
    "magic": "#4169e1",
    "superior": "#ffffff",
    "normal": "#ffffff",
    "rune": "#ffa500"
}
D2_FONT_SIZE = 26
ITEM_FONT_SIZE = 16
STAT_COLORS = {
    "fire": "#ff4d4d", "fireresist": "#ff4d4d", "fireabsorb": "#ff4d4d",
    "maxfireresist": "#ff4d4d",
    "light": "#ffff66", "lightresist": "#ffff66", "lightabsorb": "#ffff66",
    "maxlightresist": "#ffff66",
    "cold": "#66b3ff", "coldresist": "#66b3ff", "coldabsorb": "#66b3ff",
    "maxcoldresist": "#66b3ff",
    "poison": "#66ff66", "poisonresist": "#66ff66",
    "hp": "#ff4d4d", "maxhp": "#ff4d4d", "itemhp-perlevel": "#ff4d4d",
    "vitality": "#ff4d4d",
    "mana": "#66b3ff", "maxmana": "#66b3ff", "manarecovery": "#66b3ff",
    "energy": "#66b3ff",
    "magic": "#4169e1", "itemmagicbonus": "#4169e1",
    "gold": "#ffd700", "itemgoldbonus": "#ffd700",
    "fcr": "#ffffff", "ias": "#ffffff", "fhr": "#ffffff", "frw": "#ffffff"
}
STAT_HINTS = {
    "fcr": "Faster Cast Rate | Max: Rings(10), Amulets(20), Circlets(20)",
    "frw": "Faster Run/Walk | Max: Boots(30/40), Circlets(30)",
    "ias": "Increased Attack Speed | Max: Gloves(20), Amulets(20)",
    "itemmagicbonus": "Magic Find % | Max: Rings(40), Amulets(50), Boots(25)",
    "resall": "All Resistances | Max: Rings(11), Amulets(30), Shields(45)",
    "lifesteal": "Life Leech | Max: Rings(8), Amulets(6)",
    "manasteal": "Mana Leech | Max: Rings(6), Amulets(8)"
}
def _runtime_itemrulecard_set_type(self, val):
    raw_val = self.app_ref._raw_item_type(val)
    self.current_type_raw = raw_val if raw_val else "item"
    display_val = self.app_ref._display_item_type(self.current_type_raw)
    type_btn = getattr(self, 'type_btn', None)
    if type_btn is not None:
        try:
            type_btn.configure(text=display_val + " \u25bc")
        except Exception:
            pass
    summary = getattr(self, '_type_summary_label', None)
    if summary is not None:
        try:
            summary.configure(text=display_val)
        except Exception:
            pass
    _runtime_apply_rune_state_to_card(self)
    if self.app_ref and not getattr(self, '_suspend_unsaved_mark', False):
        self.app_ref.mark_unsaved()


def _runtime_card_is_rune(card):
    try:
        return _rule_uses_rune_name(
            getattr(card, 'current_type_raw', '') or '',
            type_field=getattr(card, 'type_field', 'name'),
            display_name=getattr(card, 'display_name', '') or '',
            raw_line=getattr(card, 'raw_line', '') or '',
        )
    except Exception:
        return False


def _runtime_model_is_rune(model):
    if not isinstance(model, dict):
        return False
    try:
        return _rule_uses_rune_name(
            model.get('type', '') or '',
            type_field=model.get('type_field', 'name'),
            display_name=(model.get('name', '') or model.get('display_comment', '') or ''),
            raw_line=model.get('raw_line', '') or '',
        )
    except Exception:
        return False


def _runtime_apply_rune_state_to_card(card, selected_quality=None):
    qual_menu = getattr(card, 'qual_menu', None)
    desired_quality = str(selected_quality or '').strip().lower()
    if not desired_quality:
        getter = getattr(card, 'get_quality_value', None)
        if callable(getter):
            try:
                desired_quality = str(getter() or '').strip().lower()
            except Exception:
                desired_quality = ''
    if not desired_quality and qual_menu is not None and hasattr(qual_menu, 'get'):
        try:
            desired_quality = str(qual_menu.get() or '').strip().lower()
        except Exception:
            desired_quality = ''
    if not desired_quality:
        desired_quality = str(getattr(card, '_last_non_rune_quality', 'normal') or 'normal').strip().lower() or 'normal'
    if desired_quality != 'rune':
        card._last_non_rune_quality = desired_quality

    is_rune = _runtime_card_is_rune(card)
    if is_rune:
        desired_quality = 'rune'
    elif desired_quality == 'rune':
        desired_quality = str(getattr(card, '_last_non_rune_quality', 'normal') or 'normal').strip().lower() or 'normal'

    setter = getattr(card, '_set_quality_value', None)
    if callable(setter):
        try:
            setter(desired_quality)
        except Exception:
            pass
    elif qual_menu is not None:
        try:
            current_quality = str(qual_menu.get() or '').strip().lower()
        except Exception:
            current_quality = ''
        if desired_quality and current_quality != desired_quality:
            try:
                qual_menu.set(desired_quality)
            except Exception:
                pass

    lock_setter = getattr(card, '_set_quality_locked', None)
    if callable(lock_setter):
        try:
            lock_setter(is_rune)
        except Exception:
            pass
    elif qual_menu is not None:
        try:
            qual_menu.configure(state='disabled' if is_rune else 'readonly')
        except Exception:
            try:
                qual_menu.configure(state='disabled' if is_rune else 'normal')
            except Exception:
                pass

    card.base_color = QUALITY_COLORS.get(desired_quality, "#444")
    try:
        card.indicator.configure(fg_color=card.base_color)
    except Exception:
        pass
    try:
        card.name_label.configure(text_color=card.base_color)
    except Exception:
        pass
    return is_rune


def _runtime_itemrulecard_update_color(self, val):
    _runtime_apply_rune_state_to_card(self, selected_quality=val)
    if self.app_ref and not getattr(self, '_suspend_unsaved_mark', False):
        self.app_ref.mark_unsaved()


def _runtime_itemrulecard_deferred_summary(self):
    stat_count = len(getattr(self, 'pending_stats_data', []) or [])
    advanced_count = len(getattr(self, 'pending_advanced_data', []) or [])
    parts = []
    if stat_count:
        parts.append(f"{stat_count} stat{'s' if stat_count != 1 else ''}")
    if advanced_count:
        parts.append(f"{advanced_count} advanced rule{'s' if advanced_count != 1 else ''}")
    if not parts:
        parts.append("Ready to edit")
    return " | ".join(parts)

# ---------------------------------------------------------------------------
# 8. MAIN APP
# ---------------------------------------------------------------------------
class DarcsNipEditor(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.withdraw()
        self.title(f"Darc's Visual Pickit  â€¢  {APP_VERSION}")
        self.geometry("1920x1080")
        self.minsize(1500, 900)
        self.configure(fg_color="#050505")
        # Core state
        self.folder = ""
        self.pending_errors = []
        self.loading_modal = None
        self.target_count = 0
        self._is_loading = False
        self.unsaved_changes = False
        self.tooltips_enabled = tk.BooleanVar(value=True)
        self.backup_active = tk.BooleanVar(value=True)
        self.backup_warn = tk.BooleanVar(value=True)
        self.backup_days = tk.IntVar(value=7)
        self.load_limit = tk.StringVar(value="Load 50")
        self.stat_clipboard = []
        self.syntax_errors = []
        self.catalog_widgets = [] # (header_btn, cat_name)
        self.library_widgets = [] # (header_btn, cat_name, icon)
        self.deleted_stack = []
        self.config_path = user_data_path("shortcuts.json")
        self.shortcuts = self.load_config()
        self.numeric_stat_id_map = dict(self.shortcuts.get('numeric_stat_id_map', {}) or {})
        self.recent_files = list(self.shortcuts.get('recent_files', []) or [])
        self.max_recent_files = int(self.shortcuts.get('max_recent_files', 10) or 10)
        self.validation_state = "Not checked"
        self.auto_check_updates = bool(self.shortcuts.get('auto_check_updates', True))
        self.update_check_interval_hours = int(self.shortcuts.get('update_check_interval_hours', 24) or 24)
        self.last_update_check_utc = str(self.shortcuts.get('last_update_check_utc', '') or '')
        self.skipped_update_version = str(self.shortcuts.get('skipped_update_version', '') or '')
        self._update_check_in_progress = False
        self._latest_release_info = None
        self._latest_update_error = None
        self._latest_release_cmp_result = 0
        self._latest_release_cmp_reason = "same"
        self._latest_release_label = ""
        self._latest_release_asset = None
        self.update_center_window = None
        self._update_check_thread = None
        self._update_check_pending_result = None
        self._update_check_poll_after = None
        self._update_check_timeout_after = None
        self._update_check_started_at = 0.0
        self._config_save_after = None
        self._pending_config_payload = None
        self._last_saved_config_payload = None
        self._config_save_delay_ms = 250
        self._main_destroy_in_progress = False
        self._main_thread_callback_queue = queue.Queue()
        self._main_thread_callback_after = None
        self._updater_error_log = user_data_path("update_errors.log")
        self._after_update_launch = any(str(arg).strip().lower() == "--after-update" for arg in sys.argv[1:])
        self._rule_filter_after = None
        self._catalog_filter_after = None
        self._library_filter_after = None
        self._native_drop_ready = False
        self._card_search_cache = {}
        self._empty_state_reason = "startup"
        self.card_icons = {
            "delete": load_icon("delete", "\U0001F5D1\uFE0F"),
            "down": load_icon("down", "\u2B07\uFE0F"),
            "up": load_icon("up", "\u2B06\uFE0F"),
            "clone": load_icon("clone", "\U0001F4D1"),
            "copy": load_icon("copy", "\U0001F4CB"),
            "import": load_icon("import", "\U0001F4E5"),
            "add": load_icon("add", "\u2795"),
            "undo": load_icon("undo", "\u21A9\uFE0F")
        }
        self.report_callback_exception = self._report_tk_callback_exception
        set_windows_app_id()
        self.after(0, self._finalize_main_window_chrome)
        self.load_custom_font("exocent.ttf")
        self.d2_font_name = "Arial"
        for f in ["Exocent", "Exocet", "Exocet Blizzard", "Exocet Light"]:
            if f in tkfont.families():
                self.d2_font_name = f
                break
        self.d2_font = (self.d2_font_name, D2_FONT_SIZE) if self.d2_font_name != "Arial" \
                        else ("Constantia", D2_FONT_SIZE, "bold")
        self.item_font = (self.d2_font_name, ITEM_FONT_SIZE) if self.d2_font_name != "Arial" \
                         else ("Arial", ITEM_FONT_SIZE)
        self.font_data = {"d2": self.d2_font, "item": self.item_font}
        self.current_file = ""
        self.rule_cards = []
        self.active_card = None
        self.all_file_data = []
        self.loaded_count = 0
        self.load_id = 0
        self._deferred_hydration_queue = []
        self._deferred_hydration_after = None
        self._deferred_hydration_tick_ms = 12
        self.initial_card_hydration_count = 4
        self._render_repack_pending = False
        self.page_size = 50
        self.current_page_index = 0
        self.filtered_model_indices = []
        self._model_search_cache = {}
        self.last_profile = {}
        self.last_profile_summary = ""
        self._page_sync_in_progress = False
        self.page_status_var = tk.StringVar(value="Page 0 / 0")
        self.page_size_var = tk.StringVar(value="50 / page")
        self._build_ui()
        self._sanitize_recent_files()
        self.refresh_recent_files_menu()
        self.update_status_bar()
        try:
            self._last_saved_config_payload = self._build_config_payload()
        except Exception:
            self._last_saved_config_payload = None
    def _finalize_main_window_chrome(self):
        try:
            self.deiconify()
        except Exception:
            pass
        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass
        try:
            self.state('zoomed')
        except Exception:
            pass
        polish_window(self, refresh=True)
        self.after(20, self._update_empty_state)
        self._ensure_main_thread_callback_pump()
        if not getattr(self, "_after_update_launch", False):
            self.after(1800, self.auto_check_for_updates_silent)
        self.after_idle(self._init_native_drop_support)
        self.after_idle(self._refresh_sidebars)
        self.after_idle(self.rebind_shortcuts)
    # -----------------------------------------------------------------------
    # UI BUILDER
    # -----------------------------------------------------------------------
    def _build_ui(self):
        # â”€â”€ Left sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.sidebar_left = ctk.CTkFrame(self, width=380, fg_color="#0d0d0d", corner_radius=0)
        self.sidebar_left.pack(side="left", fill="y")
        self.sidebar_left.pack_propagate(False)
        ctk.CTkButton(self.sidebar_left, text="Load Folder", font=self.d2_font,
                      height=60, fg_color="#1a1a1a", hover_color="#262626",
                      corner_radius=0, command=self.open_folder).pack(side="top", fill="x")
        ctk.CTkLabel(self.sidebar_left, text="ITEM SEARCH",
                     font=self.item_font, text_color="orange").pack(side="top", pady=(5, 0))
        self.cat_search_var = tk.StringVar()
        self.cat_search_var.trace("w", self._schedule_catalog_filter)
        ctk.CTkEntry(self.sidebar_left, textvariable=self.cat_search_var,
                     placeholder_text="Search...", font=self.item_font,
                     height=35, corner_radius=0, fg_color="#1a1a1a").pack(side="top", fill="x", pady=(2, 5))
        # Bottom buttons must be packed BEFORE the scrollable frame so they
        # stay at the bottom (pack order matters for side="bottom").
        ctk.CTkButton(self.sidebar_left, text="Save File", font=self.d2_font,
                      height=45, fg_color="#27ae60", hover_color="#2ecc71",
                      text_color="#000", corner_radius=0,
                      command=self.save_file).pack(side="bottom", fill="x")
        ctk.CTkButton(self.sidebar_left, text="Save As...", font=self.d2_font,
                      height=45, fg_color="#2980b9", text_color="#fff",
                      corner_radius=0, command=self.save_as_file).pack(side="bottom", fill="x", pady=(0, 2))
        self.side_scroll = ctk.CTkScrollableFrame(
            self.sidebar_left,
            label_text="Item Catalog", label_font=self.d2_font,
            label_text_color="#c9a063", fg_color="transparent", corner_radius=0)
        self.side_scroll.pack(side="top", fill="both", expand=True)
        self.init_catalog()
        # â”€â”€ Right sidebar â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.sidebar_right = ctk.CTkFrame(self, width=380, fg_color="#0d0d0d", corner_radius=0)
        self.sidebar_right.pack(side="right", fill="y")
        self.sidebar_right.pack_propagate(False)
        ctk.CTkLabel(self.sidebar_right, text="STAT SEARCH",
                     font=self.item_font, text_color="gold").pack(side="top", pady=(5, 0))
        self.lib_search_var = tk.StringVar()
        self.lib_search_var.trace("w", self._schedule_library_filter)
        ctk.CTkEntry(self.sidebar_right, textvariable=self.lib_search_var,
                     placeholder_text="Search...", font=self.item_font,
                     height=35, corner_radius=0, fg_color="#1a1a1a").pack(side="top", fill="x", pady=(2, 5))
        ctk.CTkButton(self.sidebar_right, text="Shortcuts", font=self.d2_font,
                      height=45, fg_color="#1a1a1a", hover_color="#262626",
                      corner_radius=0,
                      command=lambda: ShortcutDialog(
                          self,
                          self,
                          extract_shortcut_bindings=_extract_shortcut_bindings,
                          apply_window_icon=apply_window_icon,
                          configure_dialog_window=configure_dialog_window,
                      )).pack(side="bottom", fill="x")
        ctk.CTkButton(self.sidebar_right, text="Load Backup", font=self.d2_font,
                      height=45, fg_color="#2980b9", text_color="#fff",
                      corner_radius=0, command=self.load_backup_file).pack(side="bottom", fill="x", pady=(0, 2))
        self.stat_scroll = ctk.CTkScrollableFrame(
            self.sidebar_right,
            label_text="Stat & Skill Library", label_font=self.d2_font,
            label_text_color="#c9a063", fg_color="transparent", corner_radius=0)
        self.stat_scroll.pack(side="top", fill="both", expand=True)
        self.init_stat_library()
        # â”€â”€ Center â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        self.center = ctk.CTkFrame(self, fg_color="transparent")
        self.center.pack(side="left", fill="both", expand=True, padx=8, pady=4)
        self.header_frame = hf = ctk.CTkFrame(self.center, fg_color="#0d0d0d", height=60, corner_radius=0)
        hf.pack(fill="x", pady=(0, 8), padx=4)
        self.rule_search_var = tk.StringVar()
        self._rule_filter_after = None
        self.rule_search_var.trace_add("write", lambda *_: self._schedule_rule_filter())
        self.rule_search_entry = ctk.CTkEntry(
            hf,
            textvariable=self.rule_search_var,
            placeholder_text="Search Active Rules...",
            font=self.item_font,
            height=38,
            width=300
        )
        self.rule_search_entry.pack(side="left", padx=(15, 8), pady=10)
        self.recent_files_menu = ctk.CTkOptionMenu(
            hf, values=["Recent Files"], width=170, font=(self.d2_font_name, 14),
            command=self.open_recent_file)
        self.recent_files_menu.pack(side="left", padx=6)
        self.recent_files_menu.set("Recent Files")
        self.page_prev_btn = ctk.CTkButton(hf, text="\u25c0", width=38, height=38, fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.go_prev_page)
        self.page_prev_btn.pack(side="left", padx=(10, 4))
        self.page_info_label = ctk.CTkLabel(hf, textvariable=self.page_status_var, font=(self.d2_font_name, 14), text_color="#c9a063", width=120)
        self.page_info_label.pack(side="left", padx=4)
        self.page_next_btn = ctk.CTkButton(hf, text="\u25b6", width=38, height=38, fg_color="#2b2b2b", hover_color="#3a3a3a", command=self.go_next_page)
        self.page_next_btn.pack(side="left", padx=4)
        self.page_size_menu = ctk.CTkOptionMenu(hf, values=["10 / page", "25 / page", "50 / page", "100 / page", "200 / page", "All"], variable=self.page_size_var, width=105, font=(self.d2_font_name, 13), command=self.change_page_size)
        self.page_size_menu.pack(side="left", padx=6)
        ctk.CTkButton(hf, text="Backups", font=(self.d2_font_name, 14), height=38, width=90,
                      fg_color="#2b2b2b", hover_color="#3a3a3a",
                      command=self.open_backup_settings).pack(side="left", padx=6)
        self.tooltips_checkbox = None
        self.header = ctk.CTkLabel(hf, text="Select NIP",
                                   font=self.item_font, text_color="#c9a063")
        self.header.pack(side="right", padx=10)
        self.card_scroll = ctk.CTkScrollableFrame(self.center, fg_color="#050505", corner_radius=0)
        self.card_scroll.pack(fill="both", expand=True)
        self.empty_state_label = ctk.CTkLabel(
            self.card_scroll,
            text="Load a .nip file to begin editing.",
            font=(self.d2_font_name, 18),
            text_color="#8f8f8f",
            justify="center"
        )
        bottom = ctk.CTkFrame(self.center, fg_color="#0d0d0d", height=60, corner_radius=0)
        bottom.pack(side="bottom", fill="x", pady=8, padx=4)
        bc = ctk.CTkFrame(bottom, fg_color="transparent")
        bc.pack(expand=True, fill="x", padx=10)
        bf = (self.d2_font_name, 18)
        ctk.CTkButton(bc, text="+ New Rule", font=bf, height=40,
                      fg_color="#c9a063", text_color="#000", hover_color="#e0b87d",
                      command=self.add_blank).pack(side="left", expand=True, fill="x", padx=7, pady=6)
        ctk.CTkButton(bc, text="+ Comment", font=bf, height=40,
                      fg_color="#7f8c8d", hover_color="#96a1a2", text_color="#000",
                      command=self.add_comment).pack(side="left", expand=True, fill="x", padx=7, pady=6)
        self.donate_btn = None
        self.performance_mode_bottom_button = ctk.CTkButton(
            bc,
            text="PERFORMANCE ON",
            font=bf,
            height=40,
            text_color="#000000",
            border_width=2,
            border_color="#8ef0a8",
            fg_color="#16a34a",
            hover_color="#22c55e",
            command=self.toggle_performance_mode_ui,
        )
        self.performance_mode_bottom_button.pack(side="left", expand=True, fill="x", padx=7, pady=6)
        ctk.CTkButton(bc, text="Entries", font=bf, height=40,
                      fg_color="#1a2a3a", hover_color="#32597a",
                      command=self.open_entries_settings).pack(side="left", expand=True, fill="x", padx=7, pady=6)
        ctk.CTkButton(bc, text="Validate File", font=bf, height=40,
                      fg_color="#4b0082", hover_color="#8a2be2", text_color="#fff",
                      command=self.validate_loaded_file).pack(side="left", expand=True, fill="x", padx=7, pady=6)
        ctk.CTkButton(bc, text="Update", font=bf, height=40,
                      fg_color="#1f6f8b", hover_color="#2d8fb3",
                      command=self.check_for_app_update).pack(side="left", expand=True, fill="x", padx=7, pady=6)
        ctk.CTkButton(bc, text="Exit", font=bf, height=40,
                      fg_color="#5a1a1a", hover_color="#8a1a1a",
                      command=self.hard_shutdown).pack(side="left", expand=True, fill="x", padx=7, pady=6)
        self.drop_hint_label = ctk.CTkLabel(self.center, text="Tip: drag and drop a .nip file anywhere onto the app window to load it.",
                                            font=(self.d2_font_name, 12), text_color="#8f8f8f")
        self.drop_hint_label.pack(side="bottom", fill="x", padx=12, pady=(0, 4))
        self.status_bar = ctk.CTkFrame(self.center, fg_color="#0b0b0b", height=30, corner_radius=0)
        self.status_bar.pack(side="bottom", fill="x", padx=4, pady=(0, 4))
        self.status_label = ctk.CTkLabel(self.status_bar, text="", anchor="w", font=(self.d2_font_name, 12), text_color="#c9a063")
        self.status_label.pack(side="left", fill="x", expand=True, padx=12, pady=4)
    def _display_item_type(self, raw_value):
        raw = str(raw_value or "").strip()
        return RAW_TO_FRIENDLY_ITEM_TYPE.get(raw, _friendly_item_type_option(raw))

    def _raw_item_type(self, display_value):
        display = str(display_value or "").strip()
        return FRIENDLY_TO_RAW_ITEM_TYPE.get(display, display)

    def _card_raw_item_type(self, card):
        raw = str(getattr(card, "current_type_raw", "") or "").strip()
        if raw:
            return raw
        try:
            visible = (card.type_btn.cget("text") or "").replace("\u25bc", "").strip()
        except Exception:
            visible = ""
        return self._raw_item_type(visible) if visible else "item"

    def _show_loading_overlay(self):
        try:
            if getattr(self, "loading_modal", None) and self.loading_modal.winfo_exists():
                return
        except Exception:
            pass
        try:
            self.loading_modal = LoadingDialog(self)
            self.loading_modal.update_progress(0, max(1, getattr(self, 'target_count', 1)))
        except Exception:
            self.loading_modal = None

    def _hide_loading_overlay(self):
        try:
            if getattr(self, "loading_modal", None):
                self.loading_modal.safe_close()
        except Exception:
            pass
        self.loading_modal = None

    def _clear_search_cache(self):
        self._card_search_cache = {}

    def _get_empty_state_text(self):
        query = (self.rule_search_var.get().strip() if hasattr(self, 'rule_search_var') else "")
        if getattr(self, '_is_loading', False):
            return "Loading rules..."
        if query:
            return f'No rules match "{query}".'
        if not self.current_file:
            return "Load a .nip file to begin editing."
        if not self.rule_cards:
            return "This file has no visible entries yet."
        return "Nothing to show."

    def _update_empty_state(self, visible_count=None):
        if not hasattr(self, 'empty_state_label'):
            return
        if visible_count is None:
            visible_count = 0
            q = self.rule_search_var.get().lower().strip() if hasattr(self, 'rule_search_var') else ""
            for c in self.rule_cards:
                if getattr(c, 'is_comment', False) and getattr(c, 'hide_in_ui', False):
                    continue
                if not q:
                    visible_count += 1
                else:
                    blob = self._get_card_search_blob_cached(c)
                    if q in blob:
                        visible_count += 1
        if visible_count <= 0:
            self.empty_state_label.configure(text=self._get_empty_state_text())
            self.empty_state_label.pack(fill="x", padx=20, pady=40)
        else:
            self.empty_state_label.pack_forget()

    def _get_card_search_blob_cached(self, card):
        cache_key = id(card)
        cached = self._card_search_cache.get(cache_key)
        if cached is not None:
            return cached
        blob = self._card_search_blob(card)
        self._card_search_cache[cache_key] = blob
        return blob

    def _schedule_catalog_filter(self, *args):
        if self._catalog_filter_after:
            try:
                self.after_cancel(self._catalog_filter_after)
            except Exception:
                pass
        self._catalog_filter_after = self.after(120, self._run_catalog_filter)

    def _run_catalog_filter(self):
        self._catalog_filter_after = None
        self.filter_catalog()

    def _schedule_library_filter(self, *args):
        if self._library_filter_after:
            try:
                self.after_cancel(self._library_filter_after)
            except Exception:
                pass
        self._library_filter_after = self.after(120, self._run_library_filter)

    def _run_library_filter(self):
        self._library_filter_after = None
        self.filter_library()

    def _schedule_rule_filter(self, *args):
        if self._rule_filter_after:
            try:
                self.after_cancel(self._rule_filter_after)
            except Exception:
                pass
        self._rule_filter_after = self.after(120, self._run_rule_filter)

    def _run_rule_filter(self):
        self._rule_filter_after = None
        self.filter_rule_cards()

    def _status_save_text(self):
        return "Unsaved" if self.unsaved_changes else "Saved"

    def _status_rule_count(self):
        return sum(1 for c in self.rule_cards if not getattr(c, 'hide_in_ui', False))

    def update_status_bar(self, validation_state=None):
        if validation_state is not None:
            self.validation_state = validation_state
        file_name = os.path.basename(self.current_file) if self.current_file else "No file loaded"
        text = f"[ File: {file_name} ] [ {self._status_save_text()} ] [ Rules: {self._status_rule_count()} ] [ {self.validation_state} ] [ {APP_VERSION} ]"
        if hasattr(self, 'status_label') and self.status_label.winfo_exists():
            status_color = "#c9a063"
            if self.unsaved_changes:
                status_color = "#f1c40f"
            if str(self.validation_state).lower() in {"error", "partial load"}:
                status_color = "#ff7675"
            elif str(self.validation_state).lower() in {"ok", "saved", "not checked"} and not self.unsaved_changes:
                status_color = "#c9a063"
            self.status_label.configure(text=text, text_color=status_color)

    def _sanitize_recent_files(self):
        cleaned = []
        for path in list(self.recent_files or []):
            p = str(path).strip()
            if p and os.path.exists(p) and p not in cleaned:
                cleaned.append(p)
        self.recent_files = cleaned[:max(1, int(self.max_recent_files or 10))]
        self.shortcuts['recent_files'] = list(self.recent_files)

    def add_recent_file(self, path):
        p = str(path or '').strip()
        if not p:
            return
        self._sanitize_recent_files()
        if p in self.recent_files:
            self.recent_files.remove(p)
        self.recent_files.insert(0, p)
        self.recent_files = self.recent_files[:max(1, int(self.max_recent_files or 10))]
        self.shortcuts['recent_files'] = list(self.recent_files)
        self.save_config()
        self.refresh_recent_files_menu()
        self.update_status_bar()

    def refresh_recent_files_menu(self):
        if not hasattr(self, 'recent_files_menu'):
            return
        self._sanitize_recent_files()
        values = ['Recent Files']
        values.extend(self.recent_files if self.recent_files else ['(No recent files)'])
        try:
            self.recent_files_menu.configure(values=values)
            self.recent_files_menu.set('Recent Files')
        except Exception:
            pass

    def open_recent_file(self, choice):
        if not choice or choice in ('Recent Files', '(No recent files)'):
            if hasattr(self, 'recent_files_menu'):
                self.recent_files_menu.set('Recent Files')
            return
        if not os.path.exists(choice):
            try:
                self.recent_files.remove(choice)
            except ValueError:
                pass
            self.shortcuts['recent_files'] = list(self.recent_files)
            self.save_config()
            self.refresh_recent_files_menu()
            messagebox.showwarning('Recent Files', 'That file no longer exists.', parent=self)
            return
        self.load_absolute_file(choice)
        if hasattr(self, 'recent_files_menu'):
            self.recent_files_menu.set('Recent Files')

    def _init_native_drop_support(self):
        if self._native_drop_ready:
            return
        self._native_drop_ready = install_native_file_drop(self, self.handle_dropped_files)
        if self._native_drop_ready:
            self.update_status_bar()

    def handle_dropped_files(self, paths):
        valid = [p for p in (paths or []) if str(p).lower().endswith('.nip') and os.path.isfile(p)]
        if not valid:
            messagebox.showinfo('Drag and Drop', 'Drop a .nip file to load it.', parent=self)
            return
        path = valid[0]
        self.load_absolute_file(path)

    # -----------------------------------------------------------------------
    # CATALOG (left sidebar) â€” KEY FIX AREA
    # -----------------------------------------------------------------------
    def init_catalog(self):
        """Rebuild the left-sidebar item catalog."""
        for w in self.side_scroll.winfo_children():
            w.destroy()
        self.catalog_widgets = []
        for cat_name, items in ITEM_CATALOG.items():
            section = ctk.CTkFrame(self.side_scroll, fg_color="transparent")
            section.pack(fill="x", expand=False)
            section._body_visible = False
            section._item_names = list(items)
            section._item_btn_cache = {}
            header_btn = ctk.CTkButton(
                section, text=_display_label(cat_name),
                font=self.d2_font, height=45,
                text_color="#c9a063", fg_color="#1a1a1a", hover_color="#222",
                anchor="w", corner_radius=0)
            header_btn.pack(fill="x", pady=1)
            header_btn._base_label = _display_label(cat_name)
            header_btn.configure(command=lambda s=section, b=header_btn, c=cat_name: self._toggle_sidebar_section(s, b, c))
            self.catalog_widgets.append((header_btn, cat_name))

    def _get_catalog_button(self, section, item_name, cat_name):
        cache = getattr(section, "_item_btn_cache", None)
        if cache is None:
            cache = {}
            section._item_btn_cache = cache
        btn = cache.get(item_name)
        if btn is None:
            btn = ctk.CTkButton(
                section, text=f"    {item_name}",
                fg_color="#000", hover_color="#111",
                font=self.item_font, height=35, anchor="w",
                command=lambda n=item_name, c=cat_name: self.add_from_cat(n, c))
            btn._label_lower = str(item_name).lower()
            cache[item_name] = btn
        return btn

    def _get_library_button(self, section, key, label_text):
        cache = getattr(section, "_data_btn_cache", None)
        if cache is None:
            cache = {}
            section._data_btn_cache = cache
        btn = cache.get(key)
        if btn is None:
            btn = ctk.CTkButton(
                section, text=f"    {label_text}",
                fg_color="#000", hover_color="#111",
                font=self.item_font, height=35, anchor="w",
                command=lambda stat_key=key, stat_name=label_text: self.add_to_last(stat_key, stat_name))
            btn._label_lower = str(label_text).lower()
            cache[key] = btn
        return btn

    def _hide_section_buttons(self, section, cache_attr):
        for btn in list(getattr(section, cache_attr, {}).values()):
            try:
                btn.pack_forget()
            except Exception:
                pass

    def _toggle_sidebar_section(self, section, header_btn, cat_name):
        visible = getattr(section, "_body_visible", False)
        if visible:
            self._hide_section_buttons(section, "_item_btn_cache")
            self._hide_section_buttons(section, "_data_btn_cache")
            section._body_visible = False
        else:
            item_names = getattr(section, "_item_names", None)
            data_items = getattr(section, "_data_items", None)
            if item_names is not None:
                for item_name in item_names:
                    self._get_catalog_button(section, item_name, cat_name).pack(fill="x", pady=1)
            elif data_items is not None:
                for key, label_text in data_items:
                    self._get_library_button(section, key, label_text).pack(fill="x", pady=1)
            section._body_visible = True
        header_btn.configure(text=getattr(header_btn, "_base_label", _display_label(header_btn.cget("text"))))
        self.after_idle(self._refresh_sidebars)
    def _refresh_sidebars(self):
        try:
            self.side_scroll.update_idletasks()
            self.stat_scroll.update_idletasks()
        except Exception:
            pass
    def filter_catalog(self, *args):
        q = self.cat_search_var.get().lower().strip()
        for header_btn, cat_name in self.catalog_widgets:
            section = header_btn.master
            section.pack(fill="x", expand=False)
            if not q:
                self._hide_section_buttons(section, "_item_btn_cache")
                section._body_visible = False
                header_btn.configure(text=_display_label(cat_name))
                continue

            matches = []
            for item_name in getattr(section, "_item_names", []):
                label = str(item_name).lower()
                hit = q in label or q in cat_name.lower()
                if hit:
                    matches.append(item_name)
            if matches:
                section.pack(fill="x", expand=False)
                self._hide_section_buttons(section, "_item_btn_cache")
                for item_name in matches:
                    self._get_catalog_button(section, item_name, cat_name).pack(fill="x", pady=1)
                section._body_visible = True
                header_btn.configure(text=_display_label(cat_name))
            else:
                self._hide_section_buttons(section, "_item_btn_cache")
                section.pack_forget()
                section._body_visible = False
        self.after_idle(self._refresh_sidebars)
    # -----------------------------------------------------------------------
    # STAT LIBRARY (right sidebar) â€” KEY FIX AREA
    # -----------------------------------------------------------------------
    def init_stat_library(self):
        """Rebuild the right-sidebar stat/skill library."""
        for w in self.stat_scroll.winfo_children():
            w.destroy()
        self.library_widgets = []
        all_sections = list(STAT_LIBRARY.items()) + list(SKILL_LIBRARY.items())
        for cat_name, data in all_sections:
            icon = "#" if cat_name in STAT_LIBRARY else "*"
            section = ctk.CTkFrame(self.stat_scroll, fg_color="transparent")
            section.pack(fill="x", expand=False)
            section._body_visible = False
            section._data_items = list(data.items())
            section._data_btn_cache = {}
            header_btn = ctk.CTkButton(
                section, text=_display_label(cat_name),
                font=self.d2_font, height=45,
                text_color="#c9a063", fg_color="#1a1a1a", hover_color="#222",
                anchor="w", corner_radius=0)
            header_btn.pack(fill="x", pady=1)
            header_btn._base_label = _display_label(cat_name)
            header_btn.configure(command=lambda s=section, b=header_btn, c=cat_name: self._toggle_sidebar_section(s, b, c))
            self.library_widgets.append((header_btn, cat_name, icon))

    def filter_library(self, *args):
        q = self.lib_search_var.get().lower().strip()
        for header_btn, cat_name, icon in self.library_widgets:
            section = header_btn.master
            section.pack(fill="x", expand=False)
            if not q:
                self._hide_section_buttons(section, "_data_btn_cache")
                section._body_visible = False
                header_btn.configure(text=_display_label(cat_name))
                continue

            matches = []
            for key, label_text in getattr(section, "_data_items", []):
                label = str(label_text).lower()
                hit = q in label or q in cat_name.lower()
                if hit:
                    matches.append((key, label_text))
            if matches:
                section.pack(fill="x", expand=False)
                self._hide_section_buttons(section, "_data_btn_cache")
                for key, label_text in matches:
                    self._get_library_button(section, key, label_text).pack(fill="x", pady=1)
                section._body_visible = True
                header_btn.configure(text=_display_label(cat_name))
            else:
                self._hide_section_buttons(section, "_data_btn_cache")
                section.pack_forget()
                section._body_visible = False
        self.after_idle(self._refresh_sidebars)
    # -----------------------------------------------------------------------
    # STATE HELPERS
    # -----------------------------------------------------------------------
    def mark_unsaved(self):
        if getattr(self, '_is_loading', False):
            return
        self.unsaved_changes = True
        self.validation_state = "Pending"
        self._clear_search_cache()
        base = os.path.basename(self.current_file) if self.current_file else "New File"
        prog = f" ({self.loaded_count}/{len(self.all_file_data)})" if self.all_file_data else ""
        self.header.configure(text=f"Editing: {base} *{prog}")
        self.update_status_bar()
        self._update_empty_state()
    def mark_saved(self):
        self.unsaved_changes = False
        self._clear_search_cache()
        base = os.path.basename(self.current_file) if self.current_file else "New File"
        prog = f" ({self.loaded_count}/{len(self.all_file_data)})" if self.all_file_data else ""
        self.header.configure(text=f"Editing: {base}{prog}")
        self.update_status_bar()
        self._update_empty_state()
    # -----------------------------------------------------------------------
    # CONFIG / SHORTCUTS
    # -----------------------------------------------------------------------
    def load_config(self):
        defaults = {"save": "<Control-s>", "new_rule": "<Control-n>",
                    "syntax_check": "<Control-k>", "load_folder": "<Control-o>",
                    "undo": "<Control-z>", "numeric_stat_id_map": {},
                    "recent_files": [], "max_recent_files": 10,
                    "auto_check_updates": True, "update_check_interval_hours": 24,
                    "last_update_check_utc": "", "skipped_update_version": ""}
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path) as f:
                    data = json.load(f)
                    for k, v in defaults.items():
                        data.setdefault(k, v)
                    data.setdefault('numeric_stat_id_map', {})
                    data.setdefault('recent_files', [])
                    data.setdefault('max_recent_files', 10)
                    data.setdefault('auto_check_updates', True)
                    data.setdefault('update_check_interval_hours', 24)
                    data.setdefault('last_update_check_utc', '')
                    data.setdefault('skipped_update_version', '')
                    data.setdefault('performance_mode', True)
                    data.setdefault('performance_page_size', '10 / page')
                    return data
        except:
            pass
        return defaults

    def _build_config_payload(self):
        payload = dict(getattr(self, 'shortcuts', {}) or {})
        payload['numeric_stat_id_map'] = dict(getattr(self, 'numeric_stat_id_map', {}) or {})
        payload['recent_files'] = list(getattr(self, 'recent_files', []) or [])
        payload['max_recent_files'] = int(getattr(self, 'max_recent_files', 10) or 10)
        payload['auto_check_updates'] = bool(getattr(self, 'auto_check_updates', True))
        payload['update_check_interval_hours'] = int(getattr(self, 'update_check_interval_hours', 24) or 24)
        payload['last_update_check_utc'] = str(getattr(self, 'last_update_check_utc', '') or '')
        payload['skipped_update_version'] = str(getattr(self, 'skipped_update_version', '') or '')
        perf_var = getattr(self, 'performance_mode', None)
        try:
            payload['performance_mode'] = bool(perf_var.get()) if perf_var is not None else bool(payload.get('performance_mode', True))
        except Exception:
            payload['performance_mode'] = bool(payload.get('performance_mode', True))
        payload['performance_page_size'] = str(
            getattr(self, 'performance_page_size_choice', payload.get('performance_page_size', '10 / page')) or '10 / page'
        )
        return payload

    def _cancel_pending_config_save(self):
        after_id = getattr(self, '_config_save_after', None)
        if after_id is None:
            return
        try:
            self.after_cancel(after_id)
        except Exception:
            pass
        self._config_save_after = None

    def _write_config_payload(self, payload):
        if payload == getattr(self, '_last_saved_config_payload', None):
            return False
        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        self._last_saved_config_payload = payload
        return True

    def _flush_pending_config_save(self):
        self._config_save_after = None
        payload = getattr(self, '_pending_config_payload', None)
        self._pending_config_payload = None
        if payload is None:
            payload = self._build_config_payload()
        self._write_config_payload(payload)

    def save_config(self, immediate=False):
        try:
            payload = self._build_config_payload()
        except Exception:
            return
        try:
            if payload == getattr(self, '_last_saved_config_payload', None):
                self._pending_config_payload = None
                self._cancel_pending_config_save()
                return
        except Exception:
            pass
        if immediate:
            try:
                self._pending_config_payload = None
                self._cancel_pending_config_save()
                self._write_config_payload(payload)
            except Exception:
                pass
            return
        self._pending_config_payload = payload
        try:
            self._cancel_pending_config_save()
            delay = max(10, int(getattr(self, '_config_save_delay_ms', 250) or 250))
            self._config_save_after = self.after(delay, self._flush_pending_config_save)
        except Exception:
            try:
                self._write_config_payload(payload)
            except Exception:
                pass
    def rebind_shortcuts(self):
        self.unbind_all("<Key>")
        mapping = {"save": self.save_file, "new_rule": self.add_blank,
                   "syntax_check": self.manual_syntax_check,
                   "load_folder": self.open_folder, "undo": self.undo_delete}
        for act, key in _extract_shortcut_bindings(self.shortcuts).items():
            if not key:
                continue
            try:
                if act in mapping:
                    self.bind_all(key, lambda e, fn=mapping[act]: fn())
                else:
                    self.bind_all(key, lambda e, a=act: self.trigger_custom_shortcut(a))
            except Exception:
                continue
    def trigger_custom_shortcut(self, act):
        t = self.active_card or (self.rule_cards[-1] if self.rule_cards else None)
        if not t or getattr(t, 'is_comment', False):
            return
        for lib in [STAT_LIBRARY, SKILL_LIBRARY]:
            for cat, data in lib.items():
                for k, v in data.items():
                    if act.lower() in [k.lower(), v.lower()]:
                        t.add_stat_visually(k, v)
                        return
    # -----------------------------------------------------------------------
    # CARD MANAGEMENT
    # -----------------------------------------------------------------------
    def set_active(self, card):
        if (self.active_card and self.active_card != card
                and self.active_card.winfo_exists()
                and not getattr(self.active_card, 'is_comment', False)):
            self.active_card.set_active(False)
        if not getattr(card, 'is_comment', False):
            self.active_card = card
            self.active_card.set_active(True)

    def _preload_neighbor_cards(self, card, before=1, after=2):
        if not card or getattr(card, 'is_comment', False):
            return
        try:
            idx = self.rule_cards.index(card)
        except ValueError:
            return
        preload = []
        start = max(0, idx - before)
        end = min(len(self.rule_cards), idx + after + 1)
        for pos in range(start, end):
            if pos == idx:
                continue
            neighbor = self.rule_cards[pos]
            if getattr(neighbor, 'is_comment', False):
                continue
            if getattr(neighbor, '_is_hydrated', True):
                continue
            preload.append(neighbor)
        if preload:
            self._schedule_deferred_hydration(preload, prioritize=True)

    def move_card_up(self, c):
        if c in self.rule_cards:
            idx = self.rule_cards.index(c)
            if idx > 0:
                self.rule_cards[idx], self.rule_cards[idx-1] = \
                    self.rule_cards[idx-1], self.rule_cards[idx]
                self.repack_cards()
                self.mark_unsaved()
    def move_card_down(self, c):
        if c in self.rule_cards:
            idx = self.rule_cards.index(c)
            if idx < len(self.rule_cards) - 1:
                self.rule_cards[idx], self.rule_cards[idx+1] = \
                    self.rule_cards[idx+1], self.rule_cards[idx]
                self.repack_cards()
                self.mark_unsaved()
    def undo_delete(self):
        if not self.deleted_stack:
            messagebox.showinfo("Undo", "Nothing to undo.", parent=self)
            return
        data = self.deleted_stack.pop()
        idx = min(data["idx"], len(self.rule_cards))
        if data["is_comment"]:
            c = CommentRuleCard(self.card_scroll, data["name"],
                                self.del_card, self.move_card_up, self.move_card_down, self)
        else:
            c = ItemRuleCard(self.card_scroll, data["name"], data["quality"],
                             self.del_card, self.clone, self.set_active,
                             self.font_data, self, self.move_card_up, self.move_card_down)
            c.raw_line = data.get("raw_line")
            c.set_type(data["type"])
            c.type_field = data.get("type_field", "name")
            c.is_disabled = data.get("is_disabled", False)
            c.refresh_power_button()
            c.base_extra_conditions = list(data.get("base_extra_conditions", []))
            c.set_pending_conditions(data.get("stats", []), data.get("advanced_clauses", []))
            self._schedule_deferred_hydration([c])
        self.rule_cards.insert(idx, c)
        self.repack_cards()
        self.mark_unsaved()
    def filter_rule_cards(self, *args):
        self._schedule_repack_cards() if getattr(self, '_is_loading', False) else self.repack_cards()
        self.update_status_bar()

    def _get_card_stat_tuples(self, card):
        if getattr(card, 'stats', None):
            return [
                (s.stat_key, INV_OP_MAP.get(s.op_menu.get(), ">="), s.val_entry.get())
                for s in getattr(card, 'stats', [])
            ]
        return list(getattr(card, 'pending_stats_data', []) or [])

    def _get_card_advanced_expressions(self, card):
        if getattr(card, 'advanced_clauses', None):
            return [a.get_expression() for a in getattr(card, 'advanced_clauses', [])]
        return list(getattr(card, 'pending_advanced_data', []) or [])

    def _schedule_deferred_hydration(self, cards=None, reset=False, prioritize=False):
        if reset:
            self._deferred_hydration_queue = []
        if cards:
            incoming = []
            for card in cards:
                if getattr(card, 'is_comment', False):
                    continue
                if getattr(card, '_is_hydrated', True):
                    continue
                if not getattr(card, 'winfo_exists', lambda: False)():
                    continue
                incoming.append(card)
            if prioritize and incoming:
                new_queue = []
                seen = set()
                for card in incoming + self._deferred_hydration_queue:
                    key = id(card)
                    if key in seen:
                        continue
                    seen.add(key)
                    if getattr(card, '_is_hydrated', True):
                        continue
                    if not card.winfo_exists():
                        continue
                    new_queue.append(card)
                self._deferred_hydration_queue = new_queue
            else:
                for card in incoming:
                    if card not in self._deferred_hydration_queue:
                        self._deferred_hydration_queue.append(card)
        if self._deferred_hydration_after is None and self._deferred_hydration_queue:
            self._deferred_hydration_after = self.after(self._deferred_hydration_tick_ms, self._hydrate_deferred_batch)

    def _hydrate_deferred_batch(self):
        self._deferred_hydration_after = None
        queued = len(getattr(self, '_deferred_hydration_queue', []) or [])
        if getattr(self, '_is_loading', False):
            batch_size = 2
        elif queued >= 24:
            batch_size = 6
        elif queued >= 12:
            batch_size = 5
        elif queued >= 8:
            batch_size = 4
        else:
            batch_size = 3
        remaining = []
        processed = 0
        for card in list(self._deferred_hydration_queue):
            if getattr(card, '_is_hydrated', True):
                continue
            if not card.winfo_exists():
                continue
            if processed >= batch_size:
                remaining.append(card)
                continue
            try:
                card.ensure_hydrated()
            except Exception:
                remaining.append(card)
                continue
            processed += 1
        seen = set(id(c) for c in remaining)
        for card in self._deferred_hydration_queue:
            if id(card) not in seen and not getattr(card, '_is_hydrated', True) and card.winfo_exists():
                remaining.append(card)
                seen.add(id(card))
        self._deferred_hydration_queue = remaining
        if self._deferred_hydration_queue:
            self._deferred_hydration_after = self.after(self._deferred_hydration_tick_ms, self._hydrate_deferred_batch)

    def _schedule_repack_cards(self):
        if self._render_repack_pending:
            return
        self._render_repack_pending = True
        self.after(8, self._flush_repack_cards)

    def _flush_repack_cards(self):
        self._render_repack_pending = False
        self.repack_cards()

    def _card_search_blob(self, card):
        parts = [getattr(card, 'display_name', '')]
        if getattr(card, 'is_comment', False):
            parts.append(getattr(card, 'raw_line', '') or '')
        else:
            try:
                parts.append(card.type_btn.cget("text"))
                parts.append(getattr(card, 'current_type_raw', '') or '')
            except Exception:
                pass
            parts.append(getattr(card, 'raw_line', '') or '')
            raw_type = self._card_raw_item_type(card)
            if raw_type:
                parts.append(raw_type)
            parts.extend(getattr(card, 'base_extra_conditions', []) or [])
            for key, op, val in self._get_card_stat_tuples(card):
                parts.extend([str(key), str(op), str(val), FLAT_STAT_MAP.get(str(key).lower(), str(key))])
            for expr in self._get_card_advanced_expressions(card):
                parts.append(expr)
                parts.extend(extract_numeric_stat_ids(expr))
            try:
                parts.append(self.serialize_rule_card(card, hydrate=False))
            except Exception:
                pass
        return ' '.join(p for p in parts if p).lower()

    def repack_cards(self):
        q = self.rule_search_var.get().lower().strip()
        visible_count = 0
        for c in self.rule_cards:
            c.pack_forget()
            if getattr(c, 'is_comment', False) and getattr(c, 'hide_in_ui', False):
                continue
            if not q:
                c.pack(fill="x", pady=8, padx=12)
                visible_count += 1
                continue
            blob = self._get_card_search_blob_cached(c)
            if q in blob:
                c.pack(fill="x", pady=8, padx=12)
                visible_count += 1
        self._update_empty_state(visible_count)
        self.update_status_bar()
    def add_from_cat(self, name, category=None):
        if self.active_card and not getattr(self.active_card, 'is_comment', False):
            self.active_card.display_name = name
            self.active_card.name_label.configure(text=name)
            self.active_card.set_type(name)
        else:
            c = ItemRuleCard(self.card_scroll, name, "unique",
                             self.del_card, self.clone, self.set_active,
                             self.font_data, self, self.move_card_up, self.move_card_down)
            c.set_type(name)
            if category == "Most Wanted Items":
                self.rule_cards.insert(0, c)
            else:
                self.rule_cards.append(c)
            self.set_active(c)
            self.repack_cards()
        self.mark_unsaved()
    def add_blank(self):
        dialog = ctk.CTkInputDialog(text="Enter custom name for this item:", title="New Item")
        custom_name = dialog.get_input()
        if custom_name is None:
            return
        final_name = custom_name.strip() or "New Rule"
        c = ItemRuleCard(self.card_scroll, final_name, "unique",
                         self.del_card, self.clone, self.set_active,
                         self.font_data, self, self.move_card_up, self.move_card_down)
        self.rule_cards.insert(0, c)
        self.set_active(c)
        self.repack_cards()
        self.mark_unsaved()
    def add_comment(self, name=None):
        if name is None:
            dialog = ctk.CTkInputDialog(text="Enter section header text:",
                                        title="New Comment Divider")
            custom_name = dialog.get_input()
            if custom_name is None:
                return
            name = custom_name.strip() or "Section"
        c = CommentRuleCard(self.card_scroll, name,
                            self.del_card, self.move_card_up, self.move_card_down, self)
        self.rule_cards.append(c)
        self.repack_cards()
        self.mark_unsaved()
    def del_card(self, c):
        if self.active_card == c:
            self.active_card = None
        if c in self.rule_cards:
            idx = self.rule_cards.index(c)
            if getattr(c, 'is_comment', False):
                self.deleted_stack.append({"is_comment": True, "name": c.display_name, "idx": idx})
            else:
                self.deleted_stack.append({
                    "is_comment": False,
                    "name": c.display_name,
                    "quality": c.get_quality_value() if hasattr(c, 'get_quality_value') else c.qual_menu.get(),
                    "type": self._card_raw_item_type(c),
                    "type_field": getattr(c, "type_field", "name"),
                    "is_disabled": getattr(c, "is_disabled", False),
                    "base_extra_conditions": list(getattr(c, "base_extra_conditions", [])),
                    "stats": self._get_card_stat_tuples(c),
                    "advanced_clauses": self._get_card_advanced_expressions(c),
                    "idx": idx
                })
            self.rule_cards.remove(c)
        c.destroy()
        self.repack_cards()
        self.mark_unsaved()
    def clone(self, old):
        new = ItemRuleCard(self.card_scroll, old.display_name + " (Copy)", old.get_quality_value() if hasattr(old, 'get_quality_value') else old.qual_menu.get(),
                           self.del_card, self.clone, self.set_active,
                           self.font_data, self, self.move_card_up, self.move_card_down)
        new.set_type(self._card_raw_item_type(old))
        new.type_field = getattr(old, "type_field", "name")
        new.is_disabled = getattr(old, "is_disabled", False)
        new.refresh_power_button()
        new.base_extra_conditions = list(getattr(old, "base_extra_conditions", []))
        stats_payload = self._get_card_stat_tuples(old)
        advanced_payload = self._get_card_advanced_expressions(old)
        new.set_pending_conditions(stats_payload, advanced_payload)
        self._schedule_deferred_hydration([new], prioritize=True)
        self.rule_cards.append(new)
        self.set_active(new)
        self.repack_cards()
        self.mark_unsaved()
    def add_to_last(self, k, n):
        target = self.active_card or (self.rule_cards[-1] if self.rule_cards else None)
        if target and not getattr(target, 'is_comment', False):
            target.add_stat_visually(k, n)
    # -----------------------------------------------------------------------
    # FOLDER / FILE OPERATIONS
    # -----------------------------------------------------------------------
    def open_folder(self):
        p = filedialog.askdirectory(parent=self)
        if not p:
            return
        self.folder = p
        for w in self.side_scroll.winfo_children():
            w.destroy()
        ctk.CTkButton(self.side_scroll, text="â¬… Back to Catalog",
                      font=self.d2_font, height=45,
                      fg_color="#1a1a1a", hover_color="#262626",
                      command=self.init_catalog).pack(pady=5, fill="x")
        for f in sorted(os.listdir(p)):
            if f.endswith(".nip"):
                ctk.CTkButton(self.side_scroll, text=f, font=self.item_font,
                              height=35, fg_color="transparent", anchor="w",
                              command=lambda n=f: self.load_nip(n)).pack(fill="x")
    def load_backup_file(self):
        BackupHistoryDialog(
            self,
            self,
            apply_window_icon=apply_window_icon,
            configure_dialog_window=configure_dialog_window,
        )
    def _reset_for_load(self):
        self._is_loading = True
        if self._deferred_hydration_after is not None:
            try:
                self.after_cancel(self._deferred_hydration_after)
            except Exception:
                pass
            self._deferred_hydration_after = None
        self._deferred_hydration_queue = []
        self.validation_state = "Loading"
        self._clear_search_cache()
        self.update_status_bar()
        self.load_id += 1
        self.active_card = None
        self.all_file_data = []
        self.loaded_count = 0
        self.syntax_errors = []
        self.pending_errors = []
        self.deleted_stack = []
        self.unsaved_changes = False
        for c in self.rule_cards:
            c.destroy()
        self.rule_cards = []
        self._update_empty_state(0)
        if self.loading_modal and self.loading_modal.winfo_exists():
            try: self.loading_modal.safe_close()
            except: pass
        self._show_loading_overlay()
    def load_absolute_file(self, filepath):
        self._reset_for_load()
        self.current_file = filepath
        self.add_recent_file(filepath)
        threading.Thread(target=self.bg_load,
                         args=(filepath, self.load_id), daemon=True).start()
    def load_nip(self, filename):
        self._reset_for_load()
        self.current_file = os.path.join(self.folder, filename)
        self.add_recent_file(self.current_file)
        self.init_catalog()
        threading.Thread(target=self.bg_load,
                         args=(self.current_file, self.load_id), daemon=True).start()
    
    def bg_load(self, path, rid):
        try:
            parsed_data, errors = [], []
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for idx, line in enumerate(f):
                    info = parse_nip_rule_line(line)
                    if not info:
                        continue
                    if info.get("error"):
                        errors.append((idx + 1, info.get("name", "Item"), info["error"]))
                    parsed_data.append(info)
            self.after(10, lambda: self.start_render(parsed_data, rid, errors))
        except Exception as e:
            self.after(10, lambda err=str(e): messagebox.showerror('Load Error', f'Could not load file.\n\n{err}', parent=self))
            print(f"bg_load error: {e}")
    def start_render(self, data_list, rid, errors):
        if rid != self.load_id:
            return
        self.all_file_data = data_list
        self.loaded_count = 0
        self.pending_errors = errors
        limit_str = self.load_limit.get()
        if limit_str == "Load All Entries":
            self.target_count = len(self.all_file_data)
        else:
            try:
                self.target_count = int(''.join(filter(str.isdigit, limit_str)))
            except ValueError:
                self.target_count = 50
        self.target_count = min(self.target_count, len(self.all_file_data))
        self.render_batch_size = 24 if self.target_count < 150 else 36 if self.target_count < 500 else 48
        self.initial_card_hydration_count = 8 if self.target_count < 150 else 5 if self.target_count < 500 else 3
        if self.target_count > 0:
            self.after(10, self.load_next_segment)
        else:
            self.header.configure(
                text=f"Editing: {os.path.basename(self.current_file)} (0/0)")
            self._is_loading = False
            self.mark_saved()
            if self.loading_modal:
                try: self.loading_modal.safe_close()
                except: pass
                self.loading_modal = None
    def load_more_entries(self):
        if self.loaded_count >= len(self.all_file_data):
            if self.all_file_data:
                messagebox.showinfo("Done", "All entries have been loaded.", parent=self)
            return
        limit_str = self.load_limit.get()
        chunk = len(self.all_file_data) if limit_str == "Load All Entries" else \
                int(''.join(filter(str.isdigit, limit_str)) or "50")
        self.target_count = min(self.loaded_count + chunk, len(self.all_file_data))
        self.render_batch_size = 40 if self.target_count < 150 else 60 if self.target_count < 500 else 90
        if not self.loading_modal or not self.loading_modal.winfo_exists():
            self._show_loading_overlay()
        self.load_next_segment()
    def load_next_segment(self):
        start = self.loaded_count
        end = min(start + getattr(self, 'render_batch_size', 40), self.target_count)
        try:
            for i in range(start, end):
                item = self.all_file_data[i]
                if item.get("is_comment"):
                    card = CommentRuleCard(
                        self.card_scroll,
                        item["name"],
                        self.del_card,
                        self.move_card_up,
                        self.move_card_down,
                        self,
                        raw_line=item.get("raw_line"),
                        hide_in_ui=item.get("hide_in_ui", False),
                    )
                    self.rule_cards.append(card)
                else:
                    card = ItemRuleCard(
                        self.card_scroll,
                        item["name"],
                        item["quality"],
                        self.del_card,
                        self.clone,
                        self.set_active,
                        self.font_data,
                        self,
                        self.move_card_up,
                        self.move_card_down,
                    )
                    self.rule_cards.append(card)
                    card.raw_line = item.get("raw_line")
                    if item["type"]:
                        card.set_type(item["type"])
                    if item.get("error"):
                        card.highlight_error(True)
                    card.type_field = item.get("type_field", "name")
                    card.is_disabled = item.get("is_disabled", False)
                    card.refresh_power_button()
                    card.base_extra_conditions = list(item.get("base_extra_conditions", []))
                    stats_payload = list(item.get("stats", []))
                    advanced_payload = list(item.get("advanced_clauses", []))
                    if i < self.initial_card_hydration_count:
                        for sk, op, val in stats_payload:
                            stat_name = FLAT_STAT_MAP.get(sk.lower(), sk)
                            card.add_stat_visually(sk, stat_name, op, val)
                        for clause in advanced_payload:
                            card.add_advanced_clause(clause)
                    else:
                        card.set_pending_conditions(stats_payload, advanced_payload)

            self.loaded_count = end
            if self.loading_modal and self.loading_modal.winfo_exists():
                batch = max(20, getattr(self, 'render_batch_size', 40))
                if self.loaded_count == self.target_count or self.loaded_count % batch == 0:
                    self.loading_modal.update_progress(self.loaded_count, self.target_count)

            self._schedule_repack_cards()
            if self.loaded_count < self.target_count:
                self.after(1, self.load_next_segment)
            else:
                self._is_loading = False
                self.repack_cards()
                top_preload = [c for c in self.rule_cards[:max(self.initial_card_hydration_count + 4, 12)] if not getattr(c, 'is_comment', False)]
                self._schedule_deferred_hydration(top_preload, reset=True)
                self.header.configure(
                    text=f"Editing: {os.path.basename(self.current_file)} "
                         f"({self.loaded_count}/{len(self.all_file_data)})")
                self.validation_state = "Not checked"
                self.mark_saved()
                if self.loading_modal:
                    try:
                        self.loading_modal.safe_close()
                    except Exception:
                        pass
                    self.loading_modal = None
                if self.pending_errors:
                    self.syntax_errors = self.pending_errors
                    self.pending_errors = []
                    if messagebox.askyesno(
                            "Syntax Checker",
                            f"Found {len(self.syntax_errors)} potential syntax errors. "
                            f"View them?", parent=self):
                        self.walk_through_errors()
        except tk.TclError:
            self._is_loading = False
            messagebox.showwarning("System Limit",
                                   "File extremely large. Partial load complete.", parent=self)
            self.header.configure(
                text=f"Editing (Partial): {os.path.basename(self.current_file)}")
            self.validation_state = "Partial load"
            self.mark_saved()
            if self.loading_modal:
                try:
                    self.loading_modal.safe_close()
                except Exception:
                    pass
                self.loading_modal = None

    def manual_syntax_check(self):
        self.syntax_errors = []
        found_errs = []
        for idx, card in enumerate(self.rule_cards):
            if getattr(card, 'is_comment', False):
                continue
            card.highlight_error(False)
            errs = []
            if not self._card_has_resolved_base_condition(card):
                errs.append("No item type/base selected.")
            if errs:
                card.highlight_error(True)
                found_errs.append(f"Rule '{card.display_name}': " + " ".join(errs))
                self.syntax_errors.append((idx + 1, card.display_name, " ".join(errs)))
        if found_errs:
            msg = f"Found {len(found_errs)} potential issues:\n\n" + "\n".join(found_errs[:5])
            if len(found_errs) > 5:
                msg += "\n..."
            messagebox.showwarning("Syntax Report", msg, parent=self)
        else:
            messagebox.showinfo("Syntax Report", "No errors found.", parent=self)
    def walk_through_errors(self):
        if not self.syntax_errors:
            return
        err_line, name, msg = self.syntax_errors[0]
        for card in self.rule_cards:
            if not getattr(card, 'is_comment', False) and card.display_name == name:
                card.highlight_error(True)
                messagebox.showinfo(
                    "Error Found",
                    f"Line {err_line}: {msg}\n\nFix: Select a base item type.",
                    parent=self)
                break
    def _card_has_resolved_base_condition(self, card):
        clean_type = self._card_raw_item_type(card).strip().lower()
        if clean_type and clean_type != 'item':
            return True

        extras = list(getattr(card, 'base_extra_conditions', []) or [])
        for extra in extras:
            extra_s = (extra or '').strip()
            if not extra_s:
                continue
            if re.search(r'\[(?:name|type)\]', extra_s, re.I):
                return True
            if re.search(r'\(', extra_s) and re.search(r'\[(?:name|type)\]', extra_s, re.I):
                return True

        raw_line = getattr(card, 'raw_line', '') or ''
        if raw_line:
            parsed = parse_nip_rule_line(raw_line)
            if parsed and not parsed.get('is_comment'):
                if (parsed.get('type') or '').strip():
                    return True
                parsed_extras = list(parsed.get('base_extra_conditions', []) or [])
                for extra in parsed_extras:
                    extra_s = (extra or '').strip()
                    if extra_s and re.search(r'\[(?:name|type)\]', extra_s, re.I):
                        return True
        return False

    def serialize_rule_card(self, card, hydrate=True):
        return _rule_model_serialize_card_impl(self, card, hydrate=hydrate)

    def _collect_validation_results(self):
        results = {"errors": [], "warnings": [], "duplicates": []}
        seen = {}
        for idx, card in enumerate(self.rule_cards, start=1):
            if getattr(card, 'is_comment', False):
                continue
            name = getattr(card, 'display_name', f'Rule {idx}')
            line = self.serialize_rule_card(card)
            if not self._card_has_resolved_base_condition(card):
                results['errors'].append(f"Line {idx} - {name}: No item type/base selected.")

            for stat_idx, s in enumerate(getattr(card, 'stats', []) or [], start=1):
                stat_key = (getattr(s, 'stat_key', '') or '').strip()
                val = s.val_entry.get().strip() if hasattr(s, 'val_entry') else ''
                op_label = s.op_menu.get().strip() if hasattr(s, 'op_menu') else ''
                prefix = f"Line {idx} - {name} - Stat {stat_idx}: "
                if not stat_key:
                    results['errors'].append(prefix + 'Missing stat key.')
                if not val:
                    results['errors'].append(prefix + 'Missing stat value.')
                elif not re.fullmatch(r'-?\d+', val):
                    results['warnings'].append(prefix + f"Non-numeric stat value '{val}'.")
                if op_label and op_label not in INV_OP_MAP:
                    results['errors'].append(prefix + f"Unknown operator '{op_label}'.")

            for adv_idx, adv in enumerate(getattr(card, 'advanced_clauses', []) or [], start=1):
                expr = adv.get_expression() if hasattr(adv, 'get_expression') else ''
                prefix = f"Line {idx} - {name} - Advanced {adv_idx}: "
                if not expr.strip():
                    results['errors'].append(prefix + 'Advanced clause is empty.')
                else:
                    level, msg = analyze_advanced_expression(expr)
                    if level == 'error':
                        results['errors'].append(prefix + msg)
                    elif level == 'warning':
                        results['warnings'].append(prefix + msg)
                    if re.search(r'\[(\d+)\]', expr or ''):
                        nums = ", ".join(sorted(set(re.findall(r'\[(\d+)\]', expr))))
                        results['warnings'].append(prefix + f"Numeric stat id(s) detected: {nums}.")

            invalid_ops = find_invalid_comparison_operators(line)
            for bad_op, pos in invalid_ops:
                results['errors'].append(f"Line {idx} - {name}: Invalid comparison operator '{bad_op}' near position {pos}.")

            parsed = parse_nip_rule_line(line)
            if not parsed:
                results['errors'].append(f"Line {idx} - {name}: Serialized line could not be parsed back.")
            else:
                if parsed.get('is_comment') and not getattr(card, 'is_disabled', False):
                    results['errors'].append(f"Line {idx} - {name}: Serialized line became a comment instead of a rule.")
                if parsed.get('error'):
                    results['errors'].append(f"Line {idx} - {name}: {parsed['error']}")
                if '[' in line and ']' in line and '#' in line and not (parsed.get('stats') or parsed.get('advanced_clauses')):
                    results['warnings'].append(f"Line {idx} - {name}: Rule has a stat section but no parsed stats/advanced clauses were recovered.")

            norm = re.sub(r'\s+', ' ', line).strip().lower()
            if norm in seen:
                results['duplicates'].append(f"Line {seen[norm]} and line {idx} appear to serialize identically.")
            else:
                seen[norm] = idx
        return results

    def validate_loaded_file(self):
        if not self.rule_cards:
            messagebox.showinfo("Validate File", "No rules are currently loaded.", parent=self)
            return
        results = self._collect_validation_results()
        if results.get('errors'):
            self.update_status_bar('Validation: Errors')
        elif results.get('warnings') or results.get('duplicates'):
            self.update_status_bar('Validation: Warnings')
        else:
            self.update_status_bar('Validation: OK')
        ValidationReportDialog(
            self,
            results,
            save_plan_text=self._build_save_plan_text(),
            configure_dialog_window=configure_dialog_window,
        )

    def _build_output_lines(self):
        out = self._build_output_lines()
        return out

    def _collect_diff_entries(self):
        current_lines = self._build_output_lines()
        original_lines = [item.get('raw_line', '') for item in self.all_file_data] if self.all_file_data else []
        max_len = max(len(current_lines), len(original_lines))
        diffs = []
        for idx in range(max_len):
            old = original_lines[idx] if idx < len(original_lines) else ''
            new = current_lines[idx] if idx < len(current_lines) else ''
            if old != new:
                name = f"Line {idx + 1}"
                if idx < len(self.rule_cards):
                    name = getattr(self.rule_cards[idx], 'display_name', name)
                diffs.append({'line_no': idx + 1, 'name': name, 'original': old, 'current': new})
        return diffs

    def _open_diff_preview_before_save(self):
        diff_entries = self._collect_diff_entries()
        save_plan = self._build_save_plan_text()
        if diff_entries:
            DiffPreviewDialog(
                self,
                diff_entries,
                on_continue_save=self._save_file_now,
                save_plan_text=save_plan,
                configure_dialog_window=configure_dialog_window,
            )
        else:
            self._save_file_now()

    def save_with_validation_gate(self):
        results = self._collect_validation_results()
        save_plan = self._build_save_plan_text()
        has_issues = any(results.get(k) for k in ("errors", "warnings", "duplicates"))
        if has_issues:
            ValidationReportDialog(
                self,
                results,
                on_continue_save=self._open_diff_preview_before_save,
                save_plan_text=save_plan,
                configure_dialog_window=configure_dialog_window,
            )
        else:
            self._open_diff_preview_before_save()

    # -----------------------------------------------------------------------
    # MISC UI
    # -----------------------------------------------------------------------



    def _append_updater_log(self, context, exc=None, tb_text=None):
        try:
            log_path = getattr(self, "_updater_error_log", None) or user_data_path("update_errors.log")
            stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
            parts = [f"[{stamp}] {context}"]
            if exc is not None:
                parts.append(f"{type(exc).__name__}: {exc}")
            if tb_text:
                parts.append(tb_text.rstrip())
            with open(log_path, "a", encoding="utf-8") as fh:
                fh.write("\n".join(parts) + "\n\n")
        except Exception:
            pass

    def _handle_update_ui_exception(self, context, exc, parent=None, show_dialog=True):
        message = f"{context}: {exc}"
        self._append_updater_log(context, exc, traceback.format_exc())
        try:
            self._update_check_in_progress = False
            self._clear_update_check_poll()
            self._clear_update_check_timeout()
            self._update_check_thread = None
            self._update_check_pending_result = None
            self._set_latest_release_state(release=None, error=RuntimeError(message))
        except Exception:
            pass
        try:
            self._refresh_update_center_window(checking=False, auto=False)
        except Exception:
            pass
        try:
            self.update_status_bar("Update check failed")
        except Exception:
            pass
        if show_dialog:
            try:
                messagebox.showerror(
                    "Updater Error",
                    f"The updater hit an unexpected error and was stopped safely.\n\n{message}\n\nA log was written to:\n{getattr(self, '_updater_error_log', user_data_path('update_errors.log'))}",
                    parent=parent or self,
                )
            except Exception:
                pass

    def _report_tk_callback_exception(self, exc, val, tb):
        tb_text = "".join(traceback.format_exception(exc, val, tb))
        lower = tb_text.lower()
        if any(token in lower for token in ("update", "release", "github", "installer")):
            self._append_updater_log("Tk updater callback exception", val, tb_text)
            self._handle_update_ui_exception("Updater callback", val, parent=self)
            return
        self._append_updater_log("Tk callback exception", val, tb_text)
        try:
            messagebox.showerror(
                "Unexpected Error",
                f"An unexpected error occurred.\n\n{val}\n\nA log was written to:\n{getattr(self, '_updater_error_log', user_data_path('update_errors.log'))}",
                parent=self,
            )
        except Exception:
            pass

    def _fetch_latest_release_info(self):
        req = urllib.request.Request(
            GITHUB_LATEST_RELEASE_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"DarcsVisualPickit/{APP_VERSION}",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        data = json.loads(raw)
        return data if isinstance(data, dict) else None

    def _pick_release_exe_asset(self, release_data):
        assets = list((release_data or {}).get("assets") or [])
        if not assets:
            return None
        latest_label = str((release_data or {}).get("tag_name") or (release_data or {}).get("name") or "").strip()
        latest_label_lower = latest_label.lower()
        latest_numeric = _numeric_version_text(latest_label)
        latest_version_tuple = _normalize_version(latest_label)
        ranked = []
        for asset in assets:
            name = str(asset.get("name") or "")
            url = str(asset.get("browser_download_url") or "")
            lower = name.lower()
            score = 0
            if lower.endswith(".exe"):
                score += 40
            if lower.endswith(".msi"):
                score += 30
            if "setup" in lower or "installer" in lower:
                score += 100
            if "portable" in lower:
                score -= 30
            if latest_label_lower and latest_label_lower in lower:
                score += 180
            if latest_numeric and (latest_numeric in lower or f"v{latest_numeric}" in lower):
                score += 260
            embedded_versions = _extract_embedded_versions(lower)
            if latest_numeric and embedded_versions:
                if any(ver == latest_version_tuple for ver in embedded_versions):
                    score += 320
                else:
                    score -= 420
            ranked.append((score, asset))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return ranked[0][1] if ranked else None

    def _launch_windows_updater(self, downloaded_exe: str, target_exe: str):
        downloaded_exe = os.path.abspath(str(downloaded_exe or "").strip())
        target_exe = os.path.abspath(str(target_exe or "").strip())
        if not downloaded_exe or not os.path.exists(downloaded_exe):
            return False

        # Source-script runs cannot self-replace cleanly, so just launch the installer.
        if not (sys.platform.startswith("win") and getattr(sys, "frozen", False) and target_exe.lower().endswith(".exe")):
            try:
                if sys.platform.startswith("win"):
                    os.startfile(downloaded_exe)
                else:
                    subprocess.Popen([downloaded_exe], close_fds=True)
                return True
            except Exception:
                return False

        helper_dir = os.path.join(tempfile.gettempdir(), APP_SLUG, "updates")
        os.makedirs(helper_dir, exist_ok=True)
        helper_ps1 = os.path.join(helper_dir, f"run_update_{os.getpid()}.ps1")
        helper_log = os.path.join(helper_dir, f"run_update_{os.getpid()}.log")
        installer_log = os.path.join(helper_dir, f"installer_update_{os.getpid()}.log")

        def _ps_quote(value):
            return "'" + str(value or "").replace("'", "''") + "'"

        ps_text = "\r\n".join([
            "$ErrorActionPreference = 'Stop'",
            f"$TargetPid = {int(os.getpid())}",
            f"$Installer = {_ps_quote(downloaded_exe)}",
            f"$TargetExe = {_ps_quote(target_exe)}",
            f"$LogPath = {_ps_quote(helper_log)}",
            f"$InstallerLog = {_ps_quote(installer_log)}",
            "",
            "function Write-UpdateLog([string]$Message) {",
            "    try {",
            "        Add-Content -Path $LogPath -Value ((Get-Date -Format s) + ' ' + $Message) -Encoding UTF8",
            "    } catch {",
            "    }",
            "}",
            "",
            "Write-UpdateLog 'Helper started'",
            "while (Get-Process -Id $TargetPid -ErrorAction SilentlyContinue) {",
            "    Start-Sleep -Seconds 1",
            "}",
            "Start-Sleep -Milliseconds 750",
            "if (-not (Test-Path -LiteralPath $Installer)) {",
            "    Write-UpdateLog ('Installer missing: ' + $Installer)",
            "    exit 1",
            "}",
            "Write-UpdateLog ('Launching installer: ' + $Installer)",
            "$installerArgs = @(('/LOG=' + $InstallerLog))",
            "$proc = Start-Process -FilePath $Installer -ArgumentList $installerArgs -WorkingDirectory (Split-Path -Parent $Installer) -Wait -PassThru",
            "Write-UpdateLog ('Installer finished with code ' + $proc.ExitCode)",
            "if ($proc.ExitCode -eq 0 -and (Test-Path -LiteralPath $TargetExe)) {",
            "    Start-Sleep -Milliseconds 800",
            "    Write-UpdateLog ('Relaunching app: ' + $TargetExe)",
            "    Start-Process -FilePath $TargetExe -WorkingDirectory (Split-Path -Parent $TargetExe) -ArgumentList '--after-update'",
            "} elseif ($proc.ExitCode -ne 0) {",
            "    Write-UpdateLog ('Installer did not complete successfully; relaunch skipped')",
            "} else {",
            "    Write-UpdateLog ('Updated app not found for relaunch: ' + $TargetExe)",
            "}",
            "try {",
            "    Remove-Item -LiteralPath $PSCommandPath -Force -ErrorAction SilentlyContinue",
            "} catch {",
            "}",
            "exit 0",
        ])
        try:
            with open(helper_ps1, "w", encoding="utf-8", newline="\r\n") as fh:
                fh.write(ps_text)
            subprocess.Popen(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-WindowStyle",
                    "Hidden",
                    "-File",
                    helper_ps1,
                ],
                close_fds=True,
            )
            self._last_update_helper_log = helper_log
            self._last_installer_log = installer_log
            return True
        except Exception:
            try:
                if sys.platform.startswith("win"):
                    os.startfile(downloaded_exe)
                else:
                    subprocess.Popen([downloaded_exe], close_fds=True)
                return True
            except Exception:
                return False

    def _record_update_check_timestamp(self):
        try:
            self.last_update_check_utc = datetime.now().astimezone().replace(microsecond=0).astimezone().isoformat().replace('+00:00', 'Z')
            self.save_config()
        except Exception:
            pass

    def _schedule_on_main_thread(self, callback):
        if getattr(self, "_main_destroy_in_progress", False):
            return False
        try:
            callback()
            return True
        except Exception:
            return False

    def _clear_update_check_poll(self):
        after_id = getattr(self, "_update_check_poll_after", None)
        if after_id is None:
            return
        try:
            self.after_cancel(after_id)
        except Exception:
            pass
        self._update_check_poll_after = None

    def _clear_update_check_timeout(self):
        after_id = getattr(self, "_update_check_timeout_after", None)
        if after_id is None:
            return
        try:
            self.after_cancel(after_id)
        except Exception:
            pass
        self._update_check_timeout_after = None

    def _complete_update_check(self, release, error, auto=False):
        try:
            self._finish_update_check(release, error, auto=auto)
        except Exception as exc:
            self._update_check_in_progress = False
            self._clear_update_check_poll()
            self._clear_update_check_timeout()
            self._update_check_thread = None
            self._update_check_pending_result = None
            self._record_update_check_timestamp()
            self._set_latest_release_state(release=None, error=exc)
            self._refresh_update_center_window(checking=False, auto=auto)
            try:
                self.update_status_bar("Update check failed")
            except Exception:
                pass

    def _on_update_check_timeout(self, auto=False):
        self._update_check_timeout_after = None
        if not getattr(self, "_update_check_in_progress", False):
            return
        pending = getattr(self, "_update_check_pending_result", None)
        if pending is not None:
            release, error, pending_auto = pending
            self._update_check_pending_result = None
            self._complete_update_check(release, error, auto=pending_auto)
            return
        worker = getattr(self, "_update_check_thread", None)
        if worker is not None and worker.is_alive():
            self._complete_update_check(None, TimeoutError("Update check timed out after 20 seconds."), auto=auto)
            return
        self._complete_update_check(None, RuntimeError("Update check ended before a result was delivered."), auto=auto)

    def _poll_update_check_completion(self):
        self._update_check_poll_after = None
        if getattr(self, "_main_destroy_in_progress", False):
            return
        pending = getattr(self, "_update_check_pending_result", None)
        if pending is not None:
            self._update_check_pending_result = None
            self._update_check_thread = None
            release, error, auto = pending
            self._complete_update_check(release, error, auto=auto)
            return
        worker = getattr(self, "_update_check_thread", None)
        if worker is not None and worker.is_alive():
            try:
                self._update_check_poll_after = self.after(150, self._poll_update_check_completion)
            except Exception:
                self._update_check_poll_after = None
            return
        if getattr(self, "_update_check_in_progress", False):
            self._update_check_thread = None
            self._complete_update_check(None, RuntimeError("Update check ended before a result was delivered."), auto=False)

    def _ensure_main_thread_callback_pump(self):
        if getattr(self, "_main_destroy_in_progress", False):
            return False
        if getattr(self, "_main_thread_callback_after", None) is not None:
            return True
        try:
            self._main_thread_callback_after = self.after(50, self._drain_main_thread_callbacks)
            return True
        except Exception:
            self._main_thread_callback_after = None
            return False

    def _drain_main_thread_callbacks(self):
        self._main_thread_callback_after = None
        processed = 0
        while processed < 24:
            try:
                callback = self._main_thread_callback_queue.get_nowait()
            except queue.Empty:
                break
            try:
                callback()
            except Exception:
                pass
            processed += 1
        if getattr(self, "_main_destroy_in_progress", False):
            return
        if not self._main_thread_callback_queue.empty():
            self._ensure_main_thread_callback_pump()
            return
        try:
            self._main_thread_callback_after = self.after(150, self._drain_main_thread_callbacks)
        except Exception:
            self._main_thread_callback_after = None

    def _set_latest_release_state(self, release=None, error=None):
        self._latest_release_info = release if isinstance(release, dict) else None
        self._latest_update_error = error
        self._latest_release_label = str(((release or {}).get("tag_name") or (release or {}).get("name") or "")).strip()
        self._latest_release_asset = self._pick_release_exe_asset(release) if isinstance(release, dict) else None
        self._latest_release_build_date = ""
        cmp_result = 0
        reason = "same"
        if isinstance(release, dict):
            release_build_date = _extract_release_build_date(str(release.get("body") or ""))
            self._latest_release_build_date = release_build_date
            cmp_result, reason = _compare_versions_and_dates(
                APP_VERSION,
                self._latest_release_label,
                APP_BUILD_DATE,
                release_build_date,
            )
        self._latest_release_cmp_result = cmp_result
        self._latest_release_cmp_reason = reason

        if isinstance(release, dict) and cmp_result <= 0:
            skipped = str(getattr(self, "skipped_update_version", "") or "").strip()
            if skipped:
                try:
                    self.skipped_update_version = ""
                    self.save_config()
                except Exception:
                    pass
        elif isinstance(release, dict):
            skipped = str(getattr(self, "skipped_update_version", "") or "").strip()
            latest = str(self._latest_release_label or "").strip()
            if latest and skipped and skipped.lower() != latest.lower():
                try:
                    self.skipped_update_version = ""
                    self.save_config()
                except Exception:
                    pass

    def _refresh_update_center_window(self, checking=False, auto=False):
        win = getattr(self, "update_center_window", None)
        if win is not None:
            try:
                if win.winfo_exists():
                    win.refresh_from_app(checking=checking, auto=auto)
                    return
            except Exception:
                pass
        self.update_center_window = None

    def open_update_center(self, auto=False, force_check=False):
        try:
            win = getattr(self, "update_center_window", None)
            if win is None:
                win = UpdateCenterDialog(self, self)
                self.update_center_window = win
            else:
                try:
                    if not win.winfo_exists():
                        win = UpdateCenterDialog(self, self)
                        self.update_center_window = win
                except Exception:
                    win = UpdateCenterDialog(self, self)
                    self.update_center_window = win
            try:
                win.lift()
                win.focus_force()
            except Exception:
                pass
            if getattr(self, "_update_check_in_progress", False):
                pending = getattr(self, "_update_check_pending_result", None)
                worker = getattr(self, "_update_check_thread", None)
                if pending is not None:
                    release, error, pending_auto = pending
                    self._update_check_pending_result = None
                    self._complete_update_check(release, error, auto=pending_auto)
                elif worker is None or not worker.is_alive():
                    self._complete_update_check(None, RuntimeError("Update check ended before a result was delivered."), auto=auto)
            win.refresh_from_app(auto=auto)
            if force_check:
                self.start_update_check(auto=auto, force=True, source="dialog")
            return win
        except Exception as exc:
            self._handle_update_ui_exception("Open Update Center", exc, parent=self)
            return None

    def open_latest_release_page(self, parent=None):
        release = getattr(self, "_latest_release_info", None) or {}
        html_url = str(release.get("html_url") or GITHUB_RELEASES_PAGE)
        try:
            webbrowser.open(html_url)
            self.update_status_bar("Opened release page")
            return True
        except Exception as exc:
            messagebox.showerror("Open Release Page Failed", f"Could not open the release page.\n\n{exc}", parent=parent or self)
            return False

    def clear_skipped_update(self):
        if not str(getattr(self, "skipped_update_version", "") or "").strip():
            return
        self.skipped_update_version = ""
        self.save_config()
        self.update_status_bar("Cleared skipped update version")
        self._refresh_update_center_window()

    def skip_latest_update(self):
        latest_label = str(getattr(self, "_latest_release_label", "") or "").strip()
        if not latest_label:
            return
        self.skipped_update_version = latest_label
        self.save_config()
        self.update_status_bar(f"Skipped update {latest_label}")
        self._refresh_update_center_window()

    def download_and_install_latest_release(self, parent_window=None):
        release = getattr(self, "_latest_release_info", None)
        if not isinstance(release, dict):
            self.open_update_center(auto=False, force_check=True)
            return False
        asset = getattr(self, "_latest_release_asset", None)
        if not asset:
            self.open_latest_release_page(parent=parent_window or self)
            return False

        downloaded = self._download_release_asset(asset, parent_window=parent_window or self)
        if not downloaded:
            return False

        launched = self._launch_windows_updater(downloaded, getattr(sys, "executable", ""))
        if launched:
            self.update_status_bar("Update installer launched")
            is_real_self_update = bool(
                sys.platform.startswith("win")
                and getattr(sys, "frozen", False)
                and str(getattr(sys, "executable", "")).lower().endswith(".exe")
            )
            try:
                if is_real_self_update:
                    messagebox.showinfo(
                        "Updater Started",
                        "The updater has downloaded the installer and is ready to continue.\n\nDarc's Visual Pickit will now close so the installer can open and finish the upgrade.",
                        parent=parent_window or self,
                    )
                    self.after(250, self._shutdown_for_update)
                else:
                    messagebox.showinfo(
                        "Installer Ready",
                        "The update installer has been launched.\n\nSince this is not the installed EXE build, Darc's Visual Pickit will stay open. Close it manually before completing the upgrade if the installer asks.",
                        parent=parent_window or self,
                    )
            except Exception:
                if is_real_self_update:
                    self.after(250, self._shutdown_for_update)
            return True

        messagebox.showerror(
            "Launch Failed",
            "The installer downloaded but could not be launched automatically.",
            parent=parent_window or self,
        )
        return False

    def _should_auto_check_for_updates(self):
        if not bool(getattr(self, "auto_check_updates", True)):
            return False
        try:
            interval = max(1, int(getattr(self, "update_check_interval_hours", 24) or 24))
        except Exception:
            interval = 24
        last_raw = str(getattr(self, "last_update_check_utc", "") or "").strip()
        last_dt = _parse_iso_datetime(last_raw)
        if not last_dt:
            return True
        try:
            now = datetime.now(last_dt.tzinfo) if getattr(last_dt, 'tzinfo', None) else datetime.now().astimezone()
            return (now - last_dt).total_seconds() >= interval * 3600
        except Exception:
            return True

    def _prune_stale_update_downloads(self, folder, keep_names=None):
        try:
            keep = {str(x).lower() for x in (keep_names or []) if str(x).strip()}
            now = time.time()
            for name in os.listdir(folder):
                full = os.path.join(folder, name)
                if not os.path.isfile(full):
                    continue
                lower = name.lower()
                if lower in keep:
                    continue
                try:
                    age_seconds = now - os.path.getmtime(full)
                except Exception:
                    age_seconds = 0
                if lower.endswith((".exe", ".part", ".bat", ".ps1", ".log")) and age_seconds > 2 * 86400:
                    try:
                        os.remove(full)
                    except Exception:
                        pass
        except Exception:
            pass

    def _format_release_notes_preview(self, body, max_lines=12, max_chars=1200):
        text = str(body or '').replace('\r\n', '\n').replace('\r', '\n').strip()
        if not text:
            return ''
        body_lines = [line.rstrip() for line in text.split('\n')]
        preview = '\n'.join(body_lines[:max_lines]).strip()
        if len(preview) > max_chars:
            preview = preview[:max_chars].rstrip() + '...'
        return preview

    def _download_release_asset(self, asset, parent_window=None):
        url = str((asset or {}).get("browser_download_url") or "")
        name = str((asset or {}).get("name") or "update_installer.exe")
        if not url:
            return None
        temp_dir = os.path.join(tempfile.gettempdir(), APP_SLUG, "updates")
        os.makedirs(temp_dir, exist_ok=True)
        self._prune_stale_update_downloads(temp_dir, keep_names=[name, name + ".part"])
        dest = os.path.join(temp_dir, name)
        temp_dest = dest + ".part"
        progress = None
        try:
            if parent_window is not None:
                progress = UpdateProgressWindow(parent_window)
                progress.set_status("Downloading update...", detail=name, progress=0.05)
            req = urllib.request.Request(
                url,
                headers={"User-Agent": f"DarcsVisualPickit/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp, open(temp_dest, "wb") as fh:
                total = int(resp.headers.get("Content-Length", "0") or 0)
                downloaded = 0
                while True:
                    chunk = resp.read(1024 * 128)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
                    if progress is not None and total > 0:
                        pct = min(0.95, max(0.05, downloaded / float(total)))
                        progress.set_status(
                            "Downloading update...",
                            detail=name,
                            progress=pct,
                            substatus=f"{downloaded // 1024} KB / {max(1, total // 1024)} KB",
                        )
            os.replace(temp_dest, dest)
            if progress is not None:
                progress.set_status("Download complete", detail=dest, progress=1.0)
                progress.allow_close()
            return dest
        except Exception as exc:
            try:
                if os.path.exists(temp_dest):
                    os.remove(temp_dest)
            except Exception:
                pass
            if progress is not None:
                try:
                    progress.destroy()
                except Exception:
                    pass
            messagebox.showerror("Update Download Failed", f"Could not download the update.\n\n{exc}", parent=self)
            return None



    def _finish_update_check(self, release, error, auto=False):
        self._update_check_in_progress = False
        self._clear_update_check_poll()
        self._clear_update_check_timeout()
        self._update_check_thread = None
        self._update_check_pending_result = None
        self._record_update_check_timestamp()
        self._set_latest_release_state(release=release, error=error)
        self._refresh_update_center_window(checking=False, auto=auto)

        if error is not None:
            self.update_status_bar("Update check failed")
            if not auto and self.update_center_window is None:
                messagebox.showerror("Update Check Failed", f"Could not check for updates.\n\n{error}", parent=self)
            return

        latest_label = str(getattr(self, "_latest_release_label", "") or "").strip()
        cmp_result = int(getattr(self, "_latest_release_cmp_result", 0) or 0)
        skipped = str(getattr(self, "skipped_update_version", "") or "").strip()

        if cmp_result > 0:
            if str(getattr(self, "_latest_release_cmp_reason", "") or "") == "build":
                self.update_status_bar(f"Update available: refreshed {latest_label or APP_VERSION} build")
            else:
                self.update_status_bar(f"Update available: {latest_label or 'new release'}")
            if auto and latest_label and skipped and skipped.lower() == latest_label.lower():
                return
            if auto:
                self.open_update_center(auto=True, force_check=False)
            return

        if cmp_result < 0:
            self.update_status_bar("Local build is newer than published release")
        else:
            self.update_status_bar("Application is up to date")
        if not auto and self.update_center_window is None:
            self.open_update_center(auto=False, force_check=False)

    def start_update_check(self, auto=False, force=False, source="manual"):
        try:
            if self._update_check_in_progress:
                self._refresh_update_center_window(checking=True, auto=auto)
                return False
            if auto and not force and not self._should_auto_check_for_updates():
                return False

            self._update_check_in_progress = True
            self._update_check_pending_result = None
            self._update_check_started_at = time.time()
            self._clear_update_check_poll()
            self._clear_update_check_timeout()
            if not auto:
                self.update_status_bar("Checking for updates...")
            self._refresh_update_center_window(checking=True, auto=auto)

            def _worker():
                release = None
                error = None
                try:
                    release = self._fetch_latest_release_info()
                except Exception as exc:
                    error = exc
                self._update_check_pending_result = (release, error, auto)

            self._update_check_thread = threading.Thread(target=_worker, daemon=True, name=f"update-check-{source}")
            self._update_check_thread.start()
            try:
                self._update_check_poll_after = self.after(150, self._poll_update_check_completion)
            except Exception:
                self._update_check_poll_after = None
            try:
                self._update_check_timeout_after = self.after(20000, lambda a=auto: self._on_update_check_timeout(auto=a))
            except Exception:
                self._update_check_timeout_after = None
            return True
        except Exception as exc:
            self._update_check_timeout_after = None
            self._handle_update_ui_exception("Start Update Check", exc, parent=self, show_dialog=not auto)
            return False

    def auto_check_for_updates_silent(self):
        self.start_update_check(auto=True, force=False, source="auto")

    def check_for_app_update(self, release_data=None):
        try:
            if release_data is not None:
                self._set_latest_release_state(release=release_data, error=None)
                self.open_update_center(auto=False, force_check=False)
                return
            self.open_update_center(auto=False, force_check=False)
            self.start_update_check(auto=False, force=True, source="manual")
        except Exception as exc:
            self._handle_update_ui_exception("Check For App Update", exc, parent=self)

    def hard_shutdown(self):
        try:
            self.save_config(immediate=True)
        except Exception:
            pass
        try:
            self.quit()
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)

    def _shutdown_for_update(self):
        try:
            self._main_destroy_in_progress = True
        except Exception:
            pass
        try:
            self.save_config(immediate=True)
        except Exception:
            pass
        os._exit(0)

    def destroy(self):
        if getattr(self, '_main_destroy_in_progress', False):
            try:
                super().destroy()
            except Exception:
                pass
            return
        self._main_destroy_in_progress = True
        try:
            self.save_config(immediate=True)
        except Exception:
            pass
        try:
            super().destroy()
        finally:
            self._main_destroy_in_progress = False

    def get_backup_dir(self, create=False):
        base = os.path.dirname(self.current_file) if self.current_file else get_app_dir()
        backup_dir = os.path.join(base, "nip_backups")
        if create:
            os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

    def get_backup_history(self):
        backup_dir = self.get_backup_dir(create=False)
        items = []
        if not os.path.isdir(backup_dir):
            return items
        for name in sorted(os.listdir(backup_dir), reverse=True):
            path = os.path.join(backup_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                stat = os.stat(path)
                dt = datetime.fromtimestamp(stat.st_mtime)
                lower = name.lower()
                reason = 'Snapshot'
                if 'pre_save_snapshot' in lower:
                    reason = 'Pre-Save Snapshot'
                elif 'manual_snapshot' in lower:
                    reason = 'Manual Snapshot'
                elif 'pre_update_snapshot' in lower:
                    reason = 'Pre-Update Snapshot'
                elif 'pre_restore_snapshot' in lower:
                    reason = 'Pre-Restore Snapshot'
                items.append({
                    'name': name,
                    'path': path,
                    'mtime': stat.st_mtime,
                    'timestamp_display': dt.strftime('%Y-%m-%d %I:%M:%S %p'),
                    'reason': reason,
                    'size_label': f"({stat.st_size // 1024:,} KB)",
                })
            except Exception:
                continue
        return items

    def create_backup_snapshot(self, reason='Pre-Save Snapshot', source_path=None):
        src = source_path or self.current_file
        if not src or not os.path.exists(src):
            return None
        backup_dir = self.get_backup_dir(create=True)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_reason = re.sub(r'[^A-Za-z0-9]+', '_', reason.strip().lower()).strip('_') or 'snapshot'
        ext = os.path.splitext(src)[1] or '.bak'
        base_name = os.path.splitext(os.path.basename(src))[0]
        dest = os.path.join(backup_dir, f"{base_name}_{safe_reason}_{ts}{ext}")
        try:
            shutil.copy2(src, dest)
            self.run_cleanup_logic()
            return dest
        except Exception:
            return None

    def restore_backup_from_history(self, backup_path, parent=None):
        if not backup_path or not os.path.exists(backup_path):
            messagebox.showerror('Restore Backup', 'That backup file no longer exists.', parent=parent or self)
            return False
        if not self.current_file:
            target = filedialog.asksaveasfilename(defaultextension='.nip', filetypes=[('NIP files','*.nip'),('All files','*.*')], parent=parent or self, title='Choose restore target')
            if not target:
                return False
            self.current_file = target
        if not messagebox.askyesno('Restore Backup', f"Restore this backup over:\n{self.current_file}\n\n{os.path.basename(backup_path)}", parent=parent or self):
            return False
        current_snapshot = self.create_backup_snapshot(reason='Pre-Restore Snapshot', source_path=self.current_file) if os.path.exists(self.current_file) else None
        try:
            shutil.copy2(backup_path, self.current_file)
            messagebox.showinfo('Restore Backup', 'Backup restored successfully.' + (f"\n\nA restore point was made first:\n{os.path.basename(current_snapshot)}" if current_snapshot else ''), parent=parent or self)
            return True
        except Exception as e:
            messagebox.showerror('Restore Backup', f"Could not restore the selected backup.\n\n{e}", parent=parent or self)
            return False

    def _build_save_plan_text(self):
        backup_dir = self.get_backup_dir(create=True)
        state = 'enabled' if self.backup_active.get() else 'disabled'
        current = os.path.basename(self.current_file) if self.current_file else 'unsaved file'
        return f"Save safety gate active. Current file: {current}. Pre-save snapshot: {state}. Backup folder: {backup_dir}"

    def open_donate(self):
        webbrowser.open("https://www.paypal.com/paypalme/darcvigilante")
    def glow_donate(self, toggle=True):
        if hasattr(self, 'donate_btn') and self.donate_btn.winfo_exists():
            self.donate_btn.configure(fg_color="#f39c12" if toggle else "#d35400",
                                      border_color="#f1c40f" if toggle else "#e67e22")
            self.after(800, lambda: self.glow_donate(not toggle))
    def open_backup_settings(self):
        BackupHistoryDialog(
            self,
            self,
            apply_window_icon=apply_window_icon,
            configure_dialog_window=configure_dialog_window,
        )
    def open_entries_settings(self):
        EntriesSettingsDialog(
            self,
            self,
            loading_dialog_cls=LoadingDialog,
            apply_window_icon=apply_window_icon,
            configure_dialog_window=configure_dialog_window,
        )
    def load_custom_font(self, font_name):
        font_path = resource_path(font_name)
        if os.path.exists(font_path):
            try:
                FR_PRIVATE = 0x10
                WM_FONTCHANGE = 0x001D
                ctypes.windll.gdi32.AddFontResourceExW(font_path, FR_PRIVATE, 0)
                ctypes.windll.user32.PostMessageW(0xFFFF, WM_FONTCHANGE, 0, 0)
            except:
                pass
    # -----------------------------------------------------------------------
    # SAVE / LOAD
    # -----------------------------------------------------------------------
    def save_as_file(self):
        if not self.all_file_data and not self.rule_cards:
            messagebox.showinfo("Save As", "No rules loaded to save.", parent=self)
            return
        p = filedialog.asksaveasfilename(
            defaultextension=".nip",
            filetypes=[("NIP files","*.nip"),("All files","*.*")],
            parent=self)
        if p:
            self.current_file = p
            self.add_recent_file(p)
            self.save_file()
    def save_file(self):
        if not self.current_file:
            return
        self.save_with_validation_gate()

    def _save_file_now(self):
        if not self.current_file:
            return
        snapshot_path = None
        if self.backup_active.get():
            snapshot_path = self.create_backup_snapshot(reason="Pre-Save Snapshot", source_path=self.current_file)
        out = self._build_output_lines()
        with open(self.current_file, "w", encoding="utf-8") as f:
            f.write("\n".join(out))
        self.add_recent_file(self.current_file)
        self.mark_saved()
        msg = "NIP Updated!"
        if snapshot_path:
            msg += f"\n\nPre-save snapshot created:\n{os.path.basename(snapshot_path)}"
        messagebox.showinfo("Saved", msg, parent=self)
    def run_cleanup_logic(self):
        if not self.current_file:
            return
        backup_dir = self.get_backup_dir(create=False)
        if not os.path.exists(backup_dir):
            return
        threshold = time.time() - (self.backup_days.get() * 86400)
        files_to_del = [os.path.join(backup_dir, f)
                        for f in os.listdir(backup_dir)
                        if os.path.isfile(os.path.join(backup_dir, f))
                        and os.path.getmtime(os.path.join(backup_dir, f)) < threshold]
        if not files_to_del:
            return
        if self.backup_warn.get():
            if not messagebox.askyesno(
                    "Backup Cleanup",
                    f"Found {len(files_to_del)} backups older than "
                    f"{self.backup_days.get()} days. Delete them?",
                    parent=self):
                return
        for f in files_to_del:
            try: os.remove(f)
            except: pass


# ---------------------------------------------------------------------------
# 9. PAGED / PROFILED LOW-WIDGET PASS
# ---------------------------------------------------------------------------

def _paged_profile_start(self):
    self.last_profile = {"start": time.perf_counter()}


def _paged_profile_mark(self, key):
    if not isinstance(getattr(self, 'last_profile', None), dict):
        self.last_profile = {}
    self.last_profile[key] = time.perf_counter()


def _paged_profile_finish(self, total_rules=0, rendered_cards=0):
    lp = getattr(self, 'last_profile', {}) or {}
    start = lp.get('start')
    parse_done = lp.get('parse_done')
    render_done = lp.get('render_done')
    bits = []
    if start and parse_done:
        bits.append(f"parse {((parse_done - start) * 1000):.0f} ms")
    if parse_done and render_done:
        bits.append(f"first paint {((render_done - parse_done) * 1000):.0f} ms")
    elif start and render_done:
        bits.append(f"first paint {((render_done - start) * 1000):.0f} ms")
    if start and render_done:
        bits.append(f"total {((render_done - start) * 1000):.0f} ms")
    bits.append(f"rules {int(total_rules)}")
    bits.append(f"widgets {int(rendered_cards)}")
    self.last_profile_summary = " | ".join(bits)
    print(f"[chatgpt57] {self.last_profile_summary}")


def _page_size_value(self):
    raw = str(getattr(self, 'page_size_var', tk.StringVar(value='50 / page')).get()).strip().lower()
    if raw == 'all':
        return max(1, len(getattr(self, 'filtered_model_indices', []) or getattr(self, 'all_file_data', []) or [1]))
    digits = ''.join(ch for ch in raw if ch.isdigit())
    try:
        return max(1, int(digits or '50'))
    except Exception:
        return 50


def _serialize_model_to_line(self, model):
    return _rule_model_serialize_model_to_line_impl(self, model)


def _model_from_card(self, card):
    return _rule_model_from_card_impl(
        self,
        card,
        apply_rune_state=_runtime_apply_rune_state_to_card,
        friendly_item_display_name=_friendly_item_display_name,
    )


def _sync_current_page_to_models(self):
    if getattr(self, '_page_sync_in_progress', False):
        return
    self._page_sync_in_progress = True
    try:
        for card in list(getattr(self, 'rule_cards', []) or []):
            idx = getattr(card, '_model_index', None)
            if idx is None or idx < 0 or idx >= len(getattr(self, 'all_file_data', [])):
                continue
            self.all_file_data[idx] = _model_from_card(self, card)
            self._model_search_cache.pop(idx, None)
    finally:
        self._page_sync_in_progress = False


def _get_model_search_blob(self, idx, model):
    cached = self._model_search_cache.get(idx)
    if cached is not None:
        return cached
    parts = [str(model.get('name', '') or ''), str(model.get('raw_line', '') or '')]
    if not model.get('is_comment'):
        raw_type = str(model.get('type', '') or '')
        parts.append(raw_type)
        parts.append(_friendly_item_display_name(raw_type))
        parts.append(str(model.get('type_field', '') or ''))
        parts.append(str(model.get('quality', '') or ''))
        for extra in list(model.get('base_extra_conditions', []) or []):
            parts.append(str(extra))
        for key, op, val in list(model.get('stats', []) or []):
            parts.extend([str(key), str(op), str(val), FLAT_STAT_MAP.get(str(key).lower(), str(key))])
        for expr in list(model.get('advanced_clauses', []) or []):
            parts.append(str(expr))
            parts.extend(extract_numeric_stat_ids(str(expr)))
    blob = ' '.join(p for p in parts if p).lower()
    self._model_search_cache[idx] = blob
    return blob


def _rebuild_filtered_model_indices(self):
    self._sync_current_page_to_models()
    q = str(self.rule_search_var.get() or '').lower().strip()
    indices = []
    for idx, model in enumerate(getattr(self, 'all_file_data', []) or []):
        if model.get('is_comment') and model.get('hide_in_ui'):
            continue
        if not q or q in _get_model_search_blob(self, idx, model):
            indices.append(idx)
    self.filtered_model_indices = indices
    page_count = max(1, ((len(indices) - 1) // max(1, self.page_size)) + 1) if indices else 1
    self.current_page_index = min(max(0, self.current_page_index), page_count - 1)


def _update_page_controls(self):
    return _paged_update_page_controls_impl(self)


def _build_card_from_model(self, model, model_index):
    return _paged_build_card_from_model_impl(
        self,
        model,
        model_index,
        comment_rule_card_cls=CommentRuleCard,
        item_rule_card_cls=ItemRuleCard,
        flat_stat_map=FLAT_STAT_MAP,
        runtime_apply_rune_state_to_card=_runtime_apply_rune_state_to_card,
    )

def _insert_model_at(self, model, idx):
    return _paged_insert_model_at_impl(self, model, idx)


def _active_insert_index(self, fallback_to_page_start=True):
    return _paged_active_insert_index_impl(self, fallback_to_page_start=fallback_to_page_start)

def _status_rule_count_paged(self):
    return _paged_status_rule_count_impl(self)

def _build_output_lines_paged(self):
    return _paged_build_output_lines_impl(self, _sync_current_page_to_models, _serialize_model_to_line)


def _collect_diff_entries_paged(self):
    return _paged_collect_diff_entries_impl(self, _build_output_lines_paged)


def _collect_validation_results_paged(self):
    return _paged_collect_validation_results_impl(
        self,
        sync_current_page_to_models=_sync_current_page_to_models,
        serialize_model_to_line=_serialize_model_to_line,
        operator_map=OP_MAP,
        inverse_operator_map=INV_OP_MAP,
        analyze_advanced_expression=analyze_advanced_expression,
    )


def validate_loaded_file_paged(self):
    return _paged_validate_loaded_file_impl(
        self,
        collect_validation_results_func=_collect_validation_results_paged,
        messagebox_module=messagebox,
        validation_report_dialog_cls=ValidationReportDialog,
    )


def bg_load_paged(self, path, rid):
    try:
        _paged_profile_start(self)
        parsed_data, errors = [], []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for idx, line in enumerate(f):
                info = parse_nip_rule_line(line)
                if not info:
                    continue
                if info.get('error'):
                    errors.append((idx + 1, info.get('name', 'Item'), info['error']))
                parsed_data.append(info)
        _paged_profile_mark(self, 'parse_done')
        self.after(10, lambda s=self, data=parsed_data, load_id=rid, load_errors=errors: s.start_render(data, load_id, load_errors))
    except Exception as e:
        self.after(10, lambda err=str(e): messagebox.showerror('Load Error', f'Could not load file.\n\n{err}', parent=self))
        print(f'bg_load error: {e}')

# NOTE FOR chatgpt17.py
# This file was copied from chatgpt16.py as a starting point.
# Intended next change:
# - Map IDs dialog should optionally show numeric stat IDs from the entire card,
#   not only the currently opened advanced clause.


# ---------------------------------------------------------------------------
# 10. FAST CACHED PAGING PASS
# ---------------------------------------------------------------------------

_BASE_MARK_UNSAVED = DarcsNipEditor.mark_unsaved
_BASE_MARK_SAVED = DarcsNipEditor.mark_saved
_BASE_EDITOR_INIT = DarcsNipEditor.__init__


def _fast58_init(self, *args, **kwargs):
    return _paged_cache_init_impl(self, _BASE_EDITOR_INIT, *args, **kwargs)


def _fast58_page_cache_key(self, page_index=None):
    return _paged_cache_page_key_impl(self, page_index=page_index)


def _fast58_clear_page_cache(self, destroy=True, keep_current=False):
    return _paged_cache_clear_impl(self, destroy=destroy, keep_current=keep_current)


def _fast58_clear_standard_card_pool(self, destroy=True):
    return _paged_cache_clear_standard_pool_impl(self, destroy=destroy)


def _fast58_sync_current_page_to_models(self):
    return _paged_cache_sync_current_page_to_models_impl(self, _model_from_card)


def _fast58_mark_unsaved(self):
    return _paged_cache_mark_unsaved_impl(self, _BASE_MARK_UNSAVED)


def _fast58_mark_saved(self):
    return _paged_cache_mark_saved_impl(self, _BASE_MARK_SAVED)


def _fast58_rebuild_filtered_model_indices(self):
    return _paged_cache_rebuild_filtered_indices_impl(
        self,
        get_model_search_blob=_get_model_search_blob,
        clear_page_cache_func=_fast58_clear_page_cache,
    )


def _fast58_render_current_page(self):
    return _paged_cache_render_current_page_impl(
        self,
        ctk_module=ctk,
        build_card_from_model=_build_card_from_model,
        page_cache_key_func=_fast58_page_cache_key,
    )

def _fast58_profile_finish(self, total_rules=0, rendered_cards=0):
    return _paged_cache_profile_finish_impl(self, total_rules=total_rules, rendered_cards=rendered_cards)


# Neutral aliases for the active paged-cache runtime path.
_paged_cache_init = _fast58_init
_paged_cache_clear = _fast58_clear_page_cache
_paged_cache_clear_standard_pool = _fast58_clear_standard_card_pool
_paged_cache_sync_models = _fast58_sync_current_page_to_models
_paged_cache_mark_unsaved = _fast58_mark_unsaved
_paged_cache_mark_saved = _fast58_mark_saved
_paged_cache_rebuild_filtered_indices = _fast58_rebuild_filtered_model_indices
_paged_cache_render_standard_page = _fast58_render_current_page
_paged_profile_finish_runtime = _fast58_profile_finish

def _perf67_compact_title(model):
    return _compact_legacy_title_impl(model, _friendly_item_display_name, title_separator="  \u2022  ")


def _perf67_compact_summary(model):
    return _compact_legacy_summary_impl(model, FLAT_STAT_MAP, preview_joiner=" \u00b7 ")


def _perf67_build_full_editor_card(app, parent, model, model_index):
    return _compact_build_full_editor_card_impl(
        app,
        parent,
        model,
        model_index,
        comment_rule_card_cls=CommentRuleCard,
        item_rule_card_cls=ItemRuleCard,
        flat_stat_map=FLAT_STAT_MAP,
        apply_rune_state_to_card=_runtime_apply_rune_state_to_card,
    )


def _perf67_refresh_after_model_change(self, preserve_page=True):
    return _compact_refresh_after_model_change_impl(self, _paged_cache_clear, _paged_cache_rebuild_filtered_indices, preserve_page=preserve_page)


def _perf67_open_compact_editor(self, card):
    return _compact_open_editor_impl(
        self,
        card,
        messagebox_module=messagebox,
        configure_dialog_window=configure_dialog_window,
        destroy_window_safely=destroy_window_safely,
        compact_editor_builder=_compact_editor_builder,
        compact_editor_refresh=_compact_editor_refresh,
        model_from_card=_model_from_card,
        serialize_model_to_line=_serialize_model_to_line,
    )


def _perf67_build_compact_card_from_model(self, model, model_index):
    return _compact_build_card_impl(self, model, model_index, title_builder=_compact_title_cached, summary_builder=_compact_summary_cached)


_STANDARD_RENDER_CURRENT_PAGE = _paged_cache_render_standard_page


def _perf67_render_current_page(self):
    return _compact_render_current_page_impl(self, _STANDARD_RENDER_CURRENT_PAGE, _runtime_get_compact_card)

# --- chatgpt68.py patch: polish + speed pass ---

def _perf68_stat_preview_parts(stats, limit=3):
    return _compact_stat_preview_parts_impl(stats, FLAT_STAT_MAP, limit=limit)


def _perf68_model_signature(model):
    return _compact_model_signature_impl(model)


def _perf68_model_cache(self, idx, model):
    return _compact_build_model_cache_impl(
        self,
        idx,
        model,
        flat_stat_map=FLAT_STAT_MAP,
        friendly_item_display_name=_friendly_item_display_name,
        extract_numeric_stat_ids=extract_numeric_stat_ids,
        runtime_model_is_rune=_runtime_model_is_rune,
        title_separator="  \u2022  ",
        preview_joiner=" \u00b7 ",
    )


def _perf68_get_model_search_blob(self, idx, model):
    return _compact_get_model_search_blob_impl(self, idx, model, _perf68_model_cache)


def _perf68_compact_title(model):
    return _compact_title_impl(model, _friendly_item_display_name, '  â€¢  ')


def _perf68_compact_summary(model):
    return _compact_summary_impl(model, _BASE_COMPACT_SUMMARY)


def _perf68_prime_model_caches(self, page_hint=None, chunk_size=80):
    return _compact_prime_model_caches_impl(self, _perf68_model_cache, page_hint=page_hint, chunk_size=chunk_size)


def _perf68_start_render_paged(self, data_list, rid, errors):
    return _runtime_controller_start_render_paged_impl(
        self,
        data_list,
        rid,
        errors,
        page_size_value=_page_size_value,
        perf68_model_cache=_perf68_model_cache,
        perf68_prime_model_caches=_perf68_prime_model_caches,
        paged_profile_mark=_paged_profile_mark,
        paged_profile_finish=_paged_profile_finish,
    )


def _perf68_render_current_page(self):
    return _runtime_controller_render_current_page_impl(
        self,
        perf67_render_current_page=_perf67_render_current_page,
        perf68_prime_model_caches=_perf68_prime_model_caches,
    )

_BASE_COMPACT_CARD_BUILDER = _perf67_build_compact_card_from_model
_BASE_COMPACT_SUMMARY = _perf67_compact_summary

def _perf68_build_compact_card_from_model(self, model, model_index):
    try:
        _perf68_model_cache(self, model_index, model)
    except Exception:
        pass
    return _BASE_COMPACT_CARD_BUILDER(self, model, model_index)


# Neutral aliases for the active compact/page render path.
_compact_editor_builder = _perf67_build_full_editor_card
_compact_editor_refresh = _perf67_refresh_after_model_change
_compact_editor_open = _perf67_open_compact_editor
_model_search_blob_cached = _perf68_get_model_search_blob
_compact_title_cached = _perf68_compact_title
_compact_summary_cached = _perf68_compact_summary
_visible_model_cache_prime = _perf68_prime_model_caches
_paged_runtime_start_render = _perf68_start_render_paged
_paged_runtime_render = _perf68_render_current_page

# --- runtime cleanup: keep the fast path, remove dead callbacks/wrapper bloat ---

_RUNTIME_PAGE_SIZE_CHOICES = {"10 / page", "25 / page", "50 / page", "100 / page", "200 / page", "All"}


def _runtime_perf_enabled(self):
    return _runtime_controller_perf_enabled_impl(self)


def _runtime_perf_page_size_choice(self, enabled):
    return _runtime_controller_perf_page_size_choice_impl(self, enabled, _RUNTIME_PAGE_SIZE_CHOICES)


def _runtime_clear_compact_card_cache(self, destroy=True):
    return _compact_clear_card_cache_impl(self, destroy=destroy)


def _runtime_clear_standard_card_pool(self, destroy=True):
    return _paged_cache_clear_standard_pool(self, destroy=destroy)


def _runtime_get_compact_card(self, model_index, model):
    return _compact_get_card_impl(
        self,
        model_index,
        model,
        model_signature=_perf68_model_signature,
        base_compact_card_builder=_BASE_COMPACT_CARD_BUILDER,
    )


def _runtime_schedule_compact_prewarm(self, page_hint=None, page_span=1, chunk_size=3):
    return _compact_schedule_prewarm_impl(
        self,
        runtime_perf_enabled=_runtime_perf_enabled,
        runtime_get_compact_card=_runtime_get_compact_card,
        page_hint=page_hint,
        page_span=page_span,
        chunk_size=chunk_size,
    )


def _runtime_sync_perf_button(self):
    return _runtime_controller_sync_perf_button_impl(self, _runtime_perf_enabled)


def _runtime_update_status_bar(self, validation_state=None):
    return _runtime_controller_update_status_bar_impl(
        self,
        APP_VERSION,
        _status_rule_count_paged,
        _runtime_perf_enabled,
        validation_state=validation_state,
    )


def _runtime_prime_visible_models(self, chunk_size=120):
    return _compact_prime_visible_models_impl(
        self,
        runtime_perf_enabled=_runtime_perf_enabled,
        visible_model_cache_prime=_visible_model_cache_prime,
        runtime_schedule_compact_prewarm=_runtime_schedule_compact_prewarm,
        chunk_size=chunk_size,
    )


def _runtime_change_page_size(self, choice=None):
    return _runtime_controller_change_page_size_impl(
        self,
        perf_enabled_func=_runtime_perf_enabled,
        valid_choices=_RUNTIME_PAGE_SIZE_CHOICES,
        page_size_value=_page_size_value,
        paged_cache_clear=_paged_cache_clear,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
        runtime_prime_visible_models=_runtime_prime_visible_models,
    )


def _runtime_apply_performance_mode(self, refresh=True, persist=True, force_rebuild=False):
    return _runtime_controller_apply_performance_mode_impl(
        self,
        perf_enabled_func=_runtime_perf_enabled,
        perf_page_size_choice_func=_runtime_perf_page_size_choice,
        valid_choices=_RUNTIME_PAGE_SIZE_CHOICES,
        sync_perf_button_func=_runtime_sync_perf_button,
        runtime_change_page_size=_runtime_change_page_size,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_prime_visible_models=_runtime_prime_visible_models,
        refresh=refresh,
        persist=persist,
        force_rebuild=force_rebuild,
    )


def _runtime_toggle_performance(self):
    return _runtime_controller_toggle_performance_impl(
        self,
        perf_enabled_func=_runtime_perf_enabled,
        runtime_apply_performance_mode=_runtime_apply_performance_mode,
    )


def _runtime_go_prev_page(self):
    return _runtime_controller_go_prev_page_impl(self, runtime_prime_visible_models=_runtime_prime_visible_models)


def _runtime_go_next_page(self):
    return _runtime_controller_go_next_page_impl(self, runtime_prime_visible_models=_runtime_prime_visible_models)


def _runtime_filter_rule_cards(self, *args):
    return _runtime_controller_filter_rule_cards_impl(
        self,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
        runtime_prime_visible_models=_runtime_prime_visible_models,
    )


def _runtime_repack_cards(self):
    return _runtime_controller_repack_cards_impl(self, runtime_prime_visible_models=_runtime_prime_visible_models)


def _runtime_schedule_rule_filter(self, *args):
    return _runtime_controller_schedule_rule_filter_impl(self, runtime_filter_rule_cards=_runtime_filter_rule_cards)


def _runtime_run_rule_filter(self):
    return _runtime_controller_run_rule_filter_impl(self, runtime_filter_rule_cards=_runtime_filter_rule_cards)


def _runtime_add_blank(self):
    return _runtime_mutations_add_blank_impl(
        self,
        ctk_module=ctk,
        parse_nip_rule_line=parse_nip_rule_line,
        serialize_model_to_line=_serialize_model_to_line,
        active_insert_index=_active_insert_index,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        insert_model_at=_insert_model_at,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_add_comment(self, name=None):
    return _runtime_mutations_add_comment_impl(
        self,
        name=name,
        ctk_module=ctk,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        insert_model_at=_insert_model_at,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_add_from_cat(self, name, category=None):
    return _runtime_mutations_add_from_cat_impl(
        self,
        name,
        category=category,
        parse_nip_rule_line=parse_nip_rule_line,
        serialize_model_to_line=_serialize_model_to_line,
        active_insert_index=_active_insert_index,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        insert_model_at=_insert_model_at,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_del_card(self, card):
    return _runtime_mutations_del_card_impl(
        self,
        card,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_clone(self, old):
    return _runtime_mutations_clone_impl(
        self,
        old,
        serialize_model_to_line=_serialize_model_to_line,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_move_card_up(self, card):
    return _runtime_mutations_move_card_up_impl(
        self,
        card,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_move_card_down(self, card):
    return _runtime_mutations_move_card_down_impl(
        self,
        card,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_undo_delete(self):
    return _runtime_mutations_undo_delete_impl(
        self,
        messagebox_module=messagebox,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        paged_cache_rebuild_filtered_indices=_paged_cache_rebuild_filtered_indices,
    )


def _runtime_init(self, *args, **kwargs):
    return _runtime_controller_init_runtime_impl(
        self,
        _paged_cache_init,
        _RUNTIME_PAGE_SIZE_CHOICES,
        _runtime_apply_performance_mode,
        *args,
        **kwargs,
    )


def _runtime_start_render(self, data_list, rid, errors):
    return _runtime_controller_start_render_impl(
        self,
        data_list,
        rid,
        errors,
        runtime_clear_compact_card_cache=_runtime_clear_compact_card_cache,
        runtime_clear_standard_card_pool=_runtime_clear_standard_card_pool,
        paged_runtime_start_render=_paged_runtime_start_render,
    )


def _runtime_paged_profile_start(self):
    return _paged_profile_start(self)


def _runtime_paged_profile_mark(self, key):
    return _paged_profile_mark(self, key)


def _runtime_paged_profile_finish(self, total_rules=0, rendered_cards=0):
    return _paged_profile_finish_runtime(self, total_rules=total_rules, rendered_cards=rendered_cards)


def _runtime_page_size_value(self):
    return _page_size_value(self)


def _runtime_serialize_model_to_line(self, model):
    return _serialize_model_to_line(self, model)


def _runtime_model_from_card(self, card):
    return _model_from_card(self, card)


def _runtime_mark_unsaved(self):
    return _paged_cache_mark_unsaved(self)


def _runtime_mark_saved(self):
    return _paged_cache_mark_saved(self)


def _runtime_sync_current_page_to_models(self):
    return _paged_cache_sync_models(self)


def _runtime_rebuild_filtered_model_indices(self):
    return _paged_cache_rebuild_filtered_indices(self)


def _runtime_get_model_search_blob(self, idx, model):
    return _model_search_blob_cached(self, idx, model)


def _runtime_update_page_controls(self):
    return _update_page_controls(self)


def _runtime_build_card_from_model(self, model, model_index):
    return _build_card_from_model(self, model, model_index)


def _runtime_insert_model_at(self, model, idx):
    return _insert_model_at(self, model, idx)


def _runtime_active_insert_index(self, fallback_to_page_start=True):
    return _active_insert_index(self, fallback_to_page_start=fallback_to_page_start)


def _runtime_status_rule_count(self):
    return _status_rule_count_paged(self)


def _runtime_render_current_page(self):
    return _paged_runtime_render(self)


def _runtime_filter_catalog(self, *args):
    return _sidebar_catalog_filter(self, *args)


def _runtime_filter_library(self, *args):
    return _sidebar_library_filter(self, *args)


def _runtime_open_compact_editor(self, card):
    return _compact_editor_open(self, card)

def _perf76_filter_catalog(self, *args):
    return _sidebar_filter_catalog_impl(self, _display_label)


def _perf76_filter_library(self, *args):
    return _sidebar_filter_library_impl(self, _display_label)


# Neutral aliases for the active sidebar filter path.
_sidebar_catalog_filter = _perf76_filter_catalog
_sidebar_library_filter = _perf76_filter_library

configure_widget_cards_runtime(
    apply_window_icon=apply_window_icon,
    apply_rune_state_to_card=_runtime_apply_rune_state_to_card,
    nudge_window_paint=nudge_window_paint,
    destroy_window_safely=destroy_window_safely,
    configure_dialog_window=configure_dialog_window,
    display_label=_display_label,
    flat_stat_map=FLAT_STAT_MAP,
    quality_colors=QUALITY_COLORS,
    stat_colors=STAT_COLORS,
    stat_hints=STAT_HINTS,
    op_map=OP_MAP,
    inv_op_map=INV_OP_MAP,
    parse_rule_line=parse_nip_rule_line,
    all_item_types=ALL_ITEM_TYPES,
    stat_library=STAT_LIBRARY,
    skill_library=SKILL_LIBRARY,
)

bind_pickit_runtime(globals(), DarcsNipEditor, ItemRuleCard)


# --- chatgpt69.py patch: startup moved to end for release-install wiring ---
if __name__ == "__main__":
    set_windows_app_id()

    app = DarcsNipEditor()
    app.mainloop()
