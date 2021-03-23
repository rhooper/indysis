from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^match_columns/(?P<import_log_id>\d+)/$', views.match_columns, name='simple_import-match_columns'),
    url(r'^match_relations/(?P<import_log_id>\d+)/$', views.match_relations, name='simple_import-match_relations'),
    url(r'^do_import/(?P<import_log_id>\d+)/$', views.do_import, name='simple_import-do_import'),
]
