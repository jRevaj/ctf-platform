"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include

from ctf.api.urls import api_urls
from ctf.views import home, ChallengesView, scoreboard_view, FlagSubmissionView, StartDeploymentView, \
    DeploymentStatusView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('challenges/', ChallengesView.as_view(), name='challenges'),
    path('scoreboard/', scoreboard_view, name='scoreboard'),
    path('submit_flag/<uuid:challenge_uuid>/', FlagSubmissionView.as_view(), name='submit_flag'),
    path('start_deployment/<uuid:challenge_uuid>/', StartDeploymentView.as_view(), name='start_deployment'),
    path('check_deployment/<uuid:challenge_uuid>/', DeploymentStatusView.as_view(), name='check_deployment_status'),
    path('__reload__/', include('django_browser_reload.urls')),
    path('api/', include(api_urls))
]
