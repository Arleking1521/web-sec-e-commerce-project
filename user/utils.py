# accounts/utils.py
from django.conf import settings
from django.core.mail import send_mail
from .token import TokenGenerator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

acc_active_token = TokenGenerator()

def send_verification_email(user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = acc_active_token.make_token(user)
    print("uid: ", uidb64)
    print('token: ', token)
    # ссылка на фронт, а фронт пусть дергает бекенд endpoint подтверждения
    verify_link = f"{settings.FRONTEND_VERIFY_URL}?uid={uidb64}&token={token}"

    subject = "Подтверждение аккаунта"
    message = (
        f"Привет, {user.first_name}!\n\n"
        f"Подтверди аккаунт по ссылке:\n{verify_link}\n\n"
        f"Если это был не ты — просто игнорируй письмо."
    )

    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
