from constance import config
from django.core.signals import got_request_exception
from django.shortcuts import render
from django.utils.translation import gettext_lazy
from social_core.exceptions import AuthForbidden, AuthCanceled
from social_django.middleware import SocialAuthExceptionMiddleware
from social_django.strategy import DjangoStrategy


class ConstanceStrategy(DjangoStrategy):

    def get_setting(self, name):
        try:
            value = getattr(config, name)
            if name == 'SOCIAL_AUTH_WHITELISTED_DOMAINS' and value is not None:
                value = [item.strip() for item in value.split(',')]
        except AttributeError:
            value = None
        if not value:
            return super(ConstanceStrategy, self).get_setting(name)
        return value


class ExceptionMessageMiddleware(SocialAuthExceptionMiddleware):

    def process_exception(self, request, exception):
        if isinstance(exception, AuthForbidden):
            return render(request, '500.html', {
                "heading": "Authentication Failed",
                "auth_exception": exception,
                "message": str(exception),
                "additional": gettext_lazy("Please ensure you are logging in from the correct Google account.")
            })
        if isinstance(exception, (AuthForbidden, AuthCanceled)):
            got_request_exception.send(sender=self, request=request)
            return render(request, '500.html', {
                "auth_exception": exception,
                "message": str(exception),
            })

        return super().process_exception(request, exception)

