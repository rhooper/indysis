from django.conf.urls import url
from responsive_dashboard.views import generate_dashboard

urlpatterns = [
    url(r'^$', generate_dashboard, {'app_name': 'administration'}),
]
