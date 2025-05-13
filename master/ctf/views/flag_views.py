from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.generic import FormView

from challenges.utils.view_helpers import get_user_challenges
from ctf.forms.flag_forms import FlagSubmissionForm
from ctf.models import TeamAssignment
from ctf.services import FlagService
from ctf.utils.view_helpers import get_session_time_restrictions
from ctf.views.mixins import TeamRequiredMixin, TimeRestrictionMixin, AjaxResponseMixin


class FlagSubmissionView(TeamRequiredMixin, TimeRestrictionMixin, AjaxResponseMixin, FormView):
    """View for submitting flags."""

    form_class = FlagSubmissionForm
    template_name = 'challenges.html'
    challenge = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.challenge = None
        try:
            self.challenge = TeamAssignment.objects.get(uuid=kwargs.get('challenge_uuid'))
        except TeamAssignment.DoesNotExist:
            pass

    def dispatch(self, request, *args, **kwargs):
        if not self.challenge:
            messages.error(request, "Challenge not found")
            return redirect('challenges')

        if not request.user.team:
            messages.error(request, "You must be in a team to submit flags")
            return redirect('challenges')

        if self.challenge.role != 'red':
            messages.error(request, "You can only submit flags in red team phase")
            return redirect('challenges')

        time_check_result = self.check_time_restrictions(self.challenge, request.user.team)
        if time_check_result:
            return time_check_result

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['challenge'] = self.challenge
        kwargs['team'] = self.request.user.team
        return kwargs

    def form_valid(self, form):
        try:
            flag = form.cleaned_data['flag_object']
            FlagService.capture_and_award(flag, self.request.user)
            messages.success(self.request, "Flag captured successfully!")
        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

        if self.is_ajax():
            return self.render_to_response(self.get_ajax_context(form))
        return redirect('challenges')

    def form_invalid(self, form):
        if self.is_ajax():
            return self.render_to_response(self.get_ajax_context(form))
        return super().form_invalid(form)

    def get_ajax_context(self, form):
        has_time_restriction, max_time, time_spent, remaining_time, time_exceeded = (
            get_session_time_restrictions(self.challenge, self.request.user.team)
        )
        return {
            'challenge': self.challenge,
            'form': form,
            'completed': False,
            'has_time_restriction': has_time_restriction,
            'max_time': max_time,
            'time_spent': time_spent,
            'spent_percentage': round((time_spent / max_time) * 100) if max_time > 0 else 0,
            'remaining_time': remaining_time,
            'time_exceeded': time_exceeded
        }

    def render_to_response(self, context):
        if self.is_ajax():
            return render(self.request, 'partials/challenge_card.html', context)
        return super().render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.is_ajax():
            context.update(get_user_challenges(self.request.user))
            context['current_challenge_id'] = self.challenge.id
            context['current_challenge_uuid'] = self.challenge.uuid
        return context
