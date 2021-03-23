from django.conf.urls import url

from sis.attendance import views

urlpatterns = [
    url(r'^studentattendance/add_multiple/$', views.add_multiple, name="add_multiple"),
    url(r'^daily_attendance/$', views.daily_attendance, name="daily_attendance"),
    url(r'^daily_attendance/(?P<student_class_id>\d+)/$', views.daily_attendance_per_class, name="daily_attendance"),
    url(r'^exception_report/$', views.exception_report, name="exception_report"),
]
