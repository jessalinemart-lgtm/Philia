from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction

from core.models import Currency, ExchangeRate, Project


class Account(models.Model):
    TYPE_CHOICES = [
        ('ASSET', 'Asset'),
        ('LIABILITY', 'Liability'),
        ('EQUITY', 'Equity'),
        ('REVENUE', 'Revenue'),
        ('EXPENSE', 'Expense'),
    ]
    # Film production cost categories (ATL/BTL/Post) live under EXPENSE as subtypes,
    # so budgeting can roll up variance by category.
    SUBTYPE_CHOICES = [
        ('ATL', 'Above-the-Line'),
        ('BTL', 'Below-the-Line'),
        ('POST', 'Post-Production'),
        ('MARKETING', 'Marketing/Distribution'),
        ('OVERHEAD', 'Overhead'),
        ('', 'N/A'),
    ]

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=120)
    account_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    subtype = models.CharField(max_length=12, choices=SUBTYPE_CHOICES, blank=True, default='')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'

    @property
    def normal_balance(self):
        """Debit-normal for asset/expense, credit-normal for liability/equity/revenue."""
        return 'DEBIT' if self.account_type in ('ASSET', 'EXPENSE') else 'CREDIT'


class JournalEntry(models.Model):
    SOURCE_CHOICES = [
        ('MANUAL', 'Manual Entry'),
        ('REVENUE_RECOGNITION', 'Revenue Recognition'),
        ('INVESTOR_DISTRIBUTION', 'Investor Distribution'),
        ('BUDGET_ACTUAL', 'Budget Actual / Cost'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='journal_entries')
    date = models.DateField()
    memo = models.CharField(max_length=255, blank=True)
    source = models.CharField(max_length=24, choices=SOURCE_CHOICES, default='MANUAL')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date', '-id']
        verbose_name_plural = 'journal entries'

    def __str__(self):
        return f'JE#{self.id} {self.project} {self.date} {self.memo}'

    def clean(self):
        lines = list(self.lines.all())
        if not lines:
            return
        total_debit = sum((l.functional_amount for l in lines if l.direction == 'DEBIT'), Decimal('0'))
        total_credit = sum((l.functional_amount for l in lines if l.direction == 'CREDIT'), Decimal('0'))
        if total_debit != total_credit:
            raise ValidationError(
                f'Journal entry does not balance: debits {total_debit} != credits {total_credit}'
            )

    def is_balanced(self):
        lines = list(self.lines.all())
        total_debit = sum((l.functional_amount for l in lines if l.direction == 'DEBIT'), Decimal('0'))
        total_credit = sum((l.functional_amount for l in lines if l.direction == 'CREDIT'), Decimal('0'))
        return total_debit == total_credit and total_debit > 0


class JournalLine(models.Model):
    DIRECTION_CHOICES = [('DEBIT', 'Debit'), ('CREDIT', 'Credit')]

    journal_entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='lines')
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='lines')
    direction = models.CharField(max_length=6, choices=DIRECTION_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default='USD')
    functional_amount = models.DecimalField(max_digits=14, decimal_places=2, editable=False)
    memo = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        sign = '+' if self.direction == 'DEBIT' else '-'
        return f'{self.account} {sign}{self.amount} {self.currency_id}'

    def save(self, *args, **kwargs):
        self.functional_amount = ExchangeRate.convert_to_usd(
            self.amount, self.currency_id, self.journal_entry.date
        )
        super().save(*args, **kwargs)


@transaction.atomic
def post_journal_entry(project, date, memo, source, lines):
    """
    Create a balanced journal entry.
    `lines` is a list of dicts: {account, direction, amount, currency, memo}
    Raises ValidationError if debits != credits.
    """
    entry = JournalEntry.objects.create(project=project, date=date, memo=memo, source=source)
    for line in lines:
        JournalLine.objects.create(
            journal_entry=entry,
            account=line['account'],
            direction=line['direction'],
            amount=line['amount'],
            currency=line.get('currency') or Currency.objects.get(pk='USD'),
            memo=line.get('memo', ''),
        )
    entry.clean()
    return entry
