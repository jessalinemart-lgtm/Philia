from decimal import Decimal

from django.db import models


class Currency(models.Model):
    code = models.CharField(max_length=3, primary_key=True)  # ISO 4217, e.g. USD, EUR, GBP
    name = models.CharField(max_length=64)
    symbol = models.CharField(max_length=4, default='$')

    class Meta:
        verbose_name_plural = 'currencies'
        ordering = ['code']

    def __str__(self):
        return self.code


class ExchangeRate(models.Model):
    """Rate to convert 1 unit of `currency` into the functional currency (USD) on `date`."""
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='rates')
    date = models.DateField()
    rate_to_usd = models.DecimalField(max_digits=14, decimal_places=6)

    class Meta:
        unique_together = ('currency', 'date')
        ordering = ['-date']

    def __str__(self):
        return f'{self.currency_id} @ {self.date} = {self.rate_to_usd}'

    @classmethod
    def convert_to_usd(cls, amount: Decimal, currency_code: str, on_date) -> Decimal:
        if currency_code == 'USD':
            return amount
        rate = (
            cls.objects.filter(currency_id=currency_code, date__lte=on_date)
            .order_by('-date')
            .first()
        )
        if rate is None:
            raise ValueError(f'No exchange rate found for {currency_code} on or before {on_date}')
        return (amount * rate.rate_to_usd).quantize(Decimal('0.01'))


class Project(models.Model):
    STATUS_CHOICES = [
        ('DEVELOPMENT', 'Development'),
        ('PRE_PRODUCTION', 'Pre-Production'),
        ('PRODUCTION', 'Production'),
        ('POST_PRODUCTION', 'Post-Production'),
        ('DELIVERED', 'Delivered'),
        ('DISTRIBUTION', 'Distribution'),
        ('CLOSED', 'Closed'),
    ]

    title = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DEVELOPMENT')
    functional_currency = models.ForeignKey(
        Currency, on_delete=models.PROTECT, default='USD', related_name='+'
    )
    budget_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    greenlit_date = models.DateField(null=True, blank=True)
    wrap_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.title
