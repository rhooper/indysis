from django.conf.urls import url
from responsive_dashboard.views import generate_dashboard

from .misc_views import afterschool_attendance, afterschool_usage, siblings, gerri_csv, student_information_report
from .misc_views import class_roster, birthdays, parents, healthconcerns, \
    student_reports, afterschool_bulk_form, beforeschool_usage, beforeschool_bulk_form, geocode, student_map
from .misc_views import healthcards, photopermission
from .misc_views import parent_labels, student_labels
from .misc_views import parents_export, class_list, list_classes
from .misc_views import foodorders, volunteerhours
from .views import increment_year, increment_year_confirm, StudentViewDashletView
from .views import photo_flash_card, thumbnail
from .views import user_preferences, view_student, ajax_include_deleted

urlpatterns = [
    url(r'^$', generate_dashboard, {'app_name': 'studentdb'}),
    url(r'^flashcard/$', photo_flash_card, name="photo_flash_card"),
    url(r'^flashcard/(?P<year>\d+)/$', photo_flash_card, name="photo_flash_card"),
    url(r'^preferences/$', user_preferences, name="user_preferences"),
    url(r'^view_student/$', view_student, name="view_student"),
    url(r'^view_student/(?P<id>\d+)/$', view_student, name="view-student"),
    url(r'^ajax_view_student_dashlet/(?P<pk>\d+)/$', StudentViewDashletView.as_view()),
    url(r'^ajax_include_deleted/$', ajax_include_deleted, name="ajax_include_deleted"),
    url(r'^increment_year/$', increment_year, name="increment_year"),
    url(r'^increment_year_confirm/(?P<year_id>\d+)/$', increment_year_confirm, name="increment_year_confirm"),
    url(r'^thumbnail/(?P<year>\d+)/$', thumbnail, name="thumbnail"),

    url(r'^classes$', list_classes, name="list_classes"),
    url(r'^class_list/(?P<id>\d+)/$', class_list, name="class_list"),
    url(r'^student_reports$', student_reports, name="student_reports"),
    url(r'^student_reports/class_roster/(?P<grade>\d+)$', class_roster, name="class_roster"),
    url(r'^student_reports/birthdays/(?P<grade>\S+)$', birthdays, name="birthdays"),
    url(r'^student_reports/parents/(?P<grade>\S+)$', parents, name="parents"),
    url(r'^student_reports/healthconcerns/(?P<grade>\d+)$', healthconcerns, name="healthconcerns"),
    url(r'^student_reports/photopermission/(?P<grade>\d+)$', photopermission, name="photopermission"),
    url(r'^student_reports/foodorders/(?P<id>\d+)/(?P<grade>\S+)$', foodorders, name="foodorders"),
    url(r'^student_reports/volunteerhours/(?P<grade>\S+)$', volunteerhours, name="volunteerhours"),
    url(r'^student_reports/healthcards/(?P<grade>\S+)$', healthcards, name="healthcards"),
    url(r'^student_reports/afterschool_attendance/(?P<grade>\S+)$', afterschool_attendance,
        name="afterschool_attendance"),
    url(r'^student_reports/afterschool_usage$', afterschool_usage, name="afterschool_usage"),
    url(r'^student_reports/beforeschool_usage$', beforeschool_usage, name="beforeschool_usage"),
    url(r'^student_reports/siblings$', siblings, name="siblings"),
    url(r'^student_reports/student_information_pdf$', student_information_report, name='student_information_pdf'),
    url(r'^students/geocode$', geocode, name="geocode"),
    url(r'^students/student_map', student_map, name="student_map"),
    url(r'^export/parents$', parents_export, name="parents_export"),
    url(r'^export/gerri$', gerri_csv, name="gerri_csv"),
    url(r'^labels/parents/(?P<grade>\d+)$', parent_labels, name="parent_labels"),
    url(r'^labels/students/(?P<grade>\d+)$', student_labels, name="student_labels"),
    url(r'^asp_attendance/(?P<grade_id>\d+)$', afterschool_bulk_form, name="afterschool_bulk_form"),
    url(r'^asp_attendance/(?P<grade_id>\d+)/(?P<start_date>\S+)$', afterschool_bulk_form, name="afterschool_bulk_form"),
    url(r'^bsp_attendance/(?P<grade_id>\d+)$', beforeschool_bulk_form, name="beforeschool_bulk_form"),
    url(r'^bsp_attendance/(?P<grade_id>\d+)/(?P<start_date>\S+)$', beforeschool_bulk_form,
        name="beforeschool_bulk_form"),
]
