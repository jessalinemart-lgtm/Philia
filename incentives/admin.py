from django.contrib import admin

from .models import IncentiveProgram, ProjectIncentiveClaim


@admin.register(IncentiveProgram)
class IncentiveProgramAdmin(admin.ModelAdmin):
    list_display = ('jurisdiction', 'name', 'credit_type', 'rate', 'cap_amount', 'qualified_subtypes')
    list_filter = ('jurisdiction', 'credit_type')


@admin.register(ProjectIncentiveClaim)
class ProjectIncentiveClaimAdmin(admin.ModelAdmin):
    list_display = ('project', 'program', 'status', 'certified_credit_amount', 'funds_received_date')
    list_filter = ('status', 'program__jurisdiction')
