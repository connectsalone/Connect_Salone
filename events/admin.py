from django.contrib import admin
from events.models import Event, Ticket, Cart, CartItem, EventView, TicketPrice, Sponsorer


# Inline admin for managing sponsorships within Event admin
class SponsorerInline(admin.TabularInline):
    model = Event.sponsorers.through
    extra = 1  # Number of empty forms to display by default


# Inline admin for Ticket Prices inside Event admin
class TicketPriceInline(admin.TabularInline):
    model = TicketPrice
    extra = 1
    fields = ('name', 'early_bird_price', 'normal_price', 'early_bird_start', 'early_bird_end')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('event_name', 'event_type', 'event_date', 'event_location', 'event_status', 'view_count')
    list_filter = ('event_type', 'event_status', 'event_date')
    search_fields = ('event_name', 'event_location')
    inlines = [TicketPriceInline, SponsorerInline]  # Add both inlines
    readonly_fields = ('event_created_at', 'event_updated_at', 'view_count')


@admin.register(TicketPrice)
class TicketPriceAdmin(admin.ModelAdmin):
    list_display = ('event', 'name', 'early_bird_price', 'normal_price', 'early_bird_start', 'early_bird_end')
    list_filter = ('name', 'early_bird_start', 'early_bird_end')
    search_fields = ('event__event_name',)


@admin.register(Sponsorer)
class SponsorerAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo')
    search_fields = ('name',)
    list_filter = ('name',)
    ordering = ('name',)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('ticket_name', 'event', 'ticket_price', 'quantity', 'paid', 'payment_reference', 'qr_code')
    search_fields = ('ticket_name', 'event__event_name')
    list_filter = ('paid',)
    readonly_fields = ('ticket_price', 'qr_code', 'secret_token')


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'is_paid', 'cart_count', 'total_price', 'created_at')
    search_fields = ('user__username',)
    list_filter = ('is_paid',)
    readonly_fields = ('total_price', 'cart_count')


from django.contrib import admin
from .models import CartItem

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "event", "ticket_price", "quantity", "created_at")
    list_filter = ("event", "ticket_price", "created_at")
    search_fields = ("cart__id", "event__name", "ticket_price__name")
    ordering = ("-created_at",)


class EventViewAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'session_key', 'viewed_at')
    search_fields = ('event__event_name', 'user__username')
    list_filter = ('viewed_at',)
    readonly_fields = ('viewed_at',)  # Ensure this is a tuple with a comma



