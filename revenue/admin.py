from django.contrib import admin

from .models import RevenueContract, RevenueMilestone, RevenueRecognitionEntry


class RevenueMilestoneInline(admin.TabularInline):
    model = RevenueMilestone
    extra = 1


@admin.register(RevenueContract)
class RevenueContractAdmin(admin.ModelAdmin):
    list_display = ('project', 'counterparty', 'contract_type', 'recognition_method',
                     'total_contract_value', 'currency', 'signed_date')
    list_filter = ('contract_type', 'recognition_method', 'project')
    inlines = [RevenueMilestoneInline]


@admin.register(RevenueRecognitionEntry)
class RevenueRecognitionEntryAdmin(admin.ModelAdmin):
    list_display = ('contract', 'period_start', 'period_end', 'amount', 'journal_entry')
    list_filter = ('contract__project',)
