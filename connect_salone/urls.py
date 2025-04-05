from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('accounts.urls')),
    path('events/', include('events.urls')),
    path('accounts/', include('allauth.urls')),
    path('payment/', include('payment.urls')),
    path('dashboard/', include('dashboard.urls')),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


