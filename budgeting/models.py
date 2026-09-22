from decimal import Decimal

from django.db import models

from core.models import Project
from ledger.models import Account


class Budget(models.Model):
    STATUS_CHOICES = [('DRAFT', 'Draft'), ('APPROVED', 'Approved'), ('LOCKED', 'Locked')]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='budgets')
    name = models.CharField(max_length=120, default='Production Budget')
    version = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='DRAFT')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['project', '-version']
        unique_together = ('project', 'version')

    def __str__(self):
        return f'{self.project} budget v{self.version} ({self.status})'

    @property
    def total_budgeted(self):
        return self.lines.aggregate(total=models.Sum('budgeted_amount'))['total'] or Decimal('0')


class BudgetLine(models.Model):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='budget_lines')
    budgeted_amount = models.DecimalField(max_digits=14, decimal_places=2)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('budget', 'account')
        ordering = ['account__code']

    def __str__(self):
        return f'{self.budget} - {self.account}: {self.budgeted_amount}'
