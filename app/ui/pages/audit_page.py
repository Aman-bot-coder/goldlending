"""Audit logs page."""
from __future__ import annotations

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QDateEdit, QFrame,
)

from app.ui.widgets.data_table import DataTable
from app.utils.formatters import fmt_datetime


class AuditPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Audit Logs")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        # Filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(12)
        self.action_filter = QLineEdit()
        self.action_filter.setPlaceholderText("Filter by action...")
        self.action_filter.setFixedWidth(180)
        filter_row.addWidget(self.action_filter)
        self.user_filter = QLineEdit()
        self.user_filter.setPlaceholderText("Filter by username...")
        self.user_filter.setFixedWidth(160)
        filter_row.addWidget(self.user_filter)
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setDisplayFormat("dd-MM-yyyy")
        self.from_date.setCalendarPopup(True)
        filter_row.addWidget(QLabel("From:"))
        filter_row.addWidget(self.from_date)
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setDisplayFormat("dd-MM-yyyy")
        self.to_date.setCalendarPopup(True)
        filter_row.addWidget(QLabel("To:"))
        filter_row.addWidget(self.to_date)
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.load_data)
        filter_row.addWidget(search_btn)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        self.table = DataTable(
            ["ID", "Date/Time", "User", "Action", "Entity", "Entity Ref", "IP Address"],
            searchable=False,
        )
        layout.addWidget(self.table)

    def load_data(self):
        from app.services.audit_service import get_audit_service
        from datetime import datetime

        from_q = self.from_date.date()
        to_q = self.to_date.date()
        from_dt = datetime(from_q.year(), from_q.month(), from_q.day(), 0, 0, 0)
        to_dt = datetime(to_q.year(), to_q.month(), to_q.day(), 23, 59, 59)

        logs = get_audit_service().get_logs(
            action_filter=self.action_filter.text().strip(),
            username=self.user_filter.text().strip(),
            from_date=from_dt,
            to_date=to_dt,
            limit=500,
        )
        rows = [
            [
                r["id"],
                fmt_datetime(r["created_at"]),
                r["username"] or "—",
                r["action"],
                r["entity_type"] or "—",
                r["entity_ref"] or r["entity_id"] or "—",
                r["ip_address"] or "—",
            ]
            for r in logs
        ]
        self.table.load_data(rows)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_data()
