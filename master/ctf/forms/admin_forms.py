from django.forms import ModelForm, ValidationError

from ctf.models import GameContainer


class GameContainerForm(ModelForm):
    class Meta:
        model = GameContainer
        fields = '__all__'
        help_texts = {
            'status': 'Container status is automatically synced with Docker. Use the action buttons to change status.',
            'docker_id': 'Docker container ID is set automatically upon creation.',
            'template': 'Template cannot be changed after container creation.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make fields read-only if this is an existing container
        if self.instance.pk:
            self.fields['docker_id'].disabled = True
            # Don't disable status field as we're handling it with custom widget
            # self.fields['status'].disabled = True
            self.fields['template'].disabled = True

    def clean_status(self):
        """Prevent manual status editing through the form"""
        if self.instance.pk:  # If this is an existing container
            if self.cleaned_data['status'] != self.instance.status:
                raise ValidationError(
                    "Container status cannot be changed directly. Please use the action buttons instead."
                )
        return self.cleaned_data['status']