from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from events.models import Event, EventView, Sponsorer, Ticket
from dashboard.forms import EventForm, SponsorerForm

from django.shortcuts import render
from events.models import Event

def event_list(request):
    """View to display a list of all events."""
    events = Event.objects.all().order_by('-event_date')  # Order by event date (newest first)
    return render(request, 'dashboard/event_list.html', {'events': events})


# Event-related views
def event_detail(request, pk):
    """View details of a specific event."""
    event = get_object_or_404(Event, pk=pk)
    return render(request, 'dashboard/event_detail.html', {'event': event})

def event_view_count(request):
    """Display the total views for each event."""
    event_views = EventView.objects.values('event__event_name').annotate(total_views=Count('event')).order_by('-total_views')
    return render(request, 'dashboard/event_view_count.html', {'event_views': event_views})

def event_analytics(request):
    """Display analytics for events, including views and daily views."""
    events = Event.objects.annotate(total_views=Count('views')).order_by('-total_views')
    current_date = timezone.now().date()
    events_by_date = EventView.objects.filter(viewed_at__date=current_date).values('event').annotate(daily_views=Count('id'))
    return render(request, 'dashboard/analytics.html', {
        'events': events,
        'events_by_date': events_by_date,
    })

def event_search(request):
    """Search for events based on filters."""
    query = request.GET.get('q', '')
    event_type = request.GET.get('event_type', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    events = Event.objects.all()

    if query:
        events = events.filter(event_name__icontains=query)
    if event_type:
        events = events.filter(event_type=event_type)
    if start_date:
        events = events.filter(event_date__gte=start_date)
    if end_date:
        events = events.filter(event_date__lte=end_date)

    message = "No events match your search criteria." if not events else None
    return render(request, 'dashboard/event_list.html', {'events': events, 'message': message})

def add_event(request):
    """Add a new event."""
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event added successfully!')
            return redirect('dashboard')
    else:
        form = EventForm()
    return render(request, 'dashboard/add_event.html', {'form': form})

def edit_event(request, event_id):
    """Edit an existing event."""
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event_list')
    else:
        form = EventForm(instance=event)
    return render(request, 'dashboard/edit_event.html', {'form': form})

def delete_event(request, event_id):
    """Delete an event."""
    event = get_object_or_404(Event, id=event_id)
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully!')
    return redirect('events-lists')

# Sponsor-related views
def sponsor_list(request):
    """List all sponsors."""
    sponsors = Sponsorer.objects.all()
    return render(request, 'dashboard/sponsor_list.html', {'sponsors': sponsors})

def sponsor_add(request):
    """Add a new sponsor."""
    if request.method == 'POST':
        form = SponsorerForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sponsor added successfully!')
            return redirect('sponsor-list')
    else:
        form = SponsorerForm()
    return render(request, 'dashboard/add_sponsor.html', {'form': form})

def sponsor_edit(request, pk):
    """Edit an existing sponsor."""
    sponsor = get_object_or_404(Sponsorer, pk=pk)
    if request.method == 'POST':
        form = SponsorerForm(request.POST, request.FILES, instance=sponsor)
        if form.is_valid():
            form.save()
            messages.success(request, 'Sponsor updated successfully!')
            return redirect('sponsor-list')
    else:
        form = SponsorerForm(instance=sponsor)
    return render(request, 'dashboard/sponsor_form.html', {'form': form})

def sponsor_delete(request, pk):
    """Delete a sponsor."""
    sponsor = get_object_or_404(Sponsorer, pk=pk)
    if request.method == 'POST':
        sponsor.delete()
        messages.success(request, 'Sponsor deleted successfully!')
        return redirect('sponsor-list')
    return render(request, 'dashboard/sponsor_confirm_delete.html', {'sponsor': sponsor})

# Ticket-related views
def ticket_list(request):
    """List all tickets."""
    tickets = Ticket.objects.all()
    return render(request, 'dashboard/ticket_list.html', {'tickets': tickets})

# Dashboard view
from django.shortcuts import render
from django.db.models import Count, Sum
from events.models import Event, EventView, Sponsorer, Ticket
from payment.models import Payment  # Import the Payment model

def dashboard(request):
    # Event data
    events = Event.objects.all()
    total_tickets_sold = Ticket.objects.aggregate(Sum('quantity'))['quantity__sum'] or 0
    total_event_views = EventView.objects.aggregate(Count('id'))['id__count'] or 0

    # Sponsor data
    sponsors = Sponsorer.objects.all()

    # Event views data
    event_views = EventView.objects.values('event__event_name').annotate(total_views=Count('event')).order_by('-total_views')

    # Ticket statistics
    tickets = Ticket.objects.all()

    # Payment data
    payments = Payment.objects.all()
    total_payments = payments.count()
    total_revenue = payments.aggregate(Sum('amount'))['amount__sum'] or 0
    recent_payments = payments.order_by('-payment_date')[:5]  # Last 5 payments

    return render(request, 'dashboard/dashboard.html', {
        'events': events,
        'total_tickets_sold': total_tickets_sold,
        'total_event_views': total_event_views,
        'sponsors': sponsors,
        'event_views': event_views,
        'tickets': tickets,
        'total_payments': total_payments,
        'total_revenue': total_revenue,
        'recent_payments': recent_payments,
    })