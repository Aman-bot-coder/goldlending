"""Backup & Restore page for the local SQLite database."""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QMessageBox, QFrame,
)

from app.ui.widgets.data_table import DataTable


class BackupPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _card(self, title: str, desc: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("Card")
        lay = QVBoxLayout(frame)
        lay.setSpacing(10)
        t = QLabel(title)
        t.setStyleSheet("font-size: 16px; font-weight: 700;")
        lay.addWidget(t)
        d = QLabel(desc)
        d.setStyleSheet("color: #666; font-size: 13px;")
        d.setWordWrap(True)
        lay.addWidget(d)
        return frame, lay

    def _setup_ui(self):
        from app.config import BACKUP_DIR
        from app.database.connection import get_db_path

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Backup & Restore")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        frame, lay = self._card(
            "💾 Export Backup",
            "Save a full copy of all customers, loans, repayments and collateral to a file.\n"
            "Keep it on a USB drive or cloud folder. An automatic backup is also made once a day.",
        )
        self.backup_status = QLabel("")
        self.backup_status.setWordWrap(True)
        lay.addWidget(self.backup_status)
        btn = QPushButton("💾 Export Backup Now")
        btn.setFixedHeight(40)
        btn.setFixedWidth(220)
        btn.clicked.connect(self._do_backup)
        lay.addWidget(btn)
        layout.addWidget(frame)

        frame, lay = self._card(
            "♻️ Restore from Backup",
            "⚠ Restoring replaces ALL current data with the backup. "
            "A safety copy of the current data is saved first.",
        )
        btn = QPushButton("♻ Restore from Backup File")
        btn.setObjectName("SecondaryBtn")
        btn.setFixedHeight(40)
        btn.setFixedWidth(220)
        btn.clicked.connect(self._do_restore)
        lay.addWidget(btn)
        layout.addWidget(frame)

        frame, lay = self._card(
            "📁 Data Location",
            f"Database: {get_db_path()}\nBackups: {BACKUP_DIR}",
        )
        btn = QPushButton("📂 Open Backup Folder")
        btn.setObjectName("SecondaryBtn")
        btn.setFixedWidth(220)
        btn.clicked.connect(self._open_backup_folder)
        lay.addWidget(btn)
        layout.addWidget(frame)

        recent = QLabel("Backups in folder")
        recent.setObjectName("SectionTitle")
        layout.addWidget(recent)
        self.table = DataTable(["File", "Size", "Created"], searchable=False)
        layout.addWidget(self.table, 1)

    def refresh(self):
        from app.config import BACKUP_DIR
        files = sorted(BACKUP_DIR.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        rows = [
            [
                f.name,
                f"{max(1, f.stat().st_size // 1024)} KB",
                datetime.fromtimestamp(f.stat().st_mtime).strftime("%d-%m-%Y %H:%M"),
            ]
            for f in files[:50]
        ]
        self.table.load_data(rows)

    def _status(self, text: str, ok: bool):
        self.backup_status.setText(text)
        self.backup_status.setStyleSheet(
            f"color: {'#28A745' if ok else '#DC3545'}; font-size: 12px;"
        )

    def _do_backup(self):
        from app.config import BACKUP_DIR
        from app.database.connection import backup_to
        from app.ui.session_state import session
        if not session.is_admin:
            QMessageBox.warning(self, "Unauthorized", "Only admins can export backups.")
            return

        default = BACKUP_DIR / f"goldloan_backup_{datetime.now():%Y%m%d_%H%M%S}.db"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", str(default), "Backup Files (*.db)"
        )
        if not path:
            return
        if not path.lower().endswith(".db"):
            path += ".db"
        try:
            dest = backup_to(Path(path))
            size_kb = max(1, dest.stat().st_size // 1024)
            self._status(f"✅ Backup saved: {dest} ({size_kb} KB)", True)
            self._log_backup(str(dest), dest.stat().st_size, "success", None)
        except Exception as exc:
            self._status(f"❌ Backup failed: {exc}", False)
            self._log_backup(path, None, "failed", str(exc))
        self.refresh()

    def _log_backup(self, path, size, status, error):
        try:
            from app.database.connection import get_session
            from app.models.app_settings import BackupHistory
            from app.ui.session_state import session
            with get_session() as s:
                s.add(BackupHistory(
                    backup_path=path, backup_type="manual", status=status,
                    file_size_bytes=size, error_message=error, created_by=session.user_id,
                ))
        except Exception:
            pass

    def _do_restore(self):
        from app.config import BACKUP_DIR
        from app.database.connection import restore_from, validate_backup_file
        from app.ui.session_state import session
        if not session.is_admin:
            QMessageBox.warning(self, "Unauthorized", "Only admins can restore backups.")
            return

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Backup", str(BACKUP_DIR), "Backup Files (*.db)"
        )
        if not path:
            return
        err = validate_backup_file(Path(path))
        if err:
            QMessageBox.critical(self, "Invalid Backup", err)
            return

        confirm = QMessageBox.question(
            self, "Confirm Restore",
            f"Replace ALL current data with:\n{os.path.basename(path)}\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            restore_from(Path(path))
        except Exception as exc:
            QMessageBox.critical(self, "Restore Failed", str(exc))
            return
        QMessageBox.information(
            self, "Restore Complete",
            "Data restored successfully. You will now be logged out — please sign in again.",
        )
        win = self.window()
        if hasattr(win, "_logout"):
            win._logout()

    def _open_backup_folder(self):
        from app.config import BACKUP_DIR
        if sys.platform == "win32":
            os.startfile(str(BACKUP_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(BACKUP_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(BACKUP_DIR)])

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
