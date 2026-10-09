"""Professional login window with SSH connection setup."""
from __future__ import annotations

import logging

from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QCheckBox, QMessageBox, QProgressBar,
    QStackedWidget, QFormLayout, QGroupBox, QApplication,
)

logger = logging.getLogger(__name__)


class DBConnectWorker(QObject):
    success = Signal()
    error = Signal(str)

    def __init__(self, ssh_password: str = "", ssh_key: str = ""):
        super().__init__()
        self._ssh_password = ssh_password
        self._ssh_key = ssh_key

    def run(self):
        try:
            from app.database.connection import init_db
            init_db(ssh_password=self._ssh_password, ssh_key_path=self._ssh_key)
            self.success.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class LoginWindow(QDialog):
    login_successful = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gold & Silver Loan Management System — Login")
        self.setFixedSize(900, 580)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.MSWindowsFixedSizeDialogHint)
        self._db_connected = False
        self._thread: QThread = None
        self._worker: DBConnectWorker = None
        self._setup_ui()

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

        # Right panel — stacked: DB setup → login
        right = QFrame()
        right.setStyleSheet("background-color: #F8F9FA;")
        right_layout = QVBoxLayout(right)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.setContentsMargins(50, 40, 50, 40)

        self.stack = QStackedWidget()
        right_layout.addWidget(self.stack)

        self._build_db_page()
        self._build_login_page()

        main_layout.addWidget(right)

    # -------- DB connection page --------
    def _build_db_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(16)

        title = QLabel("Database Connection")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1A1A2E;")
        layout.addWidget(title)
        subtitle = QLabel("Configure SSH tunnel and MySQL connection settings")
        subtitle.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        grp = QGroupBox("SSH Tunnel Settings")
        grp.setStyleSheet("QGroupBox { font-weight: 700; } QGroupBox::title { color: #1A1A2E; }")
        form = QFormLayout(grp)
        form.setSpacing(10)

        from app.config import get_config
        cfg = get_config()

        self.ssh_host = QLineEdit(cfg.ssh_host)
        self.ssh_port = QLineEdit(str(cfg.ssh_port))
        self.ssh_user = QLineEdit(cfg.ssh_username)
        self.ssh_pass = QLineEdit()
        self.ssh_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.ssh_pass.setPlaceholderText("SSH password or leave blank for key auth")
        self.db_name = QLineEdit(cfg.db_name)
        self.db_user = QLineEdit(cfg.db_user)
        self.db_pass = QLineEdit()
        self.db_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.db_pass.setPlaceholderText("MySQL password")

        form.addRow("SSH Host:", self.ssh_host)
        form.addRow("SSH Port:", self.ssh_port)
        form.addRow("SSH User:", self.ssh_user)
        form.addRow("SSH Password:", self.ssh_pass)
        form.addRow("Database Name:", self.db_name)
        form.addRow("DB User:", self.db_user)
        form.addRow("DB Password:", self.db_pass)
        layout.addWidget(grp)

        self.db_progress = QProgressBar()
        self.db_progress.setRange(0, 0)
        self.db_progress.setVisible(False)
        self.db_progress.setFixedHeight(6)
        layout.addWidget(self.db_progress)

        self.db_status_lbl = QLabel("")
        self.db_status_lbl.setStyleSheet("color: #DC3545; font-size: 12px;")
        self.db_status_lbl.setWordWrap(True)
        layout.addWidget(self.db_status_lbl)

        connect_btn = QPushButton("Connect to Database")
        connect_btn.setFixedHeight(40)
        connect_btn.clicked.connect(self._do_connect)
        layout.addWidget(connect_btn)

        layout.addStretch()
        self.stack.addWidget(page)

    def _do_connect(self):
        from app.config import get_config
        cfg = get_config()
        # Save updated settings
        cfg.update({
            "ssh_host": self.ssh_host.text().strip(),
            "ssh_port": int(self.ssh_port.text().strip() or "56022"),
            "ssh_username": self.ssh_user.text().strip(),
            "db_name": self.db_name.text().strip(),
            "db_user": self.db_user.text().strip(),
            "db_password": self.db_pass.text(),
        })

        self.db_progress.setVisible(True)
        self.db_status_lbl.setText("Connecting...")
        self.db_status_lbl.setStyleSheet("color: #0056B3; font-size: 12px;")

        self._thread = QThread()
        self._worker = DBConnectWorker(
            ssh_password=self.ssh_pass.text(),
            ssh_key="",
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.success.connect(self._on_db_success)
        self._worker.error.connect(self._on_db_error)
        self._thread.start()

    def _on_db_success(self):
        self._thread.quit()
        self._thread.wait()
        self.db_progress.setVisible(False)
        self._db_connected = True
        # Seed first admin if needed
        self._ensure_admin()
        self.stack.setCurrentIndex(1)

    def _on_db_error(self, msg: str):
        self._thread.quit()
        self._thread.wait()
        self.db_progress.setVisible(False)
        self.db_status_lbl.setText(f"Connection failed: {msg}")
        self.db_status_lbl.setStyleSheet("color: #DC3545; font-size: 12px;")

    def _ensure_admin(self):
        """Create default admin account if no users exist."""
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

        # Username
        layout.addWidget(QLabel("Username / Email"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username or email")
        self.username_input.setFixedHeight(40)
        layout.addWidget(self.username_input)

        # Password
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

        db_settings_btn = QPushButton("Change Database Settings")
        db_settings_btn.setObjectName("SecondaryBtn")
        db_settings_btn.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        layout.addWidget(db_settings_btn)

        layout.addStretch()
        hint = QLabel("Default: admin / Admin@1234  (change on first login)")
        hint.setStyleSheet("color: #AAA; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hint)

        self.stack.addWidget(page)

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            self.login_error_lbl.setText("Please enter username and password.")
            return

        self.login_progress.setVisible(True)
        self.login_error_lbl.setText("")
        QApplication.processEvents()

        from app.services.auth_service import get_auth_service
        from app.ui.session_state import session
        from app.config import get_config

        success, message, user = get_auth_service().login(username, password)

        self.login_progress.setVisible(False)

        if success and user:
            cfg = get_config()
            session.login(
                user_id=user.id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
                timeout_minutes=cfg.session_timeout_minutes,
            )
            from app.utils.security import init_encryption
            init_encryption()
            self.login_successful.emit()
            self.accept()
        else:
            self.login_error_lbl.setText(message)

    def showEvent(self, event):
        super().showEvent(event)
        # If DB already connected (e.g. relogin), skip to login page
        if self._db_connected:
            self.stack.setCurrentIndex(1)
