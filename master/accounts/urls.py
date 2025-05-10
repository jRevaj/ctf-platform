from django.contrib.auth.decorators import login_required
from django.urls import path, include

from accounts.views import team_detail_view, teams_view, team_management_view, create_team_view, join_team_view, \
    remove_team_member_view, regenerate_team_key_view, register_view, login_view, logout_view, settings_view

urlpatterns = [
    path('auth/', include([
        path('register/', register_view, name='register'),
        path('login/', login_view, name='login'),
        path('logout/', logout_view, name='logout'),
    ])),
    path('teams/', login_required(teams_view), name='teams'),
    path('teams/<uuid:team_uuid>/', login_required(team_detail_view), name='team_detail'),
    path('settings/', include([
        path('', login_required(settings_view), name='settings'),
        path('team/details/', login_required(team_management_view), name='team_details'),
        path('team/create/', login_required(create_team_view), name='create_team'),
        path('team/join/', login_required(join_team_view), name='join_team'),
        path('team/remove-member/<int:member_id>/', login_required(remove_team_member_view), name='remove_team_member'),
        path('team/regenerate-key/', login_required(regenerate_team_key_view), name='regenerate_team_key'),
    ])),
    path('api/', include('accounts.api.urls')),
]
