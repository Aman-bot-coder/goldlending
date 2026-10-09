"""
Repayment collection, interest calculation, and receipt generation.
All calculations use Decimal. Financial records are never deleted — only reversed.
"""
from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Tuple

from app.config import get_config
from app.database.connection import get_session
from app.models.loan import Loan
from app.models.repayment import Repayment

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")


def _next_receipt_number(session) -> str:
    cfg = get_config()
    prefix = cfg.receipt_prefix
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    count = (
        session.query(Repayment)
        .filter(Repayment.receipt_number.like(f"{prefix}{date_str}%"))
        .count()
    )
    return f"{prefix}{date_str}{(count + 1):04d}"


def calculate_accrued_interest(
    principal: Decimal,
    annual_rate: Decimal,
    disbursement_date: date,
    as_of_date: Optional[date] = None,
    method: str = "simple",
) -> Decimal:
    as_of = as_of_date or date.today()
    days = (as_of - disbursement_date).days
    if days <= 0:
        return Decimal("0")
    if method == "simple":
        interest = principal * annual_rate / Decimal("100") * Decimal(str(days)) / Decimal("365")
        return interest.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return Decimal("0")


def calculate_outstanding(loan: Loan, as_of: Optional[date] = None) -> dict:
    today = as_of or date.today()
    principal = loan.outstanding_principal or loan.disbursed_amount or loan.principal_amount or Decimal("0")
    accrued_interest = Decimal("0")
    penalty = Decimal("0")

    if loan.disbursement_date and principal > 0:
        accrued_interest = calculate_accrued_interest(
            principal,
            loan.interest_rate or Decimal("0"),
            loan.disbursement_date,
            today,
            loan.interest_method or "simple",
        )

    if loan.maturity_date and today > loan.maturity_date:
        overdue_days = (today - loan.maturity_date).days
        cfg = get_config()
        penalty_rate = Decimal(str(cfg.overdue_penalty_rate))
        penalty = (principal * penalty_rate / Decimal("100") * Decimal(str(overdue_days)) / Decimal("365")).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    total = (principal + accrued_interest + penalty).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return {
        "principal": principal,
        "accrued_interest": accrued_interest,
        "penalty": penalty,
        "total_outstanding": total,
        "as_of_date": today,
        "days_since_disbursement": (today - loan.disbursement_date).days if loan.disbursement_date else 0,
        "overdue_days": max(0, (today - loan.maturity_date).days) if loan.maturity_date else 0,
    }


class RepaymentService:

    def collect_payment(
        self,
        loan_id: int,
        total_paid: Decimal,
        payment_date: date,
        payment_mode: str,
        collected_by: int,
        transaction_ref: str = "",
        notes: str = "",
        principal_paid: Optional[Decimal] = None,
        interest_paid: Optional[Decimal] = None,
        penalty_paid: Optional[Decimal] = None,
        fee_paid: Optional[Decimal] = None,
    ) -> Tuple[bool, str, Optional[dict]]:
        with get_session() as session:
            loan = session.get(Loan, loan_id)
            if not loan:
                return False, "Loan not found", None
            if loan.status in ("closed", "draft"):
                return False, f"Loan is {loan.status} and cannot accept payments", None

            outstanding = calculate_outstanding(loan, payment_date)
            total_owed = outstanding["total_outstanding"]

            if total_paid <= 0:
                return False, "Payment amount must be positive", None
            if total_paid > total_owed + Decimal("0.01"):
                return False, f"Payment ₹{total_paid} exceeds outstanding ₹{total_owed}", None

            # Auto-allocate if not specified
            if principal_paid is None and interest_paid is None:
                interest_paid = min(
                    outstanding["accrued_interest"] + outstanding["penalty"],
                    total_paid
                ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                principal_paid = (total_paid - interest_paid).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
                penalty_paid = Decimal("0")
                fee_paid = Decimal("0")
            else:
                principal_paid = principal_paid or Decimal("0")
                interest_paid = interest_paid or Decimal("0")
                penalty_paid = penalty_paid or Decimal("0")
                fee_paid = fee_paid or Decimal("0")

            new_principal = (loan.outstanding_principal or Decimal("0")) - principal_paid
            new_principal = max(new_principal, Decimal("0"))

            receipt_number = _next_receipt_number(session)
            repayment = Repayment(
                loan_id=loan_id,
                receipt_number=receipt_number,
                principal_paid=principal_paid,
                interest_paid=interest_paid,
                fee_paid=fee_paid,
                penalty_paid=penalty_paid,
                total_paid=total_paid,
                payment_date=payment_date,
                payment_mode=payment_mode,
                transaction_ref=transaction_ref,
                balance_principal_after=new_principal,
                balance_interest_after=Decimal("0"),
                total_outstanding_after=new_principal,
                created_by=collected_by,
                notes=notes,
            )
            session.add(repayment)

            # Update loan
            loan.outstanding_principal = new_principal
            loan.outstanding_interest = Decimal("0")
            loan.total_outstanding = new_principal

            if new_principal <= Decimal("0.01"):
                loan.status = "closed"
                from app.models.loan import LoanStatusHistory
                history = LoanStatusHistory(
                    loan_id=loan_id,
                    from_status=loan.status,
                    to_status="closed",
                    changed_by=collected_by,
                    remarks=f"Fully repaid via receipt {receipt_number}",
                )
                session.add(history)
            elif loan.status in ("active", "overdue"):
                loan.status = "partially_repaid"

            session.flush()
            receipt_id = repayment.id

        return True, f"Payment collected. Receipt: {receipt_number}", {
            "receipt_number": receipt_number,
            "id": receipt_id,
            "total_paid": total_paid,
            "balance_after": new_principal,
        }

    def reverse_payment(self, repayment_id: int, reversed_by: int, reason: str) -> Tuple[bool, str]:
        with get_session() as session:
            rep = session.get(Repayment, repayment_id)
            if not rep:
                return False, "Repayment not found"
            if rep.is_reversed:
                return False, "Already reversed"
            rep.is_reversed = True
            rep.reversal_reason = reason
            rep.reversed_by = reversed_by
            rep.reversed_at = datetime.now()
            # Restore loan balance
            loan = session.get(Loan, rep.loan_id)
            if loan:
                loan.outstanding_principal = (loan.outstanding_principal or Decimal("0")) + rep.principal_paid
                loan.total_outstanding = loan.outstanding_principal
                if loan.status == "closed":
                    loan.status = "partially_repaid"
        return True, "Payment reversed"

    def get_loan_repayments(self, loan_id: int) -> list[dict]:
        with get_session() as session:
            rows = (
                session.query(Repayment)
                .filter(Repayment.loan_id == loan_id)
                .order_by(Repayment.payment_date.asc())
                .all()
            )
            return [
                {
                    "id": r.id,
                    "receipt_number": r.receipt_number,
                    "principal_paid": r.principal_paid,
                    "interest_paid": r.interest_paid,
                    "fee_paid": r.fee_paid,
                    "penalty_paid": r.penalty_paid,
                    "total_paid": r.total_paid,
                    "payment_date": r.payment_date,
                    "payment_mode": r.payment_mode,
                    "transaction_ref": r.transaction_ref,
                    "balance_principal_after": r.balance_principal_after,
                    "is_reversed": r.is_reversed,
                }
                for r in rows
            ]


_repayment_service: Optional[RepaymentService] = None


def get_repayment_service() -> RepaymentService:
    global _repayment_service
    if _repayment_service is None:
        _repayment_service = RepaymentService()
    return _repayment_service
