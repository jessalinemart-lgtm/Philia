from django.urls import path

from . import views

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('project/new/', views.new_project, name='new_project'),
    path('project/<int:pk>/', views.project_detail, name='project_detail'),
    path('project/<int:pk>/trial-balance/', views.trial_balance_view, name='trial_balance'),
    path('project/<int:pk>/journal-entries/new/', views.new_journal_entry, name='new_journal_entry'),
]
