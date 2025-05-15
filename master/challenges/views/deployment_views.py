import logging
import time
from threading import Thread

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views.generic import DetailView

from challenges.services import DeploymentService
from ctf.models import TeamAssignment
from ctf.utils.view_helpers import create_challenge_data_dict
from ctf.views.mixins import TeamRequiredMixin, AjaxResponseMixin, TimeRestrictionMixin

logger = logging.getLogger(__name__)


class DeploymentStatusView(TeamRequiredMixin, AjaxResponseMixin, DetailView):
    """View for checking deployment status."""
    model = TeamAssignment
    slug_field = 'uuid'
    slug_url_kwarg = 'challenge_uuid'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.team != self.request.user.team:
            raise PermissionDenied("You don't have permission to access this deployment")
        return obj

    def get(self, request, *args, **kwargs):
        try:
            assignment = self.get_object()
            logger.info(
                f"Checking deployment status for challenge {assignment.uuid}, "
                f"deployment {assignment.deployment.uuid}"
            )

            deployment_service = DeploymentService()
            try:
                deployment_service.sync_deployment_status(assignment.deployment)
            except Exception as e:
                logger.error(f"Error syncing deployment status: {e}")
                return JsonResponse({
                    'is_running': False,
                    'error': str(e),
                    'connection_info': []
                })

            challenge_data = create_challenge_data_dict(assignment, request.user.team)

            response_data = {
                'is_running': challenge_data['is_running'],
                'connection_info': challenge_data.get('connection_string', ''),
            }
            if 'time_restrictions' in challenge_data:
                response_data.update(challenge_data['time_restrictions'])

            return JsonResponse(response_data)
        except TeamAssignment.DoesNotExist:
            return JsonResponse({'error': 'Challenge not found'}, status=404)
        except PermissionDenied as e:
            return JsonResponse({'error': str(e)}, status=403)
        except Exception as e:
            logger.error(f"Error checking deployment status: {e}", exc_info=True)
            return JsonResponse({'error': str(e)}, status=500)


class StartDeploymentView(TeamRequiredMixin, TimeRestrictionMixin, AjaxResponseMixin, DetailView):
    """View for starting a deployment."""
    model = TeamAssignment
    slug_field = 'uuid'
    slug_url_kwarg = 'challenge_uuid'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.team != self.request.user.team:
            raise PermissionDenied("You don't have permission to start this deployment")
        return obj

    def post(self, request, *args, **kwargs):
        try:
            challenge = self.get_object()

            time_check_result = self.check_time_restrictions(challenge, request.user.team)
            if time_check_result:
                return time_check_result

            thread = Thread(
                target=start_deployment_async,
                args=(challenge.deployment.id, request.user.team.id)
            )
            thread.daemon = True
            thread.start()

            if self.is_ajax():
                # Create a simplified response
                response_data = {'success': True, 'message': 'Deployment start initiated. Please wait...',
                                 'deployment_id': challenge.deployment.id, 'challenge_uuid': str(challenge.uuid),
                                 'html': render(request, 'partials/challenge_card_inner.html', {
                                     'challenge': challenge,
                                     'completed': False,
                                     'deployment_starting': True
                                 }).content.decode('utf-8')}

                return JsonResponse(response_data)

            return redirect('challenges')

        except TeamAssignment.DoesNotExist:
            messages.error(request, "Challenge not found")
            if self.is_ajax():
                return JsonResponse({'error': 'Challenge not found'}, status=404)
            return redirect('challenges')
        except PermissionDenied as e:
            messages.error(request, str(e))
            if self.is_ajax():
                return JsonResponse({'error': str(e)}, status=403)
            return redirect('challenges')
        except Exception as e:
            messages.error(request, str(e))
            if self.is_ajax():
                return JsonResponse({'error': str(e)}, status=500)
            return redirect('challenges')


def start_deployment_async(deployment_id, team_id):
    """Background task to start a deployment"""
    try:
        from challenges.models import ChallengeDeployment

        logger.info(f"Starting deployment {deployment_id} for team {team_id}")
        deployment = ChallengeDeployment.objects.get(id=deployment_id)

        deployment_service = DeploymentService()
        success = deployment_service.start_deployment(deployment)

        if success:
            logger.info(f"Deployment {deployment_id} started successfully, syncing status...")
            time.sleep(2)
            sync_result = deployment_service.sync_deployment_status(deployment)
            if not sync_result:
                logger.warning(f"Failed to sync deployment {deployment_id} status")
            else:
                logger.info(f"Deployment {deployment_id} status synced successfully")
        else:
            logger.error(f"Failed to start deployment {deployment_id}")
    except Exception as e:
        logger.error(f"Error in async deployment start: {e}", exc_info=True)
