"""Repayments page — all payments across all loans."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QMessageBox,
)

from app.ui.widgets.data_table import DataTable
from app.utils.formatters import fmt_currency, fmt_date


class RepaymentsPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QHBoxLayout()
        title = QLabel("Repayments")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        collect_btn = QPushButton("+ Collect Payment")
        collect_btn.setFixedHeight(36)
        collect_btn.clicked.connect(self._collect_payment)
        header.addWidget(collect_btn)
        refresh_btn = QPushButton("↻ Refresh")
        refresh_btn.setObjectName("SecondaryBtn")
        refresh_btn.setFixedHeight(36)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        filter_row.addWidget(QLabel("Mode:"))
        self.mode_filter = QComboBox()
        self.mode_filter.addItems(["All", "cash", "upi", "bank_transfer", "cheque", "other"])
        self.mode_filter.setFixedWidth(140)
        self.mode_filter.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self.mode_filter)

        filter_row.addWidget(QLabel("Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Loan # or Receipt #")
        self.search_input.setFixedWidth(200)
        self.search_input.textChanged.connect(self.refresh)
        filter_row.addWidget(self.search_input)
        filter_row.addStretch()

        self.total_lbl = QLabel("")
        self.total_lbl.setStyleSheet("font-weight: 700; color: #28A745;")
        filter_row.addWidget(self.total_lbl)
        layout.addLayout(filter_row)

        # Table
        self.table = DataTable(
            ["ID", "Receipt #", "Loan #", "Customer", "Total Paid", "Principal", "Interest",
             "Penalty", "Mode", "Date", "Collected By", "Status"],
            searchable=False,
        )
        self.table.row_double_clicked.connect(lambda _r: self._print_receipt())
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        receipt_btn = QPushButton("🧾 Print Receipt")
        receipt_btn.clicked.connect(self._print_receipt)
        btn_row.addWidget(receipt_btn)
        reverse_btn = QPushButton("↩ Reverse Payment")
        reverse_btn.setObjectName("SecondaryBtn")
        reverse_btn.clicked.connect(self._reverse_payment)
        btn_row.addWidget(reverse_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self):
        try:
            from app.database.connection import get_session
            from app.models.repayment import Repayment
            from app.models.loan import Loan
            from app.models.customer import Customer
            from app.models.user import User

            mode = self.mode_filter.currentText()
            search = self.search_input.text().strip().lower()

            with get_session() as session:
                q = (
                    session.query(Repayment, Loan, Customer, User)
                    .join(Loan, Repayment.loan_id == Loan.id)
                    .join(Customer, Loan.customer_id == Customer.id)
                    .outerjoin(User, Repayment.created_by == User.id)
                )
                if mode != "All":
                    q = q.filter(Repayment.payment_mode == mode)
                results = q.order_by(Repayment.payment_date.desc(), Repayment.id.desc()).limit(500).all()

                rows = []
                total = 0
                for rep, loan, cust, usr in results:
                    ln = loan.loan_number or ""
                    rn = rep.receipt_number or ""
                    cn = cust.full_name or ""
                    if search and search not in ln.lower() and search not in rn.lower() and search not in cn.lower():
                        continue
                    if not rep.is_reversed:
                        total += float(rep.total_paid or 0)
                    rows.append([
                        rep.id, rn, ln, cn,
                        fmt_currency(rep.total_paid),
                        fmt_currency(rep.principal_paid),
                        fmt_currency(rep.interest_paid),
                        fmt_currency(rep.penalty_paid),
                        (rep.payment_mode or "").replace("_", " ").title(),
                        fmt_date(rep.payment_date),
                        usr.username if usr else "—",
                        "Reversed" if rep.is_reversed else "Valid",
                    ])

            self.table.load_data(rows)
            self.total_lbl.setText(f"Total: {fmt_currency(total)}")
        except Exception as exc:
            self.total_lbl.setText(f"Error: {exc}")

    def _selected_id(self):
        row = self.table.get_selected_row_data()
        if not row:
            QMessageBox.warning(self, "No Selection", "Select a payment first.")
            return None
        return int(row[0])

    def _print_receipt(self):
        rid = self._selected_id()
        if rid is not None:
            from app.ui.loan_actions import open_receipt
            open_receipt(rid, self)

    def _reverse_payment(self):
        from PySide6.QtWidgets import QInputDialog
        from app.services.repayment_service import get_repayment_service
        from app.ui.session_state import session
        if not session.is_admin:
            QMessageBox.warning(self, "Access Denied", "Only an admin can reverse payments.")
            return
        rid = self._selected_id()
        if rid is None:
            return
        reason, ok = QInputDialog.getText(self, "Reverse Payment", "Reason for reversal (required):")
        if not ok:
            return
        if not reason.strip():
            QMessageBox.warning(self, "Reason Required", "Please enter a reason for the reversal.")
            return
        ok, msg = get_repayment_service().reverse_payment(rid, session.user_id, reason)
        if ok:
            QMessageBox.information(self, "Reversed", msg)
            self.refresh()
        else:
            QMessageBox.warning(self, "Cannot Reverse", msg)

    def _collect_payment(self):
        from PySide6.QtWidgets import QInputDialog
        from app.services.loan_service import get_loan_service
        from app.ui.dialogs.repayment_dialog import RepaymentDialog

        loan_num, ok = QInputDialog.getText(self, "Collect Payment", "Enter Loan Number:")
        if not ok or not loan_num.strip():
            return

        loan = get_loan_service().get_loan_by_number(loan_num.strip().upper())
        if not loan:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Not Found", f"Loan '{loan_num}' not found.")
            return

        dlg = RepaymentDialog(loan_id=loan["id"], parent=self)
        if dlg.exec():
            self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()
