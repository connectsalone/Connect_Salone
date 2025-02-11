from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils.timezone import now
from django.core.exceptions import ValidationError
from datetime import timedelta
import secrets

from accounts.serializers import RegisterSerializer, LoginSerializer
from accounts.forms import AccountUserCreationForm, LoginForm
from accounts.models import EmailConfirmationToken
from accounts.models import EmailAddress

# Constants for rate limiting
MAX_FAILED_ATTEMPTS = 5
BLOCK_TIME = 15 * 60  # 15 minutes


# Utility Functions
def is_blocked(username):
    """Check if a user is blocked due to too many failed login attempts."""
    attempts = cache.get(f"login_attempts_{username}", 0)
    return attempts >= MAX_FAILED_ATTEMPTS


def increment_failed_attempts(username):
    """Increment failed login attempts for a user."""
    attempts = cache.get(f"login_attempts_{username}", 0)
    cache.set(f"login_attempts_{username}", attempts + 1, timeout=BLOCK_TIME)


def reset_failed_attempts(username):
    """Reset failed login attempts for a user."""
    cache.delete(f"login_attempts_{username}")


def generate_secure_token():
    """Generate a secure token."""
    return secrets.token_urlsafe(32)



def send_email_verification(user):
    """Send email verification token to the user."""
    token = EmailConfirmationToken.objects.create(user=user, token=generate_secure_token())
    send_confirmation_email(email=user.email, token_id=token.pk, user_id=user.pk)


def is_email_verified(user):
    """Check if a user's email is verified."""
    return EmailAddress.objects.filter(user=user, verified=True).exists()

def login_view(request):
    """Traditional login view."""
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            if is_blocked(username):
                messages.error(request, 'Too many failed attempts. Please try again later.')
                return redirect('login')

            user = authenticate(request, username=username, password=password)
            if user:
                if not is_email_verified(user):
                    messages.error(request, 'Your email is not verified. Please verify your email to log in.')
                    return redirect('login')

                login(request, user)

                # Preserve cart count in session if it exists
                cart_count = request.session.get('cart_count', 0)
                request.session['cart_count'] = cart_count

                reset_failed_attempts(username)

                return redirect('home')  # After successful login, redirect to home or desired page
            else:
                increment_failed_attempts(username)
                messages.error(request, 'Invalid credentials. Please try again.')
    else:
        form = LoginForm()

    return render(request, 'accounts/login.html', {'form': form})


class RegisterUser(APIView):
    """API view for user registration."""
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            if EmailAddress.objects.filter(user=user, email=user.email).exists():
                return Response({"message": "This email is already registered."}, status=status.HTTP_400_BAD_REQUEST)

            EmailAddress.objects.create(user=user, email=user.email, verified=False)
            send_email_verification(user)

            return Response({"message": "User registered successfully. Please check your email to verify your account."},
                            status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginUser(APIView):
    """API view for user login."""
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']

            if is_blocked(username):
                return Response({"message": "Too many failed attempts. Please try again later."},
                                status=status.HTTP_403_FORBIDDEN)

            user = authenticate(username=username, password=password)
            if user:
                if not is_email_verified(user):
                    return Response({"message": "Email is not verified. Please verify your email."},
                                    status=status.HTTP_400_BAD_REQUEST)

                reset_failed_attempts(username)
                tokens = RefreshToken.for_user(user)
                return Response({'access': str(tokens.access_token), 'refresh': str(tokens)}, status=status.HTTP_200_OK)
            else:
                increment_failed_attempts(username)
                return Response({"message": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def register_view(request):
    """Traditional registration view."""
    if request.method == 'POST':
        form = AccountUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password1'])
            user.save()

            EmailAddress.objects.create(user=user, email=user.email, verified=False)
            send_email_verification(user)

            messages.success(request, 'Registration successful. Please check your email for verification.')
            return redirect('login')
    else:
        form = AccountUserCreationForm()

    return render(request, 'accounts/register.html', {'form': form})


class UserInformationAPIView(APIView):
    """API view for retrieving user information."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({'email': user.email, 'is_email_confirmed': user.is_email_confirmed},
                        status=status.HTTP_200_OK)


class SendEmailConfirmationTokenAPIView(APIView):
    """API view for sending an email confirmation token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        send_email_verification(request.user)
        return Response({"message": "Email confirmation token sent. Please check your inbox."},
                        status=status.HTTP_201_CREATED)


def confirm_email_view(request):
    """View for confirming email."""
    token_id = request.GET.get('token_id')
    try:
        token = EmailConfirmationToken.objects.get(pk=token_id)
        if token.expires_at < now():
            return render(request, 'accounts/email_confirmed.html', {'is_email_confirmation': False, 'error': 'Token expired.'})

        token.user.is_email_confirmed = True
        token.user.save()
        return render(request, 'accounts/email_confirmed.html', {'is_email_confirmation': True})
    except EmailConfirmationToken.DoesNotExist:
        return render(request, 'accounts/email_confirmed.html', {'is_email_confirmation': False, 'error': 'Invalid token.'})


from rest_framework_simplejwt.tokens import RefreshToken

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")

    # Blacklist the refresh token if provided
    refresh_token = request.COOKIES.get('refresh_token')  # Assuming it's stored in cookies
    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # Blacklists the token if SimpleJWT’s blacklist app is enabled
        except Exception:
            pass  # Token is already invalid or missing
    
    return redirect('login')

class SendEmailConfirmationTokenAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if is_email_verified(request.user):
            return Response({"message": "Email is already verified."}, status=status.HTTP_400_BAD_REQUEST)

        send_email_verification(request.user)
        return Response({"message": "Email confirmation token sent."}, status=status.HTTP_201_CREATED)


from django.core.mail import send_mail

def send_confirmation_email(email, token_id, user_id):
    subject = 'Email Verification'
    message = f'Click the link to verify your email: /confirm-email/?token_id={token_id}&user_id={user_id}'
    send_mail(subject, message, 'no-reply@saloneconnect.com', [email])
