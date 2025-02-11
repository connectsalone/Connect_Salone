from django.core.mail import send_mail
from django.template.loader import get_template


def send_confirmation_email(email, token_id, user_id):
    data = {
        'token_id': str(token_id),
        'user_id': str(user_id),
    }

    # Ensure that the path to the template is correct
    message = get_template('accounts/confirmation_email.txt').render(data)

    send_mail(
        subject="Please confirm your email",
        message=message,
        from_email='admin@ourapp.com',
        recipient_list=[email],  # Ensure the recipient list contains the user's email
        fail_silently=False  # Set to False to raise exceptions if something goes wrong
    )
