from django.urls import path

from challenges.views.challenge_views import ChallengesView
from challenges.views.deployment_views import StartDeploymentView, DeploymentStatusView

urlpatterns = [
    path('', ChallengesView.as_view(), name='challenges'),
    path('start_deployment/<uuid:challenge_uuid>/', StartDeploymentView.as_view(), name='start_deployment'),
    path('check_deployment/<uuid:challenge_uuid>/', DeploymentStatusView.as_view(), name='check_deployment_status'),
]
