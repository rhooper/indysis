"""Views for Attendance."""
import datetime
from contextlib import suppress

from constance import config
from django.contrib import messages
from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth.decorators import (permission_required,
                                            user_passes_test)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import modelformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.template import RequestContext
from django.urls import reverse
from django.utils.translation import gettext_lazy

from sis.studentdb.models import Student, StudentClass, Term, SchoolYear
from .forms import StudentAttendanceForm, StudentMultpleAttendanceForm
from .models import (OfficeAttendanceLog, StudentAttendance, AttendanceStatus)


def get_school_day_number(date):
    """Undocumented."""
    mps = Term.objects.filter(
        school_year__active_year=True).order_by('start_date')
    current_day = mps[0].start_date
    day = 0
    while current_day <= date:
        is_day = False
        for mp in mps:
            if current_day < mp.start_date or current_day > mp.end_date:
                continue
            days_off = []
            for d in mp.daysoff_set.all().values_list('date'):
                days_off.append(d[0])
            if current_day not in days_off:
                if mp.monday and current_day.isoweekday() == 1:
                    is_day = True
                elif mp.tuesday and current_day.isoweekday() == 2:
                    is_day = True
                elif mp.wednesday and current_day.isoweekday() == 3:
                    is_day = True
                elif mp.thursday and current_day.isoweekday() == 4:
                    is_day = True
                elif mp.friday and current_day.isoweekday() == 5:
                    is_day = True
                elif mp.saturday and current_day.isoweekday() == 6:
                    is_day = True
                elif mp.sunday and current_day.isoweekday() == 7:
                    is_day = True
        if is_day:
            day += 1
        current_day += datetime.timedelta(days=1)
    return day


@user_passes_test(lambda u: u.has_perm('attendance.admin_studentattendance'))
def daily_attendance(request):
    """Front office attendance forms."""
    date = get_date(request)
    date_str = date.strftime("%Y-%m-%d")

    classes = StudentClass.objects.filter(school_year=SchoolYear.get_current_year()).all()
    prior_submissions = OfficeAttendanceLog.objects.filter(date=date).all()
    prior_lookup = {c.id: {} for c in classes}
    for submission in prior_submissions:
        prior_lookup[submission.student_class_id][submission.ampm] = submission

    tomorrow, yesterday = yesterday_tomorrow(date)
    return render(request,
                  'attendance/daily_attendance_which.html',
                  {
                      'date_str': date_str,
                      'date': date,
                      'yesterday': yesterday,
                      'tomorrow': tomorrow,
                      'request': request,
                      'classes': classes,
                      'prior': prior_lookup,
                      'once': config.ATTENDANCE_FREQUENCY == 'once',
                      'am_label': gettext_lazy(
                          'Attendance') if config.ATTENDANCE_FREQUENCY == 'once' else gettext_lazy('AM'),
                      'pm_label': gettext_lazy('PM')
                  })


@user_passes_test(lambda u: u.has_perm('attendance.admin_studentattendance'))
def daily_attendance_per_class(request, student_class_id):
    """Front office attendance forms."""
    date = get_date(request)
    date_str = date.strftime("%Y-%m-%d")
    ampm = request.GET.get('ampm', 'am').lower()
    tomorrow, yesterday = yesterday_tomorrow(date)
    student_class = StudentClass.objects.get(id=student_class_id)
    students = Student.objects.filter(classes__in=[student_class], is_active=True).all()
    attendance_formset = modelformset_factory(
        StudentAttendance, form=StudentAttendanceForm,
        extra=students.count())
    cur_submission = OfficeAttendanceLog.objects.filter(
        student_class=student_class,
        date=date,
        ampm=ampm
    ).first()

    msg = ""
    if request.method == 'POST':
        StudentAttendance.objects.filter(
            date=date, student__in=students).delete()
        formset = attendance_formset(request.POST)
        if formset.is_valid():
            for form in formset.forms:
                att_object = form.save(commit=False)
                att_object.recorded_by = request.user
                att_object.save()
                LogEntry.objects.log_action(
                    user_id=request.user.pk,
                    content_type_id=ContentType.objects.get_for_model(
                        att_object).pk,
                    object_id=att_object.pk,
                    object_repr=str(att_object),
                    action_flag=ADDITION
                )
            if not cur_submission:
                cur_submission = OfficeAttendanceLog(
                    date=date, ampm=ampm, student_class=student_class,
                    user=request.user)
                cur_submission.save()

            messages.success(request, f'Attendance recorded for {date_str} {ampm}')
            return HttpResponseRedirect(
                reverse('attendance:daily_attendance') + f'?date={date_str}')
        msg = "Attendance NOT saved.  Correct the errors below and retry." \
              " Please confirm attendance." \
              " If problems persist contact an administrator."
    else:
        empty_student_attendance = StudentAttendance()
        initial = []
        for student in students:
            attendance = (StudentAttendance.objects.filter(date=date, student=student).first() or
                          empty_student_attendance)
            row = {
                'student': student.id, 'date': date,
                'notes': attendance.notes}
            with suppress(ObjectDoesNotExist):
                row['status'] = attendance.status
            initial.append(row)
        formset = attendance_formset(initial=initial,
                                     queryset=StudentAttendance.objects.none())

    for form, student in zip(formset.forms, students):
        student.form = form

    return render(request,
                  'attendance/daily_attendance.html',
                  {
                      'date': date,
                      'yesterday': yesterday,
                      'tomorrow': tomorrow,
                      'request': request,
                      'msg': msg,
                      'formset': formset,
                      'students': students,
                      'student_class': student_class,
                      'ampm': ampm,
                      'absent_ids': AbsentStatusIds(),
                      'once': config.ATTENDANCE_FREQUENCY == 'once',
                  })


class AbsentStatusIds:
    am = -1
    pm = -1
    all_day = -1

    def __init__(self):
        for choice in AttendanceStatus.objects.filter(teacher_selectable=True):
            if not choice.absent and not choice.half:
                continue
            if choice.absent:
                self.all_day = choice
            elif 'AM' in choice.name:
                self.am = choice.id
            elif 'PM' in choice.name:
                self.pm = choice.id


def get_date(request):
    date = request.GET.get('date', None)
    if not date:
        return datetime.date.today()
    return datetime.datetime.strptime(date, "%Y-%m-%d").date()


def yesterday_tomorrow(date):
    """Compute the previous and next weekday."""
    yesterday = date - datetime.timedelta(days=1)
    tomorrow = date + datetime.timedelta(days=1)
    if yesterday.weekday() > 4:
        yesterday -= datetime.timedelta(yesterday.weekday() - 4)
    if tomorrow.weekday() > 4:
        tomorrow += datetime.timedelta(7 - tomorrow.weekday())
    return tomorrow, yesterday


@permission_required('attendance.take_studentattendance')
def exception_report(request):
    """Generate a report with attendance exceptions."""
    date = request.GET.get("date", None)
    if date:
        date = datetime.datetime.strptime(date, "%Y-%m-%d")
    else:
        date = datetime.datetime.now()
    tomorrow, yesterday = yesterday_tomorrow(date)
    today = datetime.date.today() if date.date() != datetime.date.today() else None

    logs = StudentAttendance.objects.filter(date=date).order_by(
        'student__year', 'student__last_name', 'student__first_name')
    return render(request, 'attendance/exception_report.html',
                  {
                      'request': request,
                      'logs': logs,
                      "date": date,
                      "yesterday": yesterday,
                      "tomorrow": tomorrow,
                      "today": today,
                  })


def add_multiple(request):
    """Add multple records by allowing multiple students in the form.

    Each student will make one new record.
    """
    if request.POST:
        form = StudentMultpleAttendanceForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            created_records = 0
            updated_records = 0
            for student in data["student"]:
                record, created = StudentAttendance.objects.get_or_create(
                    recorded_by=request.user,
                    student=student,
                    date=data['date'],
                    status=data['status'],
                )
                record.time = data['time']
                record.notes = data['notes']
                record.private_notes = data['private_notes']
                record.save()
                if created:
                    created_records += 1
                else:
                    updated_records += 1
            messages.success(
                request,
                'Created {0} and updated {1} attendance records'.format(
                    created_records, updated_records), )
            return redirect(reverse(
                'admin:attendance_studentattendance_changelist'))

    else:
        form = StudentMultpleAttendanceForm()
    breadcrumbs = [
        {'link': reverse('admin:app_list', args=['attendance', ]),
         'name': 'Attendance'},
        {'link': reverse('admin:attendance_studentattendance_changelist'),
         'name': 'Student attendances'},
        {'name': 'Take multiple'},
    ]
    return render(request,
                  'sis/generic_form.html',
                  {'form': form, 'breadcrumbs': breadcrumbs},
                  RequestContext(request, {}), )
