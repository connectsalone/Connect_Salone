from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.conf import settings
from decouple import config

def send_confirmation_email(email, token_id, user_id):
    # Prepare data for the template
    data = {
        'token_id': str(token_id),
        'user_id': str(user_id),
    }

    # Render the template with the data
    message = get_template('accounts/confirmation_email.txt').render(data)

    # Create the email message
    email_message = EmailMessage(
        subject="Please confirm your email",  # Ensure subject is ASCII or properly encoded
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,  # Use a default from email from settings
        to=[email],  # Ensure email is a valid ASCII or properly encoded string
    )

    
    
    # Set content type and encoding
    email_message.content_subtype = "plain"  # Ensures it's sent as plain text
    email_message.encoding = "utf-8"  # Explicitly set UTF-8 encoding

    # Send the email
    email_message.send()

