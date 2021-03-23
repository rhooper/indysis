"""Report card Views."""
from json import JSONDecodeError

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils.safestring import mark_safe
from raven.contrib.django.models import client

from indysis_googlesync import tasks
from indysis_googlesync.google_group_sync import GoogleSync, NotConfigured
from indysis_googlesync.models import GoogleGroupSync


@permission_required('googlesync.synchronize')
def index(request):
    """Main page."""

    # Test credentials
    enabled = {}

    try:
        GoogleSync.get_credentials()
        enabled['Google Groups'] = reverse("googlesync:group_sync_index")

    except NotConfigured as err:

        messages.error(request, str(err))
        messages.error(
            request,
            mark_safe(
                f"Google Service Account credentials must be <a href='{reverse('admin:constance_config_changelist')}'>"
                f"configured</a> to setup synchronization."))

    except Exception as err:
        messages.error(request, str(err))
        client.captureException()

    return render(request, 'google_sync/index.html', {"enabled": enabled})


@permission_required('googlesync.synchronize')
def group_sync_index(request):

    groups = []
    try:
        groups = GoogleSync.list_groups()
    except NotConfigured as err:
        messages.error(request, str(err))
        messages.error(
            request,
            mark_safe(
                f"Double check your <a href='{reverse('admin:constance_config_changelist')}'>Configuration</a> "
                f" and ensure GOOGLE_SYNC_GROUP_ADMIN_EMAIL is set."))
    except Exception as err:
        messages.error(request, "An error occurred communicating with Google: %s" % err)
        client.captureException()

    return render(request, 'google_sync/groups_index.html', dict(
        groups=GoogleGroupSync.sync(groups)
    ))


@permission_required('googlesync.synchronize')
def group_sync(request, group_id):

    group = get_object_or_404(GoogleGroupSync, pk=group_id)

    if not group.auto_sync:
        messages.error(request, "Synchronization not enabled for group %s" % group.email)
        return redirect('googlesync:group_sync_index')

    tasks.setup_schedule()
    tasks.sync_group.apply_async((group.id, ))
    messages.info(request, "Queued sync of group %s" % group.email)

    return redirect('googlesync:group_sync_index')
