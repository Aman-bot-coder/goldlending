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
from app.services.audit_service import audit
from app.models.loan import Loan, LoanStatusHistory
from app.models.repayment import Repayment

logger = logging.getLogger(__name__)

TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
PAYABLE_STATUSES = ("active", "partially_repaid", "overdue", "auction_review")


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


def _last_active_repayment(loan: Loan) -> Optional[Repayment]:
    active = [r for r in (loan.repayments or []) if not r.is_reversed]
    if not active:
        return None
    return max(active, key=lambda r: (r.payment_date, r.id or 0))


def calculate_outstanding(loan: Loan, as_of: Optional[date] = None) -> dict:
    """
    Interest/penalty accrue only from the last payment (or disbursement) date.
    Unpaid interest from earlier payments is carried forward via
    Repayment.balance_interest_after, so nothing is ever charged twice.
    """
    today = as_of or date.today()
    principal = loan.outstanding_principal
    if principal is None:
        principal = loan.disbursed_amount or loan.principal_amount or Decimal("0")

    last = _last_active_repayment(loan)
    start = last.payment_date if last else loan.disbursement_date
    carried = (last.balance_interest_after or Decimal("0")) if last else Decimal("0")

    new_interest = Decimal("0")
    penalty = Decimal("0")
    if start and principal > 0:
        new_interest = calculate_accrued_interest(
            principal,
            loan.interest_rate or Decimal("0"),
            start,
            today,
            loan.interest_method or "simple",
        )
        if loan.maturity_date and today > loan.maturity_date:
            penalty_from = max(loan.maturity_date, start)
            penalty_days = (today - penalty_from).days
            if penalty_days > 0:
                rate = Decimal(str(get_config().overdue_penalty_rate))
                penalty = (
                    principal * rate / Decimal("100") * Decimal(str(penalty_days)) / Decimal("365")
                ).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

    accrued_interest = (carried + new_interest).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    total = (principal + accrued_interest + penalty).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
    return {
        "principal": principal,
        "accrued_interest": accrued_interest,
        "penalty": penalty,
        "total_outstanding": total,
        "as_of_date": today,
        "interest_from_date": start,
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
            if loan.status not in PAYABLE_STATUSES:
                return False, f"Loan is '{loan.status}' and cannot accept payments", None
            if total_paid <= 0:
                return False, "Payment amount must be positive", None
            if loan.disbursement_date and payment_date < loan.disbursement_date:
                return False, "Payment date cannot be before the disbursement date", None
            last = _last_active_repayment(loan)
            if last and payment_date < last.payment_date:
                return False, (
                    f"Payment date cannot be earlier than the last payment "
                    f"({last.payment_date:%d-%m-%Y})"
                ), None

            outstanding = calculate_outstanding(loan, payment_date)
            total_owed = outstanding["total_outstanding"]
            if total_paid > total_owed + Decimal("0.01"):
                return False, f"Payment ₹{total_paid} exceeds outstanding ₹{total_owed}", None

            interest_due = outstanding["accrued_interest"]
            penalty_due = outstanding["penalty"]

            if principal_paid is None and interest_paid is None:
                # Penalty first, then interest, then principal.
                penalty_paid = min(penalty_due, total_paid)
                interest_paid = min(interest_due, total_paid - penalty_paid)
                principal_paid = total_paid - penalty_paid - interest_paid
                fee_paid = Decimal("0")
            else:
                principal_paid = principal_paid or Decimal("0")
                interest_paid = interest_paid or Decimal("0")
                penalty_paid = penalty_paid or Decimal("0")
                fee_paid = fee_paid or Decimal("0")

            principal_paid = principal_paid.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            interest_paid = interest_paid.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)
            penalty_paid = penalty_paid.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

            old_principal = outstanding["principal"]
            new_principal = max(old_principal - principal_paid, Decimal("0"))
            interest_after = max(interest_due + penalty_due - interest_paid - penalty_paid, Decimal("0"))
            total_after = (new_principal + interest_after).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)

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
                balance_interest_after=interest_after,
                total_outstanding_after=total_after,
                created_by=collected_by,
                notes=notes,
            )
            session.add(repayment)

            loan.outstanding_principal = new_principal
            loan.outstanding_interest = interest_after
            loan.total_outstanding = total_after

            old_status = loan.status
            if total_after <= Decimal("0.01"):
                loan.status = "closed"
            elif loan.status == "active":
                loan.status = "partially_repaid"
            if loan.status != old_status:
                session.add(LoanStatusHistory(
                    loan_id=loan_id,
                    from_status=old_status,
                    to_status=loan.status,
                    changed_by=collected_by,
                    remarks=f"Payment receipt {receipt_number}",
                ))

            session.flush()
            receipt_id = repayment.id
            loan_number = loan.loan_number
            closed = loan.status == "closed"

        audit("PAYMENT_COLLECTED", "repayment", receipt_id, receipt_number,
              new_value={"loan": loan_number, "amount": total_paid, "mode": payment_mode})

        return True, f"Payment collected. Receipt: {receipt_number}", {
            "receipt_number": receipt_number,
            "id": receipt_id,
            "total_paid": total_paid,
            "balance_after": total_after,
            "loan_closed": closed,
        }

    def reverse_payment(self, repayment_id: int, reversed_by: int, reason: str) -> Tuple[bool, str]:
        if not reason or not reason.strip():
            return False, "A reason is required to reverse a payment"
        with get_session() as session:
            rep = session.get(Repayment, repayment_id)
            if not rep:
                return False, "Repayment not found"
            if rep.is_reversed:
                return False, "Already reversed"
            loan = session.get(Loan, rep.loan_id)
            if loan is None:
                return False, "Loan not found"
            if loan.status == "renewed":
                return False, "Loan has been renewed; its payments can no longer be reversed"
            if any(c.is_released for c in loan.collateral_items):
                return False, "Collateral has already been released for this loan"
            last = _last_active_repayment(loan)
            if last is None or last.id != rep.id:
                return False, "Only the most recent payment of a loan can be reversed"

            rep.is_reversed = True
            rep.reversal_reason = reason.strip()
            rep.reversed_by = reversed_by
            rep.reversed_at = datetime.now()
            session.flush()

            prev = _last_active_repayment(loan)
            loan.outstanding_principal = (
                prev.balance_principal_after if prev else loan.disbursed_amount
            )
            loan.outstanding_interest = (prev.balance_interest_after or Decimal("0")) if prev else Decimal("0")
            loan.total_outstanding = (loan.outstanding_principal or Decimal("0")) + loan.outstanding_interest

            old_status = loan.status
            if loan.status in ("closed", "partially_repaid"):
                if prev:
                    loan.status = "partially_repaid"
                else:
                    loan.status = "active"
                if loan.maturity_date and date.today() > loan.maturity_date:
                    loan.status = "overdue"
            if loan.status != old_status:
                session.add(LoanStatusHistory(
                    loan_id=loan.id, from_status=old_status, to_status=loan.status,
                    changed_by=reversed_by, remarks=f"Reversed receipt {rep.receipt_number}",
                ))
            receipt = rep.receipt_number

        audit("PAYMENT_REVERSED", "repayment", repayment_id, receipt, extra=reason.strip())
        return True, f"Payment {receipt} reversed"

    def get_repayment(self, repayment_id: int) -> Optional[dict]:
        with get_session() as session:
            r = session.get(Repayment, repayment_id)
            if not r:
                return None
            return {
                "id": r.id,
                "loan_id": r.loan_id,
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
                "balance_interest_after": r.balance_interest_after,
                "total_outstanding_after": r.total_outstanding_after,
                "is_reversed": r.is_reversed,
            }

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
