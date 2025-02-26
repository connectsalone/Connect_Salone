from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'admin', 'event', 'status', 'payment_reference', 'payment_date')
    list_filter = ('status', 'payment_date', 'event')
    search_fields = ('user__username', 'admin__username', 'event__event_name', 'transaction_id', 'payment_reference', 'phone_number')
    readonly_fields = ('payment_reference', 'transaction_id', 'payment_date')

    fieldsets = (
        ("Payment Information", {
            "fields": ("user", "admin", "event", "cart", "status", "payment_reference", "transaction_id", "payment_date")
        }),
        ("User Contact", {
            "fields": ("phone_number",)
        }),
    )

    def has_add_permission(self, request):
        """Prevent manual addition of payments from the admin panel"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of payment records from the admin panel"""
        return False
