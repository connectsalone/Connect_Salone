from django.contrib import admin
from .models import Event, Ticket, Cart, CartItem, Payment, EventView

from django.contrib import admin
from .models import Event, Sponsorer

class SponsorerInline(admin.TabularInline):
    model = Event.sponsorers.through  # This allows editing of the sponsorships directly in the Event admin
    extra = 1  # Number of empty forms to display by default

class EventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'event_date', 'event_location', 'event_status', 'view_count')
    list_filter = ('event_status', 'event_type', 'event_date')
    search_fields = ('event_name', 'event_location', 'event_description')
    ordering = ('-event_date',)
    filter_horizontal = ('sponsorers',)  # Makes sponsor selection easier
    inlines = [SponsorerInline]  # Adds the inline editor for sponsorers
    readonly_fields = ('event_created_at', 'event_updated_at')

    def has_add_permission(self, request):
        """Override to control permissions for adding an event (optional)."""
        return True  # Customize based on your needs

    def has_delete_permission(self, request, obj=None):
        """Override to control permissions for deleting an event (optional)."""
        return True  # Customize based on your needs

class SponsorerAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo')
    search_fields = ('name',)
    list_filter = ('name',)
    ordering = ('name',)

# Register the models in the admin interface
admin.site.register(Event, EventAdmin)
admin.site.register(Sponsorer, SponsorerAdmin)


class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_name', 'event', 'ticket_price', 'quantity', 'paid', 'payment_reference', 'qr_code')
    search_fields = ('ticket_name', 'event__event_name')
    list_filter = ('paid',)
    readonly_fields = ('ticket_price', 'qr_code', 'secret_token')
    
    def ticket_price(self, obj):
        return obj.ticket_price
    ticket_price.short_description = 'Price'

class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_paid', 'cart_count', 'total_price', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('is_paid',)
    readonly_fields = ('total_price', 'cart_count')

class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'event', 'quantity')
    search_fields = ('cart__user__username', 'event__event_name')
    list_filter = ('cart__is_paid',)
    readonly_fields = ('cart', 'event')

class PaymentAdmin(admin.ModelAdmin):
    list_display = ('cart', 'amount', 'payment_status', 'payment_date')
    search_fields = ('cart__user__username', 'payment_status')
    list_filter = ('payment_status',)
    readonly_fields = ('payment_date',)

class EventViewAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'session_key', 'viewed_at')
    search_fields = ('event__event_name', 'user__username')
    list_filter = ('viewed_at',)
    readonly_fields = ('viewed_at',)

# Register the models with custom admin classes
admin.site.register(Ticket, TicketAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(CartItem, CartItemAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(EventView, EventViewAdmin)
