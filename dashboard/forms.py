from django import forms
from events.models import Event, Sponsorer, TicketPrice
from django.forms import inlineformset_factory

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['event_name', 'event_type', 'event_date', 'event_location', 'event_status']

class SponsorerForm(forms.ModelForm):
    class Meta:
        model = Sponsorer
        fields = ['name', 'logo']

# Create an inline formset for TicketPrice
TicketPriceFormSet = inlineformset_factory(
    Event, TicketPrice,
    fields=('name', 'early_bird_price', 'normal_price', 'early_bird_start', 'early_bird_end'),
    extra=1, can_delete=True
)
