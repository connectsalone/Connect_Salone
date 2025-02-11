import logging
import secrets
import hashlib
import qrcode
from django.db import models, transaction
from django.utils import timezone
from django.core.files.base import ContentFile
from io import BytesIO
from django.core.exceptions import ValidationError
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import IntegrityError
import bleach
from django.conf import settings
from django.db.models import F
import uuid
from django.utils import timezone

# Setting up a logger for the application
logger = logging.getLogger(__name__)

class Sponsorer(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='sponsorer_logos/', null=True, blank=True)

    def __str__(self):
        return self.name

class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_description = models.TextField()
    event_type = models.CharField(
        max_length=100,
        choices=[('concert', 'Concert'), ('conference', 'Conference'), ('sports', 'Sports'), ('theatre', 'Theatre')]
    )
    event_date = models.DateTimeField()
    event_location = models.CharField(max_length=255)
    event_status = models.CharField(
        max_length=20,
        choices=[('upcoming', 'Upcoming'), ('sold_out', 'Sold Out'), ('canceled', 'Canceled'), ('normal', 'Normal')],
        default='upcoming'
    )
    event_image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    early_bird_price = models.DecimalField(max_digits=10, decimal_places=2)
    normal_price = models.DecimalField(max_digits=10, decimal_places=2)
    early_bird_end = models.DateTimeField(null=True, blank=True) 
    video_url = models.URLField(max_length=500, null=True, blank=True)
    video_file = models.FileField(upload_to='event_videos/', null=True, blank=True)
    event_logo = models.ImageField(upload_to='event_logos/', null=True, blank=True)
    event_created_at = models.DateTimeField(auto_now_add=True)
    event_updated_at = models.DateTimeField(auto_now=True)
    sponsorers = models.ManyToManyField(Sponsorer, related_name="events", blank=True)
    view_count = models.PositiveIntegerField(default=0)  # Corrected

    def increment_count(self):
        """Increase the view count for the event."""
        Event.objects.filter(id=self.id).update(view_count=models.F('view_count') + 1)

    def get_ticket_price(self):
        """Returns the ticket price based on the early bird period."""
        if self.early_bird_end and timezone.now() < self.early_bird_end:
            return self.early_bird_price
        return self.normal_price or 0  # Default to 0 if no price is set

    def save(self, *args, **kwargs):
        """Override save to clean description before saving."""
        allowed_tags = ['b', 'i', 'u', 'a']
        self.event_description = bleach.clean(self.event_description, tags=allowed_tags, strip=True)
        self.event_name = self.event_name.title()  # Capitalize each word
        super().save(*args, **kwargs)

    def is_upcoming(self):
        """Returns True if the event is upcoming based on its event date."""
        return self.event_status == 'upcoming' and self.event_date > timezone.now()

    def is_trending(self):
        """Returns True if the event is trending based on its view count."""
        return self.view_count > 100  # Adjust threshold as needed.
    
    def is_normal(self):
        """Returns True if the event is neither upcoming nor trending."""
        return self.event_status == 'normal'

    def __str__(self):
        return f"{self.event_name} at {self.event_location} on {self.event_date.strftime('%Y-%m-%d')}"

    class Meta:
        verbose_name = 'Event'
        verbose_name_plural = 'Events'



# Ticket Model
class Ticket(models.Model):
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='event_tickets')
    ticket_name = models.CharField(max_length=200)
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    payment_reference = models.CharField(max_length=128, null=True, blank=True, default="", editable=False)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True, editable=False)
    secret_token = models.CharField(max_length=64, null=True, blank=True, unique=True, editable=False)
    paid = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField()  # Track quantity

    def save(self, *args, **kwargs):
        """Override save to ensure price, QR code, and token are generated."""
        if not self.ticket_price:
            self.ticket_price = self.event.get_ticket_price()
        if self.paid and not self.qr_code:
            self.generate_qr_code()

        if not self.secret_token:
            token, hashed_token = self.generate_secure_token()
            self.secret_token = hashed_token

        super().save(*args, **kwargs)

    def generate_qr_code(self):
        """Generate a unique QR code linked to the ticket payment."""
        try:
            signed_data = self.generate_signed_data()
            qr = qrcode.make(signed_data)
            qr_image = BytesIO()
            qr.save(qr_image, format='PNG')
            qr_image.seek(0)
            if not self.qr_code:
                self.qr_code.save(f"ticket_{uuid.uuid4().hex}.png", ContentFile(qr_image.read()), save=False)
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            raise RuntimeError(f"Error generating QR code: {e}")

    def generate_secure_token(self):
        """Generate a secure token and hash it for storage."""
        token = secrets.token_hex(32)
        hashed_token = hashlib.sha256(token.encode('utf-8')).hexdigest()
        return token, hashed_token

    def generate_signed_data(self):
        """Generate signed data for the QR code."""
        signer = TimestampSigner()
        data = f"{self.id}|{self.cart.id}|{self.payment_reference}|{timezone.now().isoformat()}"
        return signer.sign(data)

    def __str__(self):
        return f"{self.ticket_name} for {self.cart.user.username}"

    class Meta:
        ordering = ['-event__event_date']


# Cart Model
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings

class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    cart_count = models.IntegerField(default=0)
    total_price = models.FloatField(default=0.0)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_total_price(self):
        """Calculate total price based on cart items."""
        return sum(item.event.get_ticket_price() * item.quantity for item in self.cart_items.all())


    def update_cart_count(self):
        """Update the total ticket count."""
        self.cart_count = sum(item.quantity for item in self.cart_items.all())

# Create the cart after a user is created or a ticket is added for the first time
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_cart(sender, instance, created, **kwargs):
    if created:
        # Create a Cart for the newly created user
        Cart.objects.create(user=instance)

# Use post-save signal to update totals after the Cart is saved
@receiver(post_save, sender=Cart)
def update_cart_totals(sender, instance, **kwargs):
    # Avoid recursion by checking if totals need to be updated
    total_price = instance.get_total_price()
    cart_count = sum(item.quantity for item in instance.cart_items.all())
    
    if instance.total_price != total_price or instance.cart_count != cart_count:
        instance.total_price = total_price
        instance.cart_count = cart_count
        # Save only if necessary, to avoid recursion
        instance.save(update_fields=["total_price", "cart_count"])


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="cart_items")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1)

    def clean(self):
        """Ensure quantity is valid."""
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

    def save(self, *args, **kwargs):
        """Save and update cart totals."""
        self.clean()
        if not self.cart.pk:
            self.cart.save()  # Ensure cart exists before saving item
        super().save(*args, **kwargs)
        self.cart.update_cart_count()  # Update count
        self.cart.total_price = self.cart.get_total_price()  # Update total price
        self.cart.save()


    def __str__(self):
        return f"{self.quantity} x {self.event.event_name} in {self.cart}"



# Payment Model
class Payment(models.Model):
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending')
    payment_date = models.DateTimeField(null=True, blank=True)

    def process_payment(self):
        """Process the payment and create tickets atomically."""
        try:
            with transaction.atomic():
                if self.payment_status == 'completed':
                    self.cart.is_paid = True
                    self.cart.save()

                    ticket_objects = []
                    for item in self.cart.cart_items.all():
                        for _ in range(item.quantity):
                            ticket_objects.append(Ticket(
                                event=item.ticket.event,
                                cart=self.cart,
                                ticket_name=item.ticket.ticket_name,
                                ticket_price=item.ticket.ticket_price,
                                payment_reference=self.id,
                            ))
                    Ticket.objects.bulk_create(ticket_objects)

        except IntegrityError as e:
            logger.error(f"Payment processing error: {e}")
            raise ValidationError("Payment processing failed.")

    def __str__(self):
        return f"Payment for {self.cart.user.username} - {self.payment_status}"


# EventView Model
class EventView(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="views")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['event', 'user', 'session_key'], name='unique_event_view')
        ]

    def __str__(self):
        return f"View on {self.viewed_at} for {self.event.event_name}"


# Signal to Update View Count
_is_signal_running = False

@receiver(post_save, sender=EventView)
def update_event_view_count(sender, instance, created, **kwargs):
    global _is_signal_running
    if _is_signal_running:
        return
    _is_signal_running = True
    try:
        if created:
            with transaction.atomic():
                event = instance.event
                event.view_count = F('view_count') + 1
                event.save(update_fields=['view_count'])
    finally:
        _is_signal_running = False
