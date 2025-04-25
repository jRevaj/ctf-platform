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

    def __init__(self, *args, **kwargs):
        self.user = kwargs.get('instance')
        super().__init__(*args, **kwargs)
        
        # If SSH key is locked, preserve the original value
        if self.is_ssh_key_locked():
            self.initial['ssh_public_key'] = self.user.ssh_public_key
            self.fields['ssh_public_key'].widget.attrs['disabled'] = True
            # Add a hidden field to ensure the original value is submitted
            self.fields['original_ssh_key'] = forms.CharField(
                widget=forms.HiddenInput(),
                required=False,
                initial=self.user.ssh_public_key
            )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This username is already taken.')
        return username
        
    def clean(self):
        cleaned_data = super().clean()
        
        # If SSH key is locked, use the original value
        if self.is_ssh_key_locked() and 'original_ssh_key' in self.data:
            cleaned_data['ssh_public_key'] = self.data.get('original_ssh_key')
            
        return cleaned_data
        
    def clean_ssh_public_key(self):
        ssh_public_key = self.cleaned_data.get('ssh_public_key', '')
        
        # If SSH key is locked, skip validation
        if self.is_ssh_key_locked():
            return self.user.ssh_public_key
            
        # Otherwise perform validation
        if ssh_public_key != self.user.ssh_public_key:
            if self.user.team and self.user.team.is_in_game:
                raise forms.ValidationError('Cannot change SSH key while your team is in game.')
        
        return ssh_public_key
        
    def is_ssh_key_locked(self):
        """Check if SSH key field should be disabled"""
        return self.user and self.user.team and self.user.team.is_in_game
