from django.conf.urls import url

from .views import index, group_sync_index, group_sync

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^groups/$', group_sync_index, name='group_sync_index'),
    url(r'^groups/sync/(?P<group_id>\d+)/$', group_sync, name='group_sync'),
]
