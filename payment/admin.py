from django.contrib import admin
from .models import ServiceFee, Payment, PaymentTicket
from django.utils.translation import gettext_lazy as _

class ServiceFeeAdmin(admin.ModelAdmin):
    list_display = ('event', 'ticket_price', 'fee_amount')
    search_fields = ('event__event_name', 'ticket_price__name')
    list_filter = ('event', 'ticket_price')

    fieldsets = (
        (None, {
            'fields': ('event', 'ticket_price', 'fee_amount')
        }),
        (_('Advanced options'), {
            'classes': ('collapse',),
            'fields': ()  # Leave this as an empty tuple since no additional fields are needed
        }),
    )


class PaymentTicketInline(admin.TabularInline):
    model = PaymentTicket
    extra = 0
    fields = ('ticket', 'event', 'quantity', 'price', 'amount')
    readonly_fields = ('ticket', 'event', 'quantity', 'price', 'amount')

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('transaction_id', 'user', 'status', 'amount', 'payment_date', 'cart')
    list_filter = ('status', 'payment_date')
    search_fields = ('transaction_id', 'user__email', 'payment_reference')
    readonly_fields = ('transaction_id', 'payment_reference', 'ticket_total', 'service_fee_total', 'amount')

    inlines = [PaymentTicketInline]

    fieldsets = (
        (None, {
            'fields': ('user', 'phone_number', 'amount', 'status', 'payment_reference', 'payment_date', 'cart')
        }),
        (_('Advanced options'), {
            'classes': ('collapse',),
            'fields': ('transaction_id', 'ticket_total', 'service_fee_total'),
        }),
    )

    def save_model(self, request, obj, form, change):
        # You can add custom logic here if you need to process or validate the payment
        if not obj.transaction_id:
            obj.transaction_id = str(uuid.uuid4())  # Ensure unique transaction ID
        super().save_model(request, obj, form, change)

class PaymentTicketAdmin(admin.ModelAdmin):
    list_display = ('payment', 'ticket', 'event', 'quantity', 'price', 'amount')
    search_fields = ('payment__transaction_id', 'ticket__name', 'event__event_name')
    list_filter = ('event', 'ticket')

    fieldsets = (
        (None, {
            'fields': ('payment', 'ticket', 'event', 'quantity', 'price', 'amount')
        }),
    )


admin.site.register(ServiceFee, ServiceFeeAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(PaymentTicket, PaymentTicketAdmin)
