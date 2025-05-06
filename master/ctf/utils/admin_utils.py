from django.shortcuts import redirect


def handle_action_redirect(request, container_id):
    """Helper to handle redirects from actions"""
    if request.META.get("HTTP_REFERER", "").endswith(f"/change/"):
        return redirect("admin:challenges_challengecontainer_change", container_id)
    return redirect("admin:challenges_challengecontainer_changelist")