from .user_views import login_view, logout_view, register_view, settings_view
from .team_views import teams_view, team_detail_view, team_management_view, create_team_view, remove_team_member_view, \
    regenerate_team_key_view, join_team_view

__all__ = [
    'login_view',
    'logout_view',
    'register_view',
    'settings_view',
    'teams_view',
    'team_detail_view',
    'create_team_view',
    'join_team_view',
    'team_management_view',
    'remove_team_member_view',
    'regenerate_team_key_view'
]
