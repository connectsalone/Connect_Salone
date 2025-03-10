from django.db import models, transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import RegexValidator
from events.models import Cart, Ticket, Event, TicketPrice
import logging
import uuid  # ✅ For unique transaction IDs

logger = logging.getLogger(__name__)


class ServiceFee(models.Model):
    """Model to store service fee for each event ticket."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="service_fees")
    ticket_price = models.ForeignKey(TicketPrice, on_delete=models.CASCADE)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    
    def __str__(self):
        return f"Service Fee for {self.event.event_name} - {self.ticket_price.name}: {self.fee_amount}"

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
    transaction_id = models.CharField(max_length=100, unique=True, null=False, blank=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    payment_reference = models.CharField(max_length=128, unique=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    @property
    def calculated_amount(self):
        """Calculate the total payment amount based on cart items and add service fee from ServiceFee model."""
        # Sum of ticket prices
        ticket_prices = Ticket.objects.filter(cart=self.cart).values_list('price', flat=True)
        total_ticket_price = sum(ticket_prices)

        # Fetch service fee for the event
        service_fee = self.event.service_fee.fee_amount if self.event and self.event.service_fee else 0.00

        # Service fee for each ticket (multiply by the number of tickets)
        total_service_fee = service_fee * len(ticket_prices)

        # Total amount
        total_amount = total_ticket_price + total_service_fee
        return total_amount

    def save(self, *args, **kwargs):
        """Handle transaction and set payment date."""
        try:
            self.transaction_id = str(uuid.uuid4())  # Ensures uniqueness
            if self.status == "completed" and not self.payment_date:
                self.payment_date = timezone.now()

            super().save(*args, **kwargs)
            logger.info(f"Payment {self.transaction_id} saved for {self.user.username}.")
        except IntegrityError as e:
            logger.error(f"Error saving payment {self.transaction_id}: {e}")
            raise ValidationError("Payment could not be processed due to a database error.")


    def __str__(self):
        event_name = self.event.event_name if self.event else "No Event"
        return f"Payment of {self.amount} by {self.user.username} for {event_name}"


    def clean(self):
        if not self.transaction_id:
            raise ValidationError("Transaction ID must be provided.")
        
        if self.status == 'completed' and not self.payment_date:
            self.payment_date = timezone.now()  # Auto-set if missing

        # Only enforce event requirement if it’s necessary
        if not self.event and not self.cart:
            raise ValidationError("Either an event or a cart must be specified for the payment.")


