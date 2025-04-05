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
from decimal import Decimal
from datetime import timedelta


# Setting up a logger for the application
logger = logging.getLogger(__name__)


class Sponsorer(models.Model):
    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='sponsorer_logos/', null=True, blank=True)

    def __str__(self):
        return self.name

from django.db import models
from django.utils import timezone
import bleach

class Event(models.Model):
    event_name = models.CharField(max_length=200)
    event_description = models.TextField()
    event_type = models.CharField(
        max_length=100,
        choices=[
            ('concert', 'Concert'),
            ('party', 'Party'),
            ('conference', 'Conference'),
            ('sports', 'Sports'),
            ('theatre', 'Theatre')
        ]
    )
    event_date = models.DateTimeField()
    event_location = models.CharField(max_length=255)
    event_status = models.CharField(
        max_length=20,
        choices=[
            ('upcoming', 'Upcoming'),
            ('sold_out', 'Sold Out'),
            ('canceled', 'Canceled'),
            ('normal', 'Normal')
        ],
        default='upcoming'
    )
    event_image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    video_url = models.URLField(max_length=500, null=True, blank=True)
    video_file = models.FileField(upload_to='event_videos/', null=True, blank=True)
    event_logo = models.ImageField(upload_to='event_logos/', null=True, blank=True)
    event_created_at = models.DateTimeField(auto_now_add=True)
    event_updated_at = models.DateTimeField(auto_now=True)
    sponsorers = models.ManyToManyField('Sponsorer', related_name="events", blank=True)
    view_count = models.PositiveIntegerField(default=0)

    def increment_count(self):
        """Increase the view count for the event."""
        Event.objects.filter(id=self.id).update(view_count=models.F('view_count') + 1)

    def save(self, *args, **kwargs):
        """Override save to sanitize event description and format name."""
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


class TicketPrice(models.Model):
    event = models.ForeignKey(Event, related_name='ticket_types', on_delete=models.CASCADE)
    name = models.CharField(
        max_length=50,
        choices=[
            ('Ordinary', 'Ordinary'),
            ('Near_Stage', 'Near Stage'),
            ('VIP', 'VIP'),
            ('VVIP', 'VVIP'),
        ]
    )
    early_bird_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    normal_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True )
    early_bird_start = models.DateTimeField(null=True, blank=True)
    early_bird_end = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Set early_bird_start to now if it's not set
        if not self.early_bird_start:
            self.early_bird_start = timezone.now()
        
        # Set early_bird_end to one week before the event date
        if not self.early_bird_end and self.event.start_date:
            self.early_bird_end = self.event.start_date - timedelta(weeks=1)

        super().save(*args, **kwargs)

    def get_price(self):
        """Returns the correct ticket price based on the early bird period."""
        now = timezone.now()
        if self.early_bird_start and self.early_bird_end and self.early_bird_start <= now <= self.early_bird_end:
            return self.early_bird_price if self.early_bird_price is not None else self.normal_price
        return self.normal_price

    def __str__(self):
        return f"{self.name} - {self.event.event_name} - ${self.get_price()}"

    class Meta:
        verbose_name = 'Ticket Type'
        verbose_name_plural = 'Ticket Types'


from django.db import models
from django.core.files.base import ContentFile
from django.core.signing import TimestampSigner
from django.utils import timezone
import secrets
import hashlib
import qrcode
import uuid
from io import BytesIO

class Ticket(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, default=1)
    event = models.ForeignKey('Event', on_delete=models.CASCADE, related_name='event_tickets')
    ticket_name = models.CharField(max_length=200)
    ticket_price = models.ForeignKey(TicketPrice, on_delete=models.CASCADE, default=1)
    payment_reference = models.CharField(max_length=128, null=True, blank=True, default="", editable=False)
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True, editable=False)
    secret_token = models.CharField(max_length=64, null=True, blank=True, unique=True, editable=False)
    paid = models.BooleanField(default=False)
    quantity = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        if not self.ticket_price and self.paid:
            self.ticket_price = self.item.ticket_price.get_price()  # Get the price when ticket is paid

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
            self.qr_code.save(f"ticket_{uuid.uuid4().hex}.png", ContentFile(qr_image.read()), save=False)
        except Exception as e:
            raise RuntimeError(f"Error generating QR code: {e}")

    def generate_secure_token(self):
        """Generate a secure token and hash it for storage."""
        token = secrets.token_hex(32)
        hashed_token = hashlib.sha256(token.encode('utf-8')).hexdigest()
        return token, hashed_token

    def generate_signed_data(self):
        """Generate signed data for the QR code."""
        signer = TimestampSigner()
        data = f"{self.id}|{self.payment_reference}|{timezone.now().isoformat()}"
        return signer.sign(data)

    def __str__(self):
        return f"Ticket for {self.event.event_name}"  # Use event_name instead of name

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
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_total_price(self):
        """Calculate total price based on cart items."""
        return sum(item.ticket_price.get_price() * item.quantity for item in self.items.all())  # Change `cart_items` to `items`

    def update_cart_count(self):
        """Update the total ticket count."""
        self.cart_count = sum(item.quantity for item in self.items.all())  # Change `cart_items` to `items`
        self.save(update_fields=["cart_count"])




# Create the cart after a user is created or a ticket is added for the first time
@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_cart(sender, instance, created, **kwargs):
    if created:
        # Create a Cart for the newly created user
        Cart.objects.create(user=instance)


@receiver(post_save, sender=Cart)
def update_cart_totals(sender, instance, **kwargs):
    """Ensure total price and cart count are updated when the cart is saved."""
    total_price = instance.get_total_price()
    cart_count = sum(item.quantity for item in instance.items.all())  # Change `cart_items` to `items`

    if instance.total_price != total_price or instance.cart_count != cart_count:
        instance.total_price = total_price
        instance.cart_count = cart_count
        instance.save(update_fields=["total_price", "cart_count"])


from django.db import models
from django.utils import timezone

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    ticket_price = models.ForeignKey(TicketPrice, on_delete=models.CASCADE, default=1)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(default=timezone.now)  # Ensure a default value
    is_paid = models.BooleanField(default=False)
    


    class Meta:
        unique_together = ('cart', 'ticket_price')  # Prevent duplicate entries


    def clean(self):
        """Ensure quantity is valid."""
        if self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

    def save(self, *args, **kwargs):
        """Save and update cart totals."""
        self.clean()
        super().save(*args, **kwargs)
        self.cart.update_cart_count()
        self.cart.total_price = self.cart.get_total_price()
        self.cart.save(update_fields=["total_price", "cart_count"])


    def __str__(self):
        return f"{self.quantity} x {self.event.event_name} in {self.cart}"



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




