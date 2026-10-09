"""Backup & Restore page."""
from __future__ import annotations

import os
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QMessageBox, QFrame, QProgressBar,
)


class BackupPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Backup & Restore")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        # Backup section
        backup_frame = QFrame()
        backup_frame.setObjectName("Card")
        backup_layout = QVBoxLayout(backup_frame)
        backup_layout.setSpacing(12)

        backup_title = QLabel("📦 Export Backup")
        backup_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        backup_layout.addWidget(backup_title)

        backup_desc = QLabel(
            "Export all loan data, customers, repayments and collateral to a SQL file.\n"
            "Store the backup file in a safe location (USB drive, Google Drive, etc.)"
        )
        backup_desc.setStyleSheet("color: #666; font-size: 13px;")
        backup_desc.setWordWrap(True)
        backup_layout.addWidget(backup_desc)

        self.backup_status = QLabel("")
        self.backup_status.setStyleSheet("color: #28A745; font-size: 12px;")
        backup_layout.addWidget(self.backup_status)

        backup_btn = QPushButton("💾 Export Backup Now")
        backup_btn.setFixedHeight(40)
        backup_btn.setFixedWidth(200)
        backup_btn.clicked.connect(self._do_backup)
        backup_layout.addWidget(backup_btn)

        layout.addWidget(backup_frame)

        # Auto-backup info
        info_frame = QFrame()
        info_frame.setObjectName("Card")
        info_layout = QVBoxLayout(info_frame)

        info_title = QLabel("📁 Backup Location")
        info_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        info_layout.addWidget(info_title)

        from app.config import BACKUP_DIR
        self.backup_dir_lbl = QLabel(f"Auto-backup folder: {BACKUP_DIR}")
        self.backup_dir_lbl.setStyleSheet("color: #666; font-size: 12px;")
        self.backup_dir_lbl.setWordWrap(True)
        info_layout.addWidget(self.backup_dir_lbl)

        open_folder_btn = QPushButton("📂 Open Backup Folder")
        open_folder_btn.setObjectName("SecondaryBtn")
        open_folder_btn.setFixedWidth(200)
        open_folder_btn.clicked.connect(self._open_backup_folder)
        info_layout.addWidget(open_folder_btn)

        layout.addWidget(info_frame)

        # Restore section
        restore_frame = QFrame()
        restore_frame.setObjectName("Card")
        restore_layout = QVBoxLayout(restore_frame)
        restore_layout.setSpacing(12)

        restore_title = QLabel("♻️ Restore from Backup")
        restore_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        restore_layout.addWidget(restore_title)

        restore_warn = QLabel(
            "⚠ Warning: Restoring will overwrite current data. "
            "Make sure to export a fresh backup first."
        )
        restore_warn.setStyleSheet("color: #DC3545; font-size: 12px;")
        restore_warn.setWordWrap(True)
        restore_layout.addWidget(restore_warn)

        restore_desc = QLabel(
            "Select a .sql backup file exported from this application.\n"
            "Contact your administrator for database restore assistance."
        )
        restore_desc.setStyleSheet("color: #666; font-size: 13px;")
        restore_desc.setWordWrap(True)
        restore_layout.addWidget(restore_desc)

        restore_btn = QPushButton("♻ Restore from SQL File")
        restore_btn.setFixedHeight(40)
        restore_btn.setFixedWidth(200)
        restore_btn.setObjectName("SecondaryBtn")
        restore_btn.clicked.connect(self._do_restore)
        restore_layout.addWidget(restore_btn)

        layout.addWidget(restore_frame)
        layout.addStretch()

    def _do_backup(self):
        from app.config import get_config, BACKUP_DIR
        from app.ui.session_state import session
        if not session.is_admin:
            QMessageBox.warning(self, "Unauthorized", "Only admins can export backups.")
            return

        cfg = get_config()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"goldloan_backup_{timestamp}.sql"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", str(BACKUP_DIR / default_name), "SQL Files (*.sql)"
        )
        if not path:
            return

        self.backup_status.setText("Exporting...")
        self.backup_status.setStyleSheet("color: #FFC107; font-size: 12px;")

        try:
            host = cfg.db_host
            port = cfg.db_port
            user = cfg.db_user
            password = cfg.db_password
            db = cfg.db_name

            import subprocess
            cmd = [
                "mysqldump",
                f"--host={host}",
                f"--port={port}",
                f"--user={user}",
                f"--password={password}",
                "--single-transaction",
                "--routines",
                "--triggers",
                db,
            ]
            with open(path, "w", encoding="utf-8") as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=120)

            if result.returncode == 0:
                size_kb = os.path.getsize(path) // 1024
                self.backup_status.setText(f"✅ Backup saved: {os.path.basename(path)} ({size_kb} KB)")
                self.backup_status.setStyleSheet("color: #28A745; font-size: 12px;")
            else:
                err = result.stderr.decode(errors="replace")
                self.backup_status.setText(f"⚠ mysqldump error — trying CSV export...")
                self.backup_status.setStyleSheet("color: #FFC107; font-size: 12px;")
                self._csv_fallback(path.replace(".sql", ""))
        except FileNotFoundError:
            self.backup_status.setText("⚠ mysqldump not found — exporting as CSV instead...")
            self.backup_status.setStyleSheet("color: #FFC107; font-size: 12px;")
            self._csv_fallback(path.replace(".sql", ""))
        except Exception as exc:
            self.backup_status.setText(f"❌ Error: {exc}")
            self.backup_status.setStyleSheet("color: #DC3545; font-size: 12px;")

    def _csv_fallback(self, base_path: str):
        """Export key tables as CSV files."""
        try:
            import csv
            from app.database.connection import get_session
            from app.models.loan import Loan
            from app.models.customer import Customer
            from app.models.repayment import Repayment
            from app.models.collateral import CollateralItem

            os.makedirs(base_path, exist_ok=True)

            exports = [
                ("customers.csv", Customer, ["id", "customer_id", "full_name", "mobile", "city", "created_at"]),
                ("loans.csv", Loan, ["id", "loan_number", "customer_id", "principal_amount",
                                     "disbursed_amount", "outstanding_principal", "status",
                                     "interest_rate", "disbursement_date", "maturity_date"]),
                ("repayments.csv", Repayment, ["id", "receipt_number", "loan_id", "total_paid",
                                               "principal_paid", "interest_paid", "payment_date",
                                               "payment_mode"]),
                ("collateral.csv", CollateralItem, ["id", "loan_id", "metal_type", "item_category",
                                                    "gross_weight", "net_weight", "purity",
                                                    "tag_number", "is_released"]),
            ]

            with get_session() as session:
                for filename, Model, cols in exports:
                    filepath = os.path.join(base_path, filename)
                    rows = session.query(Model).all()
                    with open(filepath, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(cols)
                        for row in rows:
                            writer.writerow([getattr(row, c, "") for c in cols])

            self.backup_status.setText(f"✅ CSV backup saved to: {base_path}/")
            self.backup_status.setStyleSheet("color: #28A745; font-size: 12px;")
        except Exception as exc:
            self.backup_status.setText(f"❌ CSV export error: {exc}")
            self.backup_status.setStyleSheet("color: #DC3545; font-size: 12px;")

    def _do_restore(self):
        from app.ui.session_state import session
        if not session.is_admin:
            QMessageBox.warning(self, "Unauthorized", "Only admins can restore backups.")
            return

        confirm = QMessageBox.question(
            self, "Confirm Restore",
            "This will overwrite current data with the backup.\n\nAre you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        path, _ = QFileDialog.getOpenFileName(self, "Select Backup SQL", "", "SQL Files (*.sql)")
        if not path:
            return

        from app.config import get_config
        cfg = get_config()
        try:
            import subprocess
            cmd = [
                "mysql",
                f"--host={cfg.db_host}",
                f"--port={cfg.db_port}",
                f"--user={cfg.db_user}",
                f"--password={cfg.db_password}",
                cfg.db_name,
            ]
            with open(path, "r", encoding="utf-8") as f:
                result = subprocess.run(cmd, stdin=f, stderr=subprocess.PIPE, timeout=300)

            if result.returncode == 0:
                QMessageBox.information(self, "Restore Complete", "Database restored successfully. Please restart the application.")
            else:
                err = result.stderr.decode(errors="replace")
                QMessageBox.critical(self, "Restore Failed", f"mysql error:\n{err[:500]}")
        except FileNotFoundError:
            QMessageBox.critical(self, "Error", "mysql client not found on this system.\nRestore must be done manually via MySQL Workbench or TablePlus.")
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def _open_backup_folder(self):
        from app.config import BACKUP_DIR
        import subprocess, sys
        if sys.platform == "win32":
            os.startfile(str(BACKUP_DIR))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(BACKUP_DIR)])
        else:
            subprocess.Popen(["xdg-open", str(BACKUP_DIR)])
