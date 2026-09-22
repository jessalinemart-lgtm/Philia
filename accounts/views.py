from django.contrib.auth import login
from django.db import transaction
from django.shortcuts import redirect, render

from .forms import SignupForm
from .models import Company, Profile


def signup(request):
    if request.user.is_authenticated:
        return redirect('project_list')

    if request.method == 'POST':
        form = SignupForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = form.save(commit=False)
                user.email = form.cleaned_data['email']
                user.save()
                company = Company.objects.create(name=form.cleaned_data['company_name'])
                Profile.objects.create(user=user, company=company)
            login(request, user)
            return redirect('project_list')
    else:
        form = SignupForm()

    return render(request, 'accounts/signup.html', {'form': form})
