from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError

from ctf.models.user import User


def validate_ssh_key(value: str) -> None:
    """Validate SSH public key format"""
    if value and not value.startswith(("ssh-rsa", "ssh-ed25519", "ssh-dss", "ecdsa-sha2-nistp")):
        raise ValidationError("Invalid SSH public key format")


class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class UserLoginForm(AuthenticationForm):
    class Meta:
        model = User
        fields = ("username", "password")


class UserSettingsForm(forms.ModelForm):
    ssh_public_key = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        validators=[validate_ssh_key]
    )

    class Meta:
        model = User
        fields = ('username', 'ssh_public_key')

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This username is already taken.')
        return username
