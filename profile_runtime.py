import argparse
import importlib.util
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from release_metadata import ENTRY_SCRIPT


ROOT = Path(__file__).resolve().parent
TARGET = ROOT / ENTRY_SCRIPT


def load_module():
    spec = importlib.util.spec_from_file_location(f"{TARGET.stem.lower()}_profiled", TARGET)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def reapply_runtime_bindings(mod):
    cls = mod.DarcsNipEditor
    if callable(getattr(mod, "_RUNTIME_ORIG_BUILD_UI", None)):
        cls._build_ui = mod._RUNTIME_ORIG_BUILD_UI
    if callable(getattr(mod, "_unwrap_runtime_wrapper", None)):
        for name in ("load_config", "save_config", "_finalize_main_window_chrome"):
            current = getattr(cls, name, None)
            unwrapped = mod._unwrap_runtime_wrapper(current)
            if callable(unwrapped):
                setattr(cls, name, unwrapped)
    cls.__init__ = mod._runtime_init
    cls.mark_unsaved = mod._fast58_mark_unsaved
    cls.mark_saved = mod._fast58_mark_saved
    cls._sync_current_page_to_models = mod._fast58_sync_current_page_to_models
    cls._rebuild_filtered_model_indices = mod._fast58_rebuild_filtered_model_indices
    cls._get_model_search_blob = mod._perf68_get_model_search_blob
    cls.bg_load = mod.bg_load_paged
    cls.start_render = mod._runtime_start_render
    cls.render_current_page = mod._perf68_render_current_page
    cls.go_prev_page = mod._runtime_go_prev_page
    cls.go_next_page = mod._runtime_go_next_page
    cls.change_page_size = mod._runtime_change_page_size
    cls.filter_rule_cards = mod._runtime_filter_rule_cards
    cls.repack_cards = mod._runtime_repack_cards
    cls._schedule_rule_filter = mod._runtime_schedule_rule_filter
    cls._run_rule_filter = mod._runtime_run_rule_filter
    cls.update_status_bar = mod._runtime_update_status_bar
    cls.apply_performance_mode = mod._runtime_apply_performance_mode
    cls.toggle_performance_mode_ui = mod._runtime_toggle_performance
    cls.open_compact_editor = mod._perf67_open_compact_editor
    cls.add_blank = mod._runtime_add_blank
    cls.add_comment = mod._runtime_add_comment
    cls.add_from_cat = mod._runtime_add_from_cat
    cls.del_card = mod._runtime_del_card
    cls.clone = mod._runtime_clone
    cls.move_card_up = mod._runtime_move_card_up
    cls.move_card_down = mod._runtime_move_card_down
    cls.undo_delete = mod._runtime_undo_delete
    cls._build_output_lines = mod._build_output_lines_paged
    cls._collect_diff_entries = mod._collect_diff_entries_paged
    cls._collect_validation_results = mod._collect_validation_results_paged
    cls.validate_loaded_file = mod.validate_loaded_file_paged


def make_rule_line(index: int) -> str:
    if index % 37 == 0:
        return f"// --- Section {index // 37} ---"
    if index % 11 == 0:
        return (
            f"[name] == Ring && [quality] == unique "
            f"# [itemmagicbonus] >= {10 + (index % 30)} && [fireresist] >= {5 + (index % 20)} "
            f"// Magic Ring {index}"
        )
    if index % 7 == 0:
        return (
            f"[type] == amu && [quality] == rare "
            f"# ([strength] >= {10 + (index % 8)} || [dexterity] >= {10 + (index % 6)}) && [coldresist] >= {8 + (index % 15)} "
            f"// Rare Amulet {index}"
        )
    if index % 5 == 0:
        return (
            f"[name] == Rune && [quality] == normal "
            f"# [maxquantity] == 1 && [goldfind] >= {50 + (index % 90)} "
            f"// Rune {index}"
        )
    return (
        f"[type] == ring && [quality] == rare "
        f"# [strength] >= {5 + (index % 20)} && [lightresist] >= {6 + (index % 18)} && [itemmagicbonus] >= {8 + (index % 24)} "
        f"// Rare Ring {index}"
    )


def build_lines(count: int):
    return [make_rule_line(i) for i in range(count)]


def read_lines(path: Path):
    with path.open("r", encoding="utf-8", errors="ignore") as handle:
        return [line.rstrip("\n\r") for line in handle]


def timed_runs(fn, runs=3):
    values = []
    last_result = None
    for _ in range(runs):
        start = time.perf_counter()
        last_result = fn()
        values.append((time.perf_counter() - start) * 1000.0)
    return {
        "median_ms": round(statistics.median(values), 2),
        "min_ms": round(min(values), 2),
        "max_ms": round(max(values), 2),
        "runs_ms": [round(v, 2) for v in values],
    }, last_result


def pump_events(app, duration_ms=300):
    end = time.perf_counter() + (duration_ms / 1000.0)
    while time.perf_counter() < end:
        app.update()
        time.sleep(0.01)


def profile_parse_lines(mod, lines):
    def _run():
        parsed = []
        for line in lines:
            info = mod.parse_nip_rule_line(line)
            if info:
                parsed.append(info)
        return parsed

    stats, parsed = timed_runs(_run)
    stats["parsed_entries"] = len(parsed)
    return stats, parsed


def profile_parse(mod, count: int):
    return profile_parse_lines(mod, build_lines(count))


def infer_search_term(parsed_models):
    counts = Counter()
    excluded = {
        "item",
        "items",
        "rare",
        "magic",
        "normal",
        "unique",
        "set",
        "crafted",
        "section",
    }
    for model in list(parsed_models or []):
        if model.get("is_comment"):
            continue
        for raw in (
            str(model.get("type", "") or "").strip().lower(),
            str(model.get("name", "") or "").strip().lower(),
        ):
            if not raw:
                continue
            for token in raw.replace("-", " ").split():
                token = token.strip()
                if len(token) < 3 or token in excluded:
                    continue
                counts[token] += 1
    if counts:
        token, hits = counts.most_common(1)[0]
        if hits >= 2:
            return token
    for model in list(parsed_models or []):
        if model.get("is_comment"):
            continue
        for raw in (
            str(model.get("type", "") or "").strip().lower(),
            str(model.get("name", "") or "").strip().lower(),
        ):
            if raw and raw not in excluded:
                return raw.split()[0]
    return ""


def profile_ui(mod, parsed_models, search_term="ring"):
    app = None
    results = {}
    search_term = str(search_term or "").strip().lower()
    try:
        start = time.perf_counter()
        app = mod.DarcsNipEditor()
        app.update()
        results["app_init_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

        app.load_id += 1
        rid = app.load_id
        start = time.perf_counter()
        app.start_render(parsed_models, rid, [])
        app.update_idletasks()
        results["start_render_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

        results["search_term"] = search_term
        if search_term:
            start = time.perf_counter()
            app.rule_search_var.set(search_term)
            app._run_rule_filter()
            app.update_idletasks()
            results["search_ms"] = round((time.perf_counter() - start) * 1000.0, 2)
            results["search_matches"] = len(getattr(app, "filtered_model_indices", []) or [])

            start = time.perf_counter()
            app.go_next_page()
            app.update_idletasks()
            results["next_page_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

            app.rule_search_var.set("")
            app._run_rule_filter()
            pump_events(app, 350)

            start = time.perf_counter()
            app.rule_search_var.set(search_term)
            app._run_rule_filter()
            app.update_idletasks()
            results["warm_search_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

            start = time.perf_counter()
            app.go_next_page()
            app.update_idletasks()
            results["warm_next_page_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

        start = time.perf_counter()
        app.toggle_performance_mode_ui()
        app.update_idletasks()
        results["toggle_perf_off_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

        start = time.perf_counter()
        app.toggle_performance_mode_ui()
        app.update_idletasks()
        results["toggle_perf_on_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

        start = time.perf_counter()
        app._collect_validation_results()
        results["validate_models_ms"] = round((time.perf_counter() - start) * 1000.0, 2)

        results["page_size"] = app.page_size
        results["visible_cards"] = len(getattr(app, "rule_cards", []) or [])
        results["total_models"] = len(getattr(app, "all_file_data", []) or [])
        results["performance_mode"] = bool(app.performance_mode.get())
        results["profile_summary"] = getattr(app, "last_profile_summary", "")
    finally:
        if app is not None:
            try:
                app.destroy()
            except Exception:
                pass
    return results


def build_report_for_lines(mod, label, lines, source_path=None):
    parse_stats, parsed = profile_parse_lines(mod, lines)
    ui_results = profile_ui(mod, parsed, search_term=infer_search_term(parsed))
    return {
        "label": label,
        "source_path": str(source_path) if source_path else None,
        "line_count": len(lines),
        "parse": parse_stats,
        "ui_profile": ui_results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", dest="file_path", help="Path to a real .nip file to profile")
    args = parser.parse_args()

    overall_start = time.perf_counter()

    import_start = time.perf_counter()
    mod = load_module()
    import_ms = (time.perf_counter() - import_start) * 1000.0
    reapply_runtime_bindings(mod)

    report = {
        "python": sys.executable,
        "target": str(TARGET),
        "import_ms": round(import_ms, 2),
    }
    if args.file_path:
        file_path = Path(args.file_path).expanduser().resolve()
        report["file_profile"] = build_report_for_lines(
            mod,
            label="real_file",
            lines=read_lines(file_path),
            source_path=file_path,
        )
    else:
        report["synthetic_1000"] = build_report_for_lines(mod, label="synthetic_1000", lines=build_lines(1000))
        report["synthetic_5000"] = build_report_for_lines(mod, label="synthetic_5000", lines=build_lines(5000))
    report["total_elapsed_ms"] = round((time.perf_counter() - overall_start) * 1000.0, 2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
