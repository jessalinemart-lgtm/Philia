from decimal import Decimal

from django.db import models

from core.models import Jurisdiction, Project


class IncentiveProgram(models.Model):
    """
    A jurisdiction's film production tax incentive, e.g. Georgia's 30% transferable
    credit or the UK's 25% Audio-Visual Expenditure Credit. `qualified_subtypes` lists
    which ledger.Account.subtype categories count toward qualified spend for this
    program -- most incentives exclude some above-the-line costs (e.g. star salaries
    above a cap) and non-local spend, so this is deliberately configurable per program
    rather than "all production costs qualify."
    """
    CREDIT_TYPE_CHOICES = [
        ('REBATE', 'Cash Rebate'),
        ('TRANSFERABLE_CREDIT', 'Transferable Tax Credit'),
        ('REFUNDABLE_CREDIT', 'Refundable Tax Credit'),
    ]

    jurisdiction = models.ForeignKey(Jurisdiction, on_delete=models.CASCADE, related_name='incentive_programs')
    name = models.CharField(max_length=150)
    credit_type = models.CharField(max_length=20, choices=CREDIT_TYPE_CHOICES)
    rate = models.DecimalField(max_digits=5, decimal_places=4, help_text='e.g. 0.30 for a 30% credit')
    cap_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text='Maximum credit this program will pay out per project, if capped'
    )
    # Comma-separated ledger.Account.subtype codes (ATL,BTL,POST,MARKETING,OVERHEAD) that
    # qualify as spend under this program.
    qualified_subtypes = models.CharField(max_length=100, default='BTL,POST')
    # For TRANSFERABLE_CREDIT: the discount buyers typically pay, e.g. 0.90 = credit
    # monetizes at 90 cents on the dollar when sold to a taxpayer who can use it directly.
    typical_monetization_rate = models.DecimalField(
        max_digits=5, decimal_places=4, default=Decimal('1.0'),
        help_text='Cash value per dollar of credit once sold/received, e.g. 0.90'
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['jurisdiction', 'name']

    def __str__(self):
        return f'{self.jurisdiction} - {self.name} ({self.rate:.0%})'

    def qualified_subtype_list(self):
        return [s.strip() for s in self.qualified_subtypes.split(',') if s.strip()]


class ProjectIncentiveClaim(models.Model):
    """
    A specific project's claim against an IncentiveProgram. Qualified spend and estimated
    credit are computed live from the ledger (see incentives/services.py) rather than
    stored, except once a claim is CERTIFIED -- at that point the jurisdiction's own
    audited figures become the number of record and are stored directly.
    """
    STATUS_CHOICES = [
        ('ESTIMATED', 'Estimated'),
        ('APPLIED', 'Application Filed'),
        ('UNDER_REVIEW', 'Under Audit/Review'),
        ('CERTIFIED', 'Certified'),
        ('RECEIVED', 'Funds Received'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='incentive_claims')
    program = models.ForeignKey(IncentiveProgram, on_delete=models.PROTECT, related_name='claims')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ESTIMATED')
    application_date = models.DateField(null=True, blank=True)
    certification_date = models.DateField(null=True, blank=True)
    funds_received_date = models.DateField(null=True, blank=True)
    # Set once the jurisdiction has certified the claim -- overrides the live ledger estimate.
    certified_qualified_spend = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    certified_credit_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['project', 'program']
        unique_together = ('project', 'program')

    def __str__(self):
        return f'{self.project} - {self.program} ({self.get_status_display()})'

    @property
    def is_certified(self):
        return self.certified_credit_amount is not None
