"""
Tests for the financial validation engine, including the
NOT_APPLICABLE path when a required field is missing.
"""
from app.services.financial_validation import (
    run_invoice_total_check,
    run_balance_sheet_total_check,
    run_total_income_check,
    run_net_change_in_cash_check,
)


def _field(value):
    return {"value": value}


def test_invoice_total_check_passes_within_tolerance():
    data = {
        "subtotal": _field(12500.00),
        "tax_amount": _field(625.00),
        "discount": _field(0.00),
        "total_amount": _field(13125.00),
    }
    result = run_invoice_total_check(data)
    assert result.status == "PASS"
    assert result.variance == 0.00


def test_invoice_total_check_fails_outside_tolerance():
    data = {
        "subtotal": _field(12500.00),
        "tax_amount": _field(625.00),
        "discount": _field(0.00),
        "total_amount": _field(13200.00),
    }
    result = run_invoice_total_check(data)
    assert result.status == "FAIL"


def test_invoice_total_check_not_applicable_when_field_missing():
    data = {"subtotal": _field(None), "total_amount": _field(None)}
    result = run_invoice_total_check(data)
    assert result.status == "NOT_APPLICABLE"


def test_balance_sheet_check_passes_when_totals_match():
    # Values from the dataset's 2024 balance sheet (₹ in crore).
    data = {
        "total_capital_and_liabilities": _field(4030194.26),
        "total_assets": _field(4030194.26),
    }
    result = run_balance_sheet_total_check(data)
    assert result.status == "PASS"


def test_balance_sheet_check_not_applicable_when_field_missing():
    data = {"total_capital_and_liabilities": _field(None), "total_assets": _field(None)}
    result = run_balance_sheet_total_check(data)
    assert result.status == "NOT_APPLICABLE"


def test_total_income_check_passes():
    # Values from the dataset's 2024 P&L (₹ in crore).
    data = {
        "interest_earned": _field(283649.02),
        "other_income": _field(124345.75),
        "total_income": _field(407994.77),
    }
    result = run_total_income_check(data)
    assert result.status == "PASS"


def test_net_change_in_cash_check_passes():
    # Values from the dataset's 2024 cash flow statement (₹ in crore).
    data = {
        "net_cash_from_operating_activities": _field(19069.34),
        "net_cash_from_investing_activities": _field(5313.77),
        "net_cash_from_financing_activities": _field(-3983.06),
        "effect_of_fx_fluctuation": _field(104.94),
        "net_increase_in_cash": _field(20504.99),
    }
    result = run_net_change_in_cash_check(data)
    assert result.status == "PASS"
