from django.forms import ModelForm, ValidationError
from django.utils import timezone

from ctf.models import GameSession
from ctf.models.enums import GameSessionStatus


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
