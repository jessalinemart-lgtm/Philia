from decimal import Decimal

from django.db import models

from core.models import Currency, Project


class RevenueContract(models.Model):
    """
    A licensing/distribution/theatrical deal for a project. Recognition method
    follows ASC 606 concepts in simplified form:
      - POINT_IN_TIME: recognize full amount when delivered (e.g. theatrical minimum guarantee)
      - STRAIGHT_LINE: recognize evenly over the license window (e.g. SVOD licensing term)
      - MILESTONE: recognize per-milestone as performance obligations are satisfied
    """
    CONTRACT_TYPE_CHOICES = [
        ('THEATRICAL', 'Theatrical'),
        ('SVOD', 'SVOD License'),
        ('AVOD', 'AVOD License'),
        ('TV_LICENSE', 'TV License'),
        ('INTERNATIONAL', 'International Distribution'),
        ('MERCHANDISE', 'Merchandise/Ancillary'),
    ]
    RECOGNITION_METHOD_CHOICES = [
        ('POINT_IN_TIME', 'Point in Time'),
        ('STRAIGHT_LINE', 'Straight-Line Over Term'),
        ('MILESTONE', 'Milestone-Based'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='revenue_contracts')
    counterparty = models.CharField(max_length=200)
    contract_type = models.CharField(max_length=20, choices=CONTRACT_TYPE_CHOICES)
    recognition_method = models.CharField(max_length=20, choices=RECOGNITION_METHOD_CHOICES)
    total_contract_value = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.ForeignKey(Currency, on_delete=models.PROTECT, default='USD')
    license_start = models.DateField(null=True, blank=True)
    license_end = models.DateField(null=True, blank=True)
    signed_date = models.DateField()
    notes = models.TextField(blank=True)

    def __str__(self):
        return f'{self.project} - {self.counterparty} ({self.get_contract_type_display()})'

    @property
    def total_recognized(self):
        return self.recognition_entries.aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

    @property
    def remaining_to_recognize(self):
        return self.total_contract_value - self.total_recognized


class RevenueMilestone(models.Model):
    """Performance obligation for MILESTONE-method contracts."""
    contract = models.ForeignKey(RevenueContract, on_delete=models.CASCADE, related_name='milestones')
    description = models.CharField(max_length=200)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    target_date = models.DateField(null=True, blank=True)
    delivered_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ['target_date']

    def __str__(self):
        return f'{self.contract} - {self.description}'

    @property
    def is_delivered(self):
        return self.delivered_date is not None


class RevenueRecognitionEntry(models.Model):
    """A recognized revenue event, one per period/milestone. Links to the GL via journal_entry."""
    contract = models.ForeignKey(RevenueContract, on_delete=models.CASCADE, related_name='recognition_entries')
    milestone = models.ForeignKey(
        RevenueMilestone, on_delete=models.SET_NULL, null=True, blank=True, related_name='recognition_entries'
    )
    period_start = models.DateField()
    period_end = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    journal_entry = models.ForeignKey(
        'ledger.JournalEntry', on_delete=models.SET_NULL, null=True, blank=True, related_name='+'
    )

    class Meta:
        ordering = ['period_start']

    def __str__(self):
        return f'{self.contract} {self.period_start}..{self.period_end}: {self.amount}'
