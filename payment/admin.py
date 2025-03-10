from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import ServiceFee, Payment
from django.db.models import Sum

from django.contrib import admin
from .models import ServiceFee, Event, TicketPrice

class ServiceFeeAdmin(admin.ModelAdmin):
    list_display = ('event', 'ticket_price', 'fee_amount')
    list_filter = ('event', 'ticket_price')
    search_fields = ('event__event_name', 'ticket_price__name')
    ordering = ('event',)

    def save_model(self, request, obj, form, change):
        """Custom save method to handle any specific logic when saving."""
        super().save_model(request, obj, form, change)
        
admin.site.register(ServiceFee, ServiceFeeAdmin)


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'event', 'amount', 'status', 'payment_date', 'payment_reference')
    list_filter = ('status', 'event', 'payment_date')
    search_fields = ('transaction_id', 'user__username', 'payment_reference')

    def calculated_amount(self, obj):
        return obj.calculated_amount
    calculated_amount.short_description = _('Calculated Amount')
    calculated_amount.admin_order_field = 'amount'

    actions = ['mark_as_completed', 'mark_as_failed']

    def mark_as_completed(self, request, queryset):
        """Mark selected payments as completed."""
        rows_updated = queryset.update(status='completed')
        self.message_user(request, f"{rows_updated} payment(s) marked as completed.")
    mark_as_completed.short_description = _('Mark selected payments as completed')

    def mark_as_failed(self, request, queryset):
        """Mark selected payments as failed."""
        rows_updated = queryset.update(status='failed')
        self.message_user(request, f"{rows_updated} payment(s) marked as failed.")
    mark_as_failed.short_description = _('Mark selected payments as failed')

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        # Annotate the total amount for each payment (including service fee)
        return queryset.annotate(total_amount=Sum('amount'))

admin.site.register(Payment, PaymentAdmin)
