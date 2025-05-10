from django.urls import path
from django.contrib.auth.decorators import login_required

from challenges.views.challenge_views import ChallengesView
from challenges.views.deployment_views import StartDeploymentView, DeploymentStatusView

urlpatterns = [
    path('', login_required(ChallengesView.as_view()), name='challenges'),
    path('start_deployment/<uuid:challenge_uuid>/', StartDeploymentView.as_view(), name='start_deployment'),
    path('check_deployment/<uuid:challenge_uuid>/', DeploymentStatusView.as_view(), name='check_deployment_status'),
]
