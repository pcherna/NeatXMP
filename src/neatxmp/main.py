"""NeatXMP — Dear PyGui front-end for stamping XMP sidecar dates."""

from __future__ import annotations

from pathlib import Path

import dearpygui.dearpygui as dpg

from .date_parser import find_date_in_name, format_xmp_date
from .xmp_writer import apply_date_to_xmp

MEDIA_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov"})

_folders: list[str] = []


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    dpg.create_context()

    # Directory-picker dialog (hidden until "Add Folder" is clicked)
    with dpg.file_dialog(
        directory_selector=True,
        show=False,
        callback=_on_folder_selected,
        tag="folder_dialog",
        width=700,
        height=450,
    ):
        pass

    with dpg.window(label="NeatXMP", tag="primary_window"):

        # --- Folder list ---
        dpg.add_text("Folders")
        dpg.add_listbox(tag="folder_list", items=[], width=-1, num_items=6)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Add Folder", callback=lambda: dpg.show_item("folder_dialog"))
            dpg.add_button(label="Remove Selected", callback=_remove_folder)

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=8)

        # --- Mode toggle ---
        dpg.add_text("Mode")
        with dpg.group(horizontal=True):
            dpg.add_radio_button(
                tag="mode_radio",
                items=["Preview (dry run)", "Apply (write files)"],
                default_value="Preview (dry run)",
                horizontal=True,
            )

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=8)

        # --- Action buttons ---
        with dpg.group(horizontal=True):
            dpg.add_button(
                label="Apply Folder Name as Date",
                callback=_apply_folder_date,
                width=260,
                height=40,
            )
            dpg.add_spacer(width=8)
            dpg.add_button(
                label="Apply File Name as Date",
                callback=_apply_file_date,
                width=260,
                height=40,
            )
            dpg.add_spacer(width=8)
            dpg.add_button(
                label="Clear Log",
                callback=lambda: dpg.set_value("log", ""),
                height=40,
            )

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=4)

        # --- Log ---
        dpg.add_text("Log")
        dpg.add_input_text(
            tag="log",
            multiline=True,
            readonly=True,
            width=-1,
            height=-1,
        )

    dpg.create_viewport(title="NeatXMP", width=920, height=740)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("primary_window", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


# ---------------------------------------------------------------------------
# Folder list callbacks
# ---------------------------------------------------------------------------

def _on_folder_selected(sender: str, app_data: dict) -> None:
    folder = app_data.get("file_path_name", "").strip()
    if not folder:
        return
    folder = str(Path(folder).resolve())
    if folder not in _folders:
        _folders.append(folder)
        dpg.configure_item("folder_list", items=_folders)


def _remove_folder() -> None:
    selected = dpg.get_value("folder_list")
    if selected in _folders:
        _folders.remove(selected)
        dpg.configure_item("folder_list", items=_folders)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def _log(msg: str) -> None:
    current = dpg.get_value("log")
    dpg.set_value("log", current + msg + "\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_preview() -> bool:
    return dpg.get_value("mode_radio") == "Preview (dry run)"


def _media_files(folder: Path) -> list[Path]:
    return sorted(
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
    )


def _apply_or_preview(media_file: Path, date_str: str, preview: bool) -> None:
    if preview:
        xmp_path = media_file.with_suffix(".xmp")
        action = "update" if xmp_path.exists() else "create"
        _log(f"  [preview] {media_file.name}  ->  {date_str}  ({action} {xmp_path.name})")
    else:
        apply_date_to_xmp(media_file, date_str)
        _log(f"  [ok]      {media_file.name}  ->  {date_str}")


# ---------------------------------------------------------------------------
# Action callbacks
# ---------------------------------------------------------------------------

def _apply_folder_date() -> None:
    if not _folders:
        _log("No folders selected.")
        return

    preview = _is_preview()
    mode_label = "PREVIEW" if preview else "APPLY"

    for folder_str in _folders:
        folder = Path(folder_str)
        parsed = find_date_in_name(folder.name)

        if not parsed:
            _log(f"[{mode_label}] SKIP folder {folder.name!r}: cannot parse date")
            continue

        date_str = format_xmp_date(parsed)
        _log(f"[{mode_label}] Folder {folder.name!r}  ->  {date_str}")

        files = _media_files(folder)
        if not files:
            _log("  (no matching media files)")
            continue

        count = 0
        for media_file in files:
            try:
                _apply_or_preview(media_file, date_str, preview)
                count += 1
            except Exception as exc:
                _log(f"  [err]     {media_file.name}: {exc}")

        _log(f"  {count} file(s) {'would be' if preview else ''} updated.\n")


def _apply_file_date() -> None:
    if not _folders:
        _log("No folders selected.")
        return

    preview = _is_preview()
    mode_label = "PREVIEW" if preview else "APPLY"

    for folder_str in _folders:
        folder = Path(folder_str)
        _log(f"[{mode_label}] Folder {folder.name!r}")

        files = _media_files(folder)
        if not files:
            _log("  (no matching media files)")
            continue

        count = 0
        for media_file in files:
            parsed = find_date_in_name(media_file.stem)
            if not parsed:
                _log(f"  [skip]    {media_file.name}: no date found in filename")
                continue

            date_str = format_xmp_date(parsed)
            try:
                _apply_or_preview(media_file, date_str, preview)
                count += 1
            except Exception as exc:
                _log(f"  [err]     {media_file.name}: {exc}")

        _log(f"  {count} file(s) {'would be' if preview else ''} updated.\n")
