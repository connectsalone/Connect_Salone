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

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="payments")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_payments")  # User who pays
    admin = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="admin_payments")  # Admin who owns the event
    phone_number = models.CharField(
        max_length=9,
        validators=[RegexValidator(regex=r'^\d{9}$', message="Enter a valid 9-digit phone number.")]
    )
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('successful', 'Successful'), ('failed', 'Failed')]
    )
    cart = models.OneToOneField(Cart, on_delete=models.CASCADE)
    payment_reference = models.CharField(max_length=128, unique=True)
    payment_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Payment of {self.amount} by {self.user.username} for {self.event.event_name} (Admin: {self.admin.username})"

