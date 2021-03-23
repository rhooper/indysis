from celery import shared_task
from constance import config
from raven.contrib.django.models import client
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from indysis_broadcast.models import BroadcastRecipient

TASK_NAME = 'Send emergency broadcasts'


@shared_task
def send_message(recpient_id: int):
    recipient = BroadcastRecipient.objects.get(pk=recpient_id)
    twclient = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    try:
        result = twclient.messages.create(from_=config.TWILIO_PHONE_NUMBER, to=recipient.phone_number, body=recipient.broadcast.message)
        recipient.status = 'delivered'
        recipient.message_sid = result.sid
    except TwilioRestException as exc:
        recipient.status = 'failed'
        client.captureException()
    finally:
        recipient.save()


@shared_task
def send_test(message: str, phone_number: str):
    client = Client(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN)
    client.messages.create(from_=config.TWILIO_PHONE_NUMBER, to=phone_number, body=message)
