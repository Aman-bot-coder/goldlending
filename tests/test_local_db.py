"""Integration tests against a throwaway local SQLite database."""
from datetime import date, timedelta
from decimal import Decimal

import pytest

from app.database import connection


@pytest.fixture()
def db(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(connection, "get_db_path", lambda: db_file)
    connection.init_db()
    yield db_file
    connection.close_db()


def _make_active_loan(uid=1, tag="T-1", days_ago=10, mobile="9999999999"):
    from app.services.customer_service import get_customer_service
    from app.services.loan_service import get_loan_service

    ok, _, cust = get_customer_service().create_customer("Test User", mobile, uid)
    assert ok
    svc = get_loan_service()
    ok, _, loan_id = svc.create_loan(cust["id"], Decimal("10000"), Decimal("12"), 90, "simple", uid)
    assert ok
    ok, msg, _ = svc.add_collateral(
        loan_id, "gold", "ring", Decimal("5"), Decimal("0"), "22K",
        Decimal("7000"), Decimal("7000"), tag_number=tag,
    )
    assert ok, msg
    assert svc.approve_loan(loan_id, uid, Decimal("10000"))[0]
    assert svc.disburse_loan(loan_id, uid, date.today() - timedelta(days=days_ago))[0]
    return loan_id


def test_first_launch_creates_schema_and_admin(db):
    from app.services.auth_service import get_auth_service
    assert db.exists()
    ok, _, user = get_auth_service().login("admin", connection.DEFAULT_ADMIN_PASSWORD)
    assert ok and user.must_change_password


def test_reinit_does_not_duplicate_admin(db):
    from app.services.auth_service import get_auth_service
    connection.close_db()
    connection.init_db()
    assert len(get_auth_service().list_users()) == 1


def test_gold_and_silver_collateral_purity(db):
    from app.services.loan_service import get_loan_service
    from app.models.collateral import CollateralItem

    loan_id = _make_active_loan()
    ok, msg, _ = get_loan_service().add_collateral(
        loan_id, "silver", "coin", Decimal("100"), Decimal("0"), "999",
        Decimal("90"), Decimal("90"), tag_number="S-1",
    )
    assert ok, msg
    with connection.get_session() as s:
        items = {i.metal_type: i for i in s.query(CollateralItem).all()}
        assert items["gold"].purity_value == Decimal("0.9167")
        assert items["silver"].purity_value == Decimal("0.9990")


def test_duplicate_tag_is_rejected(db):
    from app.services.loan_service import get_loan_service
    loan_id = _make_active_loan(tag="DUP")
    ok, msg, _ = get_loan_service().add_collateral(
        loan_id, "gold", "chain", Decimal("2"), Decimal("0"), "24K",
        Decimal("7000"), Decimal("7000"), tag_number="DUP",
    )
    assert not ok and "already in use" in msg


def test_payment_and_manual_rate(db):
    from app.services.repayment_service import get_repayment_service
    from app.services.rate_service import get_rate_service

    loan_id = _make_active_loan()
    ok, msg, _ = get_repayment_service().collect_payment(loan_id, Decimal("500"), date.today(), "cash", 1)
    assert ok, msg

    get_rate_service().save_manual_rate("gold", Decimal("7123.45"))
    latest = get_rate_service().get_latest_rate("gold")
    assert latest["source"] == "manual" and not latest["is_stale"]
    assert Decimal(str(latest["rate_per_gram"])) == Decimal("7123.45")


def test_backup_and_restore_roundtrip(db, tmp_path):
    from app.services.customer_service import get_customer_service

    get_customer_service().create_customer("Before", "9000000001", 1)
    backup = connection.backup_to(tmp_path / "b.db")
    assert connection.validate_backup_file(backup) is None

    get_customer_service().create_customer("After", "9000000002", 1)
    assert get_customer_service().count_customers() == 2

    connection.restore_from(backup)
    assert get_customer_service().count_customers() == 1


def test_invalid_backup_rejected(tmp_path):
    bad = tmp_path / "bad.db"
    bad.write_text("not a database")
    assert connection.validate_backup_file(bad) is not None


def _outstanding(loan_id, as_of=None):
    from app.models.loan import Loan
    from app.services.repayment_service import calculate_outstanding
    with connection.get_session() as s:
        return calculate_outstanding(s.get(Loan, loan_id), as_of)


def _pay(loan_id, amount, days_ago=0):
    from app.services.repayment_service import get_repayment_service
    ok, msg, res = get_repayment_service().collect_payment(
        loan_id, Decimal(str(amount)), date.today() - timedelta(days=days_ago), "cash", 1
    )
    assert ok, msg
    return res


def test_interest_is_not_charged_twice(db):
    loan_id = _make_active_loan(days_ago=60)
    month_interest = Decimal("98.63")  # 10000 * 12% * 30/365
    assert _outstanding(loan_id, date.today() - timedelta(days=30))["accrued_interest"] == month_interest
    _pay(loan_id, month_interest, days_ago=30)
    out = _outstanding(loan_id)
    assert out["principal"] == Decimal("10000.00")
    assert out["accrued_interest"] == month_interest


def test_unpaid_interest_is_carried_forward(db):
    loan_id = _make_active_loan(days_ago=60)
    _pay(loan_id, 50, days_ago=30)
    out = _outstanding(loan_id)
    assert out["principal"] == Decimal("10000.00")
    assert out["accrued_interest"] == Decimal("48.63") + Decimal("98.63")


def test_backdated_payment_before_last_is_rejected(db):
    from app.services.repayment_service import get_repayment_service
    loan_id = _make_active_loan(days_ago=60)
    _pay(loan_id, 100, days_ago=10)
    ok, msg, _ = get_repayment_service().collect_payment(
        loan_id, Decimal("100"), date.today() - timedelta(days=20), "cash", 1
    )
    assert not ok and "earlier than the last payment" in msg


def test_reversal_restores_previous_state_and_only_latest(db):
    from app.services.repayment_service import get_repayment_service
    loan_id = _make_active_loan(days_ago=60)
    before = _outstanding(loan_id)
    first = _pay(loan_id, 1000, days_ago=20)
    second = _pay(loan_id, 500, days_ago=5)

    ok, msg = get_repayment_service().reverse_payment(first["id"], 1, "typo")
    assert not ok and "most recent" in msg
    ok, msg = get_repayment_service().reverse_payment(second["id"], 1, "")
    assert not ok and "reason" in msg.lower()

    assert get_repayment_service().reverse_payment(second["id"], 1, "wrong amount")[0]
    assert get_repayment_service().reverse_payment(first["id"], 1, "wrong loan")[0]
    after = _outstanding(loan_id)
    assert after["total_outstanding"] == before["total_outstanding"]


def test_full_payment_closes_loan_then_release(db):
    from app.services.loan_service import get_loan_service
    from app.models.collateral import CollateralItem
    loan_id = _make_active_loan()
    svc = get_loan_service()
    ok, msg = svc.release_collateral(loan_id, 1)
    assert not ok and "closed" in msg

    res = _pay(loan_id, _outstanding(loan_id)["total_outstanding"])
    assert res["loan_closed"]
    assert svc.get_loan(loan_id)["status"] == "closed"

    ok, msg = svc.release_collateral(loan_id, 1)
    assert ok, msg
    with connection.get_session() as s:
        assert all(i.is_released for i in s.query(CollateralItem).filter_by(loan_id=loan_id))
    assert svc.get_dashboard_stats()["gold_weight_grams"] == 0
    assert not svc.release_collateral(loan_id, 1)[0]


def test_renewal_moves_collateral_and_capitalises_interest(db):
    from app.services.loan_service import get_loan_service
    from app.models.collateral import CollateralItem
    loan_id = _make_active_loan(days_ago=30)
    due = _outstanding(loan_id)["total_outstanding"]
    svc = get_loan_service()
    ok, msg, new_id = svc.renew_loan(loan_id, 1, 90)
    assert ok, msg
    old, new = svc.get_loan(loan_id), svc.get_loan(new_id)
    assert old["status"] == "renewed" and new["status"] == "active"
    assert new["principal_amount"] == due and new["renewal_count"] == 1
    with connection.get_session() as s:
        assert s.query(CollateralItem).filter_by(loan_id=new_id).count() == 1
        assert s.query(CollateralItem).filter_by(loan_id=loan_id).count() == 0
    stats = svc.get_dashboard_stats()
    assert stats["active_loans"] == 1
    assert stats["total_disbursed"] == Decimal("10000.00")


def test_overdue_and_auction_review(db):
    from app.services.loan_service import get_loan_service
    from app.models.loan import Loan
    svc = get_loan_service()
    loan_id = _make_active_loan()
    assert not svc.set_auction_review(loan_id, 1, True)[0]

    with connection.get_session() as s:
        s.get(Loan, loan_id).maturity_date = date.today() - timedelta(days=1)
    assert svc.update_overdue_statuses() == 1
    stats = svc.get_dashboard_stats()
    assert stats["overdue_loans"] == 1
    assert len(svc.search_loans(overdue_only=True)) == 1

    assert svc.set_auction_review(loan_id, 1, True, "no response")[0]
    assert svc.get_loan(loan_id)["status"] == "auction_review"
    assert svc.get_dashboard_stats()["overdue_loans"] == 1
    _pay(loan_id, 100)
    assert svc.set_auction_review(loan_id, 1, False)[0]
    assert svc.get_loan(loan_id)["status"] == "overdue"


def test_actions_are_audited(db):
    from app.services.audit_service import get_audit_service
    loan_id = _make_active_loan()
    _pay(loan_id, 100)
    actions = {r["action"] for r in get_audit_service().get_logs(limit=100)}
    for expected in ("CUSTOMER_CREATED", "LOAN_CREATED", "COLLATERAL_ADDED",
                     "LOAN_APPROVED", "LOAN_DISBURSED", "PAYMENT_COLLECTED"):
        assert expected in actions, expected


def test_receipt_pdf(db, tmp_path, monkeypatch):
    import app.config
    monkeypatch.setattr(app.config, "RECEIPT_DIR", tmp_path)
    from app.ui.loan_actions import build_receipt
    from app.services.repayment_service import get_repayment_service
    loan_id = _make_active_loan()
    res = _pay(loan_id, 100)
    path = build_receipt(res["id"])
    assert path.exists() and path.read_bytes()[:4] == b"%PDF"
    get_repayment_service().reverse_payment(res["id"], 1, "test")
    assert build_receipt(res["id"]).name.endswith("_REVERSED.pdf")
