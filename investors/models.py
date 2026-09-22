from decimal import Decimal

from django.db import models

from core.models import Currency, Project


class Investor(models.Model):
    ENTITY_TYPE_CHOICES = [
        ('INDIVIDUAL', 'Individual'),
        ('LLC', 'LLC'),
        ('FUND', 'Fund'),
        ('STUDIO', 'Studio/Financier'),
    ]
    name = models.CharField(max_length=200)
    entity_type = models.CharField(max_length=12, choices=ENTITY_TYPE_CHOICES, default='INDIVIDUAL')
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.name


class Investment(models.Model):
    INSTRUMENT_CHOICES = [
        ('EQUITY', 'Equity'),
        ('GAP', 'Gap Financing'),
        ('DEBT', 'Debt'),
        ('TAX_CREDIT_BRIDGE', 'Tax Credit Bridge Loan'),
    ]
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='investments')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='investments')
    instrument_type = models.CharField(max_length=20, choices=INSTRUMENT_CHOICES, default='EQUITY')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default='USD')
    date = models.DateField()

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.investor} -> {self.project}: {self.amount} {self.currency_id}'


class WaterfallTier(models.Model):
    """
    Ordered recoupment/profit-split tiers for a project, evaluated in sequence
    against available net proceeds. Standard indie-film waterfall:
      1. RETURN_OF_CAPITAL - repay investor principal pro-rata
      2. PREFERRED_RETURN - pay investors a preferred % return on capital before any profit split
      3. PROFIT_SPLIT - remaining net profit split between investors and producer/financier
    """
    TIER_TYPE_CHOICES = [
        ('RETURN_OF_CAPITAL', 'Return of Capital'),
        ('PREFERRED_RETURN', 'Preferred Return'),
        ('PROFIT_SPLIT', 'Profit Split'),
    ]
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='waterfall_tiers')
    order = models.PositiveSmallIntegerField()
    tier_type = models.CharField(max_length=20, choices=TIER_TYPE_CHOICES)
    # For PREFERRED_RETURN: annual simple-interest rate, e.g. 0.15 for 15%
    preferred_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    # For PROFIT_SPLIT: investor's share of this tier, e.g. 0.50 for 50/50
    investor_share = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)

    class Meta:
        ordering = ['project', 'order']
        unique_together = ('project', 'order')

    def __str__(self):
        return f'{self.project} tier {self.order}: {self.get_tier_type_display()}'


class Distribution(models.Model):
    """A distribution run: net proceeds available on `date`, allocated across the waterfall."""
    STATUS_CHOICES = [('DRAFT', 'Draft'), ('FINALIZED', 'Finalized')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='distributions')
    date = models.DateField()
    net_proceeds_available = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f'{self.project} distribution {self.date}: {self.net_proceeds_available}'


class DistributionLineItem(models.Model):
    distribution = models.ForeignKey(Distribution, on_delete=models.CASCADE, related_name='line_items')
    investor = models.ForeignKey(Investor, on_delete=models.CASCADE, related_name='distribution_line_items')
    tier = models.ForeignKey(WaterfallTier, on_delete=models.PROTECT, related_name='line_items')
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    def __str__(self):
        return f'{self.distribution} -> {self.investor}: {self.amount} ({self.tier.get_tier_type_display()})'
