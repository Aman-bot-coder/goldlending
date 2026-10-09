"""Customers & KYC management page."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QComboBox, QFrame, QDialog,
)

from app.ui.widgets.data_table import DataTable
from app.utils.formatters import fmt_date, fmt_phone


class CustomersPage(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QHBoxLayout()
        title = QLabel("Customers & KYC")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()

        new_btn = QPushButton("+ New Customer")
        new_btn.setFixedHeight(36)
        new_btn.clicked.connect(self._new_customer)
        header.addWidget(new_btn)
        layout.addLayout(header)

        # Filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        kyc_filter_lbl = QLabel("KYC Status:")
        kyc_filter_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #555;")
        filter_row.addWidget(kyc_filter_lbl)
        self.kyc_filter = QComboBox()
        self.kyc_filter.addItems(["All", "Pending", "Verified", "Rejected"])
        self.kyc_filter.setFixedWidth(130)
        self.kyc_filter.currentIndexChanged.connect(self.load_data)
        filter_row.addWidget(self.kyc_filter)
        filter_row.addStretch()
        self.total_label = QLabel("0 customers")
        self.total_label.setStyleSheet("color: #888; font-size: 12px;")
        filter_row.addWidget(self.total_label)
        layout.addLayout(filter_row)

        # Table
        self.table = DataTable(
            ["ID", "Customer ID", "Name", "Mobile", "City", "KYC Type", "KYC Status", "Registered"],
        )
        self.table.row_double_clicked.connect(self._open_customer)
        layout.addWidget(self.table)

        # Bottom action bar
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        view_btn = QPushButton("View / Edit")
        view_btn.setObjectName("SecondaryBtn")
        view_btn.clicked.connect(lambda: self._open_customer(self.table.table.currentRow()))
        verify_btn = QPushButton("Verify KYC")
        verify_btn.setObjectName("SuccessBtn")
        verify_btn.clicked.connect(self._verify_kyc)
        btn_row.addWidget(view_btn)
        btn_row.addWidget(verify_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def load_data(self):
        from app.services.customer_service import get_customer_service
        kyc_map = {"All": "", "Pending": "pending", "Verified": "verified", "Rejected": "rejected"}
        kyc_filter = kyc_map.get(self.kyc_filter.currentText(), "")

        customers = get_customer_service().search_customers(kyc_status=kyc_filter, limit=500)
        self.total_label.setText(f"{len(customers)} customers")
        rows = [
            [
                c["id"],
                c["customer_id"],
                c["full_name"],
                fmt_phone(c["mobile"]),
                c["city"] or "—",
                (c["kyc_type"] or "—").replace("_", " ").title(),
                (c["kyc_status"] or "—").title(),
                fmt_date(c["created_at"]),
            ]
            for c in customers
        ]
        self.table.load_data(rows)

    def _new_customer(self):
        from app.ui.dialogs.customer_dialog import CustomerDialog
        dlg = CustomerDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _open_customer(self, row_index: int):
        row_data = self.table.get_selected_row_data()
        if not row_data:
            return
        customer_db_id = row_data[0]
        from app.ui.dialogs.customer_dialog import CustomerDialog
        dlg = CustomerDialog(customer_id=customer_db_id, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _verify_kyc(self):
        row_data = self.table.get_selected_row_data()
        if not row_data:
            QMessageBox.warning(self, "No Selection", "Please select a customer first.")
            return
        customer_db_id = row_data[0]
        name = row_data[2]
        reply = QMessageBox.question(
            self, "Verify KYC",
            f"Mark KYC as Verified for {name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            from app.services.customer_service import get_customer_service
            from app.ui.session_state import session
            ok, msg = get_customer_service().verify_kyc(customer_db_id, session.user_id, "verified")
            if ok:
                QMessageBox.information(self, "Success", msg)
                self.load_data()
            else:
                QMessageBox.warning(self, "Error", msg)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()
