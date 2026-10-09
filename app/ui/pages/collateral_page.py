"""Collateral Inventory page — all pledged items across all loans."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit,
)

from app.ui.widgets.data_table import DataTable
from app.utils.formatters import fmt_weight, fmt_currency, fmt_date


class CollateralPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QHBoxLayout()
        title = QLabel("Collateral Inventory")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.setFixedHeight(36)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        filter_row.addWidget(QLabel("Metal:"))
        self.metal_filter = QComboBox()
        self.metal_filter.addItems(["All", "gold", "silver"])
        self.metal_filter.setFixedWidth(100)
        self.metal_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.metal_filter)

        filter_row.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["Pledged", "Released", "All"])
        self.status_filter.setFixedWidth(110)
        self.status_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.status_filter)

        filter_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Tag # or Loan #")
        self.search_input.setFixedWidth(180)
        self.search_input.textChanged.connect(self.refresh)
        filter_row.addWidget(self.search_input)
        filter_row.addStretch()

        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("font-weight: 700; color: #B8860B;")
        filter_row.addWidget(self.summary_lbl)
        layout.addLayout(filter_row)

        # Table
        self.table = DataTable(
            ["Tag #", "Loan #", "Customer", "Metal", "Category",
             "Gross Wt", "Net Wt", "Purity", "Value", "Location", "Status"],
            searchable=False,
        )
        layout.addWidget(self.table)

    def refresh(self):
        try:
            from app.database.connection import get_session
            from app.models.collateral import CollateralItem
            from app.models.loan import Loan
            from app.models.customer import Customer

            metal = self.metal_filter.currentText()
            status = self.status_filter.currentText()
            search = self.search_input.text().strip().lower()

            with get_session() as session:
                q = (
                    session.query(CollateralItem, Loan, Customer)
                    .join(Loan, CollateralItem.loan_id == Loan.id)
                    .join(Customer, Loan.customer_id == Customer.id)
                )
                if metal != "All":
                    q = q.filter(CollateralItem.metal_type == metal)
                if status == "Pledged":
                    q = q.filter(CollateralItem.is_released == False)
                elif status == "Released":
                    q = q.filter(CollateralItem.is_released == True)

                results = q.order_by(CollateralItem.created_at.desc()).limit(1000).all()

                rows = []
                total_gold_g = 0.0
                total_silver_g = 0.0

                for item, loan, cust in results:
                    tag = item.tag_number or f"#{item.id}"
                    ln = loan.loan_number or ""
                    cn = cust.full_name or ""

                    if search and search not in tag.lower() and search not in ln.lower() and search not in cn.lower():
                        continue

                    if not item.is_released:
                        if item.metal_type == "gold":
                            total_gold_g += float(item.net_weight or 0)
                        else:
                            total_silver_g += float(item.net_weight or 0)

                    rows.append([
                        tag, ln, cn,
                        item.metal_type.title() if item.metal_type else "—",
                        (item.item_category or "").replace("_", " ").title(),
                        fmt_weight(item.gross_weight),
                        fmt_weight(item.net_weight),
                        item.purity or "—",
                        fmt_currency(item.indicative_value) if item.indicative_value else "—",
                        item.storage_location or "—",
                        "Released" if item.is_released else "Pledged",
                    ])

            self.table.load_data(rows)
            self.summary_lbl.setText(
                f"🥇 Gold: {total_gold_g:.2f}g  |  🥈 Silver: {total_silver_g:.2f}g  (pledged)"
            )
        except Exception as exc:
            self.summary_lbl.setText(f"Error: {exc}")

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
