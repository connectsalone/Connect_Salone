from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from events.models import Cart, Ticket, Event, EventView, CartItem
from payment.models import Payment
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Sum
from django.contrib.auth.signals import user_logged_in
import json
from django.db.models import Sum

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
from django.shortcuts import get_object_or_404
from .models import Event, TicketPrice, Cart, CartItem
import json
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required


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
        print("Request body:", request.body.decode('utf-8'))  # Decode for clarity

        data = json.loads(request.body)

        ticket_price_id = data.get('ticket_price_id')
        quantity = int(data.get('quantity', 1))

        print(f"\n=== PARSED DATA ===")
        print(f"Ticket Price ID: {ticket_price_id}, Type: {type(ticket_price_id)}")
        print(f"Quantity: {quantity}, Type: {type(quantity)}")

        if not ticket_price_id or quantity < 1:
            return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

        event = get_object_or_404(Event, pk=event_id)
        ticket_type = get_object_or_404(TicketPrice, pk=int(ticket_price_id), event=event)  # ✅ Get TicketPrice instance

        cart, created = Cart.objects.get_or_create(user=request.user, is_paid=False)

        # Check if CartItem with the same cart and ticket_price already exists
        cart_item = CartItem.objects.filter(cart=cart, ticket_price=ticket_type).first()

        if cart_item:
            # If CartItem already exists, update the quantity
            cart_item.quantity += quantity
            cart_item.save()
        else:
            # If CartItem doesn't exist, create a new one
            CartItem.objects.create(cart=cart, event=event, ticket_price=ticket_type, quantity=quantity)

        # ✅ Calculate total cart quantity correctly
        total_cart_quantity = CartItem.objects.filter(cart=cart).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        return JsonResponse({
            'success': True,
            'cart_count': total_cart_quantity,
            'item_price': ticket_type.ticket_price,  # Use the price from TicketPrice instance
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
    """Render the user's cart."""
    # Only fetch active (unpaid) carts
    cart = Cart.objects.prefetch_related('cart_items__event').filter(
        user=request.user, 
        is_paid=False
    ).first()  # 👈 Added is_paid=False filter
    

    if not cart or cart.cart_items.count() == 0:
        # Ensure that cart count is set to 0 and session is updated
        request.session['cart_count'] = 0
        return render(request, 'events/cart.html', {'cart_items': [], 'total': 0, 'cart_count': 0})

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

    # Update session with correct cart count
    request.session['cart_count'] = cart_count

    return render(request, 'events/cart.html', {
        'event_groups': event_groups,
        'total_price': total_price,
        'cart_count': cart_count,
    })


 
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
    cart, _ = Cart.objects.get_or_create(
        user=user, 
        is_paid=False  # 👈 Critical fix here
    )

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

            # If the last item was removed, recalculate total price and set cart count to 0
            if cart.cart_items.count() == 0:
                cart.cart_count = 0
                cart.total_price = 0
                cart.save()

            # Update cart count in session
            update_cart_count_in_session(request, user)

            # Recalculate the total price
            new_total_price = calculate_cart_total(cart)
            return JsonResponse({
                "success": True,
                "new_quantity": 0,
                "new_subtotal": 0,
                "new_total_price": new_total_price,
                "new_cart_count": 0
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


        
from django.shortcuts import render
from .models import Cart, CartItem, Ticket
from payment.models import ServiceFee

def checkout_page(request):
    events_in_cart = []
    total_price = 0
    cart_count = 0

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user, is_paid=False).first()

        if cart:
            cart_count = cart.cart_count
            cart_items = CartItem.objects.filter(cart=cart)

            for item in cart_items:
                event = item.event
                quantity = item.quantity
                ticket_price = event.get_ticket_price()  # Get ticket price
                subtotal = ticket_price * quantity
                
                # Fetch service fee for the event
                service_fee = event.service_fee.fee_amount if event.service_fee else 0.00
                
                # Add the service fee to the total price
                total_price += subtotal + (service_fee * quantity)

                # Add event info to events_in_cart
                events_in_cart.append({
                    'event': event,
                    'quantity': quantity,
                    'subtotal': subtotal,
                    'service_fee': service_fee * quantity,
                })

    context = {
        'cart_count': cart_count,
        'events_in_cart': events_in_cart,
        'total_price': total_price,  # Include total price with service fee
    }

    return render(request, 'events/checkout_page.html', context)


def my_tickets(request):
    """Display user's purchased tickets."""
    tickets = Ticket.objects.filter(event__event_tickets__event__cart__user=request.user, paid=True)
    return render(request, "events/my_tickets.html", {"tickets": tickets})
