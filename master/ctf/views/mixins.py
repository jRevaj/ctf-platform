from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect

from ctf.utils.view_helpers import can_perform_time_restricted_action


class TeamRequiredMixin(LoginRequiredMixin):
    """Mixin that ensures a user is in a team before proceeding."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.team:
            messages.error(request, "You must be in a team")
            return redirect('challenges')
        return super().dispatch(request, *args, **kwargs)


class TimeRestrictionMixin:
    """Mixin that handles time restrictions for challenges."""

    def check_time_restrictions(self, challenge, team):
        """Check if the team has exceeded time limits for this challenge."""
        has_exceeded = can_perform_time_restricted_action(challenge, team)
        if has_exceeded:
            messages.error(self.request, "You have exceeded the time limit for this challenge")
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': 'Time limit exceeded'}, status=403)
            return redirect('challenges')
        return None


class AjaxResponseMixin:
    """Mixin for handling AJAX requests differently from regular requests."""

    def is_ajax(self):
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'