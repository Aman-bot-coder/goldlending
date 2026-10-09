"""Customer create/edit dialog with full KYC fields."""
from __future__ import annotations

import os
from datetime import date
from typing import Optional

from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QDateEdit, QTextEdit, QFormLayout, QGroupBox, QScrollArea,
    QWidget, QFrame, QFileDialog, QMessageBox, QTabWidget,
)

from app.utils.validators import validate_mobile, validate_pincode
from app.utils.formatters import INDIAN_STATES


class CustomerDialog(QDialog):
    def __init__(self, customer_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.is_edit = customer_id is not None
        self.setWindowTitle("Edit Customer" if self.is_edit else "New Customer")
        self.setMinimumSize(700, 580)
        self.resize(740, 620)
        self._photo_path = ""
        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ---- Tab 1: Personal Info ----
        personal_tab = QWidget()
        personal_layout = QVBoxLayout(personal_tab)
        personal_layout.setContentsMargins(16, 16, 16, 16)
        personal_layout.setSpacing(12)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Full legal name")
        form.addRow("Full Name *:", self.full_name)

        self.father_spouse = QLineEdit()
        self.father_spouse.setPlaceholderText("Father's or spouse's name")
        form.addRow("Father/Spouse:", self.father_spouse)

        self.dob = QDateEdit()
        self.dob.setDisplayFormat("dd-MM-yyyy")
        self.dob.setCalendarPopup(True)
        self.dob.setDate(QDate(1990, 1, 1))
        form.addRow("Date of Birth:", self.dob)

        self.mobile = QLineEdit()
        self.mobile.setPlaceholderText("10-digit mobile number")
        self.mobile.setMaxLength(10)
        form.addRow("Mobile *:", self.mobile)

        self.alt_mobile = QLineEdit()
        self.alt_mobile.setPlaceholderText("Alternate number (optional)")
        self.alt_mobile.setMaxLength(10)
        form.addRow("Alt Mobile:", self.alt_mobile)

        personal_layout.addLayout(form)

        address_grp = QGroupBox("Address")
        addr_form = QFormLayout(address_grp)
        addr_form.setSpacing(8)

        self.address = QTextEdit()
        self.address.setPlaceholderText("Street address")
        self.address.setFixedHeight(60)
        addr_form.addRow("Address:", self.address)

        addr_row = QHBoxLayout()
        self.city = QLineEdit()
        self.city.setPlaceholderText("City")
        self.pincode = QLineEdit()
        self.pincode.setPlaceholderText("Pincode")
        self.pincode.setMaxLength(6)
        addr_row.addWidget(self.city, 2)
        addr_row.addWidget(self.pincode, 1)
        addr_form.addRow("City / PIN:", addr_row)

        self.state = QComboBox()
        self.state.addItem("Select State")
        self.state.addItems(INDIAN_STATES)
        addr_form.addRow("State:", self.state)

        personal_layout.addWidget(address_grp)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText("Internal notes")
        self.notes.setFixedHeight(50)
        form2 = QFormLayout()
        form2.addRow("Notes:", self.notes)
        personal_layout.addLayout(form2)
        personal_layout.addStretch()

        tabs.addTab(personal_tab, "Personal Info")

        # ---- Tab 2: KYC ----
        kyc_tab = QWidget()
        kyc_layout = QVBoxLayout(kyc_tab)
        kyc_layout.setContentsMargins(16, 16, 16, 16)
        kyc_layout.setSpacing(12)

        kyc_form = QFormLayout()
        kyc_form.setSpacing(10)

        self.kyc_type = QComboBox()
        self.kyc_type.addItems([
            "Select KYC Type", "aadhaar", "pan", "voter_id",
            "passport", "driving_licence", "other"
        ])
        kyc_form.addRow("KYC Type:", self.kyc_type)

        self.kyc_ref = QLineEdit()
        self.kyc_ref.setPlaceholderText("Document reference (stored encrypted)")
        kyc_form.addRow("Document Ref:", self.kyc_ref)

        self.kyc_status = QComboBox()
        self.kyc_status.addItems(["pending", "verified", "rejected"])
        kyc_form.addRow("KYC Status:", self.kyc_status)

        kyc_layout.addLayout(kyc_form)

        # Photo
        photo_grp = QGroupBox("Customer Photograph")
        photo_row = QHBoxLayout(photo_grp)
        self.photo_lbl = QLabel("No photo selected")
        self.photo_lbl.setStyleSheet("color: #888; font-size: 12px;")
        photo_btn = QPushButton("Browse...")
        photo_btn.setObjectName("SecondaryBtn")
        photo_btn.clicked.connect(self._browse_photo)
        photo_row.addWidget(self.photo_lbl)
        photo_row.addWidget(photo_btn)
        kyc_layout.addWidget(photo_grp)

        notice = QLabel(
            "⚠  Document references are stored encrypted. "
            "Aadhaar numbers are masked for display. "
            "Ensure customer consent is obtained before collecting KYC documents."
        )
        notice.setWordWrap(True)
        notice.setStyleSheet(
            "background: #FFF3CD; color: #856404; padding: 10px; border-radius: 6px; font-size: 12px;"
        )
        kyc_layout.addWidget(notice)
        kyc_layout.addStretch()

        tabs.addTab(kyc_tab, "KYC Documents")

        # ---- Buttons ----
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(16, 12, 16, 16)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("SecondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save Customer")
        save_btn.setFixedHeight(38)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        layout.addLayout(btn_row)

    def _browse_photo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Photo", "", "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if path:
            self._photo_path = path
            self.photo_lbl.setText(os.path.basename(path))

    def _load_data(self):
        from app.services.customer_service import get_customer_service
        data = get_customer_service().get_customer(self.customer_id)
        if not data:
            return
        self.full_name.setText(data.get("full_name", ""))
        self.father_spouse.setText(data.get("father_spouse_name", "") or "")
        if data.get("date_of_birth"):
            d = data["date_of_birth"]
            self.dob.setDate(QDate(d.year, d.month, d.day))
        self.mobile.setText(data.get("mobile", ""))
        self.alt_mobile.setText(data.get("alt_mobile", "") or "")
        self.address.setPlainText(data.get("address", "") or "")
        self.city.setText(data.get("city", "") or "")
        self.pincode.setText(data.get("pincode", "") or "")
        state = data.get("state", "")
        idx = self.state.findText(state)
        if idx >= 0:
            self.state.setCurrentIndex(idx)
        self.notes.setPlainText(data.get("notes", "") or "")
        kyc_type = data.get("kyc_type", "")
        idx = self.kyc_type.findText(kyc_type)
        if idx >= 0:
            self.kyc_type.setCurrentIndex(idx)
        kyc_status = data.get("kyc_status", "pending")
        idx = self.kyc_status.findText(kyc_status)
        if idx >= 0:
            self.kyc_status.setCurrentIndex(idx)
        if data.get("photo_path"):
            self.photo_lbl.setText(os.path.basename(data["photo_path"]))
            self._photo_path = data["photo_path"]

    def _validate(self) -> Optional[str]:
        if not self.full_name.text().strip():
            return "Full name is required."
        mobile = self.mobile.text().strip()
        if not mobile or not validate_mobile(mobile):
            return "Enter a valid 10-digit mobile number."
        pincode = self.pincode.text().strip()
        if pincode and not validate_pincode(pincode):
            return "Enter a valid 6-digit PIN code."
        return None

    def _save(self):
        err = self._validate()
        if err:
            QMessageBox.warning(self, "Validation Error", err)
            return

        from app.services.customer_service import get_customer_service
        from app.ui.session_state import session
        from datetime import date as dt_date

        dob = self.dob.date().toPython() if self.dob.date().isValid() else None
        kyc_type = self.kyc_type.currentText()
        if kyc_type == "Select KYC Type":
            kyc_type = None

        kwargs = dict(
            father_spouse_name=self.father_spouse.text().strip() or None,
            date_of_birth=dob,
            alt_mobile=self.alt_mobile.text().strip() or None,
            address=self.address.toPlainText().strip() or None,
            city=self.city.text().strip() or None,
            state=self.state.currentText() if self.state.currentIndex() > 0 else None,
            pincode=self.pincode.text().strip() or None,
            photo_path=self._photo_path or None,
            kyc_type=kyc_type,
            kyc_ref=self.kyc_ref.text().strip() or None,
            kyc_status=self.kyc_status.currentText(),
            notes=self.notes.toPlainText().strip() or None,
        )

        svc = get_customer_service()
        if self.is_edit:
            ok, msg = svc.update_customer(self.customer_id, session.user_id, **kwargs)
        else:
            ok, msg, _ = svc.create_customer(
                full_name=self.full_name.text().strip(),
                mobile=self.mobile.text().strip(),
                created_by=session.user_id,
                **kwargs,
            )

        if ok:
            QMessageBox.information(self, "Success", msg)
            self.accept()
        else:
            QMessageBox.warning(self, "Error", msg)
