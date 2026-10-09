"""Simplified login — Activation Key + Username/Password only."""
from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QProgressBar, QStackedWidget, QApplication,
)

logger = logging.getLogger(__name__)

PAGE_ACTIVATE = 0
PAGE_CONNECTING = 1
PAGE_LOGIN = 2


class DBConnectWorker(QObject):
    success = Signal()
    error = Signal(str)

    def __init__(self, host: str, port: int, user: str, password: str, db: str):
        super().__init__()
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._db = db

    def run(self):
        try:
            from app.config import get_config
            get_config().update({
                "use_ssh_tunnel": False,
                "db_host": self._host,
                "db_port": self._port,
                "db_user": self._user,
                "db_password": self._password,
                "db_name": self._db,
            })
            from app.database.connection import init_db
            init_db()
            self.success.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class LoginWorker(QObject):
    success = Signal(object)   # emits User object
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


class LoginWindow(QDialog):
    login_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gold & Silver Loan Management System")
        self.setFixedSize(900, 560)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self._thread: QThread = None
        self._worker: DBConnectWorker = None
        self._login_thread: Optional[QThread] = None
        self._login_worker: Optional[LoginWorker] = None
        self._setup_ui()

        # Auto-connect if already activated
        from app.config import get_config
        cfg = get_config()
        if cfg.db_host and cfg.db_password and not cfg.use_ssh_tunnel:
            QTimer.singleShot(200, self._auto_connect)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left branding panel
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
        app_title.setStyleSheet(
            "font-size: 24px; font-weight: 800; color: #FFD700; text-align: center;"
        )
        app_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(app_title)

        tagline = QLabel("Professional Collateral Lending\nManagement System")
        tagline.setStyleSheet("font-size: 13px; color: #C0C0C0; text-align: center;")
        tagline.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(tagline)

        left_layout.addStretch()

        features = [
            "• Live Gold & Silver Rates",
            "• Complete Loan Lifecycle",
            "• KYC & Customer Management",
            "• PDF Reports & Receipts",
            "• Secure Audit Trail",
        ]
        for feat in features:
            fl = QLabel(feat)
            fl.setStyleSheet("font-size: 12px; color: #AAAAAA;")
            left_layout.addWidget(fl)

        left_layout.addSpacing(20)
        version_lbl = QLabel("Version 1.0.0")
        version_lbl.setStyleSheet("font-size: 11px; color: #666;")
        version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(version_lbl)

        main_layout.addWidget(left)

        # Right panel — stacked: DB setup (0) → auto-connecting (1) → login (2)
        right = QFrame()
        right.setStyleSheet("background-color: #F8F9FA;")
        right_layout = QVBoxLayout(right)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.setContentsMargins(50, 40, 50, 40)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)

        self._build_activate_page()   # index 0 — Activation Key (first time)
        self._build_connecting_page() # index 1 — Connecting spinner
        self._build_login_page()      # index 2 — Username/Password

        main_layout.addWidget(right)

    # -------- Page 0: Activation Key --------
    def _build_activate_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)

        h = QLabel("Activate Your Account")
        h.setStyleSheet("font-size: 22px; font-weight: 800; color: #1A1A2E;")
        lay.addWidget(h)
        sub = QLabel("Enter the details provided by your administrator")
        sub.setStyleSheet("font-size: 12px; color: #888;")
        lay.addWidget(sub)
        lay.addSpacing(8)

        lay.addWidget(self._field_label("Business / Company Name"))
        self.business_input = QLineEdit()
        self.business_input.setPlaceholderText("e.g. Sharma Gold Lending")
        self.business_input.setFixedHeight(42)
        lay.addWidget(self.business_input)

        lay.addWidget(self._field_label("Activation Key"))
        self.act_key_input = QLineEdit()
        self.act_key_input.setPlaceholderText("Paste your activation key here")
        self.act_key_input.setFixedHeight(42)
        self.act_key_input.returnPressed.connect(self._do_activate)
        lay.addWidget(self.act_key_input)

        self.act_error = QLabel("")
        self.act_error.setStyleSheet("color: #DC3545; font-size: 12px;")
        self.act_error.setWordWrap(True)
        lay.addWidget(self.act_error)

        btn = QPushButton("Activate & Connect")
        btn.setFixedHeight(44)
        btn.setStyleSheet("font-size: 15px; font-weight: 700;")
        btn.clicked.connect(self._do_activate)
        lay.addWidget(btn)

        lay.addStretch()
        note = QLabel("Contact your administrator if you don't have an activation key.")
        note.setStyleSheet("color: #AAA; font-size: 11px;")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(note)

        self.stack.addWidget(page)

    def _do_activate(self):
        from app.utils.activation import decode_activation_key
        from app.config import get_config

        biz = self.business_input.text().strip()
        key = self.act_key_input.text().strip()

        if not biz:
            self.act_error.setText("Please enter your business name.")
            return
        if not key:
            self.act_error.setText("Please enter your activation key.")
            return

        try:
            creds = decode_activation_key(key)
        except ValueError as e:
            self.act_error.setText(str(e))
            return

        self.act_error.setText("")
        get_config().set("business_name", biz)
        self.stack.setCurrentIndex(PAGE_CONNECTING)
        self._start_connect(creds)

    # -------- Page 1: Connecting --------
    def _build_connecting_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.setSpacing(20)

        icon = QLabel("⚜")
        icon.setStyleSheet("font-size: 48px; color: #FFD700;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(icon)

        self.conn_label = QLabel("Connecting...")
        self.conn_label.setStyleSheet("font-size: 16px; font-weight: 600; color: #1A1A2E;")
        self.conn_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self.conn_label)

        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setFixedHeight(6)
        bar.setFixedWidth(260)
        lay.addWidget(bar, alignment=Qt.AlignmentFlag.AlignCenter)

        retry = QPushButton("Re-enter Activation Key")
        retry.setObjectName("SecondaryBtn")
        retry.setFixedWidth(220)
        retry.clicked.connect(self._reset_activation)
        lay.addWidget(retry, alignment=Qt.AlignmentFlag.AlignCenter)

        self.stack.addWidget(page)

    def _reset_activation(self):
        from app.config import get_config
        get_config().update({"db_password": "", "db_host": ""})
        self.act_error.setText("")
        self.stack.setCurrentIndex(PAGE_ACTIVATE)

    def _auto_connect(self):
        from app.config import get_config
        cfg = get_config()
        self.stack.setCurrentIndex(PAGE_CONNECTING)
        self._start_connect({
            "db_host": cfg.db_host, "db_port": cfg.db_port,
            "db_user": cfg.db_user, "db_password": cfg.db_password,
            "db_name": cfg.db_name,
        })

    def _start_connect(self, creds: dict):
        self._thread = QThread()
        self._worker = DBConnectWorker(
            host=creds["db_host"], port=int(creds.get("db_port", 3306)),
            user=creds["db_user"], password=creds["db_password"],
            db=creds["db_name"],
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.success.connect(self._on_db_success)
        self._worker.error.connect(self._on_db_error)
        self._thread.start()

    def _on_db_success(self):
        self._thread.quit()
        self._thread.wait()
        self._ensure_admin()
        self.stack.setCurrentIndex(PAGE_LOGIN)

    def _on_db_error(self, msg: str):
        self._thread.quit()
        self._thread.wait()
        self.conn_label.setText(f"Failed: {msg[:80]}")
        self.stack.setCurrentIndex(PAGE_CONNECTING)

    def _ensure_admin(self):
        try:
            from app.database.connection import get_session
            from app.models.user import User
            from app.utils.security import hash_password, init_encryption
            init_encryption()
            with get_session() as session:
                count = session.query(User).count()
                if count == 0:
                    admin = User(
                        username="admin",
                        email="admin@goldloan.local",
                        full_name="System Administrator",
                        password_hash=hash_password("Admin@1234"),
                        role="admin",
                        must_change_password=True,
                    )
                    session.add(admin)
            logger.info("Default admin created (admin / Admin@1234)")
        except Exception as exc:
            logger.error("Seed admin error: %s", exc)

    # -------- Login page --------
    def _build_login_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
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
        layout.addWidget(self.username_input)

        layout.addWidget(QLabel("Password"))
        pw_row = QHBoxLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setFixedHeight(40)
        self.password_input.returnPressed.connect(self._do_login)
        pw_row.addWidget(self.password_input)
        self.show_pw_btn = QPushButton("👁")
        self.show_pw_btn.setFixedSize(40, 40)
        self.show_pw_btn.setObjectName("SecondaryBtn")
        self.show_pw_btn.pressed.connect(lambda: self.password_input.setEchoMode(QLineEdit.EchoMode.Normal))
        self.show_pw_btn.released.connect(lambda: self.password_input.setEchoMode(QLineEdit.EchoMode.Password))
        pw_row.addWidget(self.show_pw_btn)
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

        login_btn = QPushButton("Sign In")
        login_btn.setFixedHeight(44)
        login_btn.setStyleSheet("font-size: 15px; font-weight: 700;")
        login_btn.clicked.connect(self._do_login)
        layout.addWidget(login_btn)

        change_key_btn = QPushButton("Use Different Activation Key")
        change_key_btn.setObjectName("SecondaryBtn")
        change_key_btn.clicked.connect(self._reset_activation)
        layout.addWidget(change_key_btn)

        layout.addStretch()
        self.stack.addWidget(page)

    @staticmethod
    def _field_label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        return lbl

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.login_error_lbl.setText("Please enter username and password.")
            return

        # Disable button to prevent double-click
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Sign In":
                btn.setEnabled(False)

        self.login_progress.setVisible(True)
        self.login_error_lbl.setText("")

        self._login_thread = QThread()
        self._login_worker = LoginWorker(username, password)
        self._login_worker.moveToThread(self._login_thread)
        self._login_thread.started.connect(self._login_worker.run)
        self._login_worker.success.connect(self._on_login_success)
        self._login_worker.error.connect(self._on_login_error)
        self._login_thread.start()

    def _on_login_success(self, user):
        self._login_thread.quit()
        self._login_thread.wait()
        self.login_progress.setVisible(False)
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Sign In":
                btn.setEnabled(True)

        from app.ui.session_state import session
        from app.config import get_config
        from app.utils.security import init_encryption

        cfg = get_config()
        session.login(
            user_id=user.id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            timeout_minutes=cfg.session_timeout_minutes,
        )
        init_encryption()
        self.login_successful.emit()
        self.accept()

    def _on_login_error(self, message: str):
        self._login_thread.quit()
        self._login_thread.wait()
        self.login_progress.setVisible(False)
        for btn in self.findChildren(QPushButton):
            if btn.text() == "Sign In":
                btn.setEnabled(True)
        self.login_error_lbl.setText(message)

    def showEvent(self, event):
        super().showEvent(event)
