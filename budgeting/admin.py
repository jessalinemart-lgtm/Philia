from django.contrib import admin

from .models import Budget, BudgetLine


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 1


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('project', 'name', 'version', 'status', 'total_budgeted')
    list_filter = ('project', 'status')
    inlines = [BudgetLineInline]
