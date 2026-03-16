"""NeatXMP — Dear PyGui front-end for stamping XMP sidecar dates."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import dearpygui.dearpygui as dpg

from .date_parser import find_date_in_name, format_xmp_date
from .settings import load as load_settings, save as save_settings
from .xmp_reader import read_all_xmp_fields, read_xmp_dates
from .xmp_writer import apply_date_to_xmp

MEDIA_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov"})

_folder: str = ""


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    dpg.create_context()

    with dpg.file_dialog(
        directory_selector=True,
        show=False,
        callback=_on_folder_selected,
        tag="folder_dialog",
        width=700,
        height=450,
    ):
        pass

    _settings = load_settings()
    global _folder
    _folder = _settings.get("last_folder", "")

    with dpg.window(label="NeatXMP", tag="primary_window"):

        # --- Folder selector ---
        dpg.add_text("Folder")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Browse...", callback=_browse)
            dpg.add_text(_folder or "(none)", tag="folder_display")

        dpg.add_spacer(height=8)
        dpg.add_separator()
        dpg.add_spacer(height=8)

        # --- Mode toggle ---
        dpg.add_text("Mode")
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
                label="Scan",
                callback=_scan,
                width=100,
                height=40,
            )
            dpg.add_spacer(width=4)
            dpg.add_button(
                label="Detailed Scan",
                callback=_detailed_scan,
                width=140,
                height=40,
            )
            dpg.add_spacer(width=8)
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
# Folder selection
# ---------------------------------------------------------------------------

def _browse() -> None:
    if _folder:
        dpg.configure_item("folder_dialog", default_path=_folder)
    dpg.show_item("folder_dialog")


def _on_folder_selected(sender: str, app_data: dict) -> None:
    global _folder
    folder = app_data.get("file_path_name", "").strip()
    if not folder:
        return
    _folder = str(Path(folder).resolve())
    dpg.set_value("folder_display", _folder)
    save_settings({"last_folder": _folder})


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


def _current_folder() -> Path | None:
    if not _folder:
        _log("No folder selected.")
        return None
    return Path(_folder)


# ---------------------------------------------------------------------------
# Action callbacks
# ---------------------------------------------------------------------------

def _scan() -> None:
    folder = _current_folder()
    if folder is None:
        return

    files = _media_files(folder)
    _log(f"[SCAN] {folder.name}  ({len(files)} media file(s))\n")

    if not files:
        _log("  (no matching media files)")
        return

    # Gather rows first so we can compute column widths
    rows: list[tuple[str, str, str]] = []
    for media_file in files:
        fs_date = datetime.fromtimestamp(media_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M")

        xmp_path = media_file.with_suffix(".xmp")
        if xmp_path.exists():
            dates = read_xmp_dates(xmp_path)
            xmp_col = "  |  ".join(f"{k}: {v}" for k, v in dates.items()) if dates else "(no dates)"
        else:
            xmp_col = "(no sidecar)"

        rows.append((media_file.name, fs_date, xmp_col))

    # Column widths
    w0 = max(len(r[0]) for r in rows)
    w1 = max(len(r[1]) for r in rows)

    header = f"  {'Filename':<{w0}}  {'FS Modified':<{w1}}  XMP dates"
    _log(header)
    _log("  " + "-" * (len(header) + 4))
    for name, fs_date, xmp_col in rows:
        _log(f"  {name:<{w0}}  {fs_date:<{w1}}  {xmp_col}")
    _log("")


def _detailed_scan() -> None:
    folder = _current_folder()
    if folder is None:
        return

    files = _media_files(folder)
    _log(f"[DETAILED SCAN] {folder.name}  ({len(files)} media file(s))\n")

    if not files:
        _log("  (no matching media files)")
        return

    for media_file in files:
        xmp_path = media_file.with_suffix(".xmp")
        _log(f"  {media_file.name}")

        if not xmp_path.exists():
            _log("    (no XMP sidecar)\n")
            continue

        fields = read_all_xmp_fields(xmp_path)
        if not fields:
            _log("    (sidecar exists but contains no fields)\n")
            continue

        label_width = max(len(label) for label, _ in fields)
        for label, value in fields:
            _log(f"    {label:<{label_width}}  {value}")
        _log("")


def _apply_folder_date() -> None:
    folder = _current_folder()
    if folder is None:
        return

    preview = _is_preview()
    mode_label = "PREVIEW" if preview else "APPLY"

    parsed = find_date_in_name(folder.name)
    if not parsed:
        _log(f"[{mode_label}] SKIP: cannot parse date from folder name {folder.name!r}")
        return

    date_str = format_xmp_date(parsed)
    _log(f"[{mode_label}] {folder.name!r}  ->  {date_str}")

    files = _media_files(folder)
    if not files:
        _log("  (no matching media files)")
        return

    count = 0
    for media_file in files:
        try:
            _apply_or_preview(media_file, date_str, preview)
            count += 1
        except Exception as exc:
            _log(f"  [err]     {media_file.name}: {exc}")

    _log(f"  {count} file(s) {'would be ' if preview else ''}updated.\n")


def _apply_file_date() -> None:
    folder = _current_folder()
    if folder is None:
        return

    preview = _is_preview()
    mode_label = "PREVIEW" if preview else "APPLY"

    _log(f"[{mode_label}] {folder.name!r}")

    files = _media_files(folder)
    if not files:
        _log("  (no matching media files)")
        return

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

    _log(f"  {count} file(s) {'would be ' if preview else ''}updated.\n")
