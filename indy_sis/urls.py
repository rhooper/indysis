from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth.views import password_change, password_change_done, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.i18n import javascript_catalog

import sis.studentdb.views as sis_views
from indy_sis.views import LoginErrorPage

admin.autodiscover()
admin.site.login = login_required(admin.site.login)


def robots(request):
    """Robots handler.

    Try to prevent search engines from indexing
    uploaded media. Make sure your web server is
    configured to deny directory listings.

    :param request:
    :return:
    """
    return HttpResponse(
        'User-agent: *\r\nDisallow: /media/\r\n',
        content_type='text/plain'
    )


urlpatterns = [
    url(r'^$', sis_views.index),
    url(r'^robots.txt', robots),

    # (r'^ckeditor/', include('sis.ckeditor_urls')),  # include('ckeditor.urls')),
    url(r'^administration/', include('sis.administration.urls', namespace="administration")),
    url(r'^studentdb/', include('sis.studentdb.urls', namespace="studentdb")),

    url(r'^admin/', include('smuggler.urls')),
    url(r'^admin/', include("massadmin.urls")),
    url(r'^export_action/', include("sis.export_action_with_custom_field.urls", namespace="export_action")),
    url(r'^admin/jsi18n', javascript_catalog),
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^report_builder/', include('report_builder.urls', namespace="report_builder")),
    url(r'^simple_import/', include('sis.simple_import_with_custom_field.urls')),
    url(r'^simple_import/', include('simple_import.urls')),

    url(r'^login/$', login, name="login_view"),
    url(r'^logout/$', sis_views.logout_view, name="logout_view"),
    url(r'^login_error/$', LoginErrorPage.as_view(), name="error-page"),
    url(r'^password_change/$', password_change, name="password_change"),
    url(r'^password_change_done/$', password_change_done, name="password_change_done"),

    url(r'^autocomplete/', include('autocomplete_light.urls')),
    url(r'^impersonate/', include('impersonate.urls')),
    url(r'^', include('responsive_dashboard.urls')),
]

if 'sis.attendance' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^attendance/', include('sis.attendance.urls', namespace="attendance")))
if 'sis.alumni' in settings.INSTALLED_APPS:
    urlpatterns.append(url(r'^alumni/', include('sis.alumni.urls', namespace="alumni")))
if 'social_django' in settings.INSTALLED_APPS:
    urlpatterns.append(url('', include('social_django.urls', namespace='social')))

if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if getattr(settings, 'ADDITIONAL_SIS_URLS', None):
    for regex, module, namespace in settings.ADDITIONAL_SIS_URLS:
        urlpatterns.append(url(regex, include(module, namespace=namespace)))

handler500 = 'indy_sis.views.handler500'
handler404 = 'indy_sis.views.handler404'
