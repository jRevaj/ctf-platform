import time
import uuid
from threading import Thread

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from ctf.forms.auth_forms import UserRegistrationForm, UserLoginForm, UserSettingsForm
from ctf.forms.flag_forms import FlagSubmissionForm
from ctf.forms.team_forms import CreateTeamForm, JoinTeamForm
from ctf.models import User, TeamAssignment
from ctf.services.deployment_service import DeploymentService
from ctf.services.flag_service import FlagService
from ctf.utils import get_user_challenges


def health_check(request):
    return HttpResponse("OK")


def home(request):
    context = get_user_challenges(request.user)
    return render(request, "home.html", context)


def register_view(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserRegistrationForm()
    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.method == "POST":
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")
    else:
        form = UserLoginForm()
    return render(request, "registration/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


# noinspection PyUnresolvedReferences
@login_required
def settings_view(request):
    if request.method == "POST":
        form = UserSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your settings have been updated successfully.")
            return redirect("settings")
    else:
        form = UserSettingsForm(instance=request.user)

    ssh_key_locked = form.is_ssh_key_locked()

    context = {
        "form": form,
        "user_team": request.user.team,
        "can_manage_team": (
            request.user.team and request.user.team.can_manage_members(request.user)
            if request.user.team
            else False
        ),
        "ssh_key_locked": ssh_key_locked,
    }
    return render(request, "settings/main.html", context)


@login_required
def create_team_view(request):
    if request.user.team:
        messages.error(request, "You are already in a team.")
        return redirect("settings")

    if request.method == "POST":
        form = CreateTeamForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                team = form.save(commit=False)
                team.created_by = request.user
                team.save()
                request.user.team = team
                request.user.save()
            messages.success(request, f"Team {team.name} created successfully!")
            return redirect("team_details")
    else:
        form = CreateTeamForm()

    return render(request, "settings/create_team.html", {"form": form})


@login_required
def join_team_view(request):
    if request.user.team:
        messages.error(request, "You are already in a team.")
        return redirect("settings")

    if request.method == "POST":
        form = JoinTeamForm(request.POST, user=request.user)
        if form.is_valid():
            team = form.cleaned_data["join_key"]
            with transaction.atomic():
                request.user.team = team
                request.user.save()
                team.clean()
                team.save()
            messages.success(request, f"Successfully joined team {team.name}!")
            return redirect("team_details")
    else:
        form = JoinTeamForm(user=request.user)

    return render(request, "settings/join_team.html", {"form": form})


# noinspection PyUnresolvedReferences
@login_required
def team_management_view(request):
    if not request.user.team:
        messages.error(request, "You are not in a team.")
        return redirect("settings")

    context = {
        "user_team": request.user.team,
        "can_manage_team": (
            request.user.team.can_manage_members(request.user)
            if request.user.team
            else False
        ),
    }
    return render(request, "settings/team_details.html", context)


# noinspection PyUnresolvedReferences
@login_required
def remove_team_member_view(request, member_id):
    if not request.user.team:
        messages.error(request, "You are not in a team.")
        return redirect("settings")

    member_to_remove = get_object_or_404(User, id=member_id)

    try:
        with transaction.atomic():
            request.user.team.remove_member(request.user, member_to_remove)
        messages.success(
            request, f"Successfully removed user {member_to_remove.username} from the team."
        )
    except (PermissionDenied, ValidationError) as e:
        messages.error(request, str(e))

    return redirect("team_details")


# noinspection PyUnresolvedReferences
@login_required
def regenerate_team_key_view(request):
    if not request.user.team or request.user.team.created_by != request.user:
        messages.error(
            request, "You do not have permission to regenerate the team key."
        )
        return redirect("team_details")

    if request.user.team.is_in_game:
        messages.error(request, "Cannot regenerate team key while in a game.")
        return redirect("team_details")

    request.user.team.join_key = uuid.uuid4()
    request.user.team.save()

    messages.success(request, "Team join key has been regenerated.")
    return redirect("team_details")


def challenges_view(request):
    context = get_user_challenges(request.user)

    # If this is an AJAX request for refreshing a challenge card
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        challenge_uuid = request.GET.get('challenge_uuid')
        if challenge_uuid:
            try:
                challenge = TeamAssignment.objects.get(uuid=challenge_uuid)
                deployment_status = {
                    'is_running': challenge.deployment.is_running(),
                    'html': render(request, 'partials/challenge_card_inner.html', {
                        'challenge': challenge,
                        'completed': False
                    }).content.decode('utf-8')
                }
                return JsonResponse(deployment_status)
            except TeamAssignment.DoesNotExist:
                return JsonResponse({'error': 'Challenge not found'}, status=404)

    return render(request, "challenges.html", context)


@login_required
def check_deployment_status(request, challenge_uuid):
    """Check the status of a deployment and return connection information"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        challenge = TeamAssignment.objects.get(uuid=challenge_uuid)

        if challenge.team != request.user.team:
            return JsonResponse({'error': 'Permission denied'}, status=403)

        logger.info(f"Checking deployment status for challenge {challenge_uuid}, deployment {challenge.deployment.uuid}")

        deployment_service = DeploymentService()
        try:
            deployment_service.sync_deployment_status(challenge.deployment)
        except Exception as e:
            logger.error(f"Error syncing deployment status: {e}")
            return JsonResponse({
                'is_running': False,
                'error': str(e),
                'connection_info': []
            })

        is_running = challenge.deployment.is_running()
        connection_info = []

        if is_running:
            for container in challenge.deployment.containers.all():
                if container.is_entrypoint:
                    connection_string = container.get_connection_string()
                    connection_info.append({
                        'id': container.id,
                        'name': container.name,
                        'connection_string': connection_string,
                        'is_available': 'not' not in connection_string
                    })

        return JsonResponse({
            'is_running': is_running,
            'connection_info': connection_info
        })

    except TeamAssignment.DoesNotExist:
        return JsonResponse({'error': 'Challenge not found'}, status=404)
    except Exception as e:
        logger.error(f"Error checking deployment status: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


def start_deployment_async(deployment_id, team_id):
    """Background task to start a deployment"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        from ctf.models import ChallengeDeployment, Team

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


@login_required
def start_deployment_view(request, challenge_uuid):
    """Start a deployment for a challenge"""
    try:
        if not request.user.team:
            messages.error(request, "You must be in a team to start deployments")
            return redirect('challenges')

        challenge = TeamAssignment.objects.get(uuid=challenge_uuid)

        if challenge.team != request.user.team:
            messages.error(request, "You don't have permission to start this deployment")
            return redirect('challenges')

        thread = Thread(
            target=start_deployment_async,
            args=(challenge.deployment.id, request.user.team.id)
        )
        thread.daemon = True
        thread.start()

        messages.success(request, "Deployment start initiated. It may take a moment to be ready.")

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Deployment start initiated. Please wait...',
                'deployment_id': challenge.deployment.id,
                'challenge_uuid': str(challenge.uuid),
                'html': render(request, 'partials/challenge_card_inner.html', {
                    'challenge': challenge,
                    'completed': False,
                    'deployment_starting': True
                }).content.decode('utf-8')
            })

        return redirect('challenges')

    except TeamAssignment.DoesNotExist:
        messages.error(request, "Challenge not found")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Challenge not found'}, status=404)
        return redirect('challenges')
    except Exception as e:
        messages.error(request, str(e))
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'error': str(e)}, status=500)
        return redirect('challenges')


@login_required
def submit_flag_view(request, challenge_uuid):
    try:
        challenge = TeamAssignment.objects.get(uuid=challenge_uuid)

        if not request.user.team:
            messages.error(request, "You must be in a team to submit flags")
            return redirect('challenges')

        if challenge.role != 'red':
            messages.error(request, "You can only submit flags in red team phase")
            return redirect('challenges')

        if request.method == "POST":
            form = FlagSubmissionForm(request.POST, challenge=challenge, team=request.user.team)
            if form.is_valid():
                try:
                    flag = form.cleaned_data['flag_object']
                    FlagService.capture_and_award(flag, request.user.team)
                    messages.success(request, "Flag captured successfully!")
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        form = FlagSubmissionForm(challenge=challenge, team=request.user.team)
                    else:
                        return redirect('challenges')
                except Exception as e:
                    messages.error(request, str(e))
        else:
            form = FlagSubmissionForm(challenge=challenge, team=request.user.team)

        context = get_user_challenges(request.user)
        context['form'] = form
        context['current_challenge_id'] = challenge.id
        context['current_challenge_uuid'] = challenge.uuid

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render(request, 'partials/challenge_card.html', {
                'challenge': challenge,
                'form': form,
                'completed': False
            })

        return render(request, 'challenges.html', context)

    except TeamAssignment.DoesNotExist:
        messages.error(request, "Challenge not found")
        return redirect('challenges')
    except Exception as e:
        messages.error(request, str(e))
        return redirect('challenges')
