"""Main dashboard page."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QGridLayout,
)

from app.ui.widgets.stat_card import StatCard
from app.utils.formatters import fmt_currency, fmt_weight, fmt_datetime


class DashboardPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self.refresh)
        self._refresh_timer.start(60_000)  # refresh every minute

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

        # Header row
        header_row = QHBoxLayout()
        header_lbl = QLabel("Dashboard Overview")
        header_lbl.setObjectName("SectionTitle")
        header_row.addWidget(header_lbl)
        header_row.addStretch()
        self.last_updated_lbl = QLabel("")
        self.last_updated_lbl.setStyleSheet("color: #888; font-size: 12px;")
        header_row.addWidget(self.last_updated_lbl)
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.setFixedWidth(90)
        refresh_btn.clicked.connect(self.refresh)
        header_row.addWidget(refresh_btn)
        layout.addLayout(header_row)

        # --- Stat Cards row 1: loans/customers ---
        self.total_customers_card = StatCard("Total Customers", "—", icon="👥", color="#4A90E2")
        self.active_loans_card = StatCard("Active Loans", "—", icon="📋", color="#28A745")
        self.overdue_loans_card = StatCard("Overdue Loans", "—", icon="⚠️", color="#DC3545")
        self.due_soon_card = StatCard("Due in 7 Days", "—", icon="🔔", color="#FFC107")

        row1 = QHBoxLayout()
        row1.setSpacing(16)
        for card in [self.total_customers_card, self.active_loans_card,
                     self.overdue_loans_card, self.due_soon_card]:
            row1.addWidget(card, 1)
        layout.addLayout(row1)

        # --- Stat Cards row 2: financial ---
        self.outstanding_card = StatCard("Principal Outstanding", "—", icon="₹", color="#FF6B35")
        self.disbursed_card = StatCard("Total Disbursed", "—", icon="💰", color="#6C5CE7")
        self.repayments_card = StatCard("Total Collected", "—", icon="✅", color="#00B894")
        self.gold_weight_card = StatCard("Gold Collateral", "—", icon="🥇", color="#FFD700")

        row2 = QHBoxLayout()
        row2.setSpacing(16)
        for card in [self.outstanding_card, self.disbursed_card,
                     self.repayments_card, self.gold_weight_card]:
            row2.addWidget(card, 1)
        layout.addLayout(row2)

        # --- Rates row ---
        rates_frame = QFrame()
        rates_frame.setObjectName("Card")
        rates_layout = QHBoxLayout(rates_frame)
        rates_layout.setSpacing(24)

        gold_col = QVBoxLayout()
        gold_lbl = QLabel("🥇 Live Gold Rate (24K)")
        gold_lbl.setStyleSheet("font-weight: 700; color: #B8860B;")
        self.gold_rate_lbl = QLabel("₹ —")
        self.gold_rate_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #FFD700;")
        self.gold_rate_per10_lbl = QLabel("per 10g: —")
        self.gold_rate_per10_lbl.setStyleSheet("color: #888; font-size: 12px;")
        self.gold_rate_freshness = QLabel("")
        self.gold_rate_freshness.setStyleSheet("font-size: 11px;")
        gold_col.addWidget(gold_lbl)
        gold_col.addWidget(self.gold_rate_lbl)
        gold_col.addWidget(self.gold_rate_per10_lbl)
        gold_col.addWidget(self.gold_rate_freshness)

        silver_col = QVBoxLayout()
        silver_lbl = QLabel("🥈 Live Silver Rate (999)")
        silver_lbl.setStyleSheet("font-weight: 700; color: #808080;")
        self.silver_rate_lbl = QLabel("₹ —")
        self.silver_rate_lbl.setStyleSheet("font-size: 22px; font-weight: 800; color: #C0C0C0;")
        self.silver_rate_per10_lbl = QLabel("per 10g: —")
        self.silver_rate_per10_lbl.setStyleSheet("color: #888; font-size: 12px;")
        self.silver_rate_freshness = QLabel("")
        self.silver_rate_freshness.setStyleSheet("font-size: 11px;")
        silver_col.addWidget(silver_lbl)
        silver_col.addWidget(self.silver_rate_lbl)
        silver_col.addWidget(self.silver_rate_per10_lbl)
        silver_col.addWidget(self.silver_rate_freshness)

        refresh_rates_btn = QPushButton("Refresh Rates")
        refresh_rates_btn.clicked.connect(self._refresh_rates)

        rates_layout.addLayout(gold_col, 1)
        rates_layout.addLayout(silver_col, 1)
        rates_layout.addStretch()
        rates_layout.addWidget(refresh_rates_btn)
        layout.addWidget(rates_frame)

        # --- Recent activity ---
        recent_lbl = QLabel("Recent Loans")
        recent_lbl.setObjectName("SectionTitle")
        layout.addWidget(recent_lbl)

        from app.ui.widgets.data_table import DataTable
        self.recent_loans_table = DataTable(
            ["Loan #", "Customer", "Amount", "Status", "Created"],
            searchable=False,
        )
        self.recent_loans_table.setFixedHeight(220)
        layout.addWidget(self.recent_loans_table)

        layout.addStretch()

    def refresh(self):
        from datetime import datetime
        self.last_updated_lbl.setText(f"Updated: {datetime.now().strftime('%H:%M:%S')}")
        self._load_stats()
        self._load_rates()
        self._load_recent_loans()

    def _load_stats(self):
        try:
            from app.services.loan_service import get_loan_service
            from app.utils.formatters import fmt_currency, fmt_weight
            stats = get_loan_service().get_dashboard_stats()
            self.total_customers_card.set_value(str(stats["total_customers"]))
            self.active_loans_card.set_value(str(stats["active_loans"]))
            self.overdue_loans_card.set_value(str(stats["overdue_loans"]))
            self.due_soon_card.set_value(str(stats["due_soon_loans"]))
            self.outstanding_card.set_value(fmt_currency(stats["principal_outstanding"]))
            self.disbursed_card.set_value(fmt_currency(stats["total_disbursed"]))
            self.repayments_card.set_value(fmt_currency(stats["total_repayments"]))
            self.gold_weight_card.set_value(fmt_weight(stats["gold_weight_grams"]))
        except Exception as exc:
            pass  # DB may not be ready on first render

    def _load_rates(self):
        try:
            from app.services.rate_service import get_rate_service
            gold, silver = get_rate_service().get_both_latest()
            if gold:
                self.gold_rate_lbl.setText(f"₹ {gold['rate_per_gram']:,.2f}")
                self.gold_rate_per10_lbl.setText(f"per 10g: ₹ {gold['rate_per_10gram']:,.2f}")
                stale = gold.get("is_stale", False)
                self.gold_rate_freshness.setText("⚠ Stale rate" if stale else "● Live")
                self.gold_rate_freshness.setStyleSheet(
                    "color: #DC3545; font-size: 11px;" if stale else "color: #28A745; font-size: 11px;"
                )
            if silver:
                self.silver_rate_lbl.setText(f"₹ {silver['rate_per_gram']:,.2f}")
                self.silver_rate_per10_lbl.setText(f"per 10g: ₹ {silver['rate_per_10gram']:,.2f}")
                stale = silver.get("is_stale", False)
                self.silver_rate_freshness.setText("⚠ Stale rate" if stale else "● Live")
                self.silver_rate_freshness.setStyleSheet(
                    "color: #DC3545; font-size: 11px;" if stale else "color: #28A745; font-size: 11px;"
                )
        except Exception:
            pass

    def _refresh_rates(self):
        try:
            from app.services.rate_service import get_rate_service
            get_rate_service().fetch_and_save()
            self._load_rates()
        except Exception:
            pass

    def _load_recent_loans(self):
        try:
            from app.services.loan_service import get_loan_service
            from app.utils.formatters import fmt_currency, fmt_date
            loans = get_loan_service().search_loans(limit=20)
            rows = [
                [
                    lo["loan_number"],
                    lo["customer_name"],
                    fmt_currency(lo["disbursed_amount"] or lo["principal_amount"]),
                    lo["status"].replace("_", " ").title(),
                    fmt_date(lo["created_at"]),
                ]
                for lo in loans
            ]
            self.recent_loans_table.load_data(rows)
        except Exception:
            pass

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
