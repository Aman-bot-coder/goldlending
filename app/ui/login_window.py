"""Login window — opens the local database and asks for username/password."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QProgressBar, QFormLayout, QMessageBox,
)

logger = logging.getLogger(__name__)


class LoginWorker(QObject):
    success = Signal(object)
    error = Signal(str)

    def __init__(self, username: str, password: str):
        super().__init__()
        self._username = username
        self._password = password

    def run(self):
        try:
            from app.services.auth_service import get_auth_service
            ok, msg, user = get_auth_service().login(self._username, self._password)
            if ok and user:
                self.success.emit(user)
            else:
                self.error.emit(msg)
        except Exception as exc:
            logger.exception("Login worker error")
            self.error.emit(f"Login error: {exc}")


class ChangePasswordDialog(QDialog):
    """Forced on first login when the account still uses its initial password."""

    def __init__(self, user_id: int, current_password: str, parent=None):
        super().__init__(parent)
        self._user_id = user_id
        self._current = current_password
        self.setWindowTitle("Set a New Password")
        self.setMinimumWidth(420)

        lay = QVBoxLayout(self)
        info = QLabel("For security, please set your own password before continuing.\n"
                      "Minimum 8 characters with upper-case, lower-case and a digit.")
        info.setWordWrap(True)
        lay.addWidget(info)

        form = QFormLayout()
        self.new_pw = QLineEdit()
        self.new_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw = QLineEdit()
        self.confirm_pw.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_pw.returnPressed.connect(self._save)
        form.addRow("New Password:", self.new_pw)
        form.addRow("Confirm Password:", self.confirm_pw)
        lay.addLayout(form)

        self.err = QLabel("")
        self.err.setStyleSheet("color: #DC3545; font-size: 12px;")
        self.err.setWordWrap(True)
        lay.addWidget(self.err)

        btn = QPushButton("Save Password")
        btn.setFixedHeight(38)
        btn.clicked.connect(self._save)
        lay.addWidget(btn)

    def _save(self):
        new, confirm = self.new_pw.text(), self.confirm_pw.text()
        if new != confirm:
            self.err.setText("Passwords do not match.")
            return
        if new == self._current:
            self.err.setText("New password must be different from the current one.")
            return
        from app.services.auth_service import get_auth_service
        ok, msg = get_auth_service().change_password(self._user_id, self._current, new)
        if not ok:
            self.err.setText(msg)
            return
        self.accept()


class LoginWindow(QDialog):
    login_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gold & Silver Loan Management System")
        self.setFixedSize(900, 560)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self._login_thread: Optional[QThread] = None
        self._login_worker: Optional[LoginWorker] = None
        self._pending_password = ""
        self._setup_ui()
        self._open_database()

    def _open_database(self):
        from app.database.connection import init_db, get_engine
        try:
            get_engine()
        except RuntimeError:
            try:
                init_db()
            except Exception as exc:
                logger.exception("Database init failed")
                self.login_error_lbl.setText(f"Could not open local database: {exc}")
                self.login_btn.setEnabled(False)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        left = QFrame()
        left.setFixedWidth(420)
        left.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:0,y2:1,"
            "stop:0 #1A1A2E, stop:1 #2D2D44);"
        )
        left_layout = QVBoxLayout(left)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.setSpacing(12)
        left_layout.setContentsMargins(40, 40, 40, 40)

        logo_lbl = QLabel("⚜")
        logo_lbl.setStyleSheet("font-size: 56px; color: #FFD700;")
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(logo_lbl)

        app_title = QLabel("Gold & Silver\nLoan Manager")
        app_title.setStyleSheet("font-size: 24px; font-weight: 800; color: #FFD700;")
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(app_title)

        tagline = QLabel("Professional Collateral Lending\nManagement System")
        tagline.setStyleSheet("font-size: 13px; color: #C0C0C0;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(tagline)

        left_layout.addStretch()
        for feat in [
            "• Works fully offline",
            "• Complete Loan Lifecycle",
            "• KYC & Customer Management",
            "• PDF Reports & Receipts",
            "• Secure Audit Trail",
        ]:
            fl = QLabel(feat)
            fl.setStyleSheet("font-size: 12px; color: #AAAAAA;")
            left_layout.addWidget(fl)

        left_layout.addSpacing(20)
        from app.config import APP_VERSION
        version_lbl = QLabel(f"Version {APP_VERSION}")
        version_lbl.setStyleSheet("font-size: 11px; color: #666;")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(version_lbl)
        main_layout.addWidget(left)

        right = QFrame()
        right.setStyleSheet("background-color: #F8F9FA;")
        layout = QVBoxLayout(right)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(50, 40, 50, 40)
        layout.setSpacing(16)

        title = QLabel("Welcome Back")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #1A1A2E;")
        layout.addWidget(title)
        subtitle = QLabel("Sign in to continue")
        subtitle.setStyleSheet("font-size: 13px; color: #888;")
        layout.addWidget(subtitle)
        layout.addSpacing(16)

        layout.addWidget(QLabel("Username / Email"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username or email")
        self.username_input.setFixedHeight(40)
        self.username_input.returnPressed.connect(lambda: self.password_input.setFocus())
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Password"))
        pw_row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setFixedHeight(40)
        self.password_input.returnPressed.connect(self._do_login)
        pw_row.addWidget(self.password_input)
        show_pw_btn = QPushButton("👁")
        show_pw_btn.setFixedSize(40, 40)
        show_pw_btn.setObjectName("SecondaryBtn")
        show_pw_btn.pressed.connect(lambda: self.password_input.setEchoMode(QLineEdit.EchoMode.Normal))
        show_pw_btn.released.connect(lambda: self.password_input.setEchoMode(QLineEdit.EchoMode.Password))
        pw_row.addWidget(show_pw_btn)
        layout.addLayout(pw_row)

        self.login_error_lbl = QLabel("")
        self.login_error_lbl.setStyleSheet("color: #DC3545; font-size: 12px;")
        self.login_error_lbl.setWordWrap(True)
        layout.addWidget(self.login_error_lbl)

        self.login_progress = QProgressBar()
        self.login_progress.setRange(0, 0)
        self.login_progress.setVisible(False)
        self.login_progress.setFixedHeight(4)
        layout.addWidget(self.login_progress)

        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(44)
        self.login_btn.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.login_btn.clicked.connect(self._do_login)
        layout.addWidget(self.login_btn)

        layout.addStretch()
        main_layout.addWidget(right)

    def _set_busy(self, busy: bool):
        self.login_progress.setVisible(busy)
        self.login_btn.setEnabled(not busy)

    def _do_login(self):
        if self._login_thread is not None:
            return
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            self.login_error_lbl.setText("Please enter username and password.")
            return

        self._set_busy(True)
        self.login_error_lbl.setText("")
        self._pending_password = password

        self._login_thread = QThread()
        self._login_worker = LoginWorker(username, password)
        self._login_worker.moveToThread(self._login_thread)
        self._login_thread.started.connect(self._login_worker.run)
        self._login_worker.success.connect(self._on_login_success)
        self._login_worker.error.connect(self._on_login_error)
        self._login_thread.start()

    def _finish_thread(self):
        if self._login_thread is not None:
            self._login_thread.quit()
            self._login_thread.wait()
        self._login_thread = None
        self._login_worker = None
        self._set_busy(False)

    def _on_login_success(self, user):
        self._finish_thread()
        password, self._pending_password = self._pending_password, ""

        if user.must_change_password:
            dlg = ChangePasswordDialog(user.id, password, self)
            if not dlg.exec():
                self.password_input.clear()
                self.login_error_lbl.setText("You must set a new password to continue.")
                return

        from app.ui.session_state import session
        from app.config import get_config
        from app.utils.security import init_encryption

        session.login(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            timeout_minutes=get_config().session_timeout_minutes,
        )
        init_encryption()
        self.login_successful.emit()
        self.accept()

    def _on_login_error(self, message: str):
        self._finish_thread()
        self._pending_password = ""
        self.login_error_lbl.setText(message)
