from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Currency, ExchangeRate, Project
from ledger.models import Account, post_journal_entry
from budgeting.models import Budget, BudgetLine
from revenue.models import RevenueContract, RevenueMilestone
from revenue.services import recognize_point_in_time, recognize_straight_line_month, recognize_milestone
from investors.models import Investor, Investment, WaterfallTier
from investors.services import run_waterfall


class Command(BaseCommand):
    help = 'Seed the database with a realistic demo project for Philia.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding currencies...')
        usd, _ = Currency.objects.get_or_create(code='USD', defaults={'name': 'US Dollar', 'symbol': '$'})
        eur, _ = Currency.objects.get_or_create(code='EUR', defaults={'name': 'Euro', 'symbol': '€'})
        gbp, _ = Currency.objects.get_or_create(code='GBP', defaults={'name': 'British Pound', 'symbol': '£'})

        ExchangeRate.objects.get_or_create(currency=eur, date=date(2024, 1, 1), defaults={'rate_to_usd': Decimal('1.10')})
        ExchangeRate.objects.get_or_create(currency=eur, date=date(2024, 6, 1), defaults={'rate_to_usd': Decimal('1.08')})
        ExchangeRate.objects.get_or_create(currency=gbp, date=date(2024, 1, 1), defaults={'rate_to_usd': Decimal('1.27')})
        ExchangeRate.objects.get_or_create(currency=gbp, date=date(2024, 6, 1), defaults={'rate_to_usd': Decimal('1.25')})

        self.stdout.write('Seeding chart of accounts...')
        accounts = {}
        chart = [
            ('1000', 'Cash', 'ASSET', ''),
            ('1200', 'Accounts Receivable', 'ASSET', ''),
            ('2000', 'Accounts Payable', 'LIABILITY', ''),
            ('3000', 'Paid-in Capital', 'EQUITY', ''),
            ('4000', 'Revenue', 'REVENUE', ''),
            ('5100', 'Above-the-Line Costs', 'EXPENSE', 'ATL'),
            ('5200', 'Below-the-Line Costs', 'EXPENSE', 'BTL'),
            ('5300', 'Post-Production Costs', 'EXPENSE', 'POST'),
            ('5400', 'Marketing & Distribution Costs', 'EXPENSE', 'MARKETING'),
            ('5500', 'Overhead', 'EXPENSE', 'OVERHEAD'),
        ]
        for code, name, acct_type, subtype in chart:
            acct, _ = Account.objects.get_or_create(
                code=code, defaults={'name': name, 'account_type': acct_type, 'subtype': subtype}
            )
            accounts[code] = acct

        self.stdout.write('Creating project...')
        project, _ = Project.objects.get_or_create(
            title='The Last Reel',
            defaults={
                'status': 'DISTRIBUTION',
                'functional_currency': usd,
                'budget_total': Decimal('5000000.00'),
                'greenlit_date': date(2024, 1, 15),
                'wrap_date': date(2024, 6, 1),
                'delivery_date': date(2024, 9, 1),
                'notes': 'Independent feature financed via equity + gap financing, '
                         'shot partly in the UK and Germany (hence multi-currency cost lines).',
            },
        )

        self.stdout.write('Building budget...')
        budget, _ = Budget.objects.get_or_create(
            project=project, version=1, defaults={'name': 'Production Budget', 'status': 'APPROVED'}
        )
        budget_lines = {
            '5100': Decimal('1200000.00'),
            '5200': Decimal('2400000.00'),
            '5300': Decimal('700000.00'),
            '5400': Decimal('500000.00'),
            '5500': Decimal('200000.00'),
        }
        for code, amount in budget_lines.items():
            BudgetLine.objects.get_or_create(budget=budget, account=accounts[code], defaults={'budgeted_amount': amount})

        self.stdout.write('Recording capital raise...')
        post_journal_entry(
            project=project, date=date(2024, 1, 20), memo='Initial equity capital call',
            source='MANUAL',
            lines=[
                {'account': accounts['1000'], 'direction': 'DEBIT', 'amount': Decimal('4500000.00'), 'currency': usd},
                {'account': accounts['3000'], 'direction': 'CREDIT', 'amount': Decimal('4500000.00'), 'currency': usd},
            ],
        )

        self.stdout.write('Recording production costs (multi-currency)...')
        cost_entries = [
            (date(2024, 2, 1), '5100', Decimal('1150000.00'), usd, 'Cast & director fees'),
            (date(2024, 3, 15), '5200', Decimal('980000.00'), gbp, 'UK unit crew & stage rental'),
            (date(2024, 4, 10), '5200', Decimal('1150000.00'), eur, 'Germany location unit'),
            (date(2024, 4, 25), '5200', Decimal('520000.00'), usd, 'Equipment & production insurance'),
            (date(2024, 6, 20), '5300', Decimal('740000.00'), usd, 'Editorial, VFX & sound mix (over budget)'),
            (date(2024, 7, 5), '5400', Decimal('430000.00'), usd, 'Festival strategy & trailer campaign'),
            (date(2024, 7, 5), '5500', Decimal('180000.00'), usd, 'Legal, accounting & overhead'),
        ]
        for d, code, amount, currency, memo in cost_entries:
            post_journal_entry(
                project=project, date=d, memo=memo, source='BUDGET_ACTUAL',
                lines=[
                    {'account': accounts[code], 'direction': 'DEBIT', 'amount': amount, 'currency': currency, 'memo': memo},
                    {'account': accounts['1000'], 'direction': 'CREDIT', 'amount': amount, 'currency': currency, 'memo': memo},
                ],
            )

        self.stdout.write('Creating revenue contracts + recognizing revenue...')
        theatrical = RevenueContract.objects.create(
            project=project, counterparty='Indie Theatrical Releasing Co.',
            contract_type='THEATRICAL', recognition_method='POINT_IN_TIME',
            total_contract_value=Decimal('600000.00'), currency=usd,
            signed_date=date(2024, 8, 1),
        )
        recognize_point_in_time(theatrical, date(2024, 9, 15))

        svod = RevenueContract.objects.create(
            project=project, counterparty='StreamMax Global',
            contract_type='SVOD', recognition_method='STRAIGHT_LINE',
            total_contract_value=Decimal('2400000.00'), currency=usd,
            license_start=date(2024, 10, 1), license_end=date(2026, 9, 30),
            signed_date=date(2024, 9, 1),
        )
        for month in (date(2024, 10, 1), date(2024, 11, 1), date(2024, 12, 1)):
            recognize_straight_line_month(svod, month)

        intl = RevenueContract.objects.create(
            project=project, counterparty='Global Sales Agency Ltd.',
            contract_type='INTERNATIONAL', recognition_method='MILESTONE',
            total_contract_value=Decimal('1500000.00'), currency=usd,
            signed_date=date(2024, 8, 15),
        )
        m1 = RevenueMilestone.objects.create(contract=intl, description='EFM market delivery', allocated_amount=Decimal('500000.00'), target_date=date(2025, 2, 1))
        m2 = RevenueMilestone.objects.create(contract=intl, description='Territory deliverables complete', allocated_amount=Decimal('1000000.00'), target_date=date(2025, 5, 1))
        recognize_milestone(m1, date(2025, 2, 10))

        self.stdout.write('Setting up investors & waterfall...')
        inv1 = Investor.objects.create(name='Meridian Film Fund', entity_type='FUND', email='ir@meridianfilmfund.example')
        inv2 = Investor.objects.create(name='Alicia Chen', entity_type='INDIVIDUAL', email='alicia.chen@example.com')
        inv3 = Investor.objects.create(name='Northgate Capital LLC', entity_type='LLC', email='deals@northgatecap.example')

        Investment.objects.create(investor=inv1, project=project, instrument_type='EQUITY', amount=Decimal('2500000.00'), currency=usd, date=date(2024, 1, 20))
        Investment.objects.create(investor=inv2, project=project, instrument_type='EQUITY', amount=Decimal('750000.00'), currency=usd, date=date(2024, 1, 20))
        Investment.objects.create(investor=inv3, project=project, instrument_type='GAP', amount=Decimal('1250000.00'), currency=usd, date=date(2024, 2, 1))

        WaterfallTier.objects.create(project=project, order=1, tier_type='RETURN_OF_CAPITAL')
        WaterfallTier.objects.create(project=project, order=2, tier_type='PREFERRED_RETURN', preferred_rate=Decimal('0.15'))
        WaterfallTier.objects.create(project=project, order=3, tier_type='PROFIT_SPLIT', investor_share=Decimal('0.50'))

        self.stdout.write('Running distribution waterfall...')
        run_waterfall(project, date(2025, 3, 1), Decimal('1800000.00'), status='FINALIZED')

        self.stdout.write(self.style.SUCCESS(
            f'Done. Project "{project}" seeded with chart of accounts, budget, multi-currency costs, '
            f'3 revenue contracts, 3 investors, and a finalized distribution run.'
        ))
