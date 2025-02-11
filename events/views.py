from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from events.models import Cart, Ticket, Event, Payment, EventView
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum, F
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
import json


# ------------------- Cart Utility Functions -------------------

def get_cart_count_for_session(request):
    """Get cart count for session and authenticated users."""
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_count = cart.cart_items.count()  # Use cart_items instead of tickets
    return cart_count


def update_cart_count_on_login(sender, request, user, **kwargs):
    """Update cart count when a user logs in."""
    if user.is_authenticated:
        cart = Cart.objects.filter(user=user).first()
        # Use cart.cart_items.count() to get the number of cart items
        request.session['cart_count'] = cart.cart_items.count() if cart else 0
    else:
        request.session['cart_count'] = 0  # For guests


user_logged_in.connect(update_cart_count_on_login)


# ------------------- Cart Views -------------------

import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum  # ✅ Import Sum function
from .models import Cart, CartItem, Event

def add_to_cart(request, event_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            quantity = int(data.get('quantity', 1))  # Convert to integer, default 1

            event = get_object_or_404(Event, id=event_id)
            cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)

            # Get or create the cart item
            cart_item, created = CartItem.objects.get_or_create(cart=cart, event=event)

            if not created:
                cart_item.quantity += quantity  # Update existing quantity
            else:
                cart_item.quantity = quantity  # Set quantity for a new cart item

            cart_item.save()

            # ✅ Calculate total quantity across all cart items correctly
            total_cart_quantity = CartItem.objects.filter(cart=cart).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

            return JsonResponse({'success': True, 'cart_count': total_cart_quantity})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


from decimal import Decimal
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Cart

@login_required
def cart_page(request):
    """Render the user's cart."""
    cart = Cart.objects.prefetch_related('cart_items__event').filter(user=request.user).first()

    if not cart:
        return render(request, 'events/cart.html', {'cart_items': [], 'total': 0})

    event_groups = {}

    for ticket in cart.cart_items.all():
        event = ticket.event
        event_id = event.id

        if event_id not in event_groups:
            event_groups[event_id] = {
                'event': event,
                'tickets': [],
                'total_price': Decimal(0),
                'total_quantity': 0
            }

        # ✅ Ensure correct ticket price (early bird or normal)
        ticket_price = event.get_ticket_price()
        subtotal = ticket_price * ticket.quantity

        event_groups[event_id]['tickets'].append(ticket)
        event_groups[event_id]['total_price'] += subtotal
        event_groups[event_id]['total_quantity'] += ticket.quantity

    total_price = sum(group['total_price'] for group in event_groups.values())

    cart_count = cart.cart_items.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

    return render(request, 'events/cart.html', {
        'event_groups': event_groups,
        'total_price': total_price,
        'cart_count': cart_count,
    })



from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from .models import Cart, CartItem, Event
from django.utils import timezone
 
@login_required
def update_cart(request, event_id):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Invalid request method."}, status=400)

    user = request.user
    action = request.POST.get("action")

    if not action:
        return JsonResponse({"success": False, "error": "Action parameter is required."}, status=400)

    # Get the event
    event = get_object_or_404(Event, id=event_id)
    event_price = event.get_ticket_price()  # Ensure the correct price is used

    # Get or create the cart
    cart, _ = Cart.objects.get_or_create(user=user)

    # Get or create cart item
    cart_item, created = CartItem.objects.get_or_create(cart=cart, event=event)

    # Handle increase or decrease action
    if action == "increase":
        cart_item.quantity += 1
        cart_item.save()
    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            update_cart_count_in_session(request, user)

            # If the last item was removed, recalculate total price
            new_total_price = calculate_cart_total(cart)
            return JsonResponse({
                "success": True,
                "new_quantity": 0,
                "new_subtotal": 0,
                "new_total_price": new_total_price,
                "new_cart_count": get_cart_count(cart)
            })

    # Calculate new subtotal for this event
    new_subtotal = cart_item.quantity * event_price

    # Calculate total price and cart count
    new_total_price = calculate_cart_total(cart)
    new_cart_count = get_cart_count(cart)

    # Update session cart count
    update_cart_count_in_session(request, user)

    # Return the updated data
    return JsonResponse({
        "success": True,
        "new_quantity": cart_item.quantity,
        "new_subtotal": new_subtotal,
        "new_total_price": new_total_price,
        "new_cart_count": new_cart_count
    })


def update_cart_count_in_session(request, user):
    """Update the cart count in session."""
    cart = Cart.objects.filter(user=user).first()
    request.session['cart_count'] = get_cart_count(cart) if cart else 0


def calculate_cart_total(cart):
    """Helper function to calculate the total price of the cart."""
    return sum(item.quantity * item.event.get_ticket_price() for item in cart.cart_items.all())


def get_cart_count(cart):
    """Helper function to count the total number of tickets in the cart."""
    return sum(item.quantity for item in cart.cart_items.all())



# ------------------- Event Views -------------------

@login_required
def event_detail(request, event_id):
    """Display event details and update view count."""
    event = get_object_or_404(Event, id=event_id)

    # Ensure a valid session key exists for anonymous users
    if not request.session.session_key:
        request.session.create()

    # Increment the view count
    event.increment_count()

    # Check if the view is unique (based on user or session) before logging it
    if not EventView.objects.filter(
        event=event,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key if not request.user.is_authenticated else None
    ).exists():
        EventView.objects.create(
            event=event,
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else None
        )

    # Fetch tickets
    tickets = event.event_tickets.all()

    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count

    return render(request, 'events/event_detail.html', {
        'event': event,
        'tickets': tickets,
        'cart_count': cart_count,
    })



# ------------------- Calendar Page -------------------

def calendar_view(request):
    # Get cart count for authenticated users
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count

    # Retrieve event data and convert dates to ISO format
    events = list(Event.objects.values("id", "event_date", "event_location", "event_name", "normal_price"))
  

    # Convert event_date to ISO string for FullCalendar
    for event in events:
        event["start"] = event["event_date"].isoformat()
        event["end"] = (event["event_date"] + timezone.timedelta(hours=2)).isoformat()  # Assuming 2-hour duration
        del event["event_date"]  # Remove the original datetime object to avoid confusion

    return render(request, "events/calendar.html", {"cart_count": cart_count, "events": events})


# views.py
from django.http import JsonResponse
from .models import Event
from django.utils import timezone

def get_events(request):
    events = Event.objects.filter(event_date__gte=timezone.now())  # Only future events
    event_list = []
    for event in events:
        event_list.append({
            "title": event.event_name,
            "start": event.event_date.isoformat(),
            "end": (event.event_date + timezone.timedelta(hours=2)).isoformat(),  # Assuming 2-hour events
            "location": event.event_location,
            "description": event.event_description,
        })
    return JsonResponse(event_list, safe=False)




# ------------------- Other Pages -------------------


@login_required
def home(request):
    events = Event.objects.all()

    # Categorize events
    upcoming_events = [event for event in events if event.is_upcoming()]
    trending_events = [event for event in events if event.is_trending()]
    normal_events = [event for event in events if event.is_normal()]

    # Get cart count for authenticated users
    
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count

    # Prepare context data
    context = {
        'upcoming_events': upcoming_events,
        'trending_events': trending_events,
        'normal_events': normal_events,
        'cart_count': cart_count,
    }

    return render(request, 'events/home.html', context)


def about(request):

    # Get cart count for authenticated users
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count

    context = {'cart_count': cart_count}

    return render(request, 'events/about.html', context)


def contact(request):

    # Get cart count for authenticated users
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count

    context = {'cart_count': cart_count}
    return render(request, 'events/contact.html', context)

@login_required
def single_event(request, event_id):
    """Display event details, update view count, and show sponsors."""
    event = get_object_or_404(Event, id=event_id)

    # Ensure a valid session key exists for anonymous users
    if not request.session.session_key:
        request.session.create()

    # Increment the view count
    event.increment_count()

    # Check if the view is unique (based on user or session) before logging it
    if not EventView.objects.filter(
        event=event,
        user=request.user if request.user.is_authenticated else None,
        session_key=request.session.session_key if not request.user.is_authenticated else None
    ).exists():
        EventView.objects.create(
            event=event,
            user=request.user if request.user.is_authenticated else None,
            session_key=request.session.session_key if not request.user.is_authenticated else None
        )

    # Fetch tickets for the event
    tickets = event.event_tickets.all()

    # Cart count calculation (optimized for session-based and user-based carts)
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count
    else:
        # Handle cart count for non-authenticated users via session-based cart (if needed)
        session_cart = request.session.get('cart', {})
        cart_count = sum(item['quantity'] for item in session_cart.values())

    # Fetch sponsors associated with the event
    sponsors = event.sponsorers.all()

    return render(request, 'events/single-post.html', {
        'event': event,
        'tickets': tickets,
        'cart_count': cart_count,
        'sponsors': sponsors,  # Pass the sponsors to the template
    })



def starter_page(request):

    # Get cart count for authenticated users
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count

    context = {'cart_count': cart_count}
    return render(request, 'events/starter-page.html', context)


def event_list(request):

    events = Event.objects.all()

    # Get cart count for authenticated users
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count 

    context = {'cart_count': cart_count, 'events': events}
    return render(request, 'events/event_list.html', context)



def scan_ticket(request, secret_token):
    try:
        ticket = Ticket.objects.get(secret_token=secret_token)

        if timezone.now() > ticket.ticket_sale_end_date:
            return JsonResponse({"status": "error", "message": "Ticket has expired."})

        if not ticket.is_valid:
            return JsonResponse({"status": "error", "message": "Ticket has already been used."})

        # Mark ticket as scanned and invalidate
        ticket.is_valid = False
        ticket.save()

        return JsonResponse({"status": "success", "message": "Ticket is valid."})
    except Ticket.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Ticket not found."})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})
    
from django.contrib.auth.signals import user_logged_in

 

