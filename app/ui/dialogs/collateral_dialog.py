"""Collateral item entry dialog with live valuation calculation."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QTextEdit, QFormLayout, QGroupBox, QCheckBox,
    QDoubleSpinBox, QMessageBox,
)

from app.utils.formatters import fmt_currency


class CollateralItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Collateral Item")
        self.setMinimumSize(540, 540)
        self.resize(560, 580)
        self._data: dict = {}
        self._setup_ui()
        self._load_current_rate()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 16)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.metal_type = QComboBox()
        self.metal_type.addItems(["gold", "silver"])
        self.metal_type.currentIndexChanged.connect(self._on_metal_changed)
        form.addRow("Metal Type *:", self.metal_type)

        self.item_category = QComboBox()
        self.item_category.addItems(["ring", "chain", "necklace", "bracelet", "coin", "bar", "utensils", "other"])
        form.addRow("Category *:", self.item_category)

        self.gross_weight = QDoubleSpinBox()
        self.gross_weight.setRange(0.001, 9999.999)
        self.gross_weight.setDecimals(3)
        self.gross_weight.setSuffix(" g")
        self.gross_weight.valueChanged.connect(self._recalculate)
        form.addRow("Gross Weight *:", self.gross_weight)

        self.stone_weight = QDoubleSpinBox()
        self.stone_weight.setRange(0, 9999.999)
        self.stone_weight.setDecimals(3)
        self.stone_weight.setSuffix(" g")
        self.stone_weight.valueChanged.connect(self._recalculate)
        form.addRow("Stone/Deduction Wt:", self.stone_weight)

        self.net_weight_lbl = QLabel("0.000 g")
        self.net_weight_lbl.setStyleSheet("font-weight: 700; color: #1A1A2E;")
        form.addRow("Net Metal Weight:", self.net_weight_lbl)

        self.purity = QComboBox()
        self.purity.addItems(["24K", "22K", "20K", "18K", "14K", "Custom"])
        self.purity.currentIndexChanged.connect(self._recalculate)
        form.addRow("Purity *:", self.purity)

        self.assayed = QCheckBox("Assayed / Lab Verified")
        form.addRow("", self.assayed)

        self.market_rate = QDoubleSpinBox()
        self.market_rate.setRange(0, 999999.9999)
        self.market_rate.setDecimals(2)
        self.market_rate.setPrefix("₹ ")
        self.market_rate.setSuffix("/g")
        self.market_rate.valueChanged.connect(self._recalculate)
        form.addRow("Market Rate (₹/g):", self.market_rate)

        haircut_row = QHBoxLayout()
        self.haircut = QDoubleSpinBox()
        self.haircut.setRange(0, 50)
        self.haircut.setDecimals(1)
        self.haircut.setSuffix(" %")
        self.haircut.valueChanged.connect(self._recalculate)
        haircut_row.addWidget(self.haircut)
        haircut_row.addWidget(QLabel("valuation discount"))
        haircut_row.addStretch()
        form.addRow("Haircut %:", haircut_row)

        self.valuation_rate_lbl = QLabel("—")
        self.valuation_rate_lbl.setStyleSheet("font-weight: 700;")
        form.addRow("Effective Rate:", self.valuation_rate_lbl)

        # Calculation breakdown
        calc_grp = QGroupBox("Valuation Breakdown")
        calc_grp.setStyleSheet("QGroupBox { background: #FFF8E1; }")
        calc_layout = QFormLayout(calc_grp)
        self.pure_weight_lbl = QLabel("—")
        calc_layout.addRow("Pure Metal Equiv:", self.pure_weight_lbl)
        self.indicative_value_lbl = QLabel("—")
        self.indicative_value_lbl.setStyleSheet("font-size: 16px; font-weight: 800; color: #FFD700;")
        calc_layout.addRow("Indicative Value:", self.indicative_value_lbl)
        layout.addLayout(form)
        layout.addWidget(calc_grp)

        # Admin fields
        admin_form = QFormLayout()
        self.tag_number = QLineEdit()
        self.tag_number.setPlaceholderText("Collateral packet tag")
        admin_form.addRow("Tag Number:", self.tag_number)
        self.storage_location = QLineEdit()
        self.storage_location.setPlaceholderText("e.g. Locker A-12")
        admin_form.addRow("Storage Location:", self.storage_location)
        self.description = QTextEdit()
        self.description.setFixedHeight(50)
        self.description.setPlaceholderText("Item description / appraiser remarks")
        admin_form.addRow("Description:", self.description)
        layout.addLayout(admin_form)

        # Stale rate warning
        self.stale_warning = QLabel("")
        self.stale_warning.setStyleSheet(
            "background: #F8D7DA; color: #721C24; padding: 8px; border-radius: 4px; font-size: 12px;"
        )
        self.stale_warning.setWordWrap(True)
        self.stale_warning.setVisible(False)
        layout.addWidget(self.stale_warning)

        # Buttons
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        add_btn = QPushButton("Add to Loan")
        add_btn.setFixedHeight(38)
        add_btn.clicked.connect(self._add)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

    def _load_current_rate(self):
        try:
            from app.services.rate_service import get_rate_service
            metal = self.metal_type.currentText()
            rate = get_rate_service().get_latest_rate(metal)
            if rate:
                self.market_rate.setValue(float(rate["rate_per_gram"]))
                if rate.get("is_stale"):
                    self.stale_warning.setText(
                        f"⚠  Rate is stale (last updated {rate['fetched_at'].strftime('%d-%m-%Y %H:%M')}). "
                        "Please confirm valuation or refresh rates before proceeding."
                    )
                    self.stale_warning.setVisible(True)
                else:
                    self.stale_warning.setVisible(False)
        except Exception:
            pass

    def _on_metal_changed(self):
        metal = self.metal_type.currentText()
        self.purity.clear()
        if metal == "gold":
            self.purity.addItems(["24K", "22K", "20K", "18K", "14K", "Custom"])
        else:
            self.purity.addItems(["999", "925", "800", "Custom"])
        self._load_current_rate()

    def _recalculate(self):
        gross = Decimal(str(self.gross_weight.value()))
        stone = Decimal(str(self.stone_weight.value()))
        net = gross - stone
        if net < 0:
            net = Decimal("0")
        self.net_weight_lbl.setText(f"{net:.3f} g")

        market = Decimal(str(self.market_rate.value()))
        haircut = Decimal(str(self.haircut.value()))
        val_rate = market * (Decimal("1") - haircut / Decimal("100"))
        self.valuation_rate_lbl.setText(f"₹ {val_rate:.2f}/g")

        from app.services.loan_service import calculate_collateral_value
        purity = self.purity.currentText()
        metal = self.metal_type.currentText()
        pure_weight, indicative = calculate_collateral_value(net, purity, metal, val_rate)
        self.pure_weight_lbl.setText(f"{pure_weight:.4f} g")
        self.indicative_value_lbl.setText(fmt_currency(indicative))
        self._current_calc = {
            "net_weight": net,
            "pure_weight": pure_weight,
            "indicative_value": indicative,
            "valuation_rate": val_rate,
            "market_rate": market,
        }

    def _add(self):
        if self.gross_weight.value() <= 0:
            QMessageBox.warning(self, "Error", "Gross weight must be greater than zero.")
            return
        if self.market_rate.value() <= 0:
            QMessageBox.warning(self, "Error", "Rate must be greater than zero.")
            return
        if self.stale_warning.isVisible():
            reply = QMessageBox.question(
                self, "Stale Rate",
                "The metal rate is stale. Confirm valuation with this rate?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        calc = getattr(self, "_current_calc", {})
        self._data = {
            "metal_type": self.metal_type.currentText(),
            "item_category": self.item_category.currentText(),
            "gross_weight": Decimal(str(self.gross_weight.value())),
            "stone_weight": Decimal(str(self.stone_weight.value())),
            "net_weight": calc.get("net_weight", Decimal("0")),
            "purity": self.purity.currentText(),
            "assayed": self.assayed.isChecked(),
            "market_rate": calc.get("market_rate", Decimal("0")),
            "valuation_rate": calc.get("valuation_rate", Decimal("0")),
            "pure_weight": calc.get("pure_weight", Decimal("0")),
            "indicative_value": calc.get("indicative_value", Decimal("0")),
            "tag_number": self.tag_number.text().strip() or None,
            "storage_location": self.storage_location.text().strip(),
            "description": self.description.toPlainText().strip(),
        }
        self.accept()

    def get_data(self) -> dict:
        return self._data
