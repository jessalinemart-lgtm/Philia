"""
Investor distribution waterfall.

Standard indie-film recoupment waterfall, evaluated tier by tier against
net proceeds available in a single distribution run:

  1. RETURN_OF_CAPITAL - repay each investor's principal, pro-rata by contribution,
     net of whatever has already been returned to them in prior distributions.
  2. PREFERRED_RETURN  - pay a simple-interest preferred return on capital
     (accrued from investment date to distribution date), net of what's
     already been paid, pro-rata by contribution.
  3. PROFIT_SPLIT      - whatever remains is split investor_share to investors
     (pro-rata by contribution) and the rest to the producer/financier side,
     which this MVP does not itemize as a line item (it's the studio's retained take).

Money moves through Distribution + DistributionLineItem records; nothing here
touches the general ledger directly (that's `record_distribution_in_ledger`,
called separately once a distribution is finalized).
"""
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict

from django.db import transaction
from django.db.models import Sum

from .models import Distribution, DistributionLineItem, Investment, WaterfallTier

TWOPLACES = Decimal('0.01')


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _capital_by_investor(project):
    totals = defaultdict(Decimal)
    for inv in Investment.objects.filter(project=project).select_related('investor'):
        # NOTE: MVP assumes investment.currency == project.functional_currency (USD).
        # Multi-currency capital calls would convert via ExchangeRate here.
        totals[inv.investor_id] += inv.amount
    return dict(totals)


def _already_paid_by_tier(project, tier_type):
    """Sum of prior distribution line items for this tier type, per investor."""
    totals = defaultdict(Decimal)
    for item in DistributionLineItem.objects.filter(
        distribution__project=project, tier__tier_type=tier_type
    ).select_related('investor'):
        totals[item.investor_id] += item.amount
    return dict(totals)


def _accrued_preferred_return(project, tier, as_of_date):
    """Simple interest: capital * rate * (years elapsed since each investment)."""
    accrued = defaultdict(Decimal)
    for inv in Investment.objects.filter(project=project):
        days_elapsed = (as_of_date - inv.date).days
        if days_elapsed <= 0:
            continue
        years_elapsed = Decimal(days_elapsed) / Decimal(365)
        accrued[inv.investor_id] += inv.amount * tier.preferred_rate * years_elapsed
    return accrued


@transaction.atomic
def run_waterfall(project, distribution_date, net_proceeds_available, status='DRAFT'):
    """
    Allocate `net_proceeds_available` across the project's waterfall tiers.
    Returns the created Distribution with its line items.
    """
    remaining = Decimal(net_proceeds_available)
    capital = _capital_by_investor(project)
    total_capital = sum(capital.values()) or Decimal('0')

    distribution = Distribution.objects.create(
        project=project, date=distribution_date,
        net_proceeds_available=net_proceeds_available, status=status,
    )

    for tier in WaterfallTier.objects.filter(project=project).order_by('order'):
        if remaining <= 0:
            break

        if tier.tier_type == 'RETURN_OF_CAPITAL':
            paid = _already_paid_by_tier(project, 'RETURN_OF_CAPITAL')
            owed = {inv_id: capital.get(inv_id, Decimal('0')) - paid.get(inv_id, Decimal('0'))
                    for inv_id in capital}
            remaining = _pay_tier_pro_rata(distribution, tier, owed, remaining)

        elif tier.tier_type == 'PREFERRED_RETURN':
            accrued = _accrued_preferred_return(project, tier, distribution_date)
            paid = _already_paid_by_tier(project, 'PREFERRED_RETURN')
            owed = {inv_id: accrued.get(inv_id, Decimal('0')) - paid.get(inv_id, Decimal('0'))
                    for inv_id in accrued}
            remaining = _pay_tier_pro_rata(distribution, tier, owed, remaining)

        elif tier.tier_type == 'PROFIT_SPLIT':
            investor_pool = _round(remaining * (tier.investor_share or Decimal('0')))
            if total_capital > 0 and investor_pool > 0:
                pro_rata = {inv_id: cap / total_capital for inv_id, cap in capital.items()}
                remaining -= _pay_tier_by_ratio(distribution, tier, pro_rata, investor_pool)
            # The non-investor remainder of this tier (producer/financier share) is left
            # undistributed here by design -- it's retained, not modeled as an Investor line item.

    return distribution


def _pay_tier_pro_rata(distribution, tier, owed, remaining):
    """Pay `owed` amounts pro-rata against each other, capped by `remaining`."""
    total_owed = sum((v for v in owed.values() if v > 0), Decimal('0'))
    if total_owed <= 0:
        return remaining
    pool = min(total_owed, remaining)
    ratios = {inv_id: (amt / total_owed) for inv_id, amt in owed.items() if amt > 0}
    paid_out = _pay_tier_by_ratio(distribution, tier, ratios, pool)
    return remaining - paid_out


def _pay_tier_by_ratio(distribution, tier, ratios, pool):
    paid_out = Decimal('0')
    for investor_id, ratio in ratios.items():
        amount = _round(pool * ratio)
        if amount <= 0:
            continue
        DistributionLineItem.objects.create(
            distribution=distribution, investor_id=investor_id, tier=tier, amount=amount,
        )
        paid_out += amount
    return paid_out


def investor_roi(project, investor):
    """(total distributed to investor) / (total capital contributed by investor) - 1"""
    contributed = Investment.objects.filter(project=project, investor=investor).aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0')
    distributed = DistributionLineItem.objects.filter(
        distribution__project=project, investor=investor
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    if contributed == 0:
        return None
    return (distributed / contributed) - 1
