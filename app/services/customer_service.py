"""Customer onboarding and KYC service."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional, List, Tuple

from sqlalchemy import or_

from app.database.connection import get_session
from app.services.audit_service import audit
from app.models.customer import Customer, KYCDocument
from app.utils.security import encrypt_field, decrypt_field

logger = logging.getLogger(__name__)


class CustomerService:

    def _next_customer_id(self, session) -> str:
        from app.config import get_config
        prefix = get_config().customer_prefix
        last = (
            session.query(Customer)
            .filter(Customer.customer_id.like(f"{prefix}%"))
            .order_by(Customer.id.desc())
            .first()
        )
        if last:
            try:
                num = int(last.customer_id.replace(prefix, "")) + 1
            except Exception:
                num = 1
        else:
            num = 1
        return f"{prefix}{num:05d}"

    def create_customer(
        self,
        full_name: str,
        mobile: str,
        created_by: int,
        **kwargs,
    ) -> Tuple[bool, str, Optional[dict]]:
        with get_session() as session:
            # Duplicate check
            existing = (
                session.query(Customer)
                .filter(Customer.mobile == mobile, Customer.is_active == True)
                .first()
            )
            if existing:
                return False, f"Customer with mobile {mobile} already exists ({existing.customer_id})", None

            customer_id = self._next_customer_id(session)
            kyc_ref = kwargs.pop("kyc_ref", None)
            kyc_ref_encrypted = encrypt_field(kyc_ref) if kyc_ref else None

            customer = Customer(
                customer_id=customer_id,
                full_name=full_name.strip(),
                mobile=mobile.strip(),
                created_by=created_by,
                kyc_ref_encrypted=kyc_ref_encrypted,
                **{k: v for k, v in kwargs.items() if hasattr(Customer, k)},
            )
            session.add(customer)
            session.flush()
            cid = customer.id
            cust_id_str = customer.customer_id

        audit("CUSTOMER_CREATED", "customer", cid, cust_id_str, new_value={"name": full_name, "mobile": mobile}, user_id=created_by)
        return True, "Customer created successfully", {"id": cid, "customer_id": cust_id_str}

    def update_customer(self, customer_id: int, updated_by: int, **kwargs) -> Tuple[bool, str]:
        with get_session() as session:
            customer = session.get(Customer, customer_id)
            if not customer:
                return False, "Customer not found"

            if "kyc_ref" in kwargs:
                kyc_ref = kwargs.pop("kyc_ref")
                customer.kyc_ref_encrypted = encrypt_field(kyc_ref) if kyc_ref else None

            allowed_fields = {
                "full_name", "father_spouse_name", "date_of_birth", "mobile",
                "alt_mobile", "address", "city", "state", "pincode",
                "photo_path", "kyc_type", "kyc_status", "notes", "is_active",
            }
            for key, val in kwargs.items():
                if key in allowed_fields:
                    setattr(customer, key, val)

        audit("CUSTOMER_UPDATED", "customer", customer_id,
              new_value={k: v for k, v in kwargs.items() if k != "kyc_ref"}, user_id=updated_by)
        return True, "Customer updated"

    def verify_kyc(
        self, customer_id: int, verified_by: int, status: str, reason: str = ""
    ) -> Tuple[bool, str]:
        if status not in ("verified", "rejected"):
            return False, "Invalid KYC status"
        with get_session() as session:
            customer = session.get(Customer, customer_id)
            if not customer:
                return False, "Customer not found"
            customer.kyc_status = status
            customer.kyc_verified_by = verified_by
            customer.kyc_verified_at = datetime.now()
            if status == "rejected":
                customer.kyc_rejection_reason = reason
        audit(f"KYC_{status.upper()}", "customer", customer_id, extra=reason or None, user_id=verified_by)
        return True, f"KYC {status}"

    def get_customer(self, customer_id: int) -> Optional[dict]:
        with get_session() as session:
            c = session.get(Customer, customer_id)
            if not c:
                return None
            return self._to_dict(c)

    def get_customer_by_cid(self, cid_str: str) -> Optional[dict]:
        with get_session() as session:
            c = (
                session.query(Customer)
                .filter(Customer.customer_id == cid_str)
                .first()
            )
            return self._to_dict(c) if c else None

    def search_customers(
        self, query: str = "", kyc_status: str = "", is_active: bool = True,
        limit: int = 100, offset: int = 0
    ) -> List[dict]:
        with get_session() as session:
            q = session.query(Customer)
            if is_active is not None:
                q = q.filter(Customer.is_active == is_active)
            if query:
                like = f"%{query}%"
                q = q.filter(
                    or_(
                        Customer.full_name.ilike(like),
                        Customer.mobile.ilike(like),
                        Customer.customer_id.ilike(like),
                    )
                )
            if kyc_status:
                q = q.filter(Customer.kyc_status == kyc_status)
            customers = q.order_by(Customer.full_name).limit(limit).offset(offset).all()
            return [self._to_dict(c) for c in customers]

    def count_customers(self, is_active: bool = True) -> int:
        with get_session() as session:
            return (
                session.query(Customer)
                .filter(Customer.is_active == is_active)
                .count()
            )

    def _to_dict(self, c: Customer) -> dict:
        return {
            "id": c.id,
            "customer_id": c.customer_id,
            "full_name": c.full_name,
            "father_spouse_name": c.father_spouse_name,
            "date_of_birth": c.date_of_birth,
            "mobile": c.mobile,
            "alt_mobile": c.alt_mobile,
            "address": c.address,
            "city": c.city,
            "state": c.state,
            "pincode": c.pincode,
            "photo_path": c.photo_path,
            "kyc_type": c.kyc_type,
            "kyc_status": c.kyc_status,
            "kyc_verified_at": c.kyc_verified_at,
            "notes": c.notes,
            "is_active": c.is_active,
            "created_at": c.created_at,
        }


_customer_service: Optional[CustomerService] = None


def get_customer_service() -> CustomerService:
    global _customer_service
    if _customer_service is None:
        _customer_service = CustomerService()
    return _customer_service
