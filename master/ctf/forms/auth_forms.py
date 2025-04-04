from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm

from ctf.models.user import User


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
