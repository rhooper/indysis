# -*- coding: utf-8 -*-
"""Google Synchronization models."""
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django_extensions.db.models import TimeStampedModel

from sis.studentdb.models import StudentClass, EmergencyContact, GradeLevel


class GoogleGroupSync(TimeStampedModel):
    """Google group sync configuration."""

    group_id = models.CharField(max_length=128, null=False, blank=False)
    description = models.TextField(null=False, blank=True)
    email = models.CharField(max_length=128, null=False, blank=False, unique=True)
    synchronize_classes = models.ManyToManyField(
        StudentClass, blank=True, help_text="Which parents to synchronize")
    owners = models.ManyToManyField(
        User, blank=True, related_name='googlegroup_sync_owners',
        help_text="User accounts to add as group owners")
    managers = models.ManyToManyField(
        User, blank=True, related_name='googlegroup_sync_managers',
        help_text="User accounts to add as group managers")
    staff = models.ManyToManyField(
        User, blank=True, related_name='googlegroup_sync_staff',
        help_text="User accounts to add as members")
    auto_sync = models.BooleanField(default=True)

    def __str__(self):
        """Unicode representation."""
        return self.email

    @classmethod
    def get_dict(cls):
        """Return a dictionary of all syncs keyed on email."""
        return {group.email: group for group in GoogleGroupSync.objects.all()}

    @classmethod
    def sync(cls, groups):
        emails = {group['email']: group for group in groups}
        for group in cls.objects.all():
            if group.email in emails:
                group.group_id = emails[group.email]['id']
                group.description = emails[group.email]['description']
                group.save()

                del emails[group.email]
        # Add new groups
        for group in emails.values():
            cls.objects.create(
                group_id=group['id'],
                description=group['description'],
                email=group['email'],
                auto_sync=False)

        return GoogleGroupSync.objects.order_by('email')

    def get_parents(self):
        return EmergencyContact.objects.filter(
                (~Q(email='')) &
                Q(email__isnull=False) &
                Q(student__is_active=True) &
                Q(emergency_only=False) &
                Q(student__classes__in=self.synchronize_classes.all()))

    def last_log(self):
        return self.googlegroupsynclog_set.first()


class GoogleGroupSyncLog(TimeStampedModel):
    """Google group sync logs."""

    group = models.ForeignKey(GoogleGroupSync)
    status = models.CharField(max_length=40, default="success")
    messages = models.TextField()

    class Meta:
        indexes = [
            models.Index(fields=['created'])
        ]
        ordering = ['-id']


class ExtraEmailAddress(TimeStampedModel):
    """Extra email addresses to sync."""

    group = models.ForeignKey(GoogleGroupSync, related_name="extra_emails")
    email = models.EmailField()
    role = models.CharField(max_length=10, choices=(
        ('member', 'Member'),
        ('owner', 'Owner'),
        ('manager', 'Manager'),
    ))

    class Meta:
        ordering = ['group', 'email']
        unique_together = ['group', 'email']


class StudentGradeOUMapping(TimeStampedModel):
    """
    Mappings from grades to OUs.
    """
    level = models.OneToOneField(GradeLevel,
                                 related_name="google_ou_mapping", null=False, blank=False)
    ou = models.CharField(max_length=100, null=False, blank=False,
                          verbose_name="OU")
    enable_sync = models.BooleanField(default=True)
    enable_audit = models.BooleanField(default=True)

    class Meta:
        ordering = ['level']
        verbose_name = 'Grade level to Google OU mapping'
