from django.urls import path
from rest_framework_simplejwt import views as jwt_views
from accounts.views import (
    register_view, login_view, RegisterUser, LoginUser, 
    send_confirmation_email, UserInformationAPIView, confirm_email_view, logout_view
)

urlpatterns = [
    # Traditional views for HTML form-based authentication
    path('register/', register_view, name='register'),
    path('login/', login_view, name='login'),  # Added login URL for clarity
    path('logout/', logout_view, name='logout'),  # Logout URL

    # API views for registration and login via DRF
    path('api/register/', RegisterUser.as_view(), name='api_register'),
    path('api/login/', LoginUser.as_view(), name='api_login'),

    # JWT token views for API authentication
    path('auth/token/', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),

    # User information and email confirmation views
    path('api/me/', UserInformationAPIView.as_view(), name='user_information'),
    path('api/send-confirmation-email/', send_confirmation_email, name='send_confirmation_email'),
    path('confirm-email/', confirm_email_view, name='confirm_email'),
]
