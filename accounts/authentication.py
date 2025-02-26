from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomAuthBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(email=username)

            # Allow admin login even if email is not verified
            if user.check_password(password):
                if user.is_staff or user.is_superuser:
                    return user
                if user.is_active:  # Regular users must be active (verified email)
                    return user
        except User.DoesNotExist:
            return None
