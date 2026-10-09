"""Loan creation and detail dialog with collateral valuation."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QTextEdit, QFormLayout, QGroupBox,
    QWidget, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QMessageBox, QDoubleSpinBox,
    QSpinBox, QScrollArea, QFrame,
)

from app.utils.formatters import fmt_currency, fmt_date, fmt_weight


class LoanDialog(QDialog):
    def __init__(self, loan_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.loan_id = loan_id
        self.is_edit = loan_id is not None
        self.setWindowTitle("Loan Details" if self.is_edit else "New Loan")
        self.setMinimumSize(820, 640)
        self.resize(860, 680)
        self._collateral_rows: list = []
        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Tab 1: Loan Details
        loan_tab = QScrollArea()
        loan_tab.setWidgetResizable(True)
        loan_tab.setFrameShape(QFrame.Shape.NoFrame)
        loan_widget = QWidget()
        loan_tab.setWidget(loan_widget)
        loan_layout = QVBoxLayout(loan_widget)
        loan_layout.setContentsMargins(16, 16, 16, 16)
        loan_layout.setSpacing(14)

        # Customer search
        cust_grp = QGroupBox("Customer")
        cust_form = QFormLayout(cust_grp)
        cust_row = QHBoxLayout()
        self.customer_search = QLineEdit()
        self.customer_search.setPlaceholderText("Search by name or mobile...")
        cust_row.addWidget(self.customer_search)
        search_btn = QPushButton("Search")
        search_btn.setFixedWidth(80)
        search_btn.clicked.connect(self._search_customer)
        cust_row.addWidget(search_btn)
        cust_form.addRow("Find Customer:", cust_row)
        self.customer_id_lbl = QLabel("—")
        self.customer_id_lbl.setStyleSheet("font-weight: 700; color: #1A1A2E;")
        cust_form.addRow("Selected:", self.customer_id_lbl)
        self._selected_customer_id: Optional[int] = None
        loan_layout.addWidget(cust_grp)

        # Loan terms
        terms_grp = QGroupBox("Loan Terms")
        terms_form = QFormLayout(terms_grp)
        terms_form.setSpacing(10)

        from app.config import get_config
        cfg = get_config()

        self.principal_amount = QDoubleSpinBox()
        self.principal_amount.setRange(1, 9_999_999)
        self.principal_amount.setDecimals(2)
        self.principal_amount.setPrefix("₹ ")
        self.principal_amount.setGroupSeparatorShown(True)
        terms_form.addRow("Principal Amount *:", self.principal_amount)

        self.interest_rate = QDoubleSpinBox()
        self.interest_rate.setRange(0, 100)
        self.interest_rate.setDecimals(2)
        self.interest_rate.setSuffix(" %")
        self.interest_rate.setValue(cfg.default_interest_rate)
        terms_form.addRow("Interest Rate (Annual) *:", self.interest_rate)

        self.interest_method = QComboBox()
        self.interest_method.addItems(["simple", "reducing_balance"])
        terms_form.addRow("Interest Method:", self.interest_method)

        self.tenure_days = QSpinBox()
        self.tenure_days.setRange(1, 3650)
        self.tenure_days.setValue(cfg.default_tenure_days)
        self.tenure_days.setSuffix(" days")
        terms_form.addRow("Tenure *:", self.tenure_days)

        self.ltv = QDoubleSpinBox()
        self.ltv.setRange(0, 100)
        self.ltv.setDecimals(1)
        self.ltv.setSuffix(" %")
        self.ltv.setValue(cfg.default_ltv_percentage)
        terms_form.addRow("LTV %:", self.ltv)

        self.processing_fee = QDoubleSpinBox()
        self.processing_fee.setRange(0, 99999)
        self.processing_fee.setDecimals(2)
        self.processing_fee.setPrefix("₹ ")
        terms_form.addRow("Processing Fee:", self.processing_fee)

        self.payment_mode = QComboBox()
        self.payment_mode.addItems(["cash", "bank_transfer", "upi", "cheque", "other"])
        terms_form.addRow("Payment Mode:", self.payment_mode)

        self.remarks = QTextEdit()
        self.remarks.setFixedHeight(50)
        terms_form.addRow("Remarks:", self.remarks)
        loan_layout.addWidget(terms_grp)

        # Valuation summary
        summary_grp = QGroupBox("Collateral Valuation Summary")
        summary_form = QFormLayout(summary_grp)
        self.total_collateral_lbl = QLabel("₹ 0.00")
        self.total_collateral_lbl.setStyleSheet("font-weight: 700; font-size: 15px; color: #FFD700;")
        summary_form.addRow("Total Collateral Value:", self.total_collateral_lbl)
        self.max_eligible_lbl = QLabel("₹ 0.00")
        self.max_eligible_lbl.setStyleSheet("font-weight: 700; color: #28A745;")
        summary_form.addRow("Max Eligible (LTV):", self.max_eligible_lbl)
        self.ltv.valueChanged.connect(self._update_valuation_summary)
        loan_layout.addWidget(summary_grp)
        loan_layout.addStretch()

        tabs.addTab(loan_tab, "Loan Details")

        # Tab 2: Collateral Items
        collateral_tab = QWidget()
        coll_layout = QVBoxLayout(collateral_tab)
        coll_layout.setContentsMargins(16, 16, 16, 16)
        coll_layout.setSpacing(12)

        coll_header = QHBoxLayout()
        coll_header.addWidget(QLabel("Collateral Items"))
        coll_header.addStretch()
        add_coll_btn = QPushButton("+ Add Item")
        add_coll_btn.clicked.connect(self._add_collateral_row)
        coll_header.addWidget(add_coll_btn)
        coll_layout.addLayout(coll_header)

        self.coll_table = QTableWidget()
        self.coll_table.setColumnCount(9)
        self.coll_table.setHorizontalHeaderLabels([
            "Metal", "Category", "Gross Wt (g)", "Stone Wt (g)",
            "Net Wt (g)", "Purity", "Rate ₹/g", "Est. Value", "Tag #"
        ])
        self.coll_table.horizontalHeader().setStretchLastSection(True)
        self.coll_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.coll_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        coll_layout.addWidget(self.coll_table)

        rm_btn = QPushButton("Remove Selected")
        rm_btn.setObjectName("DangerBtn")
        rm_btn.clicked.connect(self._remove_collateral_row)
        coll_layout.addWidget(rm_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        tabs.addTab(collateral_tab, "Collateral Items")

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 12, 16, 16)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Loan")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        if not self.is_edit:
            btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _search_customer(self):
        query = self.customer_search.text().strip()
        if not query:
            return
        from app.services.customer_service import get_customer_service
        customers = get_customer_service().search_customers(query=query, limit=20)
        if not customers:
            QMessageBox.information(self, "Search", "No customers found.")
            return
        if len(customers) == 1:
            self._select_customer(customers[0])
            return
        # Show picker
        from PySide6.QtWidgets import QInputDialog
        names = [f"{c['customer_id']} — {c['full_name']} ({c['mobile']})" for c in customers]
        choice, ok = QInputDialog.getItem(self, "Select Customer", "Choose:", names, 0, False)
        if ok:
            idx = names.index(choice)
            self._select_customer(customers[idx])

    def _select_customer(self, c: dict):
        self._selected_customer_id = c["id"]
        self.customer_id_lbl.setText(
            f"{c['customer_id']} — {c['full_name']} | {c['mobile']}"
        )

    def _add_collateral_row(self):
        from app.ui.dialogs.collateral_dialog import CollateralItemDialog
        dlg = CollateralItemDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            item = dlg.get_data()
            self._collateral_rows.append(item)
            self._render_collateral_table()
            self._update_valuation_summary()

    def _remove_collateral_row(self):
        idx = self.coll_table.currentRow()
        if 0 <= idx < len(self._collateral_rows):
            self._collateral_rows.pop(idx)
            self._render_collateral_table()
            self._update_valuation_summary()

    def _render_collateral_table(self):
        self.coll_table.setRowCount(len(self._collateral_rows))
        for i, item in enumerate(self._collateral_rows):
            self.coll_table.setItem(i, 0, QTableWidgetItem(item.get("metal_type", "")))
            self.coll_table.setItem(i, 1, QTableWidgetItem(item.get("item_category", "")))
            self.coll_table.setItem(i, 2, QTableWidgetItem(str(item.get("gross_weight", ""))))
            self.coll_table.setItem(i, 3, QTableWidgetItem(str(item.get("stone_weight", ""))))
            self.coll_table.setItem(i, 4, QTableWidgetItem(str(item.get("net_weight", ""))))
            self.coll_table.setItem(i, 5, QTableWidgetItem(item.get("purity", "")))
            self.coll_table.setItem(i, 6, QTableWidgetItem(str(item.get("valuation_rate", ""))))
            self.coll_table.setItem(i, 7, QTableWidgetItem(fmt_currency(item.get("indicative_value", 0))))
            self.coll_table.setItem(i, 8, QTableWidgetItem(item.get("tag_number", "") or ""))

    def _update_valuation_summary(self):
        total = sum(Decimal(str(i.get("indicative_value", 0))) for i in self._collateral_rows)
        ltv = Decimal(str(self.ltv.value()))
        max_eligible = (total * ltv / Decimal("100")).quantize(Decimal("0.01"))
        self.total_collateral_lbl.setText(fmt_currency(total))
        self.max_eligible_lbl.setText(fmt_currency(max_eligible))

    def _load_data(self):
        from app.services.loan_service import get_loan_service
        from app.database.connection import get_session
        from app.models.collateral import CollateralItem
        loan = get_loan_service().get_loan(self.loan_id)
        if not loan:
            return
        self.customer_id_lbl.setText(
            f"{loan.get('customer_id')} — {loan['customer_name']}"
        )
        self._selected_customer_id = loan["customer_id"]
        self.principal_amount.setValue(float(loan["principal_amount"] or 0))
        self.interest_rate.setValue(float(loan["interest_rate"] or 0))
        idx = self.interest_method.findText(loan.get("interest_method", "simple"))
        if idx >= 0:
            self.interest_method.setCurrentIndex(idx)
        self.tenure_days.setValue(loan.get("tenure_days", 180))
        self.ltv.setValue(float(loan.get("ltv_percentage") or 75))
        self.processing_fee.setValue(float(loan.get("processing_fee") or 0))
        idx = self.payment_mode.findText(loan.get("payment_mode", "cash"))
        if idx >= 0:
            self.payment_mode.setCurrentIndex(idx)
        self.remarks.setPlainText(loan.get("remarks", "") or "")

        with get_session() as session:
            items = (
                session.query(CollateralItem)
                .filter(CollateralItem.loan_id == self.loan_id)
                .all()
            )
            self._collateral_rows = [
                {
                    "metal_type": i.metal_type,
                    "item_category": i.item_category,
                    "gross_weight": i.gross_weight,
                    "stone_weight": i.stone_weight,
                    "net_weight": i.net_weight,
                    "purity": i.purity,
                    "valuation_rate": i.valuation_rate,
                    "indicative_value": i.indicative_value,
                    "tag_number": i.tag_number,
                }
                for i in items
            ]
        self._render_collateral_table()
        self._update_valuation_summary()

    def _save(self):
        if not self._selected_customer_id:
            QMessageBox.warning(self, "Error", "Please select a customer.")
            return
        if self.principal_amount.value() <= 0:
            QMessageBox.warning(self, "Error", "Principal amount must be greater than zero.")
            return

        from app.services.loan_service import get_loan_service
        from app.ui.session_state import session as app_session

        svc = get_loan_service()
        ok, msg, loan_id = svc.create_loan(
            customer_id=self._selected_customer_id,
            principal_amount=Decimal(str(self.principal_amount.value())),
            interest_rate=Decimal(str(self.interest_rate.value())),
            tenure_days=self.tenure_days.value(),
            interest_method=self.interest_method.currentText(),
            created_by=app_session.user_id,
            processing_fee=Decimal(str(self.processing_fee.value())),
            payment_mode=self.payment_mode.currentText(),
            ltv_percentage=Decimal(str(self.ltv.value())),
            total_collateral_value=Decimal(str(
                sum(Decimal(str(i.get("indicative_value", 0))) for i in self._collateral_rows)
            )),
            remarks=self.remarks.toPlainText().strip(),
        )
        if not ok:
            QMessageBox.warning(self, "Error", msg)
            return

        # Save collateral items
        for item in self._collateral_rows:
            svc.add_collateral(
                loan_id=loan_id,
                metal_type=item["metal_type"],
                item_category=item["item_category"],
                gross_weight=Decimal(str(item["gross_weight"])),
                stone_weight=Decimal(str(item.get("stone_weight", 0))),
                purity=item["purity"],
                rate_per_gram=Decimal(str(item.get("market_rate", item.get("valuation_rate", 0)))),
                valuation_rate=Decimal(str(item.get("valuation_rate", 0))),
                tag_number=item.get("tag_number"),
                description=item.get("description", ""),
                storage_location=item.get("storage_location", ""),
            )

        QMessageBox.information(self, "Success", msg)
        self.accept()
