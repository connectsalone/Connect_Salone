from uuid import uuid4
from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import timedelta
from django.utils.timezone import now
from django.conf import settings  # Import settings for AUTH_USER_MODEL

from django.contrib.auth.models import BaseUserManager


# Function to return the expiration time for email confirmation tokens
def get_expiration_time():
    return now() + timedelta(hours=24)

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and return a regular user with the given email and password.
        """
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and return a superuser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if not extra_fields.get('is_staff'):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get('is_superuser'):
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_email_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    # Set the custom manager
    objects = UserManager()

    USERNAME_FIELD = 'email'  # Use email as the unique identifier for authentication
    REQUIRED_FIELDS = ['username']  # Fields required when creating a superuser

    def __str__(self):
        return self.email


class EmailConfirmationToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)  # Corrected the reference
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=get_expiration_time)  # Use the function instead of lambda

    def is_expired(self):
        return now() > self.expires_at

from django.conf import settings
from django.db import models

class EmailAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_addresses')
    email = models.EmailField()
    verified = models.BooleanField(default=False)

    def __str__(self):
        return self.email

