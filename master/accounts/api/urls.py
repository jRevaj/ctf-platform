from django.urls import path

from accounts.api.views import team_score_history

urlpatterns = [
    path('team-score-history/', team_score_history, name='team_score_history'),
]
