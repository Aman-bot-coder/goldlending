"""Repayment collection dialog with outstanding calculation."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QLineEdit, QFormLayout, QGroupBox,
    QDoubleSpinBox, QTextEdit, QMessageBox, QFrame,
)

from app.utils.formatters import fmt_currency, fmt_date


class RepaymentDialog(QDialog):
    def __init__(self, loan_id: int, parent=None):
        super().__init__(parent)
        self.loan_id = loan_id
        self._loan_data: dict = {}
        self._outstanding: dict = {}
        self.setWindowTitle("Collect Payment")
        self.setMinimumSize(560, 540)
        self.resize(580, 560)
        self._setup_ui()
        self._load_loan()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 16)

        # Loan info
        self.loan_info_frame = QFrame()
        self.loan_info_frame.setObjectName("GoldCard")
        info_layout = QHBoxLayout(self.loan_info_frame)
        self.loan_num_lbl = QLabel("—")
        self.loan_num_lbl.setStyleSheet("font-weight: 800; font-size: 15px; color: #1A1A2E;")
        self.customer_lbl = QLabel("—")
        self.customer_lbl.setStyleSheet("color: #555;")
        info_layout.addWidget(self.loan_num_lbl)
        info_layout.addSpacing(16)
        info_layout.addWidget(self.customer_lbl)
        info_layout.addStretch()
        layout.addWidget(self.loan_info_frame)

        # Outstanding breakdown
        out_grp = QGroupBox("Outstanding Balance (as of today)")
        out_form = QFormLayout(out_grp)
        out_form.setSpacing(8)
        self.principal_out_lbl = QLabel("₹ —")
        self.principal_out_lbl.setStyleSheet("font-weight: 700;")
        out_form.addRow("Principal Outstanding:", self.principal_out_lbl)
        self.interest_out_lbl = QLabel("₹ —")
        out_form.addRow("Accrued Interest:", self.interest_out_lbl)
        self.penalty_lbl = QLabel("₹ —")
        self.penalty_lbl.setStyleSheet("color: #DC3545;")
        out_form.addRow("Overdue Penalty:", self.penalty_lbl)
        self.total_out_lbl = QLabel("₹ —")
        self.total_out_lbl.setStyleSheet("font-weight: 800; font-size: 16px; color: #DC3545;")
        out_form.addRow("TOTAL DUE:", self.total_out_lbl)
        layout.addWidget(out_grp)

        # Payment details
        pay_form = QFormLayout()
        pay_form.setSpacing(10)

        self.payment_amount = QDoubleSpinBox()
        self.payment_amount.setRange(0.01, 9_999_999)
        self.payment_amount.setDecimals(2)
        self.payment_amount.setPrefix("₹ ")
        pay_form.addRow("Payment Amount *:", self.payment_amount)

        self.payment_date = QDateEdit()
        self.payment_date.setDate(QDate.currentDate())
        self.payment_date.setDisplayFormat("dd-MM-yyyy")
        self.payment_date.setCalendarPopup(True)
        pay_form.addRow("Payment Date *:", self.payment_date)

        self.payment_mode = QComboBox()
        self.payment_mode.addItems(["cash", "bank_transfer", "upi", "cheque", "other"])
        pay_form.addRow("Payment Mode *:", self.payment_mode)

        self.txn_ref = QLineEdit()
        self.txn_ref.setPlaceholderText("Transaction / reference number")
        pay_form.addRow("Transaction Ref:", self.txn_ref)

        self.notes = QLineEdit()
        self.notes.setPlaceholderText("Optional notes")
        pay_form.addRow("Notes:", self.notes)

        layout.addLayout(pay_form)

        # Balance preview
        self.balance_preview = QLabel("")
        self.balance_preview.setStyleSheet(
            "background: #D4EDDA; color: #155724; padding: 10px; "
            "border-radius: 6px; font-weight: 700; font-size: 13px;"
        )
        self.balance_preview.setVisible(False)
        layout.addWidget(self.balance_preview)

        self.payment_amount.valueChanged.connect(self._update_preview)

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        collect_btn = QPushButton("Collect Payment & Print Receipt")
        collect_btn.setFixedHeight(40)
        collect_btn.setObjectName("SuccessBtn")
        collect_btn.clicked.connect(self._collect)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(collect_btn)
        layout.addLayout(btn_row)

    def _load_loan(self):
        from app.services.loan_service import get_loan_service
        from app.services.repayment_service import calculate_outstanding
        from app.database.connection import get_session
        from app.models.loan import Loan

        loan = get_loan_service().get_loan(self.loan_id)
        if not loan:
            return
        self._loan_data = loan
        self.loan_num_lbl.setText(loan.get("loan_number", ""))
        self.customer_lbl.setText(f"{loan['customer_name']} | {loan['customer_mobile']}")

        with get_session() as session:
            loan_obj = session.get(Loan, self.loan_id)
            if loan_obj:
                self._outstanding = calculate_outstanding(loan_obj)

        principal = self._outstanding.get("principal", Decimal("0"))
        interest = self._outstanding.get("accrued_interest", Decimal("0"))
        penalty = self._outstanding.get("penalty", Decimal("0"))
        total = self._outstanding.get("total_outstanding", Decimal("0"))

        self.principal_out_lbl.setText(fmt_currency(principal))
        self.interest_out_lbl.setText(fmt_currency(interest))
        self.penalty_lbl.setText(fmt_currency(penalty))
        self.total_out_lbl.setText(fmt_currency(total))
        self.payment_amount.setValue(float(total))

    def _update_preview(self, amount: float):
        total = self._outstanding.get("total_outstanding", Decimal("0"))
        balance = total - Decimal(str(amount))
        if balance <= 0:
            self.balance_preview.setText("✓ Loan will be FULLY CLOSED after this payment")
            self.balance_preview.setStyleSheet(
                "background: #D4EDDA; color: #155724; padding: 10px; border-radius: 6px; font-weight: 700;"
            )
        else:
            self.balance_preview.setText(f"Remaining balance after payment: {fmt_currency(balance)}")
            self.balance_preview.setStyleSheet(
                "background: #FFF3CD; color: #856404; padding: 10px; border-radius: 6px; font-weight: 700;"
            )
        self.balance_preview.setVisible(True)

    def _collect(self):
        amount = Decimal(str(self.payment_amount.value()))
        if amount <= 0:
            QMessageBox.warning(self, "Error", "Payment amount must be positive.")
            return

        q_date = self.payment_date.date()
        pay_date = date(q_date.year(), q_date.month(), q_date.day())

        from app.services.repayment_service import get_repayment_service
        from app.ui.session_state import session

        svc = get_repayment_service()
        ok, msg, result = svc.collect_payment(
            loan_id=self.loan_id,
            total_paid=amount,
            payment_date=pay_date,
            payment_mode=self.payment_mode.currentText(),
            collected_by=session.user_id,
            transaction_ref=self.txn_ref.text().strip(),
            notes=self.notes.text().strip(),
        )
        if ok:
            from app.ui.loan_actions import open_receipt, release_collateral
            reply = QMessageBox.question(
                self, "Payment Collected",
                f"{msg}\nBalance due: {fmt_currency(result['balance_after'])}\n\n"
                "Open the receipt to print / share?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.Yes:
                open_receipt(result["id"], self)
            if result.get("loan_closed") and session.can("release_collateral"):
                ask = QMessageBox.question(
                    self, "Loan Closed",
                    "This loan is now fully repaid.\n\nRelease the pledged collateral to the customer now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if ask == QMessageBox.StandardButton.Yes:
                    release_collateral(self.loan_id, self, ask=False)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", msg)
