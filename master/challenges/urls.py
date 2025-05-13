from django.urls import include, path

from challenges.views import ChallengesView, StartDeploymentView, DeploymentStatusView, get_new_hint

urlpatterns = [
    path('', ChallengesView.as_view(), name='challenges'),
    path('<uuid:challenge_uuid>/', include([
        path('', ChallengesView.as_view(), name='challenge_detail'),
        path('start-deployment/', StartDeploymentView.as_view(), name='start_deployment'),
        path('check-deployment/', DeploymentStatusView.as_view(), name='check_deployment_status'),
        path('hint/', get_new_hint, name='challenge_hint'),
    ])),
]
