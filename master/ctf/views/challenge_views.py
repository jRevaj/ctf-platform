from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import TemplateView

from ctf.models import TeamAssignment
from ctf.models.settings import GlobalSettings
from ctf.services import DeploymentService
from ctf.utils.view_helpers import get_user_challenges, get_session_time_restrictions
import logging

logger = logging.getLogger(__name__)

class ChallengesView(TemplateView):
    """View for displaying all challenges."""

    template_name = "challenges.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_user_challenges(self.request.user))
        context['settings'] = GlobalSettings.get_settings()

        if self.request.user.is_authenticated and self.request.user.team:
            deployment_service = DeploymentService()
            
            # Process time restrictions for each challenge
            for challenge in context.get('challenges', []):
                try:
                    # Sync deployment status
                    deployment_service.sync_deployment_status(challenge.deployment)
                    
                    # Add time restriction data
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
        if self.is_ajax():
            return self.ajax_get(request, *args, **kwargs)
        return super().get(request, *args, **kwargs)

    def is_ajax(self):
        return self.request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    @staticmethod
    def ajax_get(request, *args, **kwargs):
        challenge_uuid = request.GET.get('challenge_uuid')
        if not challenge_uuid:
            return JsonResponse({'error': 'Missing challenge UUID'}, status=400)

        try:
            challenge = TeamAssignment.objects.get(uuid=challenge_uuid)
            
            # Sync deployment status
            deployment_service = DeploymentService()
            try:
                deployment_service.sync_deployment_status(challenge.deployment)
            except Exception as e:
                logger.error(f"Error syncing deployment status: {e}")
            
            has_time_restriction, max_time, time_spent, remaining_time, time_exceeded = (
                get_session_time_restrictions(challenge, request.user.team)
            )

            settings = GlobalSettings.get_settings()

            # Make sure we have fresh data about running status
            is_running = challenge.deployment.is_running()
            
            deployment_status = {
                'is_running': is_running,
                'html': render(request, 'partials/challenge_card_inner.html', {
                    'challenge': challenge,
                    'completed': False,
                    'settings': settings,
                    'has_time_restriction': has_time_restriction,
                    'max_time': max_time,
                    'time_spent': time_spent,
                    'spent_percentage': round((time_spent / max_time) * 100) if max_time > 0 else 0,
                    'remaining_time': remaining_time,
                    'time_exceeded': time_exceeded
                }).content.decode('utf-8')
            }
            return JsonResponse(deployment_status)
        except TeamAssignment.DoesNotExist:
            return JsonResponse({'error': 'Challenge not found'}, status=404)
