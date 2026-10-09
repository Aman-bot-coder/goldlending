"""Unit tests for loan calculation logic."""
import pytest
from decimal import Decimal
from app.services.loan_service import calculate_collateral_value
from app.services.repayment_service import calculate_accrued_interest
from datetime import date


class TestCollateralValuation:
    def test_gold_22k_valuation(self):
        net_weight = Decimal("10.000")
        rate = Decimal("6500.00")
        pure_weight, value = calculate_collateral_value(net_weight, "22K", "gold", rate)
        expected_pure = net_weight * Decimal("22") / Decimal("24")
        assert abs(pure_weight - expected_pure.quantize(Decimal("0.0001"))) < Decimal("0.0002")
        expected_value = expected_pure * rate
        # Allow up to 0.50 rounding tolerance due to intermediate Decimal quantisation
        assert abs(value - expected_value.quantize(Decimal("0.01"))) < Decimal("0.50")

    def test_gold_24k_no_adjustment(self):
        net_weight = Decimal("5.000")
        rate = Decimal("7000.00")
        pure_weight, value = calculate_collateral_value(net_weight, "24K", "gold", rate)
        assert pure_weight == Decimal("5.0000")
        assert value == Decimal("35000.00")

    def test_silver_999_valuation(self):
        net_weight = Decimal("100.000")
        rate = Decimal("85.00")
        pure_weight, value = calculate_collateral_value(net_weight, "999", "silver", rate)
        expected_pure = net_weight * Decimal("0.999")
        assert abs(pure_weight - expected_pure.quantize(Decimal("0.0001"))) < Decimal("0.0002")

    def test_rate_already_adjusted_no_double_discount(self):
        net_weight = Decimal("10.000")
        rate = Decimal("5958.33")  # 22K-adjusted rate
        pure_weight, value = calculate_collateral_value(
            net_weight, "22K", "gold", rate, rate_already_purity_adjusted=True
        )
        assert pure_weight == Decimal("10.0000")
        assert value == Decimal("59583.30")

    def test_stone_deduction(self):
        """Net weight = gross - stone."""
        from app.services.loan_service import LoanService
        net = Decimal("20.000") - Decimal("2.000")
        pure_weight, value = calculate_collateral_value(net, "22K", "gold", Decimal("6500.00"))
        assert pure_weight > Decimal("0")
        assert value > Decimal("0")


class TestInterestCalculation:
    def test_simple_interest_90_days(self):
        principal = Decimal("100000.00")
        rate = Decimal("24.00")  # 24% pa
        days = 90
        disbursement = date(2024, 1, 1)
        as_of = date(2024, 4, 1)
        interest = calculate_accrued_interest(principal, rate, disbursement, as_of, "simple")
        # Jan 1 to Apr 1 = 91 days
        actual_days = (as_of - disbursement).days
        expected = Decimal("100000") * Decimal("24") / Decimal("100") * Decimal(str(actual_days)) / Decimal("365")
        assert abs(interest - expected.quantize(Decimal("0.01"))) < Decimal("0.02")

    def test_zero_rate(self):
        principal = Decimal("50000.00")
        rate = Decimal("0.00")
        disbursement = date(2024, 1, 1)
        as_of = date(2024, 4, 1)
        interest = calculate_accrued_interest(principal, rate, disbursement, as_of)
        assert interest == Decimal("0.00")

    def test_same_day_disbursement(self):
        disbursement = date.today()
        interest = calculate_accrued_interest(Decimal("10000"), Decimal("18"), disbursement, disbursement)
        assert interest == Decimal("0.00")
