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

    def show_login():
        from app.ui.login_window import LoginWindow
        login_win = LoginWindow()

        def on_login_success():
            from app.ui.main_window import MainWindow
            main_win = MainWindow()
            main_win.logout_requested.connect(show_login)
            main_win.show()

        login_win.login_successful.connect(on_login_success)
        login_win.exec()

    show_login()
    sys.exit(app.exec())


if __name__ == "__main__":
    # Ensure src is on path when running directly
    sys.path.insert(0, str(Path(__file__).parent.parent))
    main()
