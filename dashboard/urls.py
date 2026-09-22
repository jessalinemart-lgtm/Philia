from django.urls import path

from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('project/<int:pk>/trial-balance/', views.trial_balance_view, name='trial_balance'),
]
