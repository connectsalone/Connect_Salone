from django.contrib.auth.tokens import PasswordResetTokenGenerator
import six

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}"

email_verification_token = EmailVerificationTokenGenerator()


def verify_token(user, token):
    return email_verification_token.check_token(user, token)
