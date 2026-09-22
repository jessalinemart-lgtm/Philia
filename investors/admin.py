from django.contrib import admin

from .models import Distribution, DistributionLineItem, Investment, Investor, WaterfallTier


@admin.register(Investor)
class InvestorAdmin(admin.ModelAdmin):
    list_display = ('name', 'entity_type', 'email')


@admin.register(Investment)
class InvestmentAdmin(admin.ModelAdmin):
    list_display = ('investor', 'project', 'instrument_type', 'amount', 'currency', 'date')
    list_filter = ('project', 'instrument_type')


@admin.register(WaterfallTier)
class WaterfallTierAdmin(admin.ModelAdmin):
    list_display = ('project', 'order', 'tier_type', 'preferred_rate', 'investor_share')
    list_filter = ('project',)


class DistributionLineItemInline(admin.TabularInline):
    model = DistributionLineItem
    extra = 0


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ('project', 'date', 'net_proceeds_available', 'status')
    list_filter = ('project', 'status')
    inlines = [DistributionLineItemInline]
