from django.conf.urls import url

from .views import index, review, deliver, status, incoming_sms, incoming_status

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^review/(?P<id>\d+)', review, name='review'),
    url(r'^deliver/(?P<id>\d+)', deliver, name='deliver'),
    url(r'^status/(?P<id>\d+)', status, name='status'),
    url(r'^incoming_sms', incoming_sms, name='incoming_sms'),
    url(r'^incoming_status', incoming_status, name='incoming_status'),
]
