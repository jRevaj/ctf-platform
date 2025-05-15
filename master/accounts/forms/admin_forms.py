from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from accounts.models import User, Team


class TeamAdminForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        widget=FilteredSelectMultiple('Users', is_stacked=False)
    )

    class Meta:
        model = Team
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'created_by' in self.fields:
            qs = User.objects.filter(team__isnull=True)
            if self.instance.pk and self.instance.created_by:
                qs = qs | User.objects.filter(pk=self.instance.created_by.pk)
            self.fields['created_by'].queryset = qs.distinct()
        if self.instance.pk:
            users = list(self.instance.users.all())
            if self.instance.created_by and self.instance.created_by not in users:
                users.append(self.instance.created_by)
            self.fields['users'].initial = users
        self.fields['users'].help_text = "The team owner will always be a member of the team."

    def save(self, commit=True):
        team = super().save(commit)
        if team.pk:
            users = list(self.cleaned_data['users'])
            if team.created_by and team.created_by not in users:
                users.append(team.created_by)
            team.users.set(users)
        return team
