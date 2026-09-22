"""
Revenue recognition, in simplified ASC 606 terms.

Each recognized dollar is posted to the GL as:
    Dr Accounts Receivable
        Cr Revenue
via ledger.models.post_journal_entry, so revenue recognition and the ledger
stay in sync -- the dashboard reads recognized revenue straight from the GL.
"""
from decimal import Decimal

from dateutil.relativedelta import relativedelta

from ledger.models import Account, post_journal_entry
from .models import RevenueRecognitionEntry


def _post_recognition(contract, period_start, period_end, amount, milestone=None):
    ar_account = Account.objects.get(code='1200')  # Accounts Receivable
    revenue_account = Account.objects.get(code='4000')  # Revenue

    entry = post_journal_entry(
        project=contract.project,
        date=period_end,
        memo=f'Revenue recognition: {contract.counterparty} ({contract.get_contract_type_display()})',
        source='REVENUE_RECOGNITION',
        lines=[
            {'account': ar_account, 'direction': 'DEBIT', 'amount': amount, 'currency': contract.currency},
            {'account': revenue_account, 'direction': 'CREDIT', 'amount': amount, 'currency': contract.currency},
        ],
    )
    return RevenueRecognitionEntry.objects.create(
        contract=contract, milestone=milestone,
        period_start=period_start, period_end=period_end,
        amount=amount, journal_entry=entry,
    )


def recognize_point_in_time(contract, recognition_date):
    """Recognize the full contract value on a single date."""
    return _post_recognition(contract, recognition_date, recognition_date, contract.total_contract_value)


def recognize_straight_line_month(contract, month_start):
    """
    Recognize one month's slice of a STRAIGHT_LINE contract's value, evenly
    spread across license_start..license_end.
    """
    month_end = month_start + relativedelta(months=1, days=-1)
    total_months = _month_span(contract.license_start, contract.license_end)
    if total_months <= 0:
        raise ValueError('Contract must have a valid license_start/license_end for straight-line recognition')
    monthly_amount = (contract.total_contract_value / total_months).quantize(Decimal('0.01'))
    return _post_recognition(contract, month_start, month_end, monthly_amount)


def recognize_milestone(milestone, delivered_date):
    """Recognize a milestone's allocated amount once its performance obligation is satisfied."""
    milestone.delivered_date = delivered_date
    milestone.save(update_fields=['delivered_date'])
    return _post_recognition(
        milestone.contract, delivered_date, delivered_date, milestone.allocated_amount, milestone=milestone
    )


def _month_span(start, end):
    if not start or not end:
        return 0
    return (end.year - start.year) * 12 + (end.month - start.month) + 1
