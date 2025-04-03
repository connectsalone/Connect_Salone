from django.db import models

# Create your models here.
from django.db import models, transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from events.models import Cart, Ticket, Event, TicketPrice
import logging
import uuid
from django.contrib.auth import get_user_model
from decimal import Decimal

logger = logging.getLogger(__name__)

class ServiceFee(models.Model):
    """Model to store service fee for each event ticket."""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="service_fees")
    ticket_price = models.ForeignKey(TicketPrice, on_delete=models.CASCADE)
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)

    def __str__(self):
        return f"Service Fee for {self.event.event_name} - {self.ticket_price.name}: {self.fee_amount}"

import uuid
from decimal import Decimal
from django.db import models, transaction, IntegrityError
from django.utils import timezone
from django.core.validators import RegexValidator
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="user_payments"
    )
    phone_number = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message="Enter a valid 9-digit phone number.")]
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    transaction_id = models.CharField(max_length=100, unique=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    payment_reference = models.CharField(max_length=128, unique=True)
    payment_date = models.DateTimeField(null=True, blank=True)
    cart = models.ForeignKey('events.Cart', on_delete=models.SET_NULL, null=True, blank=True)  # Updated reference to Cart

    ticket_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    service_fee_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    @property
    def calculated_amount(self):
        """Calculate total payment amount based on cart items, including service fees."""
        if not self.cart:
            return Decimal('0.00')  # If no cart, return 0

        ticket_total = Decimal('0.00')
        service_fee_total = Decimal('0.00')

        for item in self.cart.items.all():
            ticket_price = item.ticket_price.get_price() if item.ticket_price else Decimal('0.00')
            ticket_total += ticket_price * item.quantity

            try:
                service_fee = ServiceFee.objects.get(event=item.event, ticket_price=item.ticket_price)
                service_fee_total += service_fee.fee_amount * item.quantity
            except ServiceFee.DoesNotExist:
                logger.warning(f"Service fee not found for event {item.event.id} and ticket {item.ticket_price}")

        return ticket_total + service_fee_total

    def save(self, *args, **kwargs):
        """Ensure atomic save and update the payment date when completed."""
        if not self.transaction_id:
            self.transaction_id = str(uuid.uuid4())  # Ensures uniqueness
        
        # Calculate ticket total and service fee total
        if self.cart:
            ticket_total = Decimal('0.00')
            service_fee_total = Decimal('0.00')

            for item in self.cart.items.all():
                ticket_price = item.ticket_price.get_price() if item.ticket_price else Decimal('0.00')
                ticket_total += ticket_price * item.quantity

                try:
                    service_fee = ServiceFee.objects.get(event=item.event, ticket_price=item.ticket_price)
                    service_fee_total += service_fee.fee_amount * item.quantity
                except ServiceFee.DoesNotExist:
                    logger.warning(f"Service fee not found for event {item.event.id} and ticket {item.ticket_price}")

            # Store values separately
            self.ticket_total = ticket_total
            self.service_fee_total = service_fee_total
            self.amount = ticket_total + service_fee_total  # Total payment

        # Update payment date when status is completed
        if self.status == 'completed' and not self.payment_date:
            self.payment_date = timezone.now()

        # Using atomic transaction to ensure consistency
        try:
            with transaction.atomic():
                super().save(*args, **kwargs)  # Save the payment first
                # Save individual ticket payments after saving the main payment object
                self.save_payment_tickets()

        except IntegrityError as e:
            logger.error(f"Payment save failed: {e}")
            raise ValueError("An error occurred while processing the payment. Please try again.")

    def save_payment_tickets(self):
        """Save the associated tickets for the payment."""
        for item in self.cart.items.all():
            try:
                ticket_price = item.ticket_price.get_price() if item.ticket_price else Decimal('0.00')
                PaymentTicket.objects.create(
                    payment=self,
                    ticket=item.ticket_price,
                    event=item.event,
                    quantity=item.quantity,
                    price=ticket_price,
                    amount=ticket_price * item.quantity
                )
            except Exception as e:
                logger.error(f"Error saving ticket for payment {self.transaction_id}: {e}")

    def __str__(self):
        return f"Payment of {self.amount} by {self.user.username}"

from events.models import Event, TicketPrice  # Import Event model from events app


class PaymentTicket(models.Model):
    payment = models.ForeignKey(Payment, related_name="payment_tickets", on_delete=models.CASCADE)
    ticket = models.ForeignKey(TicketPrice, on_delete=models.CASCADE)  # Correct reference to TicketPrice model
    event = models.ForeignKey(Event, on_delete=models.CASCADE)  # Correct reference to Event model
    quantity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Payment for {self.quantity} tickets of {self.event.name} by {self.payment.user.username}"