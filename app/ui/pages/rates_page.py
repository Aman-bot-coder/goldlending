"""Live Gold & Silver Rates page."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox,
)

from app.utils.formatters import fmt_currency, fmt_datetime


class RatesPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._auto_refresh = QTimer()
        self._auto_refresh.timeout.connect(self._fetch_rates)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QHBoxLayout()
        title = QLabel("Live Gold & Silver Rates")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        self.status_lbl = QLabel("")
        self.status_lbl.setStyleSheet("color: #888; font-size: 12px;")
        header.addWidget(self.status_lbl)
        refresh_btn = QPushButton("↻ Fetch Live Rates")
        refresh_btn.setFixedHeight(36)
        refresh_btn.clicked.connect(self._fetch_rates)
        header.addWidget(refresh_btn)
        layout.addLayout(header)

        # Current rates
        rates_row = QHBoxLayout()
        rates_row.setSpacing(20)

        gold_frame = QFrame()
        gold_frame.setObjectName("GoldCard")
        gold_layout = QVBoxLayout(gold_frame)
        gold_layout.setSpacing(6)
        gold_icon = QLabel("🥇 Gold (24K Pure)")
        gold_icon.setStyleSheet("font-size: 15px; font-weight: 700; color: #B8860B;")
        gold_layout.addWidget(gold_icon)
        self.gold_gram = QLabel("₹ —")
        self.gold_gram.setStyleSheet("font-size: 28px; font-weight: 900; color: #FFD700;")
        gold_layout.addWidget(self.gold_gram)
        self.gold_10gram = QLabel("per 10g: ₹ —")
        self.gold_10gram.setStyleSheet("color: #888; font-size: 13px;")
        gold_layout.addWidget(self.gold_10gram)
        self.gold_freshness = QLabel("")
        self.gold_freshness.setStyleSheet("font-size: 12px; color: #28A745;")
        gold_layout.addWidget(self.gold_freshness)
        self.gold_updated = QLabel("")
        self.gold_updated.setStyleSheet("font-size: 11px; color: #aaa;")
        gold_layout.addWidget(self.gold_updated)
        rates_row.addWidget(gold_frame, 1)

        silver_frame = QFrame()
        silver_frame.setObjectName("SilverCard")
        silver_layout = QVBoxLayout(silver_frame)
        silver_layout.setSpacing(6)
        silver_icon = QLabel("🥈 Silver (999 Fine)")
        silver_icon.setStyleSheet("font-size: 15px; font-weight: 700; color: #666;")
        silver_layout.addWidget(silver_icon)
        self.silver_gram = QLabel("₹ —")
        self.silver_gram.setStyleSheet("font-size: 28px; font-weight: 900; color: #888;")
        silver_layout.addWidget(self.silver_gram)
        self.silver_10gram = QLabel("per 10g: ₹ —")
        self.silver_10gram.setStyleSheet("color: #888; font-size: 13px;")
        silver_layout.addWidget(self.silver_10gram)
        self.silver_freshness = QLabel("")
        self.silver_freshness.setStyleSheet("font-size: 12px; color: #28A745;")
        silver_layout.addWidget(self.silver_freshness)
        self.silver_updated = QLabel("")
        self.silver_updated.setStyleSheet("font-size: 11px; color: #aaa;")
        silver_layout.addWidget(self.silver_updated)
        rates_row.addWidget(silver_frame, 1)

        notice = QFrame()
        notice.setObjectName("Card")
        notice_layout = QVBoxLayout(notice)
        n = QLabel(
            "⚠  Rates shown are indicative market reference prices only.\n"
            "Actual lender valuation rates may differ and must be set by the lender.\n"
            "These prices do not constitute a price offer or guarantee.\n\n"
            "Configure your API key in Settings → Rate API Provider."
        )
        n.setWordWrap(True)
        n.setStyleSheet("color: #856404; font-size: 12px;")
        notice_layout.addWidget(n)
        rates_row.addWidget(notice, 1)
        layout.addLayout(rates_row)

        # Rate history table
        history_lbl = QLabel("Rate History (Gold)")
        history_lbl.setObjectName("SectionTitle")
        layout.addWidget(history_lbl)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels(
            ["Date/Time", "₹/gram", "₹/10g", "Source", "Status"]
        )
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setEditTriggers(self.history_table.EditTrigger.NoEditTriggers)
        self.history_table.setAlternatingRowColors(True)
        layout.addWidget(self.history_table)

    def _fetch_rates(self):
        self.status_lbl.setText("Fetching rates...")
        from app.services.rate_service import get_rate_service
        try:
            gold, silver, msg = get_rate_service().fetch_and_save()
            self.status_lbl.setText(msg)
        except Exception as exc:
            self.status_lbl.setText(f"Error: {exc}")
        self._display_rates()

    def _display_rates(self):
        from app.services.rate_service import get_rate_service
        svc = get_rate_service()
        gold = svc.get_latest_rate("gold")
        silver = svc.get_latest_rate("silver")

        if gold:
            self.gold_gram.setText(f"₹ {float(gold['rate_per_gram']):,.2f}")
            self.gold_10gram.setText(f"per 10g: ₹ {float(gold['rate_per_10gram']):,.2f}")
            stale = gold.get("is_stale", False)
            self.gold_freshness.setText("⚠ Stale Rate" if stale else "● Live Rate")
            self.gold_freshness.setStyleSheet(
                "font-size: 12px; color: #DC3545;" if stale else "font-size: 12px; color: #28A745;"
            )
            self.gold_updated.setText(f"Updated: {fmt_datetime(gold['fetched_at'])}")

        if silver:
            self.silver_gram.setText(f"₹ {float(silver['rate_per_gram']):,.2f}")
            self.silver_10gram.setText(f"per 10g: ₹ {float(silver['rate_per_10gram']):,.2f}")
            stale = silver.get("is_stale", False)
            self.silver_freshness.setText("⚠ Stale Rate" if stale else "● Live Rate")
            self.silver_freshness.setStyleSheet(
                "font-size: 12px; color: #DC3545;" if stale else "font-size: 12px; color: #28A745;"
            )
            self.silver_updated.setText(f"Updated: {fmt_datetime(silver['fetched_at'])}")

        # Load history
        history = svc.get_rate_history("gold", limit=50)
        self.history_table.setRowCount(len(history))
        for i, row in enumerate(history):
            self.history_table.setItem(i, 0, QTableWidgetItem(fmt_datetime(row["fetched_at"])))
            self.history_table.setItem(i, 1, QTableWidgetItem(f"₹ {float(row['rate_per_gram']):,.2f}"))
            self.history_table.setItem(i, 2, QTableWidgetItem(f"₹ {float(row['rate_per_10gram']):,.2f}"))
            self.history_table.setItem(i, 3, QTableWidgetItem(row["source"]))
            self.history_table.setItem(i, 4, QTableWidgetItem("Stale" if row["is_stale"] else "Live"))

    def showEvent(self, event):
        super().showEvent(event)
        self._display_rates()
        from app.config import get_config
        interval = get_config().rate_refresh_interval_minutes * 60 * 1000
        self._auto_refresh.start(interval)

    def hideEvent(self, event):
        super().hideEvent(event)
        self._auto_refresh.stop()
