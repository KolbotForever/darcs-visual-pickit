from collections.abc import Mapping
from typing import Callable, Type


EDITOR_BINDING_SPECS = (
    ("__init__", "_runtime_init"),
    ("_paged_profile_start", "_runtime_paged_profile_start"),
    ("_paged_profile_mark", "_runtime_paged_profile_mark"),
    ("_paged_profile_finish", "_runtime_paged_profile_finish"),
    ("_page_size_value", "_runtime_page_size_value"),
    ("_serialize_model_to_line", "_runtime_serialize_model_to_line"),
    ("_model_from_card", "_runtime_model_from_card"),
    ("mark_unsaved", "_runtime_mark_unsaved"),
    ("mark_saved", "_runtime_mark_saved"),
    ("_sync_current_page_to_models", "_runtime_sync_current_page_to_models"),
    ("_rebuild_filtered_model_indices", "_runtime_rebuild_filtered_model_indices"),
    ("_get_model_search_blob", "_runtime_get_model_search_blob"),
    ("_update_page_controls", "_runtime_update_page_controls"),
    ("_build_card_from_model", "_runtime_build_card_from_model"),
    ("_insert_model_at", "_runtime_insert_model_at"),
    ("_active_insert_index", "_runtime_active_insert_index"),
    ("_status_rule_count", "_runtime_status_rule_count"),
    ("bg_load", "bg_load_paged"),
    ("start_render", "_runtime_start_render"),
    ("render_current_page", "_runtime_render_current_page"),
    ("go_prev_page", "_runtime_go_prev_page"),
    ("go_next_page", "_runtime_go_next_page"),
    ("change_page_size", "_runtime_change_page_size"),
    ("filter_catalog", "_runtime_filter_catalog"),
    ("filter_library", "_runtime_filter_library"),
    ("filter_rule_cards", "_runtime_filter_rule_cards"),
    ("repack_cards", "_runtime_repack_cards"),
    ("_schedule_rule_filter", "_runtime_schedule_rule_filter"),
    ("_run_rule_filter", "_runtime_run_rule_filter"),
    ("update_status_bar", "_runtime_update_status_bar"),
    ("apply_performance_mode", "_runtime_apply_performance_mode"),
    ("toggle_performance_mode_ui", "_runtime_toggle_performance"),
    ("open_compact_editor", "_runtime_open_compact_editor"),
    ("add_blank", "_runtime_add_blank"),
    ("add_comment", "_runtime_add_comment"),
    ("add_from_cat", "_runtime_add_from_cat"),
    ("del_card", "_runtime_del_card"),
    ("clone", "_runtime_clone"),
    ("move_card_up", "_runtime_move_card_up"),
    ("move_card_down", "_runtime_move_card_down"),
    ("undo_delete", "_runtime_undo_delete"),
    ("_build_output_lines", "_build_output_lines_paged"),
    ("_collect_diff_entries", "_collect_diff_entries_paged"),
    ("_collect_validation_results", "_collect_validation_results_paged"),
    ("validate_loaded_file", "validate_loaded_file_paged"),
)

ITEM_RULE_CARD_BINDING_SPECS = (
    ("set_type", "_runtime_itemrulecard_set_type"),
    ("update_color", "_runtime_itemrulecard_update_color"),
    ("_build_deferred_summary_text", "_runtime_itemrulecard_deferred_summary"),
)


def _apply_bindings(target_cls: Type[object], bindings: Mapping[str, Callable], label: str) -> None:
    for name, method in bindings.items():
        if not callable(method):
            raise TypeError(f"{label} binding '{name}' is not callable: {method!r}")
        setattr(target_cls, name, method)


def bind_runtime_methods(
    editor_cls: Type[object],
    item_rule_card_cls: Type[object],
    *,
    editor_methods: Mapping[str, Callable],
    item_rule_card_methods: Mapping[str, Callable],
) -> Type[object]:
    _apply_bindings(editor_cls, editor_methods, "editor")
    _apply_bindings(item_rule_card_cls, item_rule_card_methods, "item card")
    return editor_cls


def _resolve_binding_specs(
    source_namespace: Mapping[str, object],
    binding_specs: tuple[tuple[str, str], ...],
    label: str,
) -> dict[str, Callable]:
    bindings: dict[str, Callable] = {}
    for target_name, source_name in binding_specs:
        method = source_namespace.get(source_name)
        if method is None:
            raise AttributeError(f"{label} source '{source_name}' is missing from the runtime namespace")
        if not callable(method):
            raise TypeError(f"{label} source '{source_name}' is not callable: {method!r}")
        bindings[target_name] = method
    return bindings


def bind_pickit_runtime(
    source_namespace: Mapping[str, object],
    editor_cls: Type[object],
    item_rule_card_cls: Type[object],
) -> Type[object]:
    return bind_runtime_methods(
        editor_cls,
        item_rule_card_cls,
        editor_methods=_resolve_binding_specs(source_namespace, EDITOR_BINDING_SPECS, "editor"),
        item_rule_card_methods=_resolve_binding_specs(
            source_namespace,
            ITEM_RULE_CARD_BINDING_SPECS,
            "item card",
        ),
    )
