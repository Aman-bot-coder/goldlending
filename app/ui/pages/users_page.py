"""User management page (admin only)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QMessageBox, QDialog,
)

from app.ui.widgets.data_table import DataTable
from app.utils.formatters import fmt_datetime


class UsersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        header = QHBoxLayout()
        title = QLabel("User Management")
        title.setObjectName("SectionTitle")
        header.addWidget(title)
        header.addStretch()
        new_btn = QPushButton("+ New User")
        new_btn.setFixedHeight(36)
        new_btn.clicked.connect(self._new_user)
        header.addWidget(new_btn)
        layout.addLayout(header)

        self.table = DataTable(
            ["ID", "Username", "Full Name", "Email", "Role", "Active", "Last Login", "Created"]
        )
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        edit_btn = QPushButton("Edit User")
        edit_btn.setObjectName("SecondaryBtn")
        edit_btn.clicked.connect(self._edit_user)
        disable_btn = QPushButton("Disable/Enable")
        disable_btn.setObjectName("DangerBtn")
        disable_btn.clicked.connect(self._toggle_user)
        reset_btn = QPushButton("Reset Password")
        reset_btn.clicked.connect(self._reset_pw)
        btn_row.addWidget(edit_btn)
        btn_row.addWidget(disable_btn)
        btn_row.addWidget(reset_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def load_data(self):
        from app.services.auth_service import get_auth_service
        users = get_auth_service().list_users()
        rows = [
            [
                u["id"],
                u["username"],
                u["full_name"],
                u["email"],
                u["role"].title(),
                "Yes" if u["is_active"] else "No",
                fmt_datetime(u["last_login"]),
                fmt_datetime(u["created_at"]),
            ]
            for u in users
        ]
        self.table.load_data(rows)

    def _new_user(self):
        from app.ui.dialogs.user_dialog import UserDialog
        dlg = UserDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _edit_user(self):
        row = self.table.get_selected_row_data()
        if not row:
            QMessageBox.warning(self, "No Selection", "Select a user first.")
            return
        from app.ui.dialogs.user_dialog import UserDialog
        dlg = UserDialog(user_id=row[0], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.load_data()

    def _toggle_user(self):
        row = self.table.get_selected_row_data()
        if not row:
            QMessageBox.warning(self, "No Selection", "Select a user first.")
            return
        user_id, username, _, _, _, is_active_str = row[:6]
        is_active = is_active_str == "Yes"
        from app.services.auth_service import get_auth_service
        from app.ui.session_state import session
        ok, msg = get_auth_service().update_user(
            session.user_id, user_id, is_active=not is_active
        )
        QMessageBox.information(self, "Result", msg) if ok else QMessageBox.warning(self, "Error", msg)
        if ok:
            self.load_data()

    def _reset_pw(self):
        row = self.table.get_selected_row_data()
        if not row:
            QMessageBox.warning(self, "No Selection", "Select a user first.")
            return
        user_id, username = row[0], row[1]
        reply = QMessageBox.question(
            self, "Reset Password",
            f"Reset password for {username}? A temporary password will be generated.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        from app.services.auth_service import get_auth_service
        from app.ui.session_state import session
        ok, msg, temp_pw = get_auth_service().admin_reset_password(session.user_id, user_id)
        if ok:
            QMessageBox.information(self, "Password Reset",
                f"{msg}\n\nTemporary password: {temp_pw}\n\nUser must change on next login.")
        else:
            QMessageBox.warning(self, "Error", msg)

    def showEvent(self, event):
        super().showEvent(event)
        from app.ui.session_state import session
        if session.is_admin:
            self.load_data()
        else:
            QMessageBox.warning(self, "Unauthorized", "Admin access required.")
