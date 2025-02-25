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

    def __str__(self):
        return f"Payment for {self.user.username} - {self.status}"
