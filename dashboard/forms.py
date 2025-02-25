from django import forms
from events.models import Event, Sponsorer

from django import forms
from events.models import Event

from django import forms
from events.models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            'event_name', 
            'event_description', 
            'event_type', 
            'event_date', 
            'event_location', 
            'event_status', 
            'event_image', 
            'early_bird_price', 
            'normal_price', 
            'early_bird_end', 
            'video_url', 
            'video_file', 
            'event_logo', 
            'sponsorers'
        ]
        widgets = {
            # Text Inputs
            'event_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter event name',
            }),
            'event_location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter event location',
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter video URL (optional)',
            }),

            # Textarea
            'event_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Enter event description',
            }),

            # Select Inputs
            'event_type': forms.Select(attrs={
                'class': 'form-control',
            }),
            'event_status': forms.Select(attrs={
                'class': 'form-control',
            }),

            # Date and Time Inputs
            'event_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),
            'early_bird_end': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
            }),

            # File Inputs
            'event_image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'video_file': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),
            'event_logo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
            }),

            # Number Inputs
            'early_bird_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter early bird price',
            }),
            'normal_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter normal price',
            }),

            # Many-to-Many Field (Checkbox Select Multiple)
            'sponsorers': forms.CheckboxSelectMultiple(attrs={
                'class': 'form-check-input',
            }),
        }

class SponsorerForm(forms.ModelForm):
    class Meta:
        model = Sponsorer
        fields = ['name', 'logo']