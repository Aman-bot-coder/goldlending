"""User create/edit dialog."""
from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QFormLayout, QMessageBox,
)

from app.utils.validators import validate_username, validate_email


class UserDialog(QDialog):
    def __init__(self, user_id: Optional[int] = None, parent=None):
        super().__init__(parent)
        self.user_id = user_id
        self.is_edit = user_id is not None
        self.setWindowTitle("Edit User" if self.is_edit else "New User")
        self.setFixedSize(440, 380)
        self._setup_ui()
        if self.is_edit:
            self._load_data()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 20)

        form = QFormLayout()
        form.setSpacing(10)

        self.username = QLineEdit()
        self.username.setPlaceholderText("username (letters, digits, _ - .)")
        form.addRow("Username *:", self.username)

        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText("Full name")
        form.addRow("Full Name *:", self.full_name)

        self.email = QLineEdit()
        self.email.setPlaceholderText("email@example.com")
        form.addRow("Email *:", self.email)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText("Mobile number")
        form.addRow("Phone:", self.phone)

        self.role = QComboBox()
        self.role.addItems(["lender", "admin", "viewer"])
        form.addRow("Role *:", self.role)

        layout.addLayout(form)

        info = QLabel(
            "A temporary password will be generated and shown after saving.\n"
            "The user must change it on first login."
        )
        info.setStyleSheet("color: #888; font-size: 12px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        btn_row = QHBoxLayout()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("SecondaryBtn")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Save")
        save.setFixedHeight(38)
        save.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addStretch()
        btn_row.addWidget(save)
        layout.addLayout(btn_row)

    def _load_data(self):
        from app.services.auth_service import get_auth_service
        data = get_auth_service().get_user_by_id(self.user_id)
        if not data:
            return
        self.username.setText(data.get("username", ""))
        self.username.setEnabled(False)
        self.full_name.setText(data.get("full_name", ""))
        self.email.setText(data.get("email", ""))
        self.phone.setText(data.get("phone", "") or "")
        idx = self.role.findText(data.get("role", "lender"))
        if idx >= 0:
            self.role.setCurrentIndex(idx)

    def _save(self):
        username = self.username.text().strip()
        full_name = self.full_name.text().strip()
        email = self.email.text().strip()
        role = self.role.currentText()

        if not full_name:
            QMessageBox.warning(self, "Error", "Full name is required.")
            return

        from app.services.auth_service import get_auth_service
        from app.ui.session_state import session

        svc = get_auth_service()
        if self.is_edit:
            ok, msg = svc.update_user(
                session.user_id, self.user_id,
                full_name=full_name, email=email,
                phone=self.phone.text().strip(), role=role,
            )
            QMessageBox.information(self, "Result", msg) if ok else QMessageBox.warning(self, "Error", msg)
            if ok:
                self.accept()
        else:
            err = validate_username(username)
            if err:
                QMessageBox.warning(self, "Error", err)
                return
            err = validate_email(email)
            if err:
                QMessageBox.warning(self, "Error", err)
                return
            ok, msg, user = svc.create_user(
                session.user_id, username, email, full_name, role,
                phone=self.phone.text().strip(),
            )
            if ok:
                QMessageBox.information(self, "User Created", msg)
                self.accept()
            else:
                QMessageBox.warning(self, "Error", msg)
