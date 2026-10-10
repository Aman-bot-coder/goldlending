"""UI helpers shared by the loans, repayments and payment screens."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox, QWidget


def build_receipt(repayment_id: int) -> Optional[Path]:
    from app.config import RECEIPT_DIR
    from app.services.customer_service import get_customer_service
    from app.services.loan_service import get_loan_service
    from app.services.repayment_service import get_repayment_service
    from app.utils.pdf_generator import generate_repayment_receipt

    rep = get_repayment_service().get_repayment(repayment_id)
    if not rep:
        return None
    loan = get_loan_service().get_loan(rep["loan_id"]) or {}
    customer = get_customer_service().get_customer(loan.get("customer_id")) or {}
    suffix = "_REVERSED" if rep["is_reversed"] else ""
    path = RECEIPT_DIR / f"{rep['receipt_number']}{suffix}.pdf"
    generate_repayment_receipt(rep, loan, customer, str(path))
    return path


def open_receipt(repayment_id: int, parent: QWidget) -> None:
    try:
        path = build_receipt(repayment_id)
    except Exception as exc:
        QMessageBox.critical(parent, "Receipt Error", f"Could not create receipt: {exc}")
        return
    if not path:
        QMessageBox.warning(parent, "Receipt", "Payment not found.")
        return
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
        QMessageBox.information(parent, "Receipt Saved", f"Receipt saved to:\n{path}")


def release_collateral(loan_id: int, parent: QWidget, ask: bool = True) -> bool:
    from app.services.loan_service import get_loan_service
    from app.ui.session_state import session

    if not session.can("release_collateral"):
        QMessageBox.warning(parent, "Access Denied", "Only an admin can release collateral.")
        return False
    if ask:
        reply = QMessageBox.question(
            parent, "Release Collateral",
            "Hand all pledged items of this loan back to the customer?\n\n"
            "Make sure the customer has received every item before confirming.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False
    ok, msg = get_loan_service().release_collateral(loan_id, session.user_id)
    if ok:
        QMessageBox.information(parent, "Collateral Released", msg)
    else:
        QMessageBox.warning(parent, "Cannot Release", msg)
    return ok
