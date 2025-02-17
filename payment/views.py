import logging
import uuid  # ✅ For unique transaction IDs
import qrcode
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from reportlab.pdfgen import canvas
from .models import Cart, Payment, Ticket

logger = logging.getLogger(__name__)

def generate_unique_transaction_id():
    """Generate a unique transaction ID."""
    return str(uuid.uuid4().hex[:12]).upper()

def calculate_cart_total(cart):
    """Calculates the total amount of the cart."""
    return sum(item.event.get_ticket_price() * item.quantity for item in cart.cart_items.all())

@login_required
def orange_payment(request):
    """Handles the payment process."""
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number', '').strip()

        if not (phone_number.isdigit() and phone_number.startswith('07') and len(phone_number) == 9):
            messages.error(request, "Invalid phone number format.")
            return redirect('orange_payment')

        with transaction.atomic():
            cart = Cart.objects.select_for_update().filter(user=request.user, is_paid=False).first()
            if not cart:
                messages.error(request, "No active cart found.")
                return redirect('orange_payment')

            total_amount = calculate_cart_total(cart)

            payment, created = Payment.objects.get_or_create(
                user=request.user,
                cart=cart,
                defaults={
                    'amount': total_amount,
                    'phone_number': phone_number,
                    'status': 'pending',
                }
            )

            if not created:
                payment.amount = total_amount
                payment.phone_number = phone_number
                payment.status = 'pending'
                payment.save()

            success = True  # Simulating successful payment for testing
            transaction_id = generate_unique_transaction_id()  # ✅ Unique transaction ID

            if success:
                try:
                    payment.status = 'completed'
                    payment.transaction_id = transaction_id
                    payment.payment_date = timezone.now()
                    payment.save()

                    # ✅ Mark cart as paid but do not delete it
                    cart.is_paid = True
                    cart.save()

                    # ✅ Create tickets and link them to the user
                    tickets = []
                    for item in cart.cart_items.all():
                        for _ in range(item.quantity):
                            ticket = Ticket.objects.create(
                                user=request.user,  # ✅ Ensures ticket ownership
                                event=item.event,
                                ticket_name=f"{item.event.event_name} Ticket",
                                ticket_price=item.event.get_ticket_price(),
                                payment_reference=transaction_id,
                                paid=True,
                                quantity=1
                            )
                            tickets.append(ticket)

                    # ✅ Clear cart items (but keep the cart for records)
                    cart.cart_items.all().delete()

                     # Delete the cart itself
                    cart.delete()

                    request.session.pop("cart_id", None)  # Remove cart session
                    request.session.modified = True  # Ensure session updates

                    logger.info(f"Payment successful: {request.user.username}, {len(tickets)} tickets created.")
                    messages.success(request, "Payment successful! Your tickets are ready.")
                    return redirect('tickets')

                except IntegrityError as e:
                    logger.error(f"Integrity error: {e}")
                    messages.error(request, "An error occurred while processing your payment. Please try again.")

                except Exception as e:
                    logger.error(f"Payment processing error: {e}")
                    messages.error(request, "Payment was successful, but an error occurred.")

            else:
                payment.status = 'failed'
                payment.save()
                messages.error(request, "Payment failed. Try again.")

    cart = Cart.objects.filter(user=request.user, is_paid=False).first()
    total_price = calculate_cart_total(cart) if cart else 0
    return render(request, 'payment/orange_payment.html', {'total_price': total_price})

import uuid
import hashlib
from datetime import datetime

def generate_secure_qr_reference(ticket):
    """Generate a secure, unique reference for the QR code."""
    # Create a unique string by combining ticket ID, event ID, and a timestamp
    unique_string = f"{ticket.id}_{ticket.event.id}_{datetime.now().isoformat()}_{uuid.uuid4()}"
    
    # Optionally, you can hash this unique string for added security
    hash_object = hashlib.sha256(unique_string.encode())
    secure_reference = hash_object.hexdigest()
    
    return secure_reference



import qrcode
from cryptography.fernet import Fernet
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# Secret key for encryption and decryption (should be kept secret and safe)
SECRET_KEY = Fernet.generate_key()
cipher_suite = Fernet(SECRET_KEY)

# Website URL for added security
WEBSITE_URL = "https://www.yourwebsite.com"

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

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

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

from django.http import HttpResponse
from io import BytesIO

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

from django.shortcuts import render, redirect
from django.http import JsonResponse
from cryptography.fernet import Fernet
from .models import Ticket
from django.contrib.auth.decorators import login_required

# Use the same secret key as in the ticket generation
SECRET_KEY = b'_R0Xpv30gHZE0HJm9XTjLQTQh-7_xihxFb6aP7_D3bI='  # Replace with your actual secret key
cipher_suite = Fernet(SECRET_KEY)

@login_required
def scan_ticket(request):
    """Scan ticket and validate the ticket details from QR code."""
    if request.method == "POST":
        qr_data = request.POST.get('qr_data')  # Get QR data from frontend
        if not qr_data:
            return JsonResponse({"error": "No QR code data provided"}, status=400)

        try:
            # Decrypt the QR code data
            decrypted_data = cipher_suite.decrypt(qr_data.encode()).decode()

            # Parse the decrypted data (it's a string representation of a dictionary)
            ticket_data = eval(decrypted_data)

            # Validate the ticket information
            ticket_id = ticket_data.get('ticket_id')
            website_url = ticket_data.get('website_url')
            
            # Check if the ticket is for your website
            if website_url != "https://www.yourwebsite.com":
                return JsonResponse({"error": "Invalid website URL"}, status=400)

            # Get the ticket object
            ticket = Ticket.objects.filter(id=ticket_id).first()
            if ticket:
                return JsonResponse({"message": "Ticket is valid", "ticket_id": ticket.id, "event_name": ticket.event.event_name}, status=200)
            else:
                return JsonResponse({"error": "Ticket not found"}, status=404)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, 'payment/scan_ticket.html')
