from django.db import models, transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import RegexValidator
from events.models import Cart, Ticket, Event
import logging

logger = logging.getLogger(__name__)


class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="payments", null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_payments")
    phone_number = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message="Enter a valid 9-digit phone number.")]
    )  # Strictly 9 digits
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)  # Kept as a field
    transaction_id = models.CharField(max_length=100, unique=True, null=False, blank=False, default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    payment_reference = models.CharField(max_length=128, unique=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    @property
    def calculated_amount(self):
        """Calculate the total payment amount based on cart items."""
        return sum(ticket.price for ticket in Ticket.objects.filter(cart=self.cart))

    def save(self, *args, **kwargs):
        """Set payment date when the payment is completed."""
        if self.status == "completed" and not self.payment_date:
            self.payment_date = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        event_name = self.event.event_name if self.event else "No Event"
        return f"Payment of {self.amount} by {self.user.username} for {event_name}"


    def clean(self):
        """Ensure transaction ID and payment date validation."""
        if not self.transaction_id:
            raise ValidationError("Transaction ID must be provided.")
        if self.status == 'completed' and not self.payment_date:
            raise ValidationError("Payment date is required for completed payments.")
        if not self.event:
            raise ValidationError("Event must be specified for the payment.")

