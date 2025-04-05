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
from payment.models import Payment, ServiceFee
from datetime import datetime
from decimal import Decimal
from django.conf import settings

WEBSITE_URL = settings.WEBSITE_URL  # or hardcode for now: 'https://salone-connect.com'




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
    unique_reference = f"{current_time}-{transaction_id}-{user.email}-{unique_code}_{get_random_string(8)}"
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

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils.crypto import get_random_string
from .models import Payment, PaymentTicket
from events.models import Cart, TicketPrice
from payment.models import ServiceFee
from django.contrib.auth.decorators import login_required
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

@login_required
def orange_payment(request):
    """Handles Orange Money payment processing and creates tickets upon success."""
    # Fetch the cart for the logged-in user that is not yet paid
    cart = Cart.objects.prefetch_related('items__event').filter(user=request.user, is_paid=False).first()

    # Check if the cart exists and contains items
    if not cart or cart.items.count() == 0:
        messages.error(request, "No active cart found.")
        return redirect('cart_view')  # Redirect to cart page if no active cart

    # Group tickets by event
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

        ticket_price = ticket.ticket_price.get_price()
        subtotal = ticket_price * ticket.quantity

        event_groups[event_id]['tickets'].append(ticket)
        event_groups[event_id]['total_price'] += subtotal
        event_groups[event_id]['total_quantity'] += ticket.quantity

    # Calculate total ticket price
    total_ticket_price = sum(group['total_price'] for group in event_groups.values())

    # Calculate total service fee only for paid tickets
    total_service_fee = Decimal(0)
    for item in cart.items.all():
        # Fetch the service fee only for the ticket_price of the paid ticket
        service_fee = ServiceFee.objects.filter(event=item.event, ticket_price=item.ticket_price).first()
        if service_fee:
            total_service_fee += service_fee.fee_amount * item.quantity

    total_price = total_ticket_price + total_service_fee

    if request.method == 'POST':
        # Step 1: Get the phone number from the POST request
        phone_number = request.POST.get('phone_number', '').strip()

        # Step 2: Validate the phone number
        if not phone_number.isdigit() or not phone_number.startswith('07') or len(phone_number) != 9:
            messages.error(request, "Invalid phone number format.")
            return redirect('orange_payment')  # Stay on the page if the phone number is invalid

        # Step 3: Generate payment reference (unique identifier)
        unique_code = get_random_string(16)
        payment_reference = generate_payment_reference(request.user, '', unique_code)

        # Ensure cart reference is valid before creating payment
        if cart is None or cart.id == 0:
            messages.error(request, "Invalid cart reference.")
            return redirect('cart_view')  # Redirect to cart page if the cart is invalid

        # Step 4: Create payment record
        payment = Payment.objects.create(
            user=request.user,
            amount=total_price,
            phone_number=phone_number,
            status='pending',
            payment_reference=payment_reference,
            cart=cart  # Ensure cart is associated correctly
        )

        # Step 5: Simulate payment processing (add the payment processing logic)
        success, transaction_id = process_orange_money_payment(phone_number, total_price)

        if success:
            try:
                with transaction.atomic():
                    # Step 6: Mark payment as completed
                    payment.status = 'completed'
                    payment.transaction_id = transaction_id
                    payment.payment_date = timezone.now()  # Ensure payment date is set
                    payment.save()

                    # Step 7: Create tickets for payment
                    logger.info("Payment processed successfully, starting ticket creation...")

                    for ticket in cart.items.all():
                        if ticket.ticket_price:
                            ticket_price = ticket.ticket_price.get_price() if ticket.ticket_price else Decimal('0.00')
                            try:
                                # Create a payment ticket record for each ticket in the cart
                                payment_ticket = PaymentTicket.objects.create(
                                    payment=payment,
                                    ticket=ticket.ticket_price,
                                    event=ticket.event,
                                    quantity=ticket.quantity,
                                    price=ticket_price,
                                    amount=ticket_price * ticket.quantity
                                )
                                logger.info(f"Payment ticket created for ticket ID: {ticket.id}.")

                            except Exception as e:
                                logger.error(f"Error creating PaymentTicket for ticket ID {ticket.id}: {e}")
                        else:
                            logger.error(f"Invalid ticket price for ticket {ticket.id}. Ticket price is None.")

                    # Step 8: Mark cart as paid and clear items
                    cart.is_paid = True
                    cart.save()
                    cart.items.all().update(is_paid=True)  # Update the items as paid instead of deleting

                    messages.success(request, "Enter correct phone number and initiate payment!")
                    return redirect('tickets')  # Redirect to tickets page

            except Exception as e:
                logger.error(f"Payment processing error: {e}")
                messages.error(request, "Payment was successful, but an error occurred while creating tickets.")
        else:
            # Payment failed
            payment.status = 'failed'
            payment.save()
            messages.error(request, "Payment failed. Please try again.")

    return render(request, 'payment/orange_payment.html', {
        'total_price': total_price
    })



from django.db import transaction
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
import json
import uuid
import logging
import hashlib
from datetime import datetime
from django.db import transaction
from django.utils.crypto import get_random_string
from django.core.files.base import ContentFile
from cryptography.fernet import Fernet
from events.models import Ticket  # adjust to your actual app
from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)
cipher_suite = Fernet(settings.FERNET_KEY)

@transaction.atomic
def create_payment_and_tickets(user, cart, phone_number, total_price, transaction_id, existing_payment):
    try:
        logger.info("Starting ticket creation process...")
        print("✅ Payment saved, now creating tickets...")


        # Debugging: Log cart item count
        logger.info(f"Cart contains {cart.items.count()} items.")

        # Step 1: Check if phone number is provided
        if not phone_number:
            raise ValidationError("Phone number is required to process payment and create tickets.")

        logger.info(f"Processing payment for user: {user.username} with phone number: {phone_number}")

        # Step 2: Use existing payment if available
        payment = existing_payment
        if not payment:
            logger.error("No existing payment found.")
            return None, "Payment does not exist."

        payment_reference = generate_payment_reference(user, transaction_id, get_random_string(16))
        payment.payment_reference = payment_reference
        payment.save()

        logger.info(f"Payment reference generated: {payment_reference}")

        tickets = []

        # Step 3: Create tickets
        for item in cart.items.all():
            for item in cart.items.all():
                print(f"Cart item: {item.event.event_name}, quantity: {item.quantity}")
                logger.info(f"Creating tickets for event: {item.event.event_name}, quantity: {item.quantity}")

            event = item.event
            ticket_price = item.ticket_price  # ✅ This is a ForeignKey object
            print(f"Ticket price object: {item.ticket_price}, price: {item.ticket_price.price}")


            # Debugging: Log ticket creation for each item in cart
            logger.info(f"Creating {item.quantity} tickets for event '{event.event_name}' at price {ticket_price.price}")

            for _ in range(item.quantity):
                # Step 4: Create the ticket first (needed to generate secure QR)
                ticket = Ticket.objects.create(
                    user=user,
                    event=event,
                    ticket_name=event.event_name,
                    ticket_price=ticket_price,
                    payment_reference=payment_reference,
                    quantity=1,
                    paid=True
                )

                logger.info(f"Created ticket ID: {ticket.id} for event {event.event_name}")

                # Step 5: Generate secure QR code image
                qr_img = generate_secure_ticket_qr(ticket)
                qr_io = BytesIO()
                qr_img.save(qr_io, format='PNG')

                # Save QR code to ticket
                ticket.qr_code.save(f"qr_{ticket.id}.png", ContentFile(qr_io.getvalue()), save=True)

                logger.info(f"QR code generated and saved for ticket ID: {ticket.id}")
                tickets.append(ticket)

        # Step 6: Return payment and tickets created
        logger.info(f"Ticket creation process completed. {len(tickets)} tickets created.")
        return payment, tickets

    except Exception as e:
        # Step 7: Error handling
        logger.error(f"Error during payment and ticket creation: {e}")
        if 'event' in locals():
            logger.error(f"Error creating ticket for event: {event.event_name}")
        return None, f"An error occurred: {str(e)}"

       

import hashlib
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def generate_qr_code(self):
    """
    Generate a secure, unique reference for the QR code.
    """
    try:
        # Create a unique string by combining ticket ID, event ID, and a timestamp
        unique_string = f"{self.id}_{self.event.id}_{datetime.now().isoformat()}_{uuid.uuid4()}"
        
        # Optionally hash this unique string for added security
        secure_reference = hashlib.sha256(unique_string.encode()).hexdigest()
        
        return secure_reference

    except Exception as e:
        logger.error(f"QR Code Generation Failed: {e}")
        raise

import json
import qrcode
import logging
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

# Make sure `cipher_suite` is defined elsewhere in your code
# Example: cipher_suite = Fernet(your_secret_key)

def generate_secure_ticket_qr(ticket):
    """
    Generate a secure QR code with encrypted ticket data and website URL.
    """
    try:
        ticket_data = {
            "payment_reference": ticket.payment_reference,
            "ticket_id": ticket.id,
            "event_name": ticket.event.event_name,
            "event_date": ticket.event.event_date.strftime('%B %d, %Y'),
            "event_location": ticket.event.event_location,
            "website_url": "https://salone-connect.com/verify"
        }

        ticket_json = json.dumps(ticket_data)
        encrypted_data = cipher_suite.encrypt(ticket_json.encode())
        qr = qrcode.make(encrypted_data).resize((300, 300))

        return qr

    except Exception as e:
        logger.error(f"Failed to generate secure QR code for ticket ID {getattr(ticket, 'id', 'unknown')}: {e}")
        raise



import logging
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

logger = logging.getLogger(__name__)

def generate_ticket_image(ticket):
    """
    Generate a dynamic ticket image with secure QR code and a centered text watermark.
    """
    try:
        width, height = 1000, 400
        ticket_image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(ticket_image)

        # Load fonts with fallback
        try:
            title_font = ImageFont.truetype("arial.ttf", 50)
            text_font = ImageFont.truetype("arial.ttf", 30)
            watermark_font = ImageFont.truetype("arial.ttf", 25)
        except IOError:
            title_font = text_font = watermark_font = ImageFont.load_default()

        # Define sections
        left_section = (0, 0, width // 3, height)
        middle_section = (width // 3, 0, 2 * width // 3, height)
        right_section = (2 * width // 3, 0, width, height)

        image_padding = 10

        # Load Event Image
        if ticket.event.event_image:
            try:
                event_img = Image.open(ticket.event.event_image.path)
                event_img = event_img.resize((width // 3 - 2 * image_padding, height - 2 * image_padding))
                ticket_image.paste(event_img, (image_padding, image_padding))
            except Exception as e:
                logger.error(f"Error loading event image for ticket {ticket.id}: {e}")

        # Draw middle section
        text_y = 50

        def draw_centered_text(text, y_offset, font):
            try:
                text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
                x_pos = middle_section[0] + (middle_section[2] - middle_section[0] - text_width) // 2
                draw.text((x_pos, y_offset), text, font=font, fill="black")
            except Exception as e:
                logger.error(f"Failed to draw text '{text}' for ticket {ticket.id}: {e}")

        draw_centered_text(ticket.event.event_name.upper(), text_y, title_font)
        draw_centered_text(ticket.event.event_date.strftime('%B %d, %Y'), text_y + 70, text_font)
        draw_centered_text(ticket.event.event_date.strftime('%I:%M %p'), text_y + 120, text_font)
        draw_centered_text(ticket.event.event_location, text_y + 170, text_font)
        draw_centered_text(f"Price: NLe{ticket.event.get_ticket_price():.2f}", text_y + 220, text_font)

        # Generate QR code
        try:
            qr = generate_secure_ticket_qr(ticket)
            qr_x = right_section[0] + (right_section[2] - right_section[0] - qr.size[0]) // 2
            qr_y = (height - qr.size[1]) // 2
            ticket_image.paste(qr, (qr_x, qr_y))
        except Exception as e:
            logger.error(f"QR code generation failed for ticket {ticket.id}: {e}")

        # Draw border
        border_width = 5
        draw.rectangle([(0, 0), (width, height)], outline="green", width=border_width)
        draw.rectangle([(border_width, border_width), (width - border_width, height - border_width)], outline="white", width=border_width)
        draw.rectangle([(2 * border_width, 2 * border_width), (width - 2 * border_width, height - 2 * border_width)], outline="blue", width=border_width)

        # Add centered text watermark
        try:
            watermark_text = "salone-connect.com"
            watermark_width, watermark_height = draw.textbbox((0, 0), watermark_text, font=watermark_font)[2:]
            watermark_x = (width - watermark_width) // 2
            watermark_y = (height - watermark_height) // 2

            draw.text((watermark_x, watermark_y), watermark_text, font=watermark_font, fill=(180, 180, 180, 128))  # light gray
        except Exception as e:
            logger.error(f"Failed to add text watermark: {e}")

        # Save image to BytesIO
        img_io = BytesIO()
        ticket_image.save(img_io, format="PNG")
        img_io.seek(0)
        return img_io

    except Exception as e:
        logger.error(f"Failed to generate ticket image for ticket ID {getattr(ticket, 'id', 'unknown')}: {e}")
        raise


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



def verify_qr(encrypted_data):
    try:
        decrypted_data = cipher_suite.decrypt(encrypted_data.encode()).decode()
        ticket_info = json.loads(decrypted_data)
        return ticket_info
    except Exception as e:
        logger.error(f"QR verification failed: {e}")
        return None




 