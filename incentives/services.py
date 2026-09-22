"""
Film tax incentive calculations: qualified spend is derived live from the general
ledger (JournalLine.incurred_jurisdiction + Account.subtype), not entered by hand,
so it can't drift out of sync with the books the way a side spreadsheet would.
"""
from decimal import Decimal

from django.db.models import Sum

from ledger.models import JournalLine

ZERO = Decimal('0')


def qualified_spend(claim):
    """
    Actual qualifying cost-to-date for this claim's program, pulled straight from the
    ledger: debit lines on EXPENSE accounts whose subtype is in the program's qualified
    list, incurred in the program's jurisdiction.
    """
    if claim.certified_qualified_spend is not None:
        return claim.certified_qualified_spend

    subtypes = claim.program.qualified_subtype_list()
    total = JournalLine.objects.filter(
        journal_entry__project=claim.project,
        direction='DEBIT',
        account__account_type='EXPENSE',
        account__subtype__in=subtypes,
        incurred_jurisdiction=claim.program.jurisdiction,
    ).aggregate(total=Sum('functional_amount'))['total'] or ZERO
    return total


def estimated_credit(claim):
    """Gross credit value: qualified spend * rate, capped at the program's cap if any."""
    if claim.certified_credit_amount is not None:
        return claim.certified_credit_amount

    spend = qualified_spend(claim)
    gross = spend * claim.program.rate
    if claim.program.cap_amount is not None:
        gross = min(gross, claim.program.cap_amount)
    return gross.quantize(Decimal('0.01'))


def cash_value(claim):
    """Estimated credit after the typical monetization discount (relevant for
    TRANSFERABLE_CREDIT programs sold to a third-party taxpayer at a discount)."""
    credit = estimated_credit(claim)
    return (credit * claim.program.typical_monetization_rate).quantize(Decimal('0.01'))


def project_incentive_summary(project):
    """One row per claim plus a total, for the dashboard."""
    rows = []
    total_cash_value = ZERO
    for claim in project.incentive_claims.select_related('program', 'program__jurisdiction'):
        spend = qualified_spend(claim)
        credit = estimated_credit(claim)
        cash = cash_value(claim)
        rows.append({
            'claim': claim,
            'qualified_spend': spend,
            'estimated_credit': credit,
            'cash_value': cash,
        })
        total_cash_value += cash
    return rows, total_cash_value
