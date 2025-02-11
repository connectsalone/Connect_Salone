from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from accounts.models import User  # Use your custom User model


class AccountUserCreationForm(UserCreationForm):
    """
    Custom UserCreationForm for registering new users.
    """

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_password2(self):
        """
        Ensures the passwords match during registration.
        """
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        return password2


class LoginForm(AuthenticationForm):
    """
    Custom AuthenticationForm for logging in users.
    """

    class Meta:
        model = User
        fields = ['username', 'password']


