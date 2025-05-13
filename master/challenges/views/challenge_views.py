import logging
import math

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView

from challenges.services import DeploymentService
from challenges.utils.view_helpers import get_user_challenges
from ctf.models import TeamAssignment
from ctf.models.settings import GlobalSettings
from ctf.utils.view_helpers import get_session_time_restrictions, create_challenge_data_dict

logger = logging.getLogger(__name__)


class ChallengesView(LoginRequiredMixin, TemplateView):
    """View for displaying all challenges."""
    template_name = "challenges.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_challenges(self.request.user))
        context['settings'] = GlobalSettings.get_settings()

        if self.request.user.is_authenticated and self.request.user.team:
            deployment_service = DeploymentService()

            for challenge in context.get('challenges', []):
                try:
                    deployment_service.sync_deployment_status(challenge.deployment)

                    has_time_restriction, max_time, time_spent, remaining_time, time_exceeded = (
                        get_session_time_restrictions(challenge, self.request.user.team)
                    )

                    challenge.has_time_restriction = has_time_restriction
                    challenge.max_time = max_time
                    challenge.time_spent = time_spent
                    challenge.remaining_time = remaining_time
                    challenge.time_exceeded = time_exceeded

                except Exception as e:
                    logger.error(f"Error processing challenge {challenge.id}: {e}")

        return context

    def get(self, request, *args, **kwargs):
        if self.is_ajax() and 'challenge_uuid' in kwargs:
            challenge_uuid = kwargs.get('challenge_uuid')
            return self.get_challenge_detail(request, challenge_uuid)
        return super().get(request, *args, **kwargs)

    def is_ajax(self):
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    @staticmethod
    def get_challenge_detail(request, challenge_uuid):
        """Get details for a specific challenge by UUID"""
        try:
            challenge = get_object_or_404(TeamAssignment, uuid=challenge_uuid)
            if not request.user.team or request.user.team != challenge.team:
                return JsonResponse({'error': 'You do not have permission to access this challenge'}, status=403)

            deployment_service = DeploymentService()
            try:
                deployment_service.sync_deployment_status(challenge.deployment)
            except Exception as e:
                logger.error(f"Error syncing deployment status: {e}")

            challenge_data = create_challenge_data_dict(challenge, request.user.team)

            html = render(request, 'partials/challenge_card_inner.html', {
                'challenge': challenge,
                'completed': challenge_data['has_captured_all_flags'],
                'settings': GlobalSettings.get_settings(),
                'has_time_restriction': challenge_data['time_restrictions']['has_time_restriction'],
                'max_time': challenge_data['time_restrictions']['max_time'],
                'time_spent': challenge_data['time_restrictions']['time_spent'],
                'spent_percentage': challenge_data['time_restrictions']['spent_percentage'],
                'remaining_time': challenge_data['time_restrictions']['remaining_time'],
                'time_exceeded': challenge_data['time_restrictions']['time_exceeded'],
                'used_hints': challenge_data['used_hints'],
                'has_next_hint': challenge_data['has_next_hint'],
            }).content.decode('utf-8')

            response_data = {
                'is_running': challenge_data['is_running'],
                'challenge_data': challenge_data,
                'html': html
            }

            return JsonResponse(response_data)
        except Exception as e:
            logger.error(f"Error getting challenge detail: {e}")
            return JsonResponse({'error': str(e)}, status=400)


@login_required
def get_new_hint(request, challenge_uuid):
    assignment = get_object_or_404(TeamAssignment, uuid=challenge_uuid)
    if not request.user.team or not assignment:
        return JsonResponse({'error': 'You do not have permission to access this challenge'}, status=403)

    new_hint_flag = assignment.get_next_available_flag_hint()
    if not new_hint_flag:
        return JsonResponse({'error': 'You have taken all hints for this challenge'}, status=400)

    new_hint_flag.use_hint(request.user.team, assignment.session)

    challenge_data = create_challenge_data_dict(assignment, request.user.team)

    return JsonResponse({
        'new_hint': {
            'hint': new_hint_flag.hint,
            'points': math.ceil(new_hint_flag.points / 2),
        },
        'used_hints': challenge_data['used_hints'],
        'has_next_hint': challenge_data['has_next_hint']
    })
