from django import forms
from django.core.exceptions import ValidationError

from accounts.models import Team


class CreateTeamForm(forms.ModelForm):
    class Meta:
        model = Team
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Enter team name'})
        }

    def clean_name(self):
        name = self.cleaned_data['name']
        if Team.objects.filter(name=name).exists():
            raise ValidationError('A team with this name already exists.')
        return name


class JoinTeamForm(forms.Form):
    join_key = forms.UUIDField(
        label='Team Join Key',
        widget=forms.TextInput(attrs={'placeholder': 'Enter team join key'})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_join_key(self):
        join_key = self.cleaned_data['join_key']
        try:
            team = Team.objects.get(join_key=join_key)
            if not team.can_join():
                raise ValidationError('This team is full or currently in a game.')
            if self.user.team == team:
                raise ValidationError('You are already a member of this team.')
            return team
        except Team.DoesNotExist:
            raise ValidationError('Invalid team join key.')
