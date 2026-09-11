"""
Financial validation engine (case study 4.4). Runs formula checks
against extracted_data. If a required field is missing, the check
returns NOT_APPLICABLE rather than assuming a value.

Rule sets are dispatched by document_type. The balance sheet /
profit & loss / cash flow rules below are written for the dataset's
actual source documents (a bank's consolidated financial statements),
where the standard "Assets = Liabilities + Equity" formula does NOT
apply -- banks report "Capital and Liabilities" vs "Assets" instead.
If a different balance-sheet layout needs to be supported later, add
a second rule set rather than changing this one, since the correct
formula depends on the source document's actual structure.
"""
from app.models.schemas import ValidationCheck, ValidationResult

TOLERANCE = 0.01  # absolute currency-unit tolerance for PASS/FAIL


def _get_value(extracted_data: dict, field: str):
    entry = extracted_data.get(field)
    return entry.get("value") if isinstance(entry, dict) else None


def _not_applicable(name: str, formula: str) -> ValidationCheck:
    return ValidationCheck(name=name, formula=formula, operands={}, status="NOT_APPLICABLE")


def _check(name: str, formula: str, operands: dict, calculated: float, reported: float) -> ValidationCheck:
    variance = round(calculated - reported, 2)
    return ValidationCheck(
        name=name,
        formula=formula,
        operands=operands,
        calculated_value=round(calculated, 2),
        reported_value=round(reported, 2),
        variance=variance,
        status="PASS" if abs(variance) <= TOLERANCE else "FAIL",
    )


# ---------------------------------------------------------------- invoice --
def run_invoice_total_check(extracted_data: dict) -> ValidationCheck:
    name, formula = "invoice_total_check", "subtotal + tax_amount - discount"
    subtotal = _get_value(extracted_data, "subtotal")
    reported_total = _get_value(extracted_data, "total_amount")
    if subtotal is None or reported_total is None:
        return _not_applicable(name, formula)

    tax_amount = _get_value(extracted_data, "tax_amount") or 0.0
    discount = _get_value(extracted_data, "discount") or 0.0
    calculated = subtotal + tax_amount - discount
    return _check(name, formula, {"subtotal": subtotal, "tax_amount": tax_amount, "discount": discount},
                  calculated, reported_total)


def run_invoice_checks(extracted_data: dict) -> list[ValidationCheck]:
    # TODO: add a line_items_sum_check (sum of line amounts == subtotal)
    # once line_items extraction is implemented -- useful for the
    # multi-line synthetic invoices in the dataset (batch*.jpg).
    return [run_invoice_total_check(extracted_data)]


# ---------------------------------------------------- balance sheet (bank) --
def run_balance_sheet_total_check(extracted_data: dict) -> ValidationCheck:
    # Dataset source: bank consolidated balance sheets. Layout is
    # "Capital and Liabilities" vs "Assets" -- NOT the standard
    # Assets = Liabilities + Equity formula used for non-bank companies.
    name = "balance_sheet_total_check"
    formula = "total_capital_and_liabilities == total_assets"
    total_liabilities = _get_value(extracted_data, "total_capital_and_liabilities")
    total_assets = _get_value(extracted_data, "total_assets")
    if total_liabilities is None or total_assets is None:
        return _not_applicable(name, formula)

    return _check(name, formula, {"total_capital_and_liabilities": total_liabilities},
                  calculated=total_liabilities, reported=total_assets)


def run_balance_sheet_checks(extracted_data: dict) -> list[ValidationCheck]:
    return [run_balance_sheet_total_check(extracted_data)]


# ------------------------------------------------------------- profit & loss --
def run_total_income_check(extracted_data: dict) -> ValidationCheck:
    name, formula = "total_income_check", "interest_earned + other_income"
    interest_earned = _get_value(extracted_data, "interest_earned")
    other_income = _get_value(extracted_data, "other_income")
    reported_total_income = _get_value(extracted_data, "total_income")
    if interest_earned is None or other_income is None or reported_total_income is None:
        return _not_applicable(name, formula)

    calculated = interest_earned + other_income
    return _check(name, formula, {"interest_earned": interest_earned, "other_income": other_income},
                  calculated, reported_total_income)


def run_total_expenditure_check(extracted_data: dict) -> ValidationCheck:
    name = "total_expenditure_check"
    formula = "interest_expended + operating_expenses + provisions_and_contingencies"
    interest_expended = _get_value(extracted_data, "interest_expended")
    operating_expenses = _get_value(extracted_data, "operating_expenses")
    provisions = _get_value(extracted_data, "provisions_and_contingencies")
    reported_total_expenditure = _get_value(extracted_data, "total_expenditure")
    if None in (interest_expended, operating_expenses, provisions, reported_total_expenditure):
        return _not_applicable(name, formula)

    calculated = interest_expended + operating_expenses + provisions
    return _check(name, formula,
                  {"interest_expended": interest_expended, "operating_expenses": operating_expenses,
                   "provisions_and_contingencies": provisions},
                  calculated, reported_total_expenditure)


def run_net_profit_check(extracted_data: dict) -> ValidationCheck:
    name, formula = "net_profit_check", "total_income - total_expenditure"
    total_income = _get_value(extracted_data, "total_income")
    total_expenditure = _get_value(extracted_data, "total_expenditure")
    reported_profit = _get_value(extracted_data, "net_profit_before_minority_interest")
    if total_income is None or total_expenditure is None or reported_profit is None:
        return _not_applicable(name, formula)

    calculated = total_income - total_expenditure
    return _check(name, formula, {"total_income": total_income, "total_expenditure": total_expenditure},
                  calculated, reported_profit)


def run_profit_loss_checks(extracted_data: dict) -> list[ValidationCheck]:
    return [
        run_total_income_check(extracted_data),
        run_total_expenditure_check(extracted_data),
        run_net_profit_check(extracted_data),
    ]


# --------------------------------------------------------------- cash flow --
def run_net_change_in_cash_check(extracted_data: dict) -> ValidationCheck:
    name = "net_change_in_cash_check"
    formula = "net_cash_operating + net_cash_investing + net_cash_financing + fx_effect"
    operating = _get_value(extracted_data, "net_cash_from_operating_activities")
    investing = _get_value(extracted_data, "net_cash_from_investing_activities")
    financing = _get_value(extracted_data, "net_cash_from_financing_activities")
    reported_net_increase = _get_value(extracted_data, "net_increase_in_cash")
    if None in (operating, investing, financing, reported_net_increase):
        return _not_applicable(name, formula)

    fx_effect = _get_value(extracted_data, "effect_of_fx_fluctuation") or 0.0
    calculated = operating + investing + financing + fx_effect
    return _check(name, formula,
                  {"net_cash_from_operating_activities": operating,
                   "net_cash_from_investing_activities": investing,
                   "net_cash_from_financing_activities": financing,
                   "effect_of_fx_fluctuation": fx_effect},
                  calculated, reported_net_increase)


def run_closing_cash_check(extracted_data: dict) -> ValidationCheck:
    name = "closing_cash_balance_check"
    formula = "opening_cash + cash_acquired_on_amalgamation + net_increase_in_cash"
    opening_cash = _get_value(extracted_data, "opening_cash_and_equivalents")
    net_increase = _get_value(extracted_data, "net_increase_in_cash")
    reported_closing = _get_value(extracted_data, "closing_cash_and_equivalents")
    if opening_cash is None or net_increase is None or reported_closing is None:
        return _not_applicable(name, formula)

    # Optional field -- not every year has an amalgamation adjustment.
    acquired = _get_value(extracted_data, "cash_acquired_on_amalgamation") or 0.0
    calculated = opening_cash + acquired + net_increase
    return _check(name, formula,
                  {"opening_cash_and_equivalents": opening_cash,
                   "cash_acquired_on_amalgamation": acquired,
                   "net_increase_in_cash": net_increase},
                  calculated, reported_closing)


def run_cash_flow_checks(extracted_data: dict) -> list[ValidationCheck]:
    return [run_net_change_in_cash_check(extracted_data), run_closing_cash_check(extracted_data)]


# ------------------------------------------------------------------ dispatch --
_CHECKS_BY_DOCUMENT_TYPE = {
    "invoice": run_invoice_checks,
    "balance_sheet": run_balance_sheet_checks,
    "profit_loss": run_profit_loss_checks,
    "cash_flow": run_cash_flow_checks,
}


def run_validations(extracted_data: dict, document_type: str) -> ValidationResult:
    checks_fn = _CHECKS_BY_DOCUMENT_TYPE.get(document_type)
    checks = checks_fn(extracted_data) if checks_fn else []

    if any(c.status == "FAIL" for c in checks):
        overall_status = "FAIL"
    elif checks and all(c.status == "NOT_APPLICABLE" for c in checks):
        overall_status = "NOT_APPLICABLE"
    else:
        overall_status = "PASS"

    return ValidationResult(checks=checks, overall_status=overall_status, issues=[])
