from django.conf import settings
from django.db import models


class Company(models.Model):
    """A production company / studio -- the tenant boundary. Every Project belongs
    to exactly one Company, and users only ever see their own Company's data."""
    name = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'companies'
        ordering = ['name']

    def __str__(self):
        return self.name


class Profile(models.Model):
    """Links a Django User to the Company they belong to. Multiple users can
    share a Company (a team), each with their own login."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='members')

    def __str__(self):
        return f'{self.user} @ {self.company}'
