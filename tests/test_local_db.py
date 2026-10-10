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


def _make_active_loan(uid=1, tag="T-1"):
    from app.services.customer_service import get_customer_service
    from app.services.loan_service import get_loan_service

    ok, _, cust = get_customer_service().create_customer("Test User", "9999999999", uid)
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
    assert svc.disburse_loan(loan_id, uid, date.today() - timedelta(days=10))[0]
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
