from django import forms
from django.forms import inlineformset_factory

from core.models import Project
from ledger.models import JournalEntry, JournalLine


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            'title', 'status', 'functional_currency', 'budget_total',
            'greenlit_date', 'wrap_date', 'delivery_date', 'notes',
        ]
        widgets = {
            'greenlit_date': forms.DateInput(attrs={'type': 'date'}),
            'wrap_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['date', 'memo']
        widgets = {'date': forms.DateInput(attrs={'type': 'date'})}


JournalLineFormSet = inlineformset_factory(
    JournalEntry,
    JournalLine,
    fields=['account', 'direction', 'amount', 'currency', 'incurred_jurisdiction', 'memo'],
    extra=2,
    can_delete=True,
    min_num=2,
    validate_min=True,
)
