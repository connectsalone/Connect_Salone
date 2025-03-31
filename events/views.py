from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from events.models import Cart, Ticket, Event, EventView, CartItem
from payment.models import Payment
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import json
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem, Event

from decouple import config

PAYPAL_CLIENT_ID = config("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = config("PAYPAL_CLIENT_SECRET")



# ------------------- Cart Utility Functions -------------------
def get_cart_count_for_session(request):
    if request.user.is_authenticated:
        active_cart = Cart.objects.filter(
            user=request.user,
            is_paid=False
        ).first()
        return active_cart.cart_count if active_cart else 0
    return 0



def update_cart_count_on_login(sender, request, user, **kwargs):
    """Sync cart count to session when a user logs in."""
    request.session['cart_count'] = user.cart.cart_count if hasattr(user, 'cart') else 0



# ------------------- Cart Views -------------------

from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.db.models import Sum
import json

@require_POST
@login_required
def add_to_cart(request, event_id):
    try:
        print("\n=== RAW REQUEST DATA ===")
        print("Request body:", request.body.decode('utf-8'))  # Debugging

        data = json.loads(request.body)

        ticket_price_id = data.get('ticket_price_id')
        quantity = int(data.get('ticket_quantity', 1))  # Ensure correct key

        print(f"\n=== PARSED DATA ===")
        print(f"Ticket Price ID: {ticket_price_id}, Type: {type(ticket_price_id)}")
        print(f"Quantity: {quantity}, Type: {type(quantity)}")

        if not ticket_price_id or quantity < 1:
            return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

        event = get_object_or_404(Event, pk=event_id)
        ticket_type = get_object_or_404(TicketPrice, pk=int(ticket_price_id), event=event)

        cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart, ticket_price=ticket_type, defaults={'event': event, 'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        total_cart_quantity = CartItem.objects.filter(cart=cart).aggregate(
            total_quantity=Sum('quantity')
        )['total_quantity'] or 0

        
        return JsonResponse({
            'success': True,
            'cart_count': total_cart_quantity,
            'item_price': ticket_type.get_price(),  # ✅ Correctly fetching price
            'item_name': ticket_type.get_name_display()
        })

    except (ValueError, json.JSONDecodeError) as e:
        print(f"Error: {e}")
        return JsonResponse({'success': False, 'error': 'Invalid data format'}, status=400)

    except Exception as e:
        print(f"Unexpected Error: {e}")
        return JsonResponse({'success': False, 'error': str(e)}, status=400)



def cart_page(request):
    """Render the user's cart."""
    cart = Cart.objects.prefetch_related('items__event').filter(
        user=request.user, 
        is_paid=False
    ).first()

    if not cart or cart.items.count() == 0:
        request.session['cart_count'] = 0
        return render(request, 'events/cart.html', {
            'cart_items': [],
            'total': 0,
            'cart_count': 0
        })

    event_groups = {}

    for ticket in cart.items.all():  # ✅ Correctly using 'items' here
        event = ticket.event
        event_id = event.id

        if event_id not in event_groups:
            event_groups[event_id] = {
                'event': event,
                'tickets': [],
                'total_price': Decimal(0),
                'total_quantity': 0
            }

        ticket_price = ticket.ticket_price.get_price()  # Corrected 
        subtotal = ticket_price * ticket.quantity

        event_groups[event_id]['tickets'].append(ticket)
        event_groups[event_id]['total_price'] += subtotal
        event_groups[event_id]['total_quantity'] += ticket.quantity

    total_price = sum(group['total_price'] for group in event_groups.values())

    # FIXED: Changed 'cart_items' to 'items' to match the related_name
    cart_count = cart.items.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

    request.session['cart_count'] = cart_count

    return render(request, 'events/cart.html', {
        'event_groups': event_groups,
        'total_price': total_price,
        'cart_count': cart_count,
    })


def update_cart(request, event_id):
    if request.method != "POST":
        print("🔵 Received AJAX request:", json.dumps(request.POST.dict(), indent=2))
        return JsonResponse({"success": False, "error": "Invalid request method."}, status=400)

    user = request.user
    action = request.POST.get("action")
    ticket_id = request.POST.get("ticket_id")

    if not action or not ticket_id:
        return JsonResponse({"success": False, "error": "Action and ticket_id are required."}, status=400)

    # Get the event and cart
    event = get_object_or_404(Event, id=event_id)
    cart, _ = Cart.objects.get_or_create(user=user, is_paid=False)

    # Get the cart item
    cart_item = get_object_or_404(CartItem, cart=cart, event=event, id=ticket_id)
    
    # Get ticket price
    ticket_price = cart_item.ticket_price.get_price()
    was_deleted = False  # Track if the item gets deleted

    # Handle action (increase/decrease)
    if action == "increase":
        cart_item.quantity += 1
        cart_item.save()
    elif action == "decrease":
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
            was_deleted = True  # Mark the item as deleted

    # Get the updated list of cart items for this event
    event_cart_items = CartItem.objects.filter(cart=cart, event=event)

    # Calculate new subtotal for the entire event
    new_event_subtotal = sum(item.quantity * item.ticket_price.get_price() for item in event_cart_items)

    # Calculate the new total price for the entire cart
    new_total_price = calculate_cart_total(cart)

    # Get the updated cart count
    new_cart_count = get_cart_count(cart)

    # If the item was deleted, return quantity = 0 and instantly remove the row
    if was_deleted:
        return JsonResponse({
            "success": True,
            "new_quantity": 0,
            "new_subtotal": 0,  # No subtotal for a deleted item
            "new_event_quantity": sum(item.quantity for item in event_cart_items),  # Update event quantity
            "new_event_subtotal": new_event_subtotal,  # Event subtotal
            "new_total_price": new_total_price,
            "new_cart_count": new_cart_count,
            "remove_ticket": True  # Flag to remove the ticket row
        })

    # Otherwise, return updated values
    return JsonResponse({
        "success": True,
        "new_quantity": cart_item.quantity,
        "new_subtotal": cart_item.quantity * ticket_price,  # Corrected subtotal calculation
        "new_event_quantity": sum(item.quantity for item in event_cart_items),  # Update event quantity
        "new_event_subtotal": new_event_subtotal,  # Updated event subtotal
        "new_total_price": new_total_price,
        "new_cart_count": new_cart_count,
        "remove_ticket": False  # No need to remove ticket row
    })



def update_cart_count_in_session(request, user):
    """Update the cart count in session."""
    cart = Cart.objects.filter(user=user).first()
    request.session['cart_count'] = get_cart_count(cart) if cart else 0

def calculate_cart_total(cart):
    """Helper function to calculate the total price of the cart."""
    total = Decimal(0)

    for item in cart.items.all():  # ✅ Use `cart.items.all()`
        ticket_price = item.ticket_price.get_price()  # ✅ Get price from `TicketPrice` model
        total += item.quantity * ticket_price  # ✅ Multiply by quantity

    return total



def get_cart_count(request):
    """Calculate the total number of tickets in the cart for both authenticated and non-authenticated users."""
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count
    else:
        # Handle cart count for non-authenticated users via session-based cart
        session_cart = request.session.get('cart', {})
        cart_count = sum(item['quantity'] for item in session_cart.values())
    
    return cart_count


def calculate_cart_total(cart):
    """Calculates the total price of all items in the cart."""
    total = sum(item.quantity * item.ticket_price.get_price()  for item in cart.items.all())
    cart.total_price = total
    cart.save()
    return total


def update_cart_count_in_session(request, user):
    """Updates the cart count in session."""
    cart = Cart.objects.get(user=user, is_paid=False)
    request.session['cart_count'] = cart.cart_count


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

from django.shortcuts import render
from .models import Event

def calendar_view(request):
    # You can add filtering based on event status or other criteria if needed
    events = Event.objects.all()  # Fetch all events, you can filter by status if needed
    return render(request, 'events/calendar.html', {'events': events})


from django.http import JsonResponse
from .models import Event

def get_events(request):
    # Fetch all events
    events = Event.objects.all()

    # Prepare event data in a format suitable for FullCalendar
    event_data = []
    for event in events:
        event_data.append({
            'id': event.id,  # Unique ID for each event
            'title': event.event_name,  # Event title
            'start': event.event_date.isoformat(),  # Start date and time in ISO format
            'end': event.event_date.isoformat(),  # You can add an actual end date if needed
            'location': event.event_location,  # Event location
            'image': event.event_image.url if event.event_image else None,  # Optional image URL
            'event_type': event.event_type,  # Type of event (e.g., concert, party, etc.)
            'status': event.event_status,  # Status of the event (e.g., upcoming, sold out)
        })

    return JsonResponse(event_data, safe=False)

# ------------------- Other Pages -------------------


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from events.models import  TicketPrice  # Assuming TicketType is the ticket model
from events.models import Cart, Event


from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Event, Cart, TicketPrice

@login_required
def home(request):
    events = Event.objects.all()  # Fetch all events

    # Categorize events using Python
    upcoming_events = [event for event in events if event.is_upcoming()]
    trending_events = [event for event in events if event.is_trending()]
    normal_events = [event for event in events if event.is_normal()]

    # Get cart count for authenticated users
    cart_count = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()
        if cart:
            cart_count = cart.cart_count

    # Fetch all ticket prices for each event
    event_ticket_data = {}
    for event in events:
        ticket_prices = TicketPrice.objects.filter(event=event)
        event_ticket_data[event.id] = [
            {"ticket_type": ticket.name, "price": ticket.get_price()}
            for ticket in ticket_prices
        ]

    # Prepare context data
    context = {
        'upcoming_events': upcoming_events,
        'trending_events': trending_events,
        'normal_events': normal_events,
        'cart_count': cart_count,
        'event_ticket_data': event_ticket_data,  # Pass ticket price data
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

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Event, TicketPrice, EventView, Sponsorer
from events.views import get_cart_count  # Assuming you have a utility function for cart count

@login_required
def single_event(request, event_id):
    """Display event details, update view count, show sponsors, and handle ticket selection."""
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

    # Fetch tickets and prices for the event
    tickets = event.event_tickets.all()
    ticket_prices = TicketPrice.objects.filter(event=event)  # Fetch ticket prices for the event

    # Cart count calculation (optimized for session-based and user-based carts)
    cart_count = get_cart_count(request)

    # Fetch sponsors associated with the event
    sponsors = event.sponsorers.all()

    return render(request, 'events/single-event.html', {
        'event': event,
        'tickets': tickets,
        'ticket_prices': ticket_prices,  # Pass ticket prices to the template
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

from decimal import Decimal
from collections import defaultdict
from django.db.models import Sum
from django.shortcuts import render
from .models import Cart, CartItem
from payment.models import ServiceFee

def checkout_page(request):
    events_in_cart = defaultdict(lambda: {"quantity": 0, "subtotal": Decimal(0), "service_fee": Decimal(0)})
    total_price = Decimal(0)
    cart_count = 0
    service_fee_total = Decimal(0)  # Initialize the service fee total

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()

        if cart:
            cart_count = cart.items.aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0
            cart_items = CartItem.objects.filter(cart=cart)

            for item in cart_items:
                event = item.event
                quantity = item.quantity
                ticket_price = item.ticket_price.get_price()
                subtotal = ticket_price * quantity

                # ✅ Safe way to get service fee (avoiding RelatedObjectDoesNotExist)
                service_fee = ServiceFee.objects.filter(event=event, ticket_price=item.ticket_price).first()
                service_fee_amount = service_fee.fee_amount if service_fee else Decimal(0.00)

                # ✅ Aggregate by event
                events_in_cart[event]["event"] = event
                events_in_cart[event]["quantity"] += quantity
                events_in_cart[event]["subtotal"] += subtotal
                events_in_cart[event]["service_fee"] += service_fee_amount * quantity

                # ✅ Update total price
                total_price += subtotal + (service_fee_amount * quantity)

                # Add service fee to total service fee
                service_fee_total += service_fee_amount * quantity

    context = {
        'cart_count': cart_count,
        'events_in_cart': events_in_cart.values(),
        'total_price': total_price,
        'service_fee_total': service_fee_total,  # Add the service fee total to context
    }

    return render(request, 'events/checkout_page.html', context)




def my_tickets(request):
    """Display user's purchased tickets."""
    tickets = Ticket.objects.filter(event__event_tickets__event__cart__user=request.user, paid=True)
    return render(request, "events/my_tickets.html", {"tickets": tickets})
