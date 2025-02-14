from django.db import models, transaction, IntegrityError
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import RegexValidator
from events.models import Cart, Ticket
import logging

logger = logging.getLogger(__name__)

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    phone_number = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message="Enter a valid 9-digit phone number.")]
    )
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    payment_date = models.DateTimeField(null=True, blank=True)

    def process_payment(self):
        """Process payment: mark cart as paid, generate tickets, clear cart items, and delete cart."""
        if self.status != 'completed':
            raise ValidationError("Payment is not completed yet.")

        if not self.transaction_id:
            raise ValidationError("Transaction ID is missing. Cannot process payment.")

        try:
            with transaction.atomic():
                # ✅ Ensure transaction ID is unique before proceeding
                if Payment.objects.filter(transaction_id=self.transaction_id).exists():
                    raise ValidationError("This transaction ID already exists. Payment cannot be duplicated.")

                self.payment_date = timezone.now()
                self.save()

                tickets = []
                for item in self.cart.cart_items.all():
                    for _ in range(item.quantity):
                        ticket = Ticket.objects.create(
                            user=self.user,
                            event=item.event,
                            ticket_name=f"Ticket for {item.event.name}",
                            ticket_price=item.event.get_ticket_price(),
                            payment_reference=self.transaction_id,
                            paid=True,
                        )
                        ticket.generate_qr_code()
                        tickets.append(ticket)

                # ✅ Clear cart items and delete cart
                self.cart.cart_items.all().delete()
                self.cart.delete()

                logger.info(f"Payment successful for {self.user.username} (Transaction ID: {self.transaction_id}).")
                return tickets

        except IntegrityError:
            logger.error(f"Duplicate payment attempt detected for Transaction ID: {self.transaction_id}.")
            raise ValidationError("This payment has already been processed. Please do not retry.")


        def __str__(self):
            return f"Payment for {self.user.username} - {self.status}"
