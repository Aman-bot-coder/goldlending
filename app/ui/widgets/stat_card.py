"""Reusable stat card widget for the dashboard."""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatCard(QFrame):
    def __init__(
        self,
        title: str,
        value: str = "—",
        subtitle: str = "",
        icon: str = "",
        color: str = "#FFD700",
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setMinimumWidth(160)
        self.setMinimumHeight(100)

        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(16, 14, 16, 14)

        # Top row: icon + title
        top_row = QHBoxLayout()
        top_row.setSpacing(6)

        if icon:
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"font-size: 20px; color: {color};")
            top_row.addWidget(icon_lbl)

        title_lbl = QLabel(title.upper())
        title_lbl.setObjectName("StatCardTitle")
        top_row.addWidget(title_lbl)
        top_row.addStretch()
        layout.addLayout(top_row)

        # Value
        self.value_lbl = QLabel(value)
        self.value_lbl.setObjectName("StatCardValue")
        self.value_lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: 800;")
        layout.addWidget(self.value_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setObjectName("StatCardChange")
            sub_lbl.setStyleSheet("color: #888; font-size: 11px;")
            layout.addWidget(sub_lbl)

        layout.addStretch()

        # Color accent bar on top
        self.setStyleSheet(
            f"#StatCard {{ border-top: 3px solid {color}; border-radius: 12px; "
            f"background: #FFFFFF; border: 1px solid #E8E8E8; border-top: 3px solid {color}; }}"
        )

    def set_value(self, value: str):
        self.value_lbl.setText(value)
