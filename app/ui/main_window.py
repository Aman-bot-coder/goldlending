"""
Main application window with sidebar navigation, top bar,
session timeout, and notification center.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QFont, QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QStatusBar, QMessageBox,
    QSizePolicy, QScrollArea,
)

from app.ui.session_state import session as app_session

logger = logging.getLogger(__name__)

NAV_ITEMS = [
    ("dashboard",         "Dashboard",          "🏠"),
    ("customers",         "Customers & KYC",    "👥"),
    ("new_loan",          "New Loan",            "➕"),
    ("loans",             "Active Loans",        "📋"),
    ("repayments",        "Repayments",          "💳"),
    ("rates",             "Gold & Silver Rates", "📈"),
    ("collateral",        "Collateral Inventory","🔒"),
    ("reports",           "Reports",             "📊"),
    ("users",             "User Management",     "👤"),
    ("audit",             "Audit Logs",          "📝"),
    ("backup",            "Backup & Restore",    "💾"),
    ("settings",          "Settings",            "⚙️"),
]


class SidebarButton(QPushButton):
    def __init__(self, icon: str, label: str, page_key: str, parent=None):
        super().__init__(f"  {icon}  {label}", parent)
        self.page_key = page_key
        self.setObjectName("SidebarBtn")
        self.setCheckable(False)
        self.setMinimumHeight(44)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_active(self, active: bool):
        self.setProperty("active", "true" if active else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class MainWindow(QMainWindow):
    logout_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Gold & Silver Loan Management System")
        self.setMinimumSize(1280, 760)
        self.resize(1400, 820)
        self._pages: Dict[str, QWidget] = {}
        self._sidebar_btns: Dict[str, SidebarButton] = {}
        self._current_page = "dashboard"

        self._setup_ui()
        self._setup_timeout()

        # Auto-update overdue statuses on startup
        QTimer.singleShot(2000, self._update_overdue)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ---- Sidebar ----
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setSpacing(0)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        # Logo
        logo_widget = QWidget()
        logo_widget.setObjectName("SidebarLogo")
        logo_layout = QVBoxLayout(logo_widget)
        logo_layout.setContentsMargins(16, 16, 16, 8)
        logo_layout.setSpacing(2)
        logo_lbl = QLabel("⚜ Gold & Silver")
        logo_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #FFD700;")
        sub_lbl = QLabel("Loan Management")
        sub_lbl.setObjectName("SidebarSubtitle")
        logo_layout.addWidget(logo_lbl)
        logo_layout.addWidget(sub_lbl)
        sidebar_layout.addWidget(logo_widget)

        # Nav buttons
        for page_key, label, icon in NAV_ITEMS:
            btn = SidebarButton(icon, label, page_key)
            btn.clicked.connect(lambda _, k=page_key: self._navigate(k))
            sidebar_layout.addWidget(btn)
            self._sidebar_btns[page_key] = btn

        sidebar_layout.addStretch()

        # User info + logout
        user_frame = QFrame()
        user_frame.setStyleSheet("background: #2D2D44; border-top: 1px solid #444;")
        user_layout = QVBoxLayout(user_frame)
        user_layout.setContentsMargins(12, 10, 12, 10)
        user_layout.setSpacing(4)

        self.user_name_lbl = QLabel(app_session.full_name or app_session.username or "User")
        self.user_name_lbl.setStyleSheet("color: #FFD700; font-weight: 700; font-size: 12px;")
        self.user_role_lbl = QLabel((app_session.role or "").title())
        self.user_role_lbl.setStyleSheet("color: #999; font-size: 11px;")
        logout_btn = QPushButton("⏻ Logout")
        logout_btn.setObjectName("SidebarBtn")
        logout_btn.setStyleSheet("color: #FF6B6B; padding: 6px 12px; font-size: 12px;")
        logout_btn.clicked.connect(self._logout)
        user_layout.addWidget(self.user_name_lbl)
        user_layout.addWidget(self.user_role_lbl)
        user_layout.addWidget(logout_btn)
        sidebar_layout.addWidget(user_frame)

        main_layout.addWidget(sidebar)

        # ---- Content area ----
        content_area = QWidget()
        content_area.setObjectName("ContentArea")
        content_layout = QVBoxLayout(content_area)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Top bar
        top_bar = QFrame()
        top_bar.setObjectName("TopBar")
        top_bar.setFixedHeight(52)
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(20, 0, 20, 0)
        self.page_title_lbl = QLabel("Dashboard")
        self.page_title_lbl.setObjectName("PageTitle")
        top_bar_layout.addWidget(self.page_title_lbl)
        top_bar_layout.addStretch()

        # Rate mini display
        self.rates_mini_lbl = QLabel("Gold: — | Silver: —")
        self.rates_mini_lbl.setStyleSheet(
            "color: #B8860B; font-size: 12px; font-weight: 600; "
            "background: #FFF8E1; padding: 4px 10px; border-radius: 4px;"
        )
        top_bar_layout.addWidget(self.rates_mini_lbl)

        self.session_timer_lbl = QLabel("")
        self.session_timer_lbl.setStyleSheet("color: #888; font-size: 11px;")
        top_bar_layout.addWidget(self.session_timer_lbl)

        user_lbl = QLabel(f"👤 {app_session.username}")
        user_lbl.setObjectName("UserInfo")
        top_bar_layout.addWidget(user_lbl)

        content_layout.addWidget(top_bar)

        # Page stack
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        main_layout.addWidget(content_area)

        # Load all pages
        self._load_pages()

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

    def _load_pages(self):
        from app.ui.pages.dashboard_page import DashboardPage
        from app.ui.pages.customers_page import CustomersPage
        from app.ui.pages.loans_page import LoansPage
        from app.ui.pages.rates_page import RatesPage
        from app.ui.pages.reports_page import ReportsPage
        from app.ui.pages.settings_page import SettingsPage
        from app.ui.pages.audit_page import AuditPage
        from app.ui.pages.users_page import UsersPage

        page_map = {
            "dashboard": DashboardPage,
            "customers": CustomersPage,
            "loans": LoansPage,
            "rates": RatesPage,
            "reports": ReportsPage,
            "settings": SettingsPage,
            "audit": AuditPage,
            "users": UsersPage,
        }

        for key, Page in page_map.items():
            page = Page()
            self._pages[key] = page
            self.stack.addWidget(page)

        # Placeholders for remaining pages
        for key, label, _ in NAV_ITEMS:
            if key not in self._pages:
                placeholder = self._make_placeholder(label)
                self._pages[key] = placeholder
                self.stack.addWidget(placeholder)

        self._navigate("dashboard")

    def _make_placeholder(self, label: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"{label}\n\nThis module is available in the next phase.")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color: #888; font-size: 14px;")
        layout.addWidget(lbl)
        return w

    def _navigate(self, page_key: str):
        if page_key not in self._pages:
            return

        # Check permission
        restricted = {"users": "manage_users", "audit": "view_audit_logs",
                      "backup": "backup_restore", "settings": "manage_settings"}
        if page_key in restricted and not app_session.can(restricted[page_key]):
            QMessageBox.warning(self, "Access Denied", "You do not have permission for this section.")
            return

        self._current_page = page_key
        self.stack.setCurrentWidget(self._pages[page_key])

        # Update sidebar active state
        for key, btn in self._sidebar_btns.items():
            btn.set_active(key == page_key)

        # Update title
        label = next((l for k, l, _ in NAV_ITEMS if k == page_key), page_key)
        self.page_title_lbl.setText(label)
        app_session.touch()

    def _setup_timeout(self):
        self._timeout_timer = QTimer()
        self._timeout_timer.setInterval(30_000)  # check every 30 seconds
        self._timeout_timer.timeout.connect(self._check_timeout)
        self._timeout_timer.start()

        self._rates_timer = QTimer()
        self._rates_timer.setInterval(300_000)  # update mini rates every 5 min
        self._rates_timer.timeout.connect(self._update_mini_rates)
        self._rates_timer.start()
        QTimer.singleShot(3000, self._update_mini_rates)

    def _check_timeout(self):
        if app_session.is_timed_out():
            self._timeout_timer.stop()
            QMessageBox.warning(
                self, "Session Expired",
                "Your session has expired due to inactivity. Please log in again."
            )
            self._logout()

    def _update_mini_rates(self):
        try:
            from app.services.rate_service import get_rate_service
            gold = get_rate_service().get_latest_rate("gold")
            silver = get_rate_service().get_latest_rate("silver")
            g = f"₹{float(gold['rate_per_gram']):,.0f}/g" if gold else "—"
            s = f"₹{float(silver['rate_per_gram']):,.1f}/g" if silver else "—"
            self.rates_mini_lbl.setText(f"🥇 {g}  |  🥈 {s}")
        except Exception:
            pass

    def _update_overdue(self):
        try:
            from app.services.loan_service import get_loan_service
            n = get_loan_service().update_overdue_statuses()
            if n > 0:
                self.statusBar().showMessage(f"{n} loan(s) marked as overdue", 5000)
        except Exception:
            pass

    def _logout(self):
        app_session.logout()
        self._timeout_timer.stop()
        self._rates_timer.stop()
        self.logout_requested.emit()
        self.close()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        app_session.touch()

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        app_session.touch()
