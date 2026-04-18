import re


def build_output_lines(app, sync_current_page_to_models, serialize_model_to_line):
    sync_current_page_to_models(app)
    return [serialize_model_to_line(app, model) for model in list(app.all_file_data or [])]


def collect_diff_entries(app, build_output_lines_func):
    current_lines = build_output_lines_func(app)
    original_lines = [item.get("raw_line", "") for item in app.all_file_data] if app.all_file_data else []
    max_len = max(len(current_lines), len(original_lines))
    diffs = []
    for idx in range(max_len):
        old = original_lines[idx] if idx < len(original_lines) else ""
        new = current_lines[idx] if idx < len(current_lines) else ""
        if old != new:
            model = app.all_file_data[idx] if idx < len(app.all_file_data) else {}
            name = model.get("name", f"Line {idx + 1}")
            diffs.append({"line_no": idx + 1, "name": name, "original": old, "current": new})
    return diffs


def collect_validation_results(
    app,
    *,
    sync_current_page_to_models,
    serialize_model_to_line,
    operator_map,
    inverse_operator_map,
    analyze_advanced_expression,
):
    sync_current_page_to_models(app)
    results = {"errors": [], "warnings": [], "duplicates": []}
    seen = {}
    for idx, model in enumerate(app.all_file_data, start=1):
        if model.get("is_comment"):
            continue
        name = str(model.get("name", f"Rule {idx}"))
        line = serialize_model_to_line(app, model)
        type_ok = str(model.get("type", "") or "").strip().lower()
        if not type_ok or type_ok == "item":
            extras = " ".join(str(x or "") for x in list(model.get("base_extra_conditions", []) or []))
            if not re.search(r"\[(?:name|type)\]", extras, re.I):
                results["errors"].append(f"Line {idx} - {name}: No item type/base selected.")
        for stat_idx, payload in enumerate(list(model.get("stats", []) or []), start=1):
            try:
                stat_key, op_label, val = payload
            except Exception:
                stat_key, op_label, val = "", ">=", ""
            prefix = f"Line {idx} - {name} - Stat {stat_idx}: "
            if not str(stat_key).strip():
                results["errors"].append(prefix + "Missing stat key.")
            if str(val).strip() == "":
                results["errors"].append(prefix + "Missing stat value.")
            elif not re.fullmatch(r"-?\d+", str(val).strip()):
                results["warnings"].append(prefix + f"Non-numeric stat value '{val}'.")
            if str(op_label).strip() not in operator_map and str(op_label).strip() not in inverse_operator_map:
                results["errors"].append(prefix + f"Unknown operator '{op_label}'.")
        for adv_idx, expr in enumerate(list(model.get("advanced_clauses", []) or []), start=1):
            prefix = f"Line {idx} - {name} - Advanced {adv_idx}: "
            expr = str(expr or "").strip()
            if not expr:
                results["errors"].append(prefix + "Advanced clause is empty.")
            else:
                level, msg = analyze_advanced_expression(expr)
                if level == "error":
                    results["errors"].append(prefix + msg)
                elif level == "warning":
                    results["warnings"].append(prefix + msg)
        norm = re.sub(r"\s+", " ", line).strip().lower()
        if norm in seen:
            results["duplicates"].append(f"Line {seen[norm]} and line {idx} appear to serialize identically.")
        else:
            seen[norm] = idx
    return results


def validate_loaded_file(
    app,
    *,
    collect_validation_results_func,
    messagebox_module,
    validation_report_dialog_cls,
):
    if not app.all_file_data and not app.rule_cards:
        messagebox_module.showinfo("Validate File", "No rules are currently loaded.", parent=app)
        return
    results = collect_validation_results_func(app)
    if results.get("errors"):
        app.update_status_bar("Validation: Errors")
    elif results.get("warnings") or results.get("duplicates"):
        app.update_status_bar("Validation: Warnings")
    else:
        app.update_status_bar("Validation: OK")
    validation_report_dialog_cls(app, results, save_plan_text=app._build_save_plan_text())
