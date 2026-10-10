"""
Loan origination and lifecycle management service.
All monetary calculations use Decimal to prevent floating-point errors.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Tuple

from sqlalchemy import and_, or_

from app.config import get_config
from app.database.connection import get_session
from app.models.collateral import CollateralItem
from app.models.loan import Loan, LoanStatusHistory

logger = logging.getLogger(__name__)


def _next_loan_number(session) -> str:
    cfg = get_config()
    prefix = cfg.loan_prefix
    today = date.today()
    date_str = today.strftime("%Y%m%d")
    count = (
        session.query(Loan)
        .filter(Loan.loan_number.like(f"{prefix}{date_str}%"))
        .count()
    )
    return f"{prefix}{date_str}{(count + 1):04d}"


def _calculate_interest(
    principal: Decimal,
    annual_rate: Decimal,
    days: int,
    method: str = "simple",
) -> Decimal:
    """Returns total interest for the period."""
    if method == "simple":
        interest = principal * annual_rate / Decimal("100") * Decimal(str(days)) / Decimal("365")
        return interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Decimal("0.00")  # reducing balance handled in repayment service


def calculate_collateral_value(
    net_weight: Decimal,
    purity_str: str,
    metal_type: str,
    rate_per_gram: Decimal,
    rate_already_purity_adjusted: bool = False,
) -> Tuple[Decimal, Decimal]:
    """
    Returns (pure_metal_weight, indicative_value).
    Never applies the purity adjustment twice if rate_already_purity_adjusted is True.
    """
    purity_map_gold = {"24K": Decimal("1.0"), "22K": Decimal("22") / Decimal("24"),
                       "20K": Decimal("20") / Decimal("24"), "18K": Decimal("18") / Decimal("24"),
                       "14K": Decimal("14") / Decimal("24")}
    purity_map_silver = {"999": Decimal("0.999"), "925": Decimal("0.925"), "800": Decimal("0.800")}

    if rate_already_purity_adjusted:
        pure_weight = net_weight
    else:
        if metal_type == "gold":
            factor = purity_map_gold.get(purity_str.upper())
            if factor is None:
                try:
                    k = Decimal(purity_str.replace("K", "").replace("k", ""))
                    factor = k / Decimal("24")
                except Exception:
                    factor = Decimal("1.0")
        else:
            factor = purity_map_silver.get(purity_str)
            if factor is None:
                try:
                    factor = Decimal(purity_str) / Decimal("1000")
                except Exception:
                    factor = Decimal("1.0")
        pure_weight = net_weight * factor

    pure_weight = pure_weight.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    value = (pure_weight * rate_per_gram).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return pure_weight, value


class LoanService:

    def create_loan(
        self,
        customer_id: int,
        principal_amount: Decimal,
        interest_rate: Decimal,
        tenure_days: int,
        interest_method: str,
        created_by: int,
        processing_fee: Decimal = Decimal("0"),
        other_charges: Decimal = Decimal("0"),
        payment_mode: str = "cash",
        ltv_percentage: Optional[Decimal] = None,
        total_collateral_value: Optional[Decimal] = None,
        remarks: str = "",
    ) -> Tuple[bool, str, Optional[int]]:
        cfg = get_config()
        if ltv_percentage and ltv_percentage > Decimal(str(cfg.max_ltv_percentage)):
            return False, f"LTV {ltv_percentage}% exceeds maximum allowed {cfg.max_ltv_percentage}%", None

        with get_session() as session:
            loan_number = _next_loan_number(session)
            loan = Loan(
                loan_number=loan_number,
                customer_id=customer_id,
                status="draft",
                principal_amount=principal_amount,
                interest_rate=interest_rate,
                interest_method=interest_method,
                tenure_days=tenure_days,
                processing_fee=processing_fee,
                other_charges=other_charges,
                payment_mode=payment_mode,
                ltv_percentage=ltv_percentage,
                total_collateral_value=total_collateral_value,
                outstanding_principal=principal_amount,
                outstanding_interest=Decimal("0"),
                total_outstanding=principal_amount,
                remarks=remarks,
                created_by=created_by,
            )
            session.add(loan)
            session.flush()
            loan_id = loan.id
            self._add_status_history(session, loan_id, None, "draft", created_by)

        return True, f"Loan {loan_number} created", loan_id

    def add_collateral(
        self,
        loan_id: int,
        metal_type: str,
        item_category: str,
        gross_weight: Decimal,
        stone_weight: Decimal,
        purity: str,
        rate_per_gram: Decimal,
        valuation_rate: Decimal,
        assayed: bool = False,
        description: str = "",
        tag_number: Optional[str] = None,
        storage_location: str = "",
        appraiser_remarks: str = "",
        rate_already_purity_adjusted: bool = False,
    ) -> Tuple[bool, str, Optional[int]]:
        net_weight = gross_weight - stone_weight
        if net_weight <= 0:
            return False, "Net weight must be positive", None

        pure_weight, indicative_value = calculate_collateral_value(
            net_weight, purity, metal_type, valuation_rate, rate_already_purity_adjusted
        )

        purity_val, _ = calculate_collateral_value(
            Decimal("1"), purity, metal_type, Decimal("1")
        )

        with get_session() as session:
            if tag_number and session.query(CollateralItem).filter(
                CollateralItem.tag_number == tag_number
            ).first():
                return False, f"Tag number '{tag_number}' is already in use", None
            item = CollateralItem(
                loan_id=loan_id,
                metal_type=metal_type,
                item_category=item_category,
                gross_weight=gross_weight,
                stone_weight=stone_weight,
                net_weight=net_weight,
                purity=purity,
                purity_value=purity_val,
                assayed_purity=assayed,
                market_rate=rate_per_gram,
                valuation_rate=valuation_rate,
                valuation_date=datetime.now(),
                pure_metal_weight=pure_weight,
                indicative_value=indicative_value,
                description=description,
                tag_number=tag_number,
                storage_location=storage_location,
                appraiser_remarks=appraiser_remarks,
            )
            session.add(item)
            session.flush()
            item_id = item.id

            # Update loan's total collateral value
            loan = session.get(Loan, loan_id)
            if loan:
                existing = sum(
                    i.indicative_value or Decimal("0")
                    for i in session.query(CollateralItem)
                    .filter(CollateralItem.loan_id == loan_id)
                    .all()
                )
                loan.total_collateral_value = existing

        return True, "Collateral added", item_id

    def approve_loan(self, loan_id: int, approved_by: int, approved_amount: Decimal, remarks: str = "") -> Tuple[bool, str]:
        with get_session() as session:
            loan = session.get(Loan, loan_id)
            if not loan:
                return False, "Loan not found"
            if loan.status not in ("draft", "pending_approval"):
                return False, f"Cannot approve loan in status '{loan.status}'"
            loan.approved_amount = approved_amount
            loan.approved_by = approved_by
            loan.approved_at = datetime.now()
            loan.remarks = remarks
            old_status = loan.status
            loan.status = "approved"
            self._add_status_history(session, loan_id, old_status, "approved", approved_by, remarks)
        return True, "Loan approved"

    def disburse_loan(self, loan_id: int, disbursed_by: int, disbursement_date: Optional[date] = None) -> Tuple[bool, str]:
        with get_session() as session:
            loan = session.get(Loan, loan_id)
            if not loan:
                return False, "Loan not found"
            if loan.status != "approved":
                return False, "Loan must be approved before disbursement"
            loan.status = "active"
            disburse_date = disbursement_date or date.today()
            loan.disbursement_date = disburse_date
            loan.disbursed_amount = loan.approved_amount or loan.principal_amount
            loan.outstanding_principal = loan.disbursed_amount
            loan.maturity_date = disburse_date + timedelta(days=loan.tenure_days)
            self._add_status_history(session, loan_id, "approved", "active", disbursed_by)
        return True, "Loan disbursed"

    def get_loan(self, loan_id: int) -> Optional[dict]:
        with get_session() as session:
            loan = session.get(Loan, loan_id)
            if not loan:
                return None
            return self._to_dict(loan, session)

    def get_loan_by_number(self, loan_number: str) -> Optional[dict]:
        with get_session() as session:
            loan = session.query(Loan).filter(Loan.loan_number == loan_number).first()
            return self._to_dict(loan, session) if loan else None

    def search_loans(
        self,
        query: str = "",
        status: str = "",
        customer_id: Optional[int] = None,
        overdue_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[dict]:
        with get_session() as session:
            from app.models.customer import Customer
            q = session.query(Loan).join(Customer, Loan.customer_id == Customer.id)
            if query:
                like = f"%{query}%"
                q = q.filter(
                    or_(Loan.loan_number.ilike(like), Customer.full_name.ilike(like),
                        Customer.mobile.ilike(like))
                )
            if status:
                q = q.filter(Loan.status == status)
            if customer_id:
                q = q.filter(Loan.customer_id == customer_id)
            if overdue_only:
                today = date.today()
                q = q.filter(
                    and_(Loan.maturity_date < today, Loan.status.in_(["active", "partially_repaid"]))
                )
            loans = q.order_by(Loan.created_at.desc()).limit(limit).offset(offset).all()
            return [self._to_dict(lo, session) for lo in loans]

    def get_dashboard_stats(self) -> dict:
        with get_session() as session:
            from app.models.customer import Customer
            from app.models.repayment import Repayment
            total_customers = session.query(Customer).filter(Customer.is_active == True).count()
            active_loans = session.query(Loan).filter(
                Loan.status.in_(["active", "partially_repaid", "overdue"])
            ).count()
            today = date.today()
            overdue = session.query(Loan).filter(
                and_(Loan.maturity_date < today, Loan.status.in_(["active", "partially_repaid"]))
            ).count()
            due_soon = session.query(Loan).filter(
                and_(
                    Loan.maturity_date >= today,
                    Loan.maturity_date <= today + timedelta(days=7),
                    Loan.status.in_(["active", "partially_repaid"]),
                )
            ).count()
            from sqlalchemy import func
            principal_outstanding = session.query(
                func.coalesce(func.sum(Loan.outstanding_principal), 0)
            ).filter(Loan.status.in_(["active", "partially_repaid", "overdue"])).scalar()
            total_disbursed = session.query(
                func.coalesce(func.sum(Loan.disbursed_amount), 0)
            ).filter(Loan.status != "draft").scalar()
            total_repayments = session.query(
                func.coalesce(func.sum(Repayment.total_paid), 0)
            ).filter(Repayment.is_reversed == False).scalar()
            gold_weight = session.query(
                func.coalesce(func.sum(CollateralItem.net_weight), 0)
            ).filter(CollateralItem.metal_type == "gold", CollateralItem.is_released == False).scalar()
            silver_weight = session.query(
                func.coalesce(func.sum(CollateralItem.net_weight), 0)
            ).filter(CollateralItem.metal_type == "silver", CollateralItem.is_released == False).scalar()
            return {
                "total_customers": total_customers,
                "active_loans": active_loans,
                "overdue_loans": overdue,
                "due_soon_loans": due_soon,
                "principal_outstanding": Decimal(str(principal_outstanding)),
                "total_disbursed": Decimal(str(total_disbursed)),
                "total_repayments": Decimal(str(total_repayments)),
                "gold_weight_grams": Decimal(str(gold_weight)),
                "silver_weight_grams": Decimal(str(silver_weight)),
            }

    def update_overdue_statuses(self) -> int:
        """Mark active loans as overdue if past maturity. Returns count updated."""
        today = date.today()
        with get_session() as session:
            loans = session.query(Loan).filter(
                and_(
                    Loan.maturity_date < today,
                    Loan.status.in_(["active", "partially_repaid"]),
                )
            ).all()
            for loan in loans:
                old = loan.status
                loan.status = "overdue"
                self._add_status_history(session, loan.id, old, "overdue", None, "Auto-marked overdue")
            return len(loans)

    def _add_status_history(
        self, session, loan_id: int, from_status, to_status: str,
        changed_by: Optional[int], remarks: str = ""
    ):
        history = LoanStatusHistory(
            loan_id=loan_id,
            from_status=from_status,
            to_status=to_status,
            changed_by=changed_by,
            remarks=remarks,
        )
        session.add(history)

    def _to_dict(self, loan: Loan, session) -> dict:
        from app.models.customer import Customer
        customer = session.get(Customer, loan.customer_id)
        return {
            "id": loan.id,
            "loan_number": loan.loan_number,
            "customer_id": loan.customer_id,
            "customer_name": customer.full_name if customer else "",
            "customer_mobile": customer.mobile if customer else "",
            "status": loan.status,
            "principal_amount": loan.principal_amount,
            "approved_amount": loan.approved_amount,
            "disbursed_amount": loan.disbursed_amount,
            "outstanding_principal": loan.outstanding_principal,
            "outstanding_interest": loan.outstanding_interest,
            "total_outstanding": loan.total_outstanding,
            "interest_rate": loan.interest_rate,
            "interest_method": loan.interest_method,
            "tenure_days": loan.tenure_days,
            "disbursement_date": loan.disbursement_date,
            "maturity_date": loan.maturity_date,
            "ltv_percentage": loan.ltv_percentage,
            "total_collateral_value": loan.total_collateral_value,
            "processing_fee": loan.processing_fee,
            "other_charges": loan.other_charges,
            "payment_mode": loan.payment_mode,
            "remarks": loan.remarks,
            "renewal_count": loan.renewal_count,
            "created_at": loan.created_at,
        }


_loan_service: Optional[LoanService] = None


def get_loan_service() -> LoanService:
    global _loan_service
    if _loan_service is None:
        _loan_service = LoanService()
    return _loan_service
