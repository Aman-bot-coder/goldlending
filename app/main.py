"""
Gold & Silver Loan Management System — Application Entry Point.
Sets up logging, loads stylesheet, shows login window, launches main window.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


def setup_logging():
    from app.config import LOG_DIR
    log_file = LOG_DIR / "app.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_stylesheet(app) -> None:
    qss_path = Path(__file__).parent.parent / "assets" / "styles" / "main.qss"
    if qss_path.exists():
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())


def main():
    setup_logging()
    logger = logging.getLogger("main")
    logger.info("Starting Gold & Silver Loan Management System")

    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont

    app = QApplication(sys.argv)
    app.setApplicationName("Gold Silver Loan Manager")
    app.setOrganizationName("GoldSilverLoan")

    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    load_stylesheet(app)

    from PySide6.QtWidgets import QDialog
    from app.database.connection import close_db, auto_backup_if_due

    app.aboutToQuit.connect(close_db)
    windows: dict = {}

    def show_login() -> bool:
        from app.ui.login_window import LoginWindow
        from app.ui.main_window import MainWindow

        login_win = LoginWindow()
        if login_win.exec() != QDialog.DialogCode.Accepted:
            return False

        try:
            auto_backup_if_due()
        except Exception:
            logger.exception("Automatic backup failed")

        main_win = MainWindow()
        main_win.logout_requested.connect(on_logout)
        windows["main"] = main_win
        main_win.show()
        return True

    def on_logout():
        if not show_login():
            app.quit()

    if not show_login():
        close_db()
        sys.exit(0)
    sys.exit(app.exec())


if __name__ == "__main__":
    # Ensure src is on path when running directly
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
