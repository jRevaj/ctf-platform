from django.urls import path

from ctf.views import scoreboard_view, FlagSubmissionView

urlpatterns = [
    path('scoreboard/', scoreboard_view, name='scoreboard'),
    path('submit_flag/<uuid:challenge_uuid>/', FlagSubmissionView.as_view(), name='submit_flag'),
]
