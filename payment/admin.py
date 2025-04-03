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


from django.contrib import admin
from .models import Payment, Ticket
from django.utils.translation import gettext_lazy as _

class EventFilter(admin.SimpleListFilter):
    title = _('Event')  # The label for the filter
    parameter_name = 'event'

    def lookups(self, request, model_admin):
        # Get a list of unique event names from the tickets related to payments
        events = Ticket.objects.values_list('event__event_name', flat=True).distinct()
        return [(event, event) for event in events]

    def queryset(self, request, queryset):
        if self.value():
            # Filter payments by event name through related tickets
            return queryset.filter(tickets__event__event_name=self.value())
        return queryset

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'amount', 'status', 'transaction_id', 'get_event')
    list_filter = ('status', EventFilter)  # Using the custom EventFilter for filtering by event

    def get_event(self, obj):
        """Returns the event name from the first ticket."""
        first_ticket = Ticket.objects.filter(payment=obj).first()
        if first_ticket:
            return first_ticket.event.event_name
        return "No Event"

    get_event.short_description = _('Event')

admin.site.register(Payment, PaymentAdmin)


