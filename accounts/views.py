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


from django.shortcuts import render, redirect
from django.contrib import messages
from accounts.forms import AccountUserCreationForm
from accounts.tokens import email_verification_token
import uuid
from accounts.utils import send_confirmation_email  # Import your email utility



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

from django.http import JsonResponse

def check_user_type(request):
    return JsonResponse({'is_admin': request.user.is_authenticated and request.user.is_staff})


def login_view(request):
    """Traditional login view."""
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('username')  # Ensure this is email
            password = form.cleaned_data.get('password')

            if is_blocked(email):
                messages.error(request, 'Too many failed attempts. Please try again later.')
                return redirect('login')

            user = authenticate(request, email=email, password=password)  # Ensure email is used
            if user:
                # Allow admins to log in without email verification
                if not user.is_email_confirmed and not user.is_staff:
                    messages.error(request, 'Your email is not verified. Please verify your email to log in.')
                    return redirect('login')

                login(request, user)

                # Preserve cart count in session if it exists
                cart_count = request.session.get('cart_count', 0)
                request.session['cart_count'] = cart_count

                reset_failed_attempts(email)

                # Redirect admins to the dashboard, others to home
                if user.is_staff:
                    return redirect('dashboard')  # Change to your actual dashboard URL name
                else:
                    return redirect('home')  # Regular users go to home page

            else:
                increment_failed_attempts(email)
                messages.error(request, 'Invalid credentials. Please try again.')
    else:
        form = LoginForm()

    # Pass the user type (is_admin) to the template
    return render(request, 'accounts/login.html', {
        'form': form,
        'is_admin': request.user.is_staff  # Pass the is_admin status to the template
    })



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

            # Generate a unique token (using UUID)
            token_id = uuid.uuid4()

            # Send confirmation email
            try:
                send_email_verification(user, request)  # Send the email with the request object
                messages.success(request, 'Registration successful. Check your email for verification.')
            except Exception as e:
                # Log the error and inform the user
                messages.error(request, f'Failed to send confirmation email. Error: {str(e)}')

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
    

from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from accounts.tokens import verify_token

User = get_user_model()

def confirm_email_view(request):
    token_id = request.GET.get("token_id")
    user_id = request.GET.get("user_id")

    if not token_id or not user_id:
        return HttpResponse("Invalid confirmation link.", status=400)

    print(f"Received user_id: {user_id}")  # Debugging

    try:
        user = User.objects.get(id=user_id)
        print(f"User Found: {user.email}")  # Debugging
        if verify_token(user, token_id):
            user.is_email_confirmed = True  # Ensure this is updated
            user.is_active = True  # Ensure user is active
            user.save()
            return HttpResponse("Email successfully confirmed!", status=200)
        else:
            return HttpResponse("Invalid or expired token.", status=400)
    except User.DoesNotExist:
        return HttpResponse(f"User with ID {user_id} not found.", status=404)






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


from django.core.mail import EmailMessage
from django.conf import settings
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from accounts.tokens import email_verification_token

def send_email_verification(user, request):
    # Create the token
    token = email_verification_token.make_token(user)

    # Build the confirmation URL
    confirmation_url = f"http://{get_current_site(request).domain}{reverse('confirm_email')}?token_id={token}&user_id={user.id}"

    subject = "Verify Your Email"
    message = f"Click the link to verify your email: {confirmation_url}"

    # Create the email message
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.EMAIL_HOST_USER,  # Use the sender's email from settings
        to=[user.email]
    )

    # Ensure proper content type and encoding
    email.content_subtype = "html"  # If you are sending HTML content
    email.encoding = "utf-8"  # Ensure UTF-8 encoding

    # Send the email
    email.send()



