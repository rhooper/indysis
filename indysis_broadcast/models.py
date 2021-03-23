# -*- coding: utf-8 -*-
"""SMS Broadcast models."""
from typing import List

from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django_extensions.db.models import TimeStampedModel

from sis.studentdb.models import EmergencyContact, Faculty


class Broadcast(TimeStampedModel):
    """
    A SMS Broadcast.
    """
    PENDING = 'pending'
    QUEUED = 'queued'

    message = models.CharField(max_length=140, help_text="Text message body",
                               validators=[MinLengthValidator(4)])
    created_by = models.ForeignKey(User)
    status = models.CharField(max_length=40, default='pending')
    recipients = models.ManyToManyField(through='BroadcastRecipient', to=EmergencyContact,
                                        related_name='broadcast',
                                        related_query_name='recipients')

    def add_contacts(self):
        contact: EmergencyContact
        for contact in EmergencyContact.objects.filter(
            student__is_active=True,
            emergencycontactnumber__type='C',
            emergency_only=False
        ).distinct():
            number: str = contact.emergencycontactnumber_set.filter(type='C').first().number.as_e164
            BroadcastRecipient.objects.create(
                broadcast=self,
                recipient=contact,
                phone_number=number
            )

    def add_faculty(self):
        faculty: Faculty
        for faculty in Faculty.objects.filter(
            Q(is_active=True) &
            Q(cell__isnull=False) &
            ~Q(cell="")
        ).distinct():
            BroadcastRecipient.objects.create(
                broadcast=self,
                faculty=faculty,
                phone_number=faculty.cell
            )

    def add_arbitrary(self, numbers: List[str]):
        for number in numbers:
            BroadcastRecipient.objects.create(
                broadcast=self,
                phone_number=number
            )


    @property
    def num_recipients(self):
        return self.get_recipients().count()

    @property
    def num_sent(self):
        return self.get_recipients(status='delivered').count()

    @property
    def num_queued(self):
        return self.get_recipients(status='queued').count()

    @property
    def num_failed(self):
        return self.get_recipients(status='failed').count()

    def send(self):
        from indysis_broadcast.tasks import send_message
        for recipient in BroadcastRecipient.objects.filter(broadcast=self, status='pending'):
            recipient.status = 'queued'
            recipient.save()
            send_message.apply_async((recipient.id, ))
        self.status = 'sent'
        self.save()

    def get_recipients(self, *args, **kwargs):
        return BroadcastRecipient.objects.filter(*args, broadcast=self, **kwargs)


class BroadcastRecipient(TimeStampedModel):
    """
    A recipient for a broadcast.
    """
    broadcast = models.ForeignKey(Broadcast)
    recipient = models.ForeignKey(EmergencyContact, null=True, blank=True)
    faculty = models.ForeignKey(Faculty, null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    status = models.CharField(max_length=40, default='pending')
    message_sid = models.CharField(max_length=80, unique=True, null=True, blank=True)
    status_message = models.CharField(max_length=255, null=True, blank=True)
