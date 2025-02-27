from django.contrib import admin
from .models import Payment

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'event', 'status', 'amount', 'payment_date', 'transaction_id')
    list_filter = ('status', 'payment_date', 'event')
    search_fields = ('user__username', 'transaction_id', 'payment_reference')
    readonly_fields = ('amount', 'payment_date')

    def amount(self, obj):
        return obj.amount
    amount.short_description = 'Total Amount'

admin.site.register(Payment, PaymentAdmin)
