from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils.translation import gettext_lazy as _

def send_branded_verification_email(user_email, code):
    """
    Sends a premium HTML verification email to the user.
    """
    subject = _("Verify your TAFAHOM account")
    html_message = render_to_string('emails/verification_code.html', {'code': code})
    plain_message = strip_tags(html_message)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "webmaster@localhost")
    
    return send_mail(
        subject,
        plain_message,
        from_email,
        [user_email],
        html_message=html_message,
        fail_silently=True
    )
