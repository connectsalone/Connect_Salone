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

from cryptography.fernet import Fernet
from datetime import datetime
import uuid
from django.conf import settings
from events.models import Ticket  # Assuming your Ticket model is in the 'events' app

def generate_ticket_number():
    # Create cipher suite
    cipher = Fernet(settings.FERNET_KEY)

    # Raw string to encrypt (e.g., a short UUID part)
    raw = uuid.uuid4().hex[:5].upper().encode()

    # Encrypt and decode to string
    encrypted_part = cipher.encrypt(raw).decode()[:10].replace('/', '').replace('+', '')  # Shorten & clean

    # Format date
    date_part = datetime.now().strftime("%d%b%Y").upper()

    # Combine encrypted part and date part
    ticket_number = f"TKT-{encrypted_part}-{date_part}"

    # Ensure uniqueness by checking if ticket number already exists in the database
    while Ticket.objects.filter(ticket_number=ticket_number).exists():
        raw = uuid.uuid4().hex[:5].upper().encode()  # Regenerate the UUID part
        encrypted_part = cipher.encrypt(raw).decode()[:10].replace('/', '').replace('+', '')  # Re-encrypt
        ticket_number = f"TKT-{encrypted_part}-{date_part}"  # Rebuild ticket number

    return ticket_number


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

                    # Step 7: Call create_payment_and_tickets for ticket creation
                    logger.info("✅ Payment processed successfully, now calling ticket creation...")

                    payment, tickets = create_payment_and_tickets(
                        user=request.user,
                        cart=cart,
                        phone_number=phone_number,
                        total_price=total_price,
                        transaction_id=transaction_id,
                        existing_payment=payment
                    )

                    if not tickets:
                        messages.error(request, "Tickets were not created. Please contact support.")
                        return redirect('cart_view')

                    # Step 8: Mark cart as paid and clear items
                    cart.is_paid = True
                    cart.save()
                    cart.items.all().update(is_paid=True)  # Update the items as paid instead of deleting

                    messages.success(request, "Payment successful and tickets created!")
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


import hashlib
import uuid
import json
import qrcode
from cryptography.fernet import Fernet
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from events.models import Ticket
from django.conf import settings
import logging

# Initialize logger
logger = logging.getLogger(__name__)

def generate_qr_code(ticket):
    """
    Generate a secure, unique reference for the QR code.
    """
    try:
        if not ticket.id or not ticket.event.id:
            raise ValueError("Ticket and Event must be saved before generating QR code.")

        unique_string = f"{ticket.id}_{ticket.event.id}_{timezone.now().isoformat()}_{uuid.uuid4()}"
        secure_reference = hashlib.sha256(unique_string.encode()).hexdigest()

        return secure_reference
    except Exception as e:
        logger.error(f"QR Code Generation Failed: {e}")
        raise


def generate_secure_ticket_qr(ticket, cipher_suite, size=300):
    """
    Generates a secure QR code with encrypted ticket data.
    Returns a resized RGB PIL image.
    """
    try:
        # Prepare ticket payload
        payload = {
            "payment_reference": ticket.payment_reference,
            "ticket_id": ticket.id,
            "event_name": ticket.event.event_name,
            "event_date": ticket.event.event_date.strftime('%B %d, %Y'),
            "event_location": ticket.event.event_location,
            "website_url": "https://salone-connect.com/verify"  # Update with actual verification URL
        }

        # Encrypt the ticket data
        encrypted_data = cipher_suite.encrypt(json.dumps(payload).encode()).decode()

        # Create QR code
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
        qr.add_data(encrypted_data)
        qr.make(fit=True)

        # Generate QR image in RGB mode and resize it
        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        resized_img = qr_img.resize((size, size))

        return resized_img
    except Exception as e:
        logger.error(f"[QR FAIL] Ticket ID {getattr(ticket, 'id', 'unknown')}: {str(e)}")
        raise ValueError(f"Error generating QR code: {e}")



import hashlib
import uuid
from cryptography.fernet import Fernet
from datetime import datetime
import random
import string
from django.conf import settings
from events.models import Ticket
import logging

logger = logging.getLogger(__name__)

def generate_ticket_number():
    """
    Generates a cryptographically secure and unique ticket number.
    """
    cipher = Fernet(settings.FERNET_KEY)

    # Generate a secure random string as a base for ticket number (e.g., a random alphanumeric string)
    random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    # Use UUID and current timestamp to ensure uniqueness across instances
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    raw = f"{random_string}-{uuid.uuid4().hex[:6].upper()}-{timestamp}"

    # Encrypt the base string
    encrypted_part = cipher.encrypt(raw.encode()).decode()[:15]  # Limit length to avoid too long ticket numbers

    # Generate a date part (e.g., 06APR2025)
    date_part = datetime.now().strftime("%d%b%Y").upper()

    # Ensure uniqueness by checking if ticket number exists in the database
    ticket_number = f"TKT-{encrypted_part}-{date_part}"

    while Ticket.objects.filter(ticket_number=ticket_number).exists():
        logger.warning(f"⚠️ Duplicate ticket number found: {ticket_number}. Regenerating.")
        random_string = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        raw = f"{random_string}-{uuid.uuid4().hex[:6].upper()}-{timestamp}"
        encrypted_part = cipher.encrypt(raw.encode()).decode()[:15]
        ticket_number = f"TKT-{encrypted_part}-{date_part}"

    # Generate the ticket number without relying on ticket.id or ticket.pk before saving
    # Once the ticket is created, we will update it with the sequence number (1, 2, 3, etc.)
    return ticket_number

from django.db import transaction
from events.models import Ticket
from io import BytesIO
from django.core.files.base import ContentFile
from cryptography.fernet import Fernet
from django.conf import settings

def create_payment_and_tickets(user, cart, phone_number, total_price, transaction_id, existing_payment):
    """
    Handles payment processing and ticket creation in an atomic transaction block.
    """
    try:
        print("🚀 Starting ticket creation process...")

        if not phone_number:
            print("❌ Phone number is required to process payment and create tickets.")
            raise ValueError("Phone number is required")

        if not existing_payment:
            print("❌ No existing payment found.")
            return None, "Payment does not exist."

        # Set payment reference and save
        payment = existing_payment
        payment_reference = generate_payment_reference(user, transaction_id, get_random_string(16))
        payment.payment_reference = payment_reference
        payment.save()
        print(f"✅ Payment reference generated and saved: {payment_reference}")

        tickets = []
        cart_items = cart.items.all()
        print(f"🛒 Cart has {cart_items.count()} items.")

        for item in cart_items:
            event = item.event
            ticket_price = item.ticket_price

            if not ticket_price:
                print(f"⚠️ Skipping event '{event.event_name}' due to missing ticket_price.")
                continue

            try:
                price = ticket_price.get_price()
                print(f"🎫 Creating tickets for event: {event.event_name} | Price: {price} | Quantity: {item.quantity}")
            except Exception as e:
                print(f"❌ Error getting price for event {event.event_name}: {e}")
                continue

            for i in range(item.quantity):
                ticket_number = generate_ticket_number()  # Ensure unique ticket number

                # Print ticket number for debugging
                print(f"🎫 Generated ticket number for ticket {i + 1}: {ticket_number}")

                try:
                    ticket = Ticket.objects.create(
                        user=user,
                        event=event,
                        ticket_name=ticket_number,
                        ticket_price=ticket_price,
                        price=price,
                        quantity=1,
                        payment_reference=payment_reference,
                        paid=True
                    )
                    print(f"✅ Ticket created: {ticket.ticket_name} (ID: {ticket.id})")

                    # After the ticket is created, we assign the sequence number
                    sequence_number = str(ticket.pk).zfill(2)  # Use the primary key (ticket.pk) as the sequence number
                    ticket_number_with_sequence = f"{ticket.ticket_number}-{sequence_number}"

                    # Update the ticket number with the sequence number
                    ticket.ticket_number = ticket_number_with_sequence

                    # Generate and attach QR code
                    try:
                        qr_img = generate_secure_ticket_qr(ticket, Fernet(settings.FERNET_KEY))
                        qr_io = BytesIO()
                        qr_img.save(qr_io, format='PNG')
                        ticket.qr_code.save(f"qr_{ticket.id}.png", ContentFile(qr_io.getvalue()), save=True)
                        print(f"📷 QR code saved for ticket ID: {ticket.id}")
                    except Exception as qr_error:
                        print(f"❌ Failed to generate QR for ticket {ticket.id}: {qr_error}")

                    tickets.append(ticket)

                except Exception as create_error:
                    print(f"❌ Failed to create ticket for event {event.event_name}: {create_error}")
                    raise  # Raise error to trigger rollback

        print(f"✅ Ticket creation complete. Total tickets created: {len(tickets)}")
        return payment, tickets

    except Exception as e:
        print(f"💥 Error during ticket creation: {e}")
        return None, f"An error occurred: {str(e)}"


from PIL import Image, ImageDraw, ImageFont, ImageOps
from io import BytesIO
from cryptography.fernet import Fernet
from django.conf import settings
import logging
import math

logger = logging.getLogger(__name__)

def generate_ticket_image(ticket, cipher_suite):
    # Load fonts with reduced sizes for event name and ticket number
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 30)  # Use Arial Bold for the event name
        text_font = ImageFont.truetype("arial.ttf", 30)
        watermark_font = ImageFont.truetype("arial.ttf", 45)
        ticket_num_font = ImageFont.truetype("arial.ttf", 15)  # Reduced font size for ticket number
    except IOError:
        title_font = text_font = watermark_font = ticket_num_font = ImageFont.load_default()

    try:
        width, height = 1000, 400
        img = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(img)

        # Layout sections
        left, middle, right = (0, 0, width//3), (width//3, 0, 2*width//3), (2*width//3, 0, width)
        padding = 10

        # Left: Event Image
        if ticket.event.event_image:
            try:
                event_img = Image.open(ticket.event.event_image.path)
                event_img = event_img.resize((width//3 - 2*padding, height - 2*padding))
                img.paste(event_img, (padding, padding))
            except Exception as e:
                logger.error(f"[Image Fail] Ticket {ticket.id}: {e}")

        # Middle: Event Details Centered
        def center_text(text, y, font, color="black"):
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x = middle[0] + ((middle[2] - middle[0]) - text_width) // 2
            draw.text((x, y), text, font=font, fill=color)

        y = 50
        center_text(ticket.event.event_name.upper(), y, title_font, color="#0a3338")  # Set color to #0a3338 with bold font
        center_text(ticket.event.event_date.strftime('%B %d, %Y'), y + 70, text_font)
        center_text(ticket.event.event_date.strftime('%I:%M %p'), y + 120, text_font)
        center_text(ticket.event.event_location, y + 170, text_font)
        center_text(f"Price: NLe{ticket.ticket_price.get_price():.2f}", y + 220, text_font)

        # Right: QR Code with Ticket Number above
        try:
            qr = generate_secure_ticket_qr(ticket, cipher_suite)
            qr_x = right[0] + ((right[2] - right[0]) - qr.width) // 2
            qr_y = (height - qr.height) // 2

            # Draw ticket number above QR code
            tn_text = f"{ticket.ticket_name}"

            # Calculate the bounding box of the ticket number text
            tn_bbox = draw.textbbox((0, 0), tn_text, font=ticket_num_font)

            # Calculate the width of the text and available space in the right section
            ticket_width = tn_bbox[2] - tn_bbox[0]  # Width of the ticket number text
            available_width = right[2] - right[0]  # Available width for centering the ticket number

            # Center the text within the right section
            tn_x = right[0] + (available_width - ticket_width) // 2

            # Draw the ticket number text at the calculated x position and y position above the QR code
            draw.text((tn_x, qr_y - 30), tn_text, font=ticket_num_font, fill="black")

            # Paste QR code
            img.paste(qr, (qr_x, qr_y))

        except Exception as e:
            logger.error(f"[QR Paste Fail] Ticket {ticket.id}: {e}")

        # Borders
        draw.rectangle([(0, 0), (width, height)], outline="green", width=5)
        draw.rectangle([(5, 5), (width - 5, height - 5)], outline="white", width=5)
        draw.rectangle([(10, 10), (width - 10, height - 10)], outline="blue", width=5)

        # Diagonal Watermark
        try:
            watermark = "salone-connect.com"
            watermark_img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
            watermark_draw = ImageDraw.Draw(watermark_img)

            bbox = watermark_draw.textbbox((0, 0), watermark, font=watermark_font)
            wm_width = bbox[2] - bbox[0]
            wm_height = bbox[3] - bbox[1]

            # Calculate center and rotate
            wm_x = (width - wm_width) // 2
            wm_y = (height - wm_height) // 2
            watermark_draw.text((wm_x, wm_y), watermark, font=watermark_font, fill=(180, 180, 180, 90))

            # Rotate watermark image
            rotated_wm = watermark_img.rotate(45, resample=Image.BICUBIC)
            img = Image.alpha_composite(img.convert("RGBA"), rotated_wm).convert("RGB")

        except Exception as e:
            logger.error(f"[Watermark Fail]: {e}")

        # Save to BytesIO
        output = BytesIO()
        img.save(output, format="PNG")
        output.seek(0)
        return output

    except Exception as e:
        logger.error(f"[Ticket Gen Fail] ID {getattr(ticket, 'id', 'unknown')}: {e}")
        raise


from cryptography.fernet import Fernet
from django.conf import settings


@login_required
def ticket(request, ticket_id):

    """View the ticket image before downloading."""
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user)

    # Initialize cipher_suite (use your 32-byte base64 key)
    cipher_suite = Fernet(settings.FERNET_KEY)
    
    # Then call the function with both args
    img_io = generate_ticket_image(ticket, cipher_suite)
    
    return HttpResponse(img_io, content_type="image/png")


from collections import defaultdict
from django.shortcuts import render
from payment.models import Ticket

def tickets_view(request):
    tickets = Ticket.objects.all()  # Fetch all tickets

    # Group tickets by event using defaultdict
    grouped_tickets = defaultdict(list)
    for ticket in tickets:
        grouped_tickets[ticket.event].append(ticket)

    # Convert the defaultdict to a regular dictionary (optional)
    grouped_tickets = dict(grouped_tickets)

    # Pass the grouped tickets to the template
    return render(request, 'payment/ticket_list.html', {'grouped_tickets': grouped_tickets})


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

import json
import logging
from cryptography.fernet import Fernet
from django.conf import settings
from django.http import JsonResponse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from decouple import config
from .models import Ticket

logger = logging.getLogger(__name__)

# Load the Fernet encryption key securely
fernet_key = config("FERNET_SECRET_KEY")
cipher_suite = Fernet(fernet_key)


@csrf_exempt  # Optional: only needed if your frontend does not send CSRF token
def scan_ticket(request):
    if request.method == "POST":
        encrypted_data = request.POST.get('qr_data')

        if not encrypted_data:
            return JsonResponse({"status": "error", "message": "No QR code data provided"}, status=400)

        try:
            # Decrypt and load ticket data
            decrypted_data = cipher_suite.decrypt(encrypted_data.encode()).decode()
            ticket_data = json.loads(decrypted_data)

            ticket_id = ticket_data.get('ticket_id')
            website_url = ticket_data.get('website_url')

            # Verify the ticket source
            if website_url != getattr(settings, 'EXPECTED_WEBSITE_URL', 'https://yourdomain.com'):
                return JsonResponse({"status": "error", "message": "Invalid website URL"}, status=400)

            ticket = Ticket.objects.filter(id=ticket_id).first()

            if not ticket:
                return JsonResponse({"status": "error", "message": "Ticket not found"}, status=404)

            if ticket.scanned:
                return JsonResponse({
                    "status": "error",
                    "message": f"Ticket has already been scanned on {ticket.used_at.strftime('%Y-%m-%d %H:%M') if ticket.used_at else 'an earlier date.'}"
                }, status=400)

            # Mark ticket as scanned
            ticket.scanned = True
            ticket.used_at = now()
            ticket.save()

            return JsonResponse({
                "status": "success",
                "data": {
                    "ticket_id": ticket.id,
                    "event_name": ticket.event.event_name,
                    "scanned": ticket.scanned,
                    "used_at": ticket.used_at.strftime('%Y-%m-%d %H:%M')
                }
            })

        except Exception as e:
            logger.error(f"[scan_ticket] QR decryption or processing error: {e}")
            return JsonResponse({"status": "error", "message": "Invalid QR code data"}, status=400)

    return render(request, 'payment/live_scanner.html')


def verify_qr(encrypted_data):
    try:
        decrypted_data = cipher_suite.decrypt(encrypted_data.encode()).decode()
        ticket_info = json.loads(decrypted_data)
        return ticket_info
    except Exception as e:
        logger.error(f"QR verification failed: {e}")
        return None



#from django.shortcuts import render

#def live_qr_scanner(request):
 #   return render(request, 'payment/live_scanner.html')
