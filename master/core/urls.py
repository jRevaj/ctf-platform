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
from django.contrib.auth.decorators import login_required
from django.urls import path, include

from ctf.views import (
    health_check, home, register_view, login_view, logout_view, settings_view,
    create_team_view, join_team_view, remove_team_member_view, team_management_view,
    regenerate_team_key_view, challenges_view, submit_flag_view, start_deployment_view,
    check_deployment_status, scoreboard_view, teams_view, team_detail_view,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home, name='home'),
    path('challenges/', challenges_view, name='challenges'),
    path('scoreboard/', scoreboard_view, name='scoreboard'),
    path('teams/', teams_view, name='teams'),
    path('teams/<uuid:team_uuid>/', team_detail_view, name='team_detail'),
    path('auth/', include([
        path('register/', register_view, name='register'),
        path('login/', login_view, name='login'),
        path('logout/', logout_view, name='logout'),
    ])),
    path('settings/', include([
        path('', login_required(settings_view), name='settings'),
        path('team/details/', login_required(team_management_view), name='team_details'),
        path('team/create/', login_required(create_team_view), name='create_team'),
        path('team/join/', login_required(join_team_view), name='join_team'),
        path('team/remove-member/<int:member_id>/', login_required(remove_team_member_view), name='remove_team_member'),
        path('team/regenerate-key/', login_required(regenerate_team_key_view), name='regenerate_team_key'),
    ])),
    path('submit_flag/<uuid:challenge_uuid>/', login_required(submit_flag_view), name='submit_flag'),
    path('start_deployment/<uuid:challenge_uuid>/', login_required(start_deployment_view), name='start_deployment'),
    path('check_deployment/<uuid:challenge_uuid>/', login_required(check_deployment_status),
         name='check_deployment_status'),
    path('__reload__/', include('django_browser_reload.urls')),
    path('health/', health_check, name='health_check'),
]
