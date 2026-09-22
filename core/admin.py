from django.contrib import admin

from .models import Currency, ExchangeRate, Project


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'symbol')


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'date', 'rate_to_usd')
    list_filter = ('currency',)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'functional_currency', 'budget_total', 'greenlit_date')
    list_filter = ('status',)
