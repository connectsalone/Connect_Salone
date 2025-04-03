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


from django.contrib import admin
from django import forms
from .models import TicketPrice, Event

# Admin form to display the ticket price
class TicketPriceAdminForm(forms.ModelForm):
    class Meta:
        model = TicketPrice
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.event:
            # Set the ticket price on form initialization
            self.fields['ticket_price_display'] = forms.CharField(
                initial=str(self.instance.get_price()), disabled=True, required=False
            )

    def clean_event(self):
        event = self.cleaned_data.get('event')
        if event:
            # Update ticket price display when the event is changed
            self.fields['ticket_price_display'].initial = str(event.ticket_types.first().get_price() if event.ticket_types.exists() else "No ticket price available")
        return event


@admin.register(TicketPrice)
class TicketPriceAdmin(admin.ModelAdmin):
    form = TicketPriceAdminForm
    list_display = ('event', 'name', 'early_bird_price', 'normal_price', 'early_bird_start', 'early_bird_end', 'get_ticket_price_display')
    list_filter = ('name', 'early_bird_start', 'early_bird_end')
    search_fields = ('event__event_name',)

    readonly_fields = ('get_ticket_price_display',)

    def get_ticket_price_display(self, obj):
        """ Custom method to return the ticket price for display in the list. """
        return obj.get_price() if obj else "No price available"
    get_ticket_price_display.short_description = 'Ticket Price'

    def save_model(self, request, obj, form, change):
        # Ensure ticket price is correctly saved based on event
        obj.save()  # Save the model to update the ticket price
        super().save_model(request, obj, form, change)



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



