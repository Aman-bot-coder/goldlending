"""Active Loans page with search, filters, and loan detail actions."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QMessageBox, QDialog,
)

from app.ui.widgets.data_table import DataTable
from app.utils.formatters import fmt_currency, fmt_date


STATUSES = [
    "All", "draft", "pending_approval", "approved", "disbursed",
    "active", "partially_repaid", "overdue", "closed", "renewed", "auction_review"
]

STATUS_COLORS = {
    "active": "#28A745",
    "partially_repaid": "#17A2B8",
    "overdue": "#DC3545",
    "closed": "#6C757D",
    "approved": "#0056B3",
    "draft": "#6C757D",
    "pending_approval": "#FFC107",
}


class LoansPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QHBoxLayout()
        title = QLabel("Loans")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        new_btn = QPushButton("+ New Loan")
        new_btn.setFixedHeight(36)
        new_btn.clicked.connect(self._new_loan)
        header.addWidget(new_btn)
        layout.addLayout(header)

        # Filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)

        filter_row.addWidget(QLabel("Status:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems([s.replace("_", " ").title() if s != "All" else "All" for s in STATUSES])
        self.status_filter.setFixedWidth(150)
        self.status_filter.currentIndexChanged.connect(self.load_data)
        filter_row.addWidget(self.status_filter)

        overdue_btn = QPushButton("Show Overdue Only")
        overdue_btn.setObjectName("SecondaryBtn")
        overdue_btn.setCheckable(True)
        overdue_btn.toggled.connect(lambda _: self.load_data())
        self.overdue_toggle = overdue_btn
        filter_row.addWidget(overdue_btn)

        filter_row.addStretch()
        self.total_lbl = QLabel("")
        self.total_lbl.setStyleSheet("color: #888; font-size: 12px;")
        filter_row.addWidget(self.total_lbl)
        layout.addLayout(filter_row)

        # Table
        self.table = DataTable(
            ["ID", "Loan #", "Customer", "Mobile", "Principal", "Status",
             "Disbursed", "Maturity", "Outstanding"],
        )
        self.table.row_double_clicked.connect(self._view_loan)
        layout.addWidget(self.table)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        view_btn = QPushButton("View Details")
        view_btn.setObjectName("SecondaryBtn")
        view_btn.clicked.connect(lambda: self._view_loan(0))
        approve_btn = QPushButton("Approve")
        approve_btn.setObjectName("SuccessBtn")
        approve_btn.clicked.connect(self._approve_loan)
        disburse_btn = QPushButton("Disburse")
        disburse_btn.clicked.connect(self._disburse_loan)
        repay_btn = QPushButton("Collect Payment")
        repay_btn.setObjectName("SuccessBtn")
        repay_btn.clicked.connect(self._collect_payment)
        btn_row.addWidget(view_btn)
        btn_row.addWidget(approve_btn)
        btn_row.addWidget(disburse_btn)
        btn_row.addWidget(repay_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def load_data(self):
        from app.services.loan_service import get_loan_service
        status_idx = self.status_filter.currentIndex()
        status = "" if status_idx == 0 else STATUSES[status_idx]
        overdue_only = self.overdue_toggle.isChecked()

        loans = get_loan_service().search_loans(
            status=status, overdue_only=overdue_only, limit=500
        )
        self.total_lbl.setText(f"{len(loans)} loans")
        rows = [
            [
                lo["id"],
                lo["loan_number"],
                lo["customer_name"],
                lo["customer_mobile"],
                fmt_currency(lo["principal_amount"]),
                lo["status"].replace("_", " ").title(),
                fmt_date(lo["disbursement_date"]),
                fmt_date(lo["maturity_date"]),
                fmt_currency(lo["total_outstanding"]),
            ]
            for lo in loans
        ]
        self.table.load_data(rows)

    def _new_loan(self):
        from app.ui.dialogs.loan_dialog import LoanDialog
        dlg = LoanDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _view_loan(self, _row):
        row_data = self.table.get_selected_row_data()
        if not row_data:
            return
        from app.ui.dialogs.loan_dialog import LoanDialog
        dlg = LoanDialog(loan_id=row_data[0], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _approve_loan(self):
        row_data = self.table.get_selected_row_data()
        if not row_data:
            QMessageBox.warning(self, "No Selection", "Select a loan first.")
            return
        loan_id = row_data[0]
        from app.services.loan_service import get_loan_service
        from app.ui.session_state import session
        from decimal import Decimal
        loan = get_loan_service().get_loan(loan_id)
        if not loan:
            return
        ok, msg = get_loan_service().approve_loan(
            loan_id, session.user_id, loan["principal_amount"], "Approved"
        )
        QMessageBox.information(self, "Result", msg) if ok else QMessageBox.warning(self, "Error", msg)
        if ok:
            self.load_data()

    def _disburse_loan(self):
        row_data = self.table.get_selected_row_data()
        if not row_data:
            QMessageBox.warning(self, "No Selection", "Select a loan first.")
            return
        loan_id = row_data[0]
        from app.services.loan_service import get_loan_service
        from app.ui.session_state import session
        ok, msg = get_loan_service().disburse_loan(loan_id, session.user_id)
        QMessageBox.information(self, "Result", msg) if ok else QMessageBox.warning(self, "Error", msg)
        if ok:
            self.load_data()

    def _collect_payment(self):
        row_data = self.table.get_selected_row_data()
        if not row_data:
            QMessageBox.warning(self, "No Selection", "Select a loan first.")
            return
        loan_id = row_data[0]
        from app.ui.dialogs.repayment_dialog import RepaymentDialog
        dlg = RepaymentDialog(loan_id=loan_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()
