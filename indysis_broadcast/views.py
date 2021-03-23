"""Report card Views."""
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.csrf import csrf_exempt
from phonenumber_field.phonenumber import PhoneNumber
from raven.contrib.django.models import client
from twilio.base.exceptions import TwilioRestException

from indysis_broadcast.forms import BroadcastForm, BroadcastTestForm, ConfirmForm
from indysis_broadcast.models import Broadcast, BroadcastRecipient
from indysis_broadcast.tasks import send_test


@permission_required('broadcast.send')
def index(request: HttpRequest) -> HttpResponse:
    """Main page."""

    if request.method != 'POST':

        form = BroadcastForm()

    else:  # POST
        form = BroadcastForm(request.POST)
        if form.is_valid():
            broadcast: Broadcast = form.save(commit=False)
            broadcast.created_by = request.user
            broadcast.save()
            if form.cleaned_data['include_parents']:
                broadcast.add_contacts()
            if form.cleaned_data['include_staff']:
                broadcast.add_faculty()
            if form.cleaned_data['extra_numbers']:
                numbers = [
                    num.strip() for num in
                    form.cleaned_data['extra_numbers'].strip().split('\n')]
                broadcast.add_arbitrary([num for num in numbers if num])
            broadcast.save()
            return redirect('broadcast:review', broadcast.id)

    return render(request, 'broadcast/index.html', dict(form=form))


@permission_required('broadcast.send')
def review(request: HttpRequest, id: int) -> HttpResponse:
    """Review and test page."""

    broadcast = get_object_or_404(Broadcast, pk=id)

    if request.method != 'POST':
        form = BroadcastTestForm(initial=dict(broadcast_id=broadcast.id))
    else:
        form = BroadcastTestForm(request.POST)
        if form.is_valid():
            tel: PhoneNumber = form.cleaned_data['phone_number']
            try:
                send_test(broadcast.message, tel.as_e164)
                broadcast.status = 'tested'
                broadcast.save()
                return redirect('broadcast:deliver', broadcast.id)
            except TwilioRestException as exc:
                messages.error(request, str(exc))

    return render(request, 'broadcast/review.html', dict(broadcast=broadcast, form=form))


@permission_required('broadcast.send')
def deliver(request: HttpRequest, id: int) -> HttpResponse:
    """Queue for delivery."""

    broadcast = get_object_or_404(Broadcast, pk=id)
    if broadcast.status == 'pending':
        return redirect('broadcast:review', broadcast.id)
    if broadcast.status == 'sent':
        return redirect('broadcast:status', broadcast.id)

    if request.method != 'POST':
        form = ConfirmForm(initial=dict(broadcast_id=broadcast.id))
    else:
        form = ConfirmForm(request.POST)
        if form.is_valid():
            broadcast.send()
            return redirect('broadcast:status', broadcast.id)

    return render(request, 'broadcast/deliver.html', dict(broadcast=broadcast, form=form))


@permission_required('broadcast.send')
def status(request: HttpRequest, id: int) -> HttpResponse:
    """Monitor status."""

    broadcast = get_object_or_404(Broadcast, pk=id)

    return render(request, 'broadcast/status.html', dict(broadcast=broadcast))


@csrf_exempt
def incoming_sms(request):
    twiml = '<Response><Message>This number is not monitored / Ce numéro n\'est pas surveillé</Message></Response>'
    # client.capture('raven.events.Message', message="Incoming SMS message", data={"post": request.POST})

    users = User.objects.filter(is_superuser=True)
    try:
        send_mail("Incoming text message from %s" % request.POST.get('From', ''),
                  "A text message was received by %s.\n"
                  "Sender: %s   (%s, %s)\n\n%s\n\n" % (
                      request.POST.get('To', ''),
                      request.POST.get('From', ''),
                      request.POST.get('FromCity', ''),
                      request.POST.get('FromState', ''),
                      request.POST.get('Body', ''),
                  ),
                  f"text-message@{settings.EMAIL_DOMAIN}",
                  [user.email for user in users]
        )
    except Exception as e:
        client.captureException()

    return HttpResponse(twiml, content_type='text/xml')


@csrf_exempt
def incoming_status(request):
    message_sid = request.POST.get('MessageSid')
    message_status = request.POST.get('MessageStatus')
    if not message_sid:
        return HttpResponse(status=404, content='')

    try:
        recipient = BroadcastRecipient.objects.get(message_sid=message_sid)
        recipient.status_message = message_status
        if message_status == 'failed':
            recipient.status = 'failed'
        recipient.save()
    except BroadcastRecipient.DoesNotExist:
        pass

    return HttpResponse(status=204, content='')
