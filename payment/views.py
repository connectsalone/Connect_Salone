import uuid  # ✅ For unique transaction IDs
import qrcode
import json
import requests
import hashlib
import logging
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError, DatabaseError
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from reportlab.pdfgen import canvas
from events.models import Cart, Ticket
from payment.models import  Payment
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from cryptography.fernet import Fernet
from django.conf import settings
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from payment.models import Payment
from django.core.exceptions import ObjectDoesNotExist
from django.utils.crypto import get_random_string
from django.core.files.base import ContentFile

from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from events.models import Cart, Ticket, Event
from payment.models import Payment
from datetime import datetime

SECRET_KEY = settings.PAYMENT_SECRET_KEY
WEBSITE_URL = settings.WEBSITE_URL  # Replace with your actual secret key
cipher_suite = Fernet(SECRET_KEY)



logger = logging.getLogger(__name__)


def generate_unique_transaction_id():
    """Generate a unique transaction ID."""
    return str(uuid.uuid4().hex[:12]).upper()

def calculate_cart_total(cart):
    """Calculates the total amount of the cart."""
    try:
        return sum(item.event.get_ticket_price() * item.quantity for item in cart.cart_items.all())
    except Exception as e:
        logger.error(f"Error calculating cart total: {e}")
        return 0  # Default to 0 if any error occurs



def generate_payment_reference(user, transaction_id, unique_code):
    # Get the current date and time for extra uniqueness
    current_time = datetime.now().strftime('%Y%m%d%H%M%S')  # e.g. '20250227123045'
    # Return a unique reference using time, transaction_id, user email, and unique_code
    unique_reference = f"{current_time}-{transaction_id}-{user.email}-{unique_code}"
    return unique_reference


def process_orange_money_payment(phone_number, amount):
    """Simulates Orange Money payment processing for testing purposes."""
    # Simulate a successful payment response
    success = True
    transaction_id = generate_unique_transaction_id()  # Use the unique transaction ID generator
    
    if success:
        return True, transaction_id
    else:
        return False, None



from payment.models import ServiceFee  # Import the ServiceFee model
from decimal import Decimal  # ✅ Add this

@login_required
def orange_payment(request):
    """Handles Orange Money payment processing and creates tickets upon success."""
    cart = Cart.objects.prefetch_related('items__event').filter(user=request.user, is_paid=False).first()

    if not cart or cart.items.count() == 0:
        messages.error(request, "No active cart found.")
        return redirect('cart_view')  # Redirect to cart page if no active cart

    # ✅ Using the same event grouping logic as cart_page
    event_groups = {}

    for ticket in cart.items.all():
        event = ticket.event
        event_id = event.id

        if event_id not in event_groups:
            event_groups[event_id] = {
                'event': event,
                'tickets': [],
                'total_price': Decimal(0),
                'total_quantity': 0
            }

        ticket_price = ticket.ticket_price.get_price()  # ✅ Ensuring we get correct price
        subtotal = ticket_price * ticket.quantity

        event_groups[event_id]['tickets'].append(ticket)
        event_groups[event_id]['total_price'] += subtotal
        event_groups[event_id]['total_quantity'] += ticket.quantity

    # ✅ Total ticket price
    total_ticket_price = sum(group['total_price'] for group in event_groups.values())

    # ✅ Total service fee
    total_service_fee = sum(
        (service_fee.fee_amount * item.quantity)
        for item in cart.items.all()
        if (service_fee := ServiceFee.objects.filter(event=item.event).first())
    )

    # ✅ Final total = ticket price + service fee
    total_price = total_ticket_price + total_service_fee

    print(f"Total Ticket Price: {total_ticket_price}, Total Service Fee: {total_service_fee}, Final Total: {total_price}")

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()

        # Validate phone number format
        if not phone_number.isdigit() or not phone_number.startswith('07') or len(phone_number) != 9:
            messages.error(request, "Invalid phone number format.")
            return redirect('orange_payment')

        # Generate the payment reference
        unique_code = get_random_string(16)
        payment_reference = generate_payment_reference(request.user, '', unique_code)

        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=total_price,
            phone_number=phone_number,
            status='pending',
            cart=cart,
            payment_reference=payment_reference,
        )

        # Simulate payment success with a unique transaction ID
        success, transaction_id = process_orange_money_payment(phone_number, total_price)

        if success:
            try:
                with transaction.atomic():
                    payment.status = 'completed'
                    payment.transaction_id = transaction_id
                    payment.save()

                    # Call the function to create tickets (pass the existing payment)
                    payment, tickets = create_payment_and_tickets(request.user, cart, phone_number, total_price, transaction_id, payment)

                    if payment and tickets:
                        cart.is_paid = True
                        cart.save()
                        cart.items.all().delete()  # ✅ Clear cart items after payment

                        messages.success(request, "Payment successful and tickets have been created!")
                        return redirect('tickets')
                    else:
                        raise Exception("Error occurred while creating tickets")

            except Exception as e:
                logger.error(f"Payment processing error: {e}")
                messages.error(request, "Payment was successful, but an error occurred while creating tickets.")
        else:
            payment.status = 'failed'
            payment.save()
            messages.error(request, "Payment failed. Please try again.")

    return render(request, 'payment/orange_payment.html', {
        'total_price': total_price
    })


@transaction.atomic()
def create_payment_and_tickets(user, cart, phone_number, amount, transaction_id, existing_payment):
    try:
        payment = existing_payment  # Use the existing payment object

        # Generate unique payment reference
        payment_reference = generate_payment_reference(user, transaction_id, get_random_string(16))

        # Log the payment reference
        logger.info(f"Generated payment reference: {payment_reference}")

        # Ensure the reference does not already exist
        if Payment.objects.filter(payment_reference=payment_reference).exists():
            logger.error(f"Duplicate payment reference: {payment_reference}")
            return None, "Duplicate payment reference"

        # Debug Payment fields before saving
        logger.info(f"Payment data before save: {payment.__dict__}")

        payment.payment_reference = payment_reference
        payment.save()  # Save the updated payment reference

        # Process tickets
        tickets = []
        for item in cart.items.all():  # ✅ Use `items` instead of `cart_items`
            event = item.event
            ticket_count = item.quantity

            for _ in range(ticket_count):
                unique_code = get_random_string(16)
                qr = qrcode.make(unique_code)
                qr_io = BytesIO()
                qr.save(qr_io, format='PNG')
                qr_image = ContentFile(qr_io.getvalue(), f"qr_{unique_code}.png")

                # Create the ticket
                ticket = Ticket.objects.create(
                    user=user,
                    event=event,
                    ticket_name=event.event_name,
                    ticket_price=ticket.ticket_price.get_price() ,
                    payment_reference=payment_reference,
                    qr_code=qr_image,
                    quantity=1,
                    paid=True
                )
                tickets.append(ticket)

        return payment, tickets

    except ObjectDoesNotExist:
        logger.error(f"Cart not found for user: {user.username}")
        return None, "Cart not found"
    except Exception as e:
        logger.error(f"Error creating payment and tickets: {e}")
        return None, f"An error occurred: {str(e)}"


def generate_secure_qr_reference(ticket):
    """Generate a secure, unique reference for the QR code."""
    # Create a unique string by combining ticket ID, event ID, and a timestamp
    unique_string = f"{ticket.id}_{ticket.event.id}_{datetime.now().isoformat()}_{uuid.uuid4()}"
    
    # Optionally, you can hash this unique string for added security
    hash_object = hashlib.sha256(unique_string.encode())
    secure_reference = hash_object.hexdigest()
    
    return secure_reference







def generate_secure_ticket_qr(ticket):
    """Generate a secure QR code with encrypted ticket data and website URL."""
    
    # Encrypt ticket data (payment reference, ticket ID, event details)
    ticket_data = {
        "payment_reference": ticket.payment_reference,
        "ticket_id": ticket.id,
        "event_name": ticket.event.event_name,
        "event_date": ticket.event.event_date.strftime('%B %d, %Y'),
        "event_location": ticket.event.event_location,
        "website_url": WEBSITE_URL  # Include the website URL for added security
    }
    
    # Convert ticket data to string and encrypt it
    ticket_data_str = str(ticket_data)
    encrypted_data = cipher_suite.encrypt(ticket_data_str.encode())

    # Generate QR Code with encrypted data
    qr = qrcode.make(encrypted_data).resize((300, 300))  # Resized to fit the ticket
    return qr



def generate_ticket_image(ticket):
    """Generate a dynamic ticket image with secure QR code."""
    width, height = 1000, 400
    ticket_image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(ticket_image)

    # Load fonts with fallback
    try:
        title_font = ImageFont.truetype("arial.ttf", 50)
        text_font = ImageFont.truetype("arial.ttf", 30)
    except IOError:
        title_font = text_font = ImageFont.load_default()

    # Define sections
    left_section = (0, 0, width // 3, height)  # Event Image
    middle_section = (width // 3, 0, 2 * width // 3, height)  # Event Details
    right_section = (2 * width // 3, 0, width, height)  # QR Code

    image_padding = 10  # Padding around images

    # Load Event Image with padding
    if ticket.event.event_image:
        try:
            event_img = Image.open(ticket.event.event_image.path)
            event_img = event_img.resize((width // 3 - 2 * image_padding, height - 2 * image_padding))
            ticket_image.paste(event_img, (image_padding, image_padding))
        except Exception as e:
            print(f"Error loading event image: {e}")

    # Draw middle section (event details)
    text_y = 50

    def draw_centered_text(text, y_offset, font):
        text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
        x_pos = middle_section[0] + (middle_section[2] - middle_section[0] - text_width) // 2
        draw.text((x_pos, y_offset), text, font=font, fill="black")

    draw_centered_text(ticket.event.event_name.upper(), text_y, title_font)
    draw_centered_text(ticket.event.event_date.strftime('%B %d, %Y'), text_y + 70, text_font)
    draw_centered_text(ticket.event.event_date.strftime('%I:%M %p'), text_y + 120, text_font)
    draw_centered_text(ticket.event.event_location, text_y + 170, text_font)
    draw_centered_text(f"Price: NLe{ticket.event.get_ticket_price():.2f}", text_y + 220, text_font)

    # Generate secure QR code
    qr = generate_secure_ticket_qr(ticket)

    # Center the QR code in the right section
    qr_x = right_section[0] + (right_section[2] - right_section[0] - qr.size[0]) // 2
    qr_y = (height - qr.size[1]) // 2
    ticket_image.paste(qr, (qr_x, qr_y))

    # Draw border for aesthetics
    border_width = 5
    draw.rectangle([(0, 0), (width, height)], outline="green", width=border_width)
    draw.rectangle([(border_width, border_width), (width - border_width, height - border_width)], outline="white", width=border_width)
    draw.rectangle([(2 * border_width, 2 * border_width), (width - 2 * border_width, height - 2 * border_width)], outline="blue", width=border_width)

    # Save to BytesIO
    img_io = BytesIO()
    ticket_image.save(img_io, format="PNG")
    img_io.seek(0)
    return img_io


@login_required
def ticket_view(request, ticket_id):
    """View the ticket image before downloading."""
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)
    img_io = generate_ticket_image(ticket)
    
    return HttpResponse(img_io, content_type="image/png")

@login_required
def tickets_view(request):
    """Displays all tickets for the current user."""
    tickets = Ticket.objects.filter(user=request.user)
    return render(request, 'payment/ticket_list.html', {'tickets': tickets})



@login_required
def download_ticket(request, ticket_id):
    """Generates and downloads the ticket image."""
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    # Generate the ticket image (reusing the same logic from `generate_ticket_image`)
    img_io = generate_ticket_image(ticket)

    # Send the image as response with 'image/png' content type for download
    response = HttpResponse(img_io, content_type='image/png')
    response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.id}.png"'

    return response



@login_required
def scan_ticket(request):
    if request.method == "POST":
        qr_data = request.POST.get('qr_data')
        if not qr_data:
            return JsonResponse({"error": "No QR code data provided"}, status=400)

        try:
            decrypted_data = cipher_suite.decrypt(qr_data.encode()).decode()
            ticket_data = json.loads(decrypted_data)  # Safer alternative to eval
            ticket_id = ticket_data.get('ticket_id')
            website_url = ticket_data.get('website_url')
            
            if website_url != WEBSITE_URL:
                return JsonResponse({"error": "Invalid website URL"}, status=400)

            ticket = Ticket.objects.filter(id=ticket_id).first()
            if ticket:
                return JsonResponse({"message": "Ticket is valid", "ticket_id": ticket.id, "event_name": ticket.event.event_name}, status=200)
            else:
                return JsonResponse({"error": "Ticket not found"}, status=404)

        except Exception as e:
            logger.error(f"Error scanning ticket: {e}")
            return JsonResponse({"error": "Invalid QR code data"}, status=400)

    return render(request, 'payment/scan_ticket.html')




 