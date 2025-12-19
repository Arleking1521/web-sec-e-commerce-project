# accounts/token_serializers.py
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['first_name'] = user.first_name
        token['last_name'] = user.last_name
        return token

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                email=email,
                password=password
            )
        else:
            msg = _('Необходимо указать email и пароль.')
            raise serializers.ValidationError(msg)

        if not user:
            msg = _('Неверный email или пароль.')
            raise serializers.ValidationError(msg)

        if not user.is_active:
            msg = _('Этот аккаунт заблокирован или не активирован.')
            raise serializers.ValidationError(msg)

        # здесь передаём дальше как будто это username_field
        data = super().validate({'email': email, 'password': password})
        return data
