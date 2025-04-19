from django.forms import ModelForm, ValidationError
from django.utils import timezone

from ctf.models import GameContainer, GameSession
from ctf.models.enums import GameSessionStatus


class GameContainerForm(ModelForm):
    class Meta:
        model = GameContainer
        fields = '__all__'
        help_texts = {
            'status': 'Container status is automatically synced with Docker. Use the action buttons to change status.',
            'docker_id': 'Docker container ID is set automatically upon creation.',
            'template_name': 'Template cannot be changed after container creation.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['docker_id'].disabled = True
            self.fields['template_name'].disabled = True
            self.fields['port'].disabled = True

    def clean_status(self):
        """Prevent manual status editing through the form"""
        if self.instance.pk:
            if self.cleaned_data['status'] != self.instance.status:
                raise ValidationError(
                    "Container status cannot be changed directly. Please use the action buttons instead."
                )
        return self.cleaned_data['status']


class GameSessionForm(ModelForm):
    class Meta:
        model = GameSession
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        start_date = cleaned_data.get('start_date')

        if status == GameSessionStatus.PLANNED and start_date and start_date <= timezone.now():
            raise ValidationError("Planned sessions must have a future start date")

        return cleaned_data
