from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class SignupForm(UserCreationForm):
    company_name = forms.CharField(max_length=200, label='Company / production name')
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('username', 'email', 'company_name', 'password1', 'password2')
