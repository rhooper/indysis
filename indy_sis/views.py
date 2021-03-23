import logging

from django.shortcuts import render
from django.views.generic import TemplateView


class LoginErrorPage(TemplateView):
    template_name = 'login_error.html'

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


def handler500(request, *args, **argv):
    response = render(request, '500.html', {})
    response.status_code = 500
    return response


def csrf_failure(request, *args, **argv):
    response = render(request, '500.html', {"message": "CSRF validation failed"})
    response.status_code = 403
    logging.critical("CSRF validation failure")
    return response


def handler404(request, *args, **argv):
    response = render(request, '404.html', {})
    response.status_code = 404
    return response
