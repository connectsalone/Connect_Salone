from django.contrib import admin
from .models import Payment

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "transaction_id", "status", "payment_date")  # ✅ Key fields visible in the list view
    list_filter = ("status", "payment_date")  # ✅ Quick filters for status & date
    search_fields = ("user__username", "transaction_id", "phone_number")  # ✅ Search by user, transaction ID, or phone
    readonly_fields = ("transaction_id", "payment_date")  # ✅ Prevent accidental changes
    ordering = ("-payment_date",)  # ✅ Show latest payments first

    fieldsets = (
        ("Payment Info", {
            "fields": ("user", "amount", "phone_number", "transaction_id", "status", "payment_date")
        }),
        ("Related Cart", {
            "fields": ("cart",)
        }),
    )

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of completed payments."""
        if obj and obj.status == "completed":
            return False  # ✅ Prevent deletion of completed payments
        return super().has_delete_permission(request, obj)

