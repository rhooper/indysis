from django.conf.urls import url

from .views import batch_generate_reportcard
from .views import conflicting_edit_student, ping_student_edit, done_student_edit
from .views import conflicting_edit_subject, ping_subject_edit, done_subject_edit
from .views import generate_comment_report, comment_report, term_state
from .views import generate_student, generate_grade_batch, generate_grade_zip
from .views import index, view_term, term_admin, edit_student, edit_subject, \
    view_student, email_rc_to_current_user, email_rc_to_parents, \
    email_grade_batch

urlpatterns = [
    url(r'^$', index, name='index'),

    url(r'term/(?P<id>\d+)$', view_term, name='view_term'),

    url(r'view/student/(?P<student_id>\d+)/(?P<term_id>\d+)$', view_student, name='view_student'),
    url(r'edit/student/(?P<student_id>\d+)/(?P<term_id>\d+)$', edit_student, name='edit_student'),
    url(r'ping/student/(?P<student_id>\d+)/(?P<term_id>\d+)$', ping_student_edit, name='ping_student_edit'),
    url(r'done/student/(?P<student_id>\d+)/(?P<term_id>\d+)$', done_student_edit, name='done_student_edit'),
    url(r'conflict/student/(?P<student_id>\d+)/(?P<term_id>\d+)$', conflicting_edit_student,
        name='conflicting_edit_student'),

    # TODO Refactor to use class_id instead of grade_id
    url(r'edit/subject/(?P<subject_id>\d+)/(?P<grade_id>\d+)/(?P<term_id>\d+)$', edit_subject, name='edit_subject'),
    url(r'conflict/subject/(?P<subject_id>\d+)/(?P<grade_id>\d+)/(?P<term_id>\d+)$', conflicting_edit_subject,
        name='conflicting_edit_subject'),
    url(r'ping/subject/(?P<subject_id>\d+)/(?P<grade_id>\d+)/(?P<term_id>\d+)$', ping_subject_edit,
        name='ping_subject_edit'),
    url(r'done/subject/(?P<subject_id>\d+)/(?P<grade_id>\d+)/(?P<term_id>\d+)$', done_subject_edit,
        name='done_subject_edit'),

    url(r'generate/student/(?P<student_id>\d+)/(?P<term_id>\d+)/(?P<filename>.*)$', generate_student,
        name='generate_student'),
    url(r'email_me/student/(?P<student_id>\d+)/(?P<term_id>\d+)$', email_rc_to_current_user,
        name='email_current_user'),
    url(r'email_parents/student/(?P<student_id>\d+)/(?P<term_id>\d+)$', email_rc_to_parents,
        name='email_rc_to_parents'),
    url(r'generate_batch/(?P<term_id>\d+)/(?P<year_id>\d+)$', generate_grade_batch, name='generate_grade_batch'),
    url(r'generate_batch/(?P<term_id>\d+)/(?P<year_id>\d+)/zip$', generate_grade_zip, name='generate_grade_zip'),
    url(r'email_grade_batch/(?P<term_id>\d+)/(?P<year_id>\d+)$', email_grade_batch, name='email_grade_batch'),

    url(r'term/generate_all/(?P<id>\d+)$', batch_generate_reportcard, name='generate_all'),

    url(r'term/comment_report/(?P<id>\d+)$', comment_report, name='comment_report'),
    url(r'term/generate_comment_report/(?P<grade_id>\d+)/(?P<term_id>\d+)', generate_comment_report,
        name='generate_comment_report'),

    url(r'term_admin/(?P<id>\d+)$', term_admin, name='term_admin'),
    url(r'term_state/(?P<id>\d+)/(?P<state>\d+)$', term_state, name='term_state'),
]
