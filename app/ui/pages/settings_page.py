"""Application settings page."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox, QGroupBox,
    QFormLayout, QMessageBox, QScrollArea, QFrame, QCheckBox,
)

from app.config import get_config


class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        content = QWidget()
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Settings")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        cfg = get_config()

        # Business identity
        biz_grp = QGroupBox("Business Identity")
        biz_form = QFormLayout(biz_grp)
        biz_form.setSpacing(10)
        self.biz_name = QLineEdit(cfg.get("business_name", ""))
        biz_form.addRow("Business Name:", self.biz_name)
        self.biz_address = QLineEdit(cfg.get("business_address", ""))
        biz_form.addRow("Address:", self.biz_address)
        self.biz_phone = QLineEdit(cfg.get("business_phone", ""))
        biz_form.addRow("Phone:", self.biz_phone)
        self.biz_email = QLineEdit(cfg.get("business_email", ""))
        biz_form.addRow("Email:", self.biz_email)
        self.biz_gstin = QLineEdit(cfg.get("business_gstin", ""))
        biz_form.addRow("GSTIN:", self.biz_gstin)
        layout.addWidget(biz_grp)

        # Number prefixes
        prefix_grp = QGroupBox("Number Prefixes")
        prefix_form = QFormLayout(prefix_grp)
        prefix_form.setSpacing(10)
        self.loan_prefix = QLineEdit(cfg.loan_prefix)
        prefix_form.addRow("Loan Number Prefix:", self.loan_prefix)
        self.cust_prefix = QLineEdit(cfg.customer_prefix)
        prefix_form.addRow("Customer ID Prefix:", self.cust_prefix)
        self.receipt_prefix = QLineEdit(cfg.receipt_prefix)
        prefix_form.addRow("Receipt Prefix:", self.receipt_prefix)
        layout.addWidget(prefix_grp)

        # Loan defaults
        loan_grp = QGroupBox("Loan Defaults")
        loan_form = QFormLayout(loan_grp)
        loan_form.setSpacing(10)
        self.default_rate = QDoubleSpinBox()
        self.default_rate.setRange(0, 100)
        self.default_rate.setDecimals(2)
        self.default_rate.setSuffix(" % pa")
        self.default_rate.setValue(cfg.default_interest_rate)
        loan_form.addRow("Default Interest Rate:", self.default_rate)
        self.default_ltv = QDoubleSpinBox()
        self.default_ltv.setRange(0, 100)
        self.default_ltv.setDecimals(1)
        self.default_ltv.setSuffix(" %")
        self.default_ltv.setValue(cfg.default_ltv_percentage)
        loan_form.addRow("Default LTV %:", self.default_ltv)
        self.max_ltv = QDoubleSpinBox()
        self.max_ltv.setRange(0, 100)
        self.max_ltv.setDecimals(1)
        self.max_ltv.setSuffix(" %")
        self.max_ltv.setValue(cfg.max_ltv_percentage)
        loan_form.addRow("Maximum LTV % (policy):", self.max_ltv)
        self.default_tenure = QSpinBox()
        self.default_tenure.setRange(1, 3650)
        self.default_tenure.setSuffix(" days")
        self.default_tenure.setValue(cfg.default_tenure_days)
        loan_form.addRow("Default Tenure:", self.default_tenure)
        self.penalty_rate = QDoubleSpinBox()
        self.penalty_rate.setRange(0, 100)
        self.penalty_rate.setDecimals(2)
        self.penalty_rate.setSuffix(" % pa")
        self.penalty_rate.setValue(cfg.overdue_penalty_rate)
        loan_form.addRow("Overdue Penalty Rate:", self.penalty_rate)
        layout.addWidget(loan_grp)

        # Rate API
        api_grp = QGroupBox("Live Rates API")
        api_form = QFormLayout(api_grp)
        api_form.setSpacing(10)
        self.api_provider = QComboBox()
        self.api_provider.addItems(["goldapi"])
        idx = self.api_provider.findText(cfg.rate_api_provider)
        if idx >= 0:
            self.api_provider.setCurrentIndex(idx)
        api_form.addRow("Provider:", self.api_provider)
        self.api_key = QLineEdit(cfg.rate_api_key)
        self.api_key.setPlaceholderText("Get a free key at goldapi.io")
        api_form.addRow("API Key:", self.api_key)
        self.rate_interval = QSpinBox()
        self.rate_interval.setRange(5, 1440)
        self.rate_interval.setSuffix(" minutes")
        self.rate_interval.setValue(cfg.rate_refresh_interval_minutes)
        api_form.addRow("Auto-Refresh Interval:", self.rate_interval)
        layout.addWidget(api_grp)

        # Session
        session_grp = QGroupBox("Session & Security")
        session_form = QFormLayout(session_grp)
        self.session_timeout = QSpinBox()
        self.session_timeout.setRange(5, 240)
        self.session_timeout.setSuffix(" minutes")
        self.session_timeout.setValue(cfg.session_timeout_minutes)
        session_form.addRow("Session Timeout:", self.session_timeout)
        layout.addWidget(session_grp)

        # Theme
        ui_grp = QGroupBox("Appearance")
        ui_form = QFormLayout(ui_grp)
        self.theme = QComboBox()
        self.theme.addItems(["light", "dark"])
        idx = self.theme.findText(cfg.theme)
        if idx >= 0:
            self.theme.setCurrentIndex(idx)
        ui_form.addRow("Theme:", self.theme)
        layout.addWidget(ui_grp)

        # Save button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("Save Settings")
        save_btn.setFixedHeight(40)
        save_btn.setFixedWidth(160)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)
        layout.addStretch()

    def _save(self):
        from app.ui.session_state import session
        if not session.is_admin:
            QMessageBox.warning(self, "Unauthorized", "Only admins can change settings.")
            return

        cfg = get_config()
        cfg.update({
            "business_name": self.biz_name.text().strip(),
            "business_address": self.biz_address.text().strip(),
            "business_phone": self.biz_phone.text().strip(),
            "business_email": self.biz_email.text().strip(),
            "business_gstin": self.biz_gstin.text().strip(),
            "loan_prefix": self.loan_prefix.text().strip() or "LN",
            "customer_prefix": self.cust_prefix.text().strip() or "CUST",
            "receipt_prefix": self.receipt_prefix.text().strip() or "RCPT",
            "default_interest_rate": self.default_rate.value(),
            "default_ltv_percentage": self.default_ltv.value(),
            "max_ltv_percentage": self.max_ltv.value(),
            "default_tenure_days": self.default_tenure.value(),
            "overdue_penalty_rate": self.penalty_rate.value(),
            "rate_api_provider": self.api_provider.currentText(),
            "rate_api_key": self.api_key.text().strip(),
            "rate_refresh_interval_minutes": self.rate_interval.value(),
            "session_timeout_minutes": self.session_timeout.value(),
            "theme": self.theme.currentText(),
        })
        QMessageBox.information(self, "Saved", "Settings saved. Some changes take effect on next launch.")
