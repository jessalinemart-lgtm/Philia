"""
Budget-vs-actual variance and a simplified asset-impairment risk score.

Real film-cost impairment testing (ASC 926-20-35) compares unamortized
capitalized film costs to the estimated remaining ultimate revenue for the
title. This is a simplified version for the MVP: it compares total budgeted
production cost to actual cost-to-date (overrun risk) and total contracted
+ recognized revenue to total cost (revenue-shortfall risk), then blends
both into a single 0-100 risk score.
"""
from decimal import Decimal

from django.db.models import Sum

from ledger.models import JournalLine
from revenue.models import RevenueContract

ZERO = Decimal('0')


def actual_amount_for_account(project, account):
    """Net actual amount posted to `account` for `project`, signed per the account's normal balance."""
    lines = JournalLine.objects.filter(journal_entry__project=project, account=account)
    debits = lines.filter(direction='DEBIT').aggregate(total=Sum('functional_amount'))['total'] or ZERO
    credits = lines.filter(direction='CREDIT').aggregate(total=Sum('functional_amount'))['total'] or ZERO
    return (debits - credits) if account.normal_balance == 'DEBIT' else (credits - debits)


def budget_variance(budget):
    """
    Returns a list of dicts, one per budget line:
    {account, budgeted, actual, variance, variance_pct}
    variance = actual - budgeted (positive = over budget for cost accounts)
    """
    rows = []
    for line in budget.lines.select_related('account'):
        actual = actual_amount_for_account(budget.project, line.account)
        variance = actual - line.budgeted_amount
        variance_pct = (variance / line.budgeted_amount * 100) if line.budgeted_amount else None
        rows.append({
            'account': line.account,
            'budgeted': line.budgeted_amount,
            'actual': actual,
            'variance': variance,
            'variance_pct': variance_pct,
        })
    return rows


def variance_by_subtype(budget):
    """Roll up variance by cost category (ATL/BTL/POST/MARKETING/OVERHEAD)."""
    rows = budget_variance(budget)
    rollup = {}
    for row in rows:
        subtype = row['account'].subtype or 'OTHER'
        bucket = rollup.setdefault(subtype, {'budgeted': ZERO, 'actual': ZERO})
        bucket['budgeted'] += row['budgeted']
        bucket['actual'] += row['actual']
    for subtype, bucket in rollup.items():
        bucket['variance'] = bucket['actual'] - bucket['budgeted']
        bucket['variance_pct'] = (
            (bucket['variance'] / bucket['budgeted'] * 100) if bucket['budgeted'] else None
        )
    return rollup


def impairment_risk_assessment(project, budget):
    """
    Blends two signals into a 0-100 risk score:
      - cost overrun: actual production cost vs budget
      - revenue shortfall: contracted+recognized revenue vs total cost basis
    """
    total_budgeted = budget.total_budgeted
    total_actual = sum((row['actual'] for row in budget_variance(budget)), ZERO)

    cost_overrun_pct = ((total_actual - total_budgeted) / total_budgeted) if total_budgeted else ZERO
    cost_overrun_score = max(ZERO, min(cost_overrun_pct, Decimal('1'))) * 100  # cap at 100% overrun

    ultimate_revenue = RevenueContract.objects.filter(project=project).aggregate(
        total=Sum('total_contract_value')
    )['total'] or ZERO
    cost_basis = max(total_actual, total_budgeted) or Decimal('1')
    shortfall_pct = max(ZERO, (cost_basis - ultimate_revenue) / cost_basis)
    shortfall_score = min(shortfall_pct, Decimal('1')) * 100

    risk_score = (cost_overrun_score * Decimal('0.5')) + (shortfall_score * Decimal('0.5'))

    if risk_score >= 50:
        level = 'HIGH'
    elif risk_score >= 20:
        level = 'MEDIUM'
    else:
        level = 'LOW'

    return {
        'total_budgeted': total_budgeted,
        'total_actual': total_actual,
        'cost_overrun_pct': cost_overrun_pct * 100,
        'ultimate_revenue': ultimate_revenue,
        'cost_basis': cost_basis,
        'shortfall_pct': shortfall_pct * 100,
        'risk_score': risk_score,
        'risk_level': level,
    }
