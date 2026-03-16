"""NeatXMP — PySide6 front-end for stamping XMP sidecar dates."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .date_parser import find_date_in_name, format_xmp_date
from .settings import load as load_settings, save as save_settings
from .xmp_reader import read_all_xmp_fields, read_xmp_dates
from .xmp_writer import apply_date_to_xmp

MEDIA_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".heic", ".mp4", ".mov"})


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NeatXMP")
        self.resize(920, 740)

        settings = load_settings()
        self._folder: str = settings.get("last_folder", "")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # --- Folder selector ---
        folder_row = QHBoxLayout()
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse)
        browse_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._folder_label = QLabel(self._folder or "(no folder selected)")
        self._folder_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        folder_row.addWidget(browse_btn)
        folder_row.addWidget(self._folder_label, stretch=1)
        root.addLayout(folder_row)

        root.addWidget(_hline())

        # --- Mode toggle ---
        mode_row = QHBoxLayout()
        self._preview_radio = QRadioButton("Preview (dry run)")
        self._apply_radio = QRadioButton("Apply (write files)")
        self._preview_radio.setChecked(True)
        mode_group = QButtonGroup(self)
        mode_group.addButton(self._preview_radio)
        mode_group.addButton(self._apply_radio)
        mode_row.addWidget(QLabel("Mode:"))
        mode_row.addWidget(self._preview_radio)
        mode_row.addWidget(self._apply_radio)
        mode_row.addStretch()
        root.addLayout(mode_row)

        root.addWidget(_hline())

        # --- Action buttons ---
        btn_row = QHBoxLayout()
        for label, slot in (
            ("Scan", self._scan),
            ("Detailed Scan", self._detailed_scan),
            ("Apply Folder Name as Date", self._apply_folder_date),
            ("Apply File Name as Date", self._apply_file_date),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            btn_row.addWidget(btn)
        btn_row.addStretch()
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self._clear_log)
        btn_row.addWidget(clear_btn)
        root.addLayout(btn_row)

        root.addWidget(_hline())

        # --- Log ---
        self._log_widget = QTextEdit()
        self._log_widget.setReadOnly(True)
        fixed_font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        fixed_font.setPointSize(12)
        self._log_widget.setFont(fixed_font)
        root.addWidget(self._log_widget, stretch=1)

    # ------------------------------------------------------------------
    # Folder selection
    # ------------------------------------------------------------------

    def _browse(self) -> None:
        start = self._folder if self._folder else str(Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", start)
        if folder:
            self._folder = folder
            self._folder_label.setText(folder)
            save_settings({"last_folder": folder})

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, msg: str) -> None:
        cursor = self._log_widget.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(msg + "\n")
        self._log_widget.setTextCursor(cursor)
        self._log_widget.ensureCursorVisible()

    def _clear_log(self) -> None:
        self._log_widget.clear()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _is_preview(self) -> bool:
        return self._preview_radio.isChecked()

    def _current_folder(self) -> Path | None:
        if not self._folder:
            self._log("No folder selected.")
            return None
        return Path(self._folder)

    def _media_files(self, folder: Path) -> list[Path]:
        return sorted(
            f for f in folder.iterdir()
            if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS
        )

    def _apply_or_preview(self, media_file: Path, date_str: str, preview: bool) -> None:
        if preview:
            xmp_path = media_file.with_suffix(".xmp")
            action = "update" if xmp_path.exists() else "create"
            self._log(f"  [preview] {media_file.name}  ->  {date_str}  ({action} {xmp_path.name})")
        else:
            apply_date_to_xmp(media_file, date_str)
            self._log(f"  [ok]      {media_file.name}  ->  {date_str}")

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _scan(self) -> None:
        folder = self._current_folder()
        if folder is None:
            return

        files = self._media_files(folder)
        self._log(f"[SCAN] {folder.name}  ({len(files)} media file(s))\n")

        if not files:
            self._log("  (no matching media files)")
            return

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

        w0 = max(len(r[0]) for r in rows)
        w1 = max(len(r[1]) for r in rows)
        header = f"  {'Filename':<{w0}}  {'FS Modified':<{w1}}  XMP dates"
        self._log(header)
        self._log("  " + "-" * (len(header) + 4))
        for name, fs_date, xmp_col in rows:
            self._log(f"  {name:<{w0}}  {fs_date:<{w1}}  {xmp_col}")
        self._log("")

    def _detailed_scan(self) -> None:
        folder = self._current_folder()
        if folder is None:
            return

        files = self._media_files(folder)
        self._log(f"[DETAILED SCAN] {folder.name}  ({len(files)} media file(s))\n")

        if not files:
            self._log("  (no matching media files)")
            return

        for media_file in files:
            xmp_path = media_file.with_suffix(".xmp")
            self._log(f"  {media_file.name}")
            if not xmp_path.exists():
                self._log("    (no XMP sidecar)\n")
                continue
            fields = read_all_xmp_fields(xmp_path)
            if not fields:
                self._log("    (sidecar exists but contains no fields)\n")
                continue
            label_width = max(len(label) for label, _ in fields)
            for label, value in fields:
                self._log(f"    {label:<{label_width}}  {value}")
            self._log("")

    def _apply_folder_date(self) -> None:
        folder = self._current_folder()
        if folder is None:
            return

        preview = self._is_preview()
        mode_label = "PREVIEW" if preview else "APPLY"

        parsed = find_date_in_name(folder.name)
        if not parsed:
            self._log(f"[{mode_label}] SKIP: cannot parse date from folder name {folder.name!r}")
            return

        date_str = format_xmp_date(parsed)
        self._log(f"[{mode_label}] {folder.name!r}  ->  {date_str}")

        files = self._media_files(folder)
        if not files:
            self._log("  (no matching media files)")
            return

        count = 0
        for media_file in files:
            try:
                self._apply_or_preview(media_file, date_str, preview)
                count += 1
            except Exception as exc:
                self._log(f"  [err]     {media_file.name}: {exc}")

        self._log(f"  {count} file(s) {'would be ' if preview else ''}updated.\n")

    def _apply_file_date(self) -> None:
        folder = self._current_folder()
        if folder is None:
            return

        preview = self._is_preview()
        mode_label = "PREVIEW" if preview else "APPLY"

        self._log(f"[{mode_label}] {folder.name!r}")

        files = self._media_files(folder)
        if not files:
            self._log("  (no matching media files)")
            return

        count = 0
        for media_file in files:
            parsed = find_date_in_name(media_file.stem)
            if not parsed:
                self._log(f"  [skip]    {media_file.name}: no date found in filename")
                continue
            date_str = format_xmp_date(parsed)
            try:
                self._apply_or_preview(media_file, date_str, preview)
                count += 1
            except Exception as exc:
                self._log(f"  [err]     {media_file.name}: {exc}")

        self._log(f"  {count} file(s) {'would be ' if preview else ''}updated.\n")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hline() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
