from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from paypal.standard.ipn import urls as paypal_urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts', include('accounts.urls')),
    path('', include('events.urls')),
    path('accounts/', include('allauth.urls')),
    path('paypal/', include(paypal_urls)),  # Ensure this line is included
    path('payment/', include('payment.urls')),
    path('dashboard/', include('dashboard.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
