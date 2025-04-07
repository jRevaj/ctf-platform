from django import forms
from django.core.exceptions import ValidationError

from ctf.models import Flag


class FlagSubmissionForm(forms.Form):
    flag = forms.CharField(
        max_length=128,
        widget=forms.TextInput(attrs={'placeholder': 'Enter flag value'})
    )

    def __init__(self, *args, **kwargs):
        self.challenge = kwargs.pop('challenge', None)
        self.team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)

    def clean_flag(self):
        flag_value = self.cleaned_data['flag']

        try:
            flag = Flag.objects.get_flag_by_value(flag_value)
            if not flag:
                raise ValidationError("Invalid flag")

            if flag.is_captured:
                raise ValidationError("Flag has already been captured")

            if flag.owner == self.team:
                raise ValidationError("You cannot capture your own team's flag")

            if flag.container and flag.container.deployment:
                blue_assignment = flag.container.deployment.assignments.filter(role='blue').first()
                if not blue_assignment:
                    raise ValidationError("Invalid flag configuration - no blue team assignment found")
                
                if flag.container.deployment != self.challenge.deployment:
                    raise ValidationError("This flag does not belong to this challenge")
                if blue_assignment.team != self.challenge.session.team_assignments.filter(role='blue').first().team:
                    raise ValidationError("This flag does not belong to the correct blue team")
            else:
                raise ValidationError("Invalid flag configuration")

            self.cleaned_data['flag_object'] = flag
            return flag_value

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(str(e))
