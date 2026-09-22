from django.contrib import admin

from .models import Account, JournalEntry, JournalLine


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'account_type', 'subtype', 'is_active')
    list_filter = ('account_type', 'subtype', 'is_active')


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 2
    readonly_fields = ('functional_amount',)


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'date', 'source', 'memo')
    list_filter = ('source', 'project')
    inlines = [JournalLineInline]
