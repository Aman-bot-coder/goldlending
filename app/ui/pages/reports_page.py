"""Reports page — generate and export PDF/Excel reports."""
from __future__ import annotations

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QFrame, QGroupBox, QMessageBox,
    QScrollArea, QGridLayout,
)


REPORTS = [
    ("Daily Disbursements", "daily_disbursements"),
    ("Daily Collections", "daily_collections"),
    ("Active Loans", "active_loans"),
    ("Outstanding Summary", "outstanding_summary"),
    ("Overdue Loans", "overdue_loans"),
    ("Upcoming Maturities", "upcoming_maturities"),
    ("Closed Loans", "closed_loans"),
    ("Collateral Inventory", "collateral_inventory"),
    ("Customer Account Statement", "customer_statement"),
    ("Interest Income", "interest_income"),
]


class ReportCard(QFrame):
    def __init__(self, title: str, report_key: str, on_click, parent=None):
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFixedHeight(100)
        layout = QVBoxLayout(self)
        lbl = QLabel(title)
        lbl.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(lbl)
        btn_row = QHBoxLayout()
        pdf_btn = QPushButton("PDF")
        pdf_btn.setFixedHeight(30)
        pdf_btn.setFixedWidth(70)
        pdf_btn.clicked.connect(lambda: on_click(report_key, "pdf"))
        xlsx_btn = QPushButton("Excel")
        xlsx_btn.setObjectName("SecondaryBtn")
        xlsx_btn.setFixedHeight(30)
        xlsx_btn.setFixedWidth(70)
        xlsx_btn.clicked.connect(lambda: on_click(report_key, "xlsx"))
        btn_row.addWidget(pdf_btn)
        btn_row.addWidget(xlsx_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)


class ReportsPage(QWidget):
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

        title = QLabel("Reports & Analytics")
        title.setObjectName("SectionTitle")
        layout.addWidget(title)

        # Date range
        filter_grp = QGroupBox("Date Range (applies to date-based reports)")
        filter_row = QHBoxLayout(filter_grp)
        filter_row.addWidget(QLabel("From:"))
        self.from_date = QDateEdit()
        self.from_date.setDate(QDate.currentDate().addDays(-30))
        self.from_date.setDisplayFormat("dd-MM-yyyy")
        self.from_date.setCalendarPopup(True)
        filter_row.addWidget(self.from_date)
        filter_row.addWidget(QLabel("To:"))
        self.to_date = QDateEdit()
        self.to_date.setDate(QDate.currentDate())
        self.to_date.setDisplayFormat("dd-MM-yyyy")
        self.to_date.setCalendarPopup(True)
        filter_row.addWidget(self.to_date)
        filter_row.addStretch()
        layout.addWidget(filter_grp)

        # Report cards grid
        grid = QGridLayout()
        grid.setSpacing(16)
        for idx, (report_name, report_key) in enumerate(REPORTS):
            row, col = divmod(idx, 3)
            card = ReportCard(report_name, report_key, self._generate)
            grid.addWidget(card, row, col)
        layout.addLayout(grid)
        layout.addStretch()

    def _get_date_range(self):
        from datetime import datetime
        fq = self.from_date.date()
        tq = self.to_date.date()
        return (
            datetime(fq.year(), fq.month(), fq.day()),
            datetime(tq.year(), tq.month(), tq.day(), 23, 59, 59),
        )

    def _generate(self, report_key: str, fmt: str):
        from PySide6.QtWidgets import QFileDialog
        from datetime import datetime
        import os

        from_dt, to_dt = self._get_date_range()

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Save {report_key} Report",
            f"{report_key}_{datetime.now().strftime('%Y%m%d')}.{fmt}",
            "PDF Files (*.pdf)" if fmt == "pdf" else "Excel Files (*.xlsx)",
        )
        if not save_path:
            return

        try:
            if fmt == "pdf":
                self._generate_pdf(report_key, from_dt, to_dt, save_path)
            else:
                self._generate_xlsx(report_key, from_dt, to_dt, save_path)
            QMessageBox.information(self, "Success", f"Report saved:\n{save_path}")
            if os.name == "nt":
                os.startfile(save_path)
        except Exception as exc:
            QMessageBox.warning(self, "Error", f"Report generation failed:\n{exc}")

    def _generate_pdf(self, report_key: str, from_dt, to_dt, path: str):
        from app.utils.pdf_generator import generate_report_pdf
        generate_report_pdf(report_key, from_dt, to_dt, path)

    def _generate_xlsx(self, report_key: str, from_dt, to_dt, path: str):
        from app.utils.excel_exporter import generate_report_xlsx
        generate_report_xlsx(report_key, from_dt, to_dt, path)
