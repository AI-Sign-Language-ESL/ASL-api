import os
from email.mime.image import MIMEImage
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils.translation import gettext_lazy as _


def send_branded_verification_email(user_email, code):
    """
    Sends a premium HTML verification email with an inline logo.
    """
    subject = str(_("Verify your TAFAHOM account"))
    html_message = render_to_string('emails/verification_code.html', {'code': code})
    plain_message = strip_tags(html_message)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost")

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=from_email,
        to=[user_email],
    )
    email.attach_alternative(html_message, "text/html")

    # Attach logo as inline image (CID)
    logo_path = os.path.join(settings.BASE_DIR, 'templates', 'emails', 'tafahom-logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<tafahom_logo>')
            logo.add_header('Content-Disposition', 'inline', filename='tafahom-logo.png')
            email.attach(logo)

    email.send(fail_silently=True)


def send_password_reset_email(user_email, token):
    """
    Sends a premium HTML password reset email with an inline logo.
    """
    subject = str(_("Reset Your TAFAHOM Password"))
    html_message = render_to_string('emails/reset_password.html', {'token': token})
    plain_message = strip_tags(html_message)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost")

    email = EmailMultiAlternatives(
        subject=subject,
        body=plain_message,
        from_email=from_email,
        to=[user_email],
    )
    email.attach_alternative(html_message, "text/html")

    # Attach logo as inline image (CID)
    logo_path = os.path.join(settings.BASE_DIR, 'templates', 'emails', 'tafahom-logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo = MIMEImage(f.read())
            logo.add_header('Content-ID', '<tafahom_logo>')
            logo.add_header('Content-Disposition', 'inline', filename='tafahom-logo.png')
            email.attach(logo)

    email.send(fail_silently=True)
