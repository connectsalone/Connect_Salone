from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, EmailConfirmationToken, EmailAddress


class EmailConfirmationTokenAdmin(admin.ModelAdmin):
    """Admin panel customization for EmailConfirmationToken."""
    list_display = ('user', 'token', 'created_at', 'expires_at', 'is_confirmed')
    search_fields = ('user__username', 'user__email', 'token')
    list_filter = ('created_at', 'expires_at')

    def is_confirmed(self, obj):
        """Return whether the email is confirmed."""
        return obj.user.is_email_confirmed
    is_confirmed.boolean = True
    is_confirmed.short_description = _('Email Confirmed')


class EmailAddressAdmin(admin.ModelAdmin):
    """Admin panel customization for EmailAddress."""
    list_display = ('user', 'email', 'verified')  # Removed 'primary' if it does not exist
    search_fields = ('user__username', 'email')
    list_filter = ('verified',)

    def get_readonly_fields(self, request, obj=None):
        if obj:  # If editing an existing email address, make user field readonly
            return ['user', 'email']
        return []


class CustomUserAdmin(UserAdmin):
    """Custom admin panel for User model."""
    model = User
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'email')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 'is_active', 'is_staff', 'is_superuser')
        }),
    )
    ordering = ('username',)


# Register models with the Django admin
admin.site.register(User, CustomUserAdmin)
admin.site.register(EmailConfirmationToken, EmailConfirmationTokenAdmin)
admin.site.register(EmailAddress, EmailAddressAdmin)


