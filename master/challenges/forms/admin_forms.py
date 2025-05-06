from pathlib import Path
from zipfile import ZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms import ModelForm, Textarea

from challenges.models import ChallengeTemplate, ChallengeContainer


class ChallengeTemplateForm(ModelForm):
    class Meta:
        model = ChallengeTemplate
        fields = ['template_file', 'name', 'title', 'description', 'docker_compose', 'containers_config',
                  'networks_config']
        widgets = {
            'docker_compose': Textarea(attrs={'rows': 10}),
            'containers_config': Textarea(attrs={'rows': 10}),
            'networks_config': Textarea(attrs={'rows': 10}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.files.get('template_file'):
            self.fields['name'].required = True
            self.fields['title'].required = True
        else:
            self.fields['name'].required = False
            self.fields['title'].required = False

    def clean(self):
        cleaned_data = super().clean()
        template_file = cleaned_data.get('template_file')
        name = cleaned_data.get('name')
        title = cleaned_data.get('title')

        if not template_file and (not name or not title):
            if not name:
                self.add_error('name', 'Name is required when not uploading a template file')
            if not title:
                self.add_error('title', 'Title is required when not uploading a template file')

        if template_file:
            try:
                with ZipFile(template_file, 'r') as zip_ref:
                    first_dir = next((name for name in zip_ref.namelist() if name.endswith('/')), None)
                    if not first_dir:
                        raise ValidationError('Zip file must contain a directory.')

                    folder_name = first_dir.rstrip('/')
                    template_path = Path(settings.BASE_DIR) / f"game-challenges/{folder_name}"

                    if template_path.exists():
                        self.add_error('template_file',
                                       f'A template with folder name "{folder_name}" already exists. Please use a different folder name in your zip file.')
            except Exception as e:
                if not isinstance(e, ValidationError):
                    self.add_error('template_file', f'Error validating zip file: {str(e)}')

        return cleaned_data


class ChallengeContainerForm(ModelForm):
    class Meta:
        model = ChallengeContainer
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
