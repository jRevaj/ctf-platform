from django.urls import path
from django.contrib.auth.decorators import login_required

from ctf.views import scoreboard_view, FlagSubmissionView

urlpatterns = [
    path('scoreboard/', login_required(scoreboard_view), name='scoreboard'),
    path('submit_flag/<uuid:challenge_uuid>/', FlagSubmissionView.as_view(), name='submit_flag'),
]
