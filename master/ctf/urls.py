from django.contrib.auth.decorators import login_required
from django.urls import path

from ctf.views import scoreboard_view, FlagSubmissionView, rules_view

urlpatterns = [
    path('scoreboard/', scoreboard_view, name='scoreboard'),
    path('challenge/<uuid:challenge_uuid>/submit-flag/', FlagSubmissionView.as_view(), name='submit_flag'),
    path('rules/', rules_view, name='rules'),
]
