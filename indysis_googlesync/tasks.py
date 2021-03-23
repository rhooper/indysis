import pytz
from celery import shared_task
from django.conf import settings
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django_celery_beat.models import CrontabSchedule, PeriodicTask

from indysis_googlesync.google_group_sync import GoogleSync
from indysis_googlesync.models import GoogleGroupSync

TASK_NAME = 'Synchronize Google groups'


def setup_schedule():
    """Setup schedule for sync task."""
    minute, hour, day_of_week, day_of_month, month_of_year = settings.GOOGLE_SYNC_INITIAL_CRON_SCHEDULE.split(' ')
    schedule, _ = CrontabSchedule.objects.get_or_create(
        minute=minute,
        hour=hour,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
        month_of_year=month_of_year,
        timezone=pytz.timezone(settings.TIME_ZONE)
    )
    task = PeriodicTask.objects.filter(name=TASK_NAME).first()
    if not task:
        PeriodicTask.objects.create(
            crontab=schedule,
            name=TASK_NAME,
            task='indysis_googlesync.tasks.sync_all_groups',
        )


@shared_task
def sync_all_groups():
    for group in GoogleGroupSync.objects.filter(auto_sync=True).all():
        GoogleSync.sync_group(group)


@shared_task
def sync_group(group_id: int):
    group = GoogleGroupSync.objects.get(pk=group_id)
    GoogleSync.sync_group(group)


@receiver([post_save, post_delete], sender=GoogleGroupSync)
def setup_scheduler(sender, instance, **kwargs):
    setup_schedule()
