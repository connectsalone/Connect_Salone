from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import ServiceFee, Payment, PaymentTicket
from django.utils.html import format_html

class ServiceFeeAdmin(admin.ModelAdmin):
    list_display = ('event', 'ticket_price', 'fee_amount', 'get_event_name')

    def get_event_name(self, obj):
        return obj.event.event_name
    get_event_name.short_description = 'Event Name'

    search_fields = ('event__event_name', 'ticket_price__name')

admin.site.register(ServiceFee, ServiceFeeAdmin)


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'payment_date', 'ticket_total', 'service_fee_total', 'calculated_amount')
    search_fields = ('user__username', 'status')
    list_filter = ('status', 'payment_date')
    readonly_fields = ('transaction_id', 'payment_reference', 'payment_date', 'ticket_total', 'service_fee_total', 'calculated_amount')

    def get_calculated_amount(self, obj):
        return obj.calculated_amount
    get_calculated_amount.short_description = 'Calculated Amount'

admin.site.register(Payment, PaymentAdmin)


class PaymentTicketAdmin(admin.ModelAdmin):
    list_display = ('payment', 'ticket', 'event', 'quantity', 'price', 'amount')
    list_filter = ('event', 'payment__status')
    search_fields = ('ticket__name', 'event__event_name', 'payment__transaction_id')

admin.site.register(PaymentTicket, PaymentTicketAdmin)
