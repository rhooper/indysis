from datetime import date

from constance import config
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.decorators import (
    login_required, user_passes_test, permission_required)
from django.contrib.auth.forms import PasswordChangeForm
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views import generic

from sis.attendance.models import StudentAttendance
from sis.studentdb.models import Term, StudentClass, StudentClassTeacher
from .forms import UserPreferenceForm, StudentLookupForm
from .forms import YearSelectForm
from .models import Student, UserPreference, GradeLevel, SchoolYear
from .pdf_reports import student_thumbnail


@login_required
def user_preferences(request):
    """ Displays user preferences
    """
    profile = UserPreference.objects.get_or_create(user=request.user)[0]
    if request.POST:
        if "password_change" in request.POST:
            password_form = PasswordChangeForm(user=request.user, data=request.POST)
            form = UserPreferenceForm(instance=profile)

            if password_form.is_valid():
                password_form.save()
                messages.success(request, 'Your password has been successfully changed.')
                update_session_auth_hash(request, password_form.user)
        elif "prefs_change" in request.POST:
            form = UserPreferenceForm(request.POST, instance=profile)
            password_form = PasswordChangeForm(user=request.user)

            if form.is_valid():
                form.cleaned_data['user'] = request.user
                form.save()
                messages.info(request, 'Successfully updated preferences')
                if 'refer' in request.GET and request.GET['refer']:
                    return HttpResponseRedirect(request.GET['refer'])
                return HttpResponseRedirect(reverse('admin:index'))
    else:
        form = UserPreferenceForm(instance=profile)
        password_form = PasswordChangeForm(user=request.user)
    return render(request, 'sis/user_preferences.html', {
        'form': form,
        'password_form': password_form,
    })


@login_required
def index(request):
    """Render an error page for unauthorized users."""
    if 'next' in request.GET and request.GET['next'] != "/":
        return HttpResponseRedirect(request.GET['next'])
    if request.user.is_staff:
        return HttpResponseRedirect('/studentdb/dashboard')

    return render(request,
                  '500.html',
                  {
                      'message': "Account not authorized.",
                      "additional": "Please contact your school administrator(s) to get access."
                  })


@user_passes_test(lambda u: u.has_perm("studentdb.view_student"))
def photo_flash_card(request, year=None):
    """ Simple flash card game"""
    students = Student.objects.filter(is_active=True, pic__isnull=False).exclude(pic='')
    grade_levels = GradeLevel.objects.all()
    try:
        if request.POST:
            form = StudentLookupForm(request.POST, request.FILES)
            if form.is_valid():
                student_id = form.cleaned_data['student']
            else:
                student_id = students.order_by('?')[0].pk
        else:
            form = StudentLookupForm()
            if year:
                student_id = students.filter(year=GradeLevel.objects.get(id=year)).order_by('?')[0].pk
            else:
                student_id = students.order_by('?')[0].pk
        student = Student.objects.get(pk=student_id)
    except:
        messages.error(request, 'Student not found')
        return HttpResponseRedirect(reverse('admin:index'))
    return render(request, 'sis/flashcard.html',
                  {'form': form,
                   'student_name': student,
                   'grade_levels': grade_levels,
                   'student_img': student.pic.url_530x400,
                   'request': request})


def thumbnail(request, year):
    return student_thumbnail(request, GradeLevel.objects.get(id=year))


def logout_view(request):
    """ Logout, by sending a message to the base.html template
    """
    logout(request)
    messages.add_message(request, messages.INFO, 'You have been logged out.')
    return render(request, 'sis_base.html')


@login_required
def ajax_include_deleted(request):
    """ ajax call to enable or disable user preference to search for inactive students
    """
    checked = request.GET.get('checked')
    profile = UserPreference.objects.get_or_create(user=request.user)[0]
    if checked == "true":
        profile.include_deleted_students = True
    else:
        profile.include_deleted_students = False
    profile.save()
    return HttpResponse('SUCCESS')


def attendance_years_for_student(student):
    # Figure out the maximum number of school years the student might
    # have been a student for based on grade.
    if not student.year:
        return []
    num_years = student.year.id
    years = SchoolYear.objects.order_by("-start_date").filter(
        start_date__lte=date.today()).all()
    if num_years > len(years):
        return years
    trimmed_years = list(years)[:-num_years]
    years = list(years)[-num_years:]

    while trimmed_years and StudentAttendance.objects.filter(
            student=student, date__lt=trimmed_years[0].start_date
    ):
        years.insert(0, trimmed_years[0])
        trimmed_years = trimmed_years[1:]

    return years


@user_passes_test(lambda u: u.has_perm("studentdb.view_student"))
def view_student(request, id=None):
    """ Lookup all student information
    """
    if request.method == "GET":
        if id and 'next' in request.GET or 'previous' in request.GET:
            current_student = get_object_or_404(Student, pk=id)
            found = False
            preference = UserPreference.objects.get_or_create(user=request.user)[0]
            if 'next' in request.GET:
                if preference.include_deleted_students:
                    students = Student.objects.order_by('last_name', 'first_name')
                else:
                    students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')
            elif 'previous' in request.GET:
                if preference.include_deleted_students:
                    students = Student.objects.order_by('-last_name', '-first_name')
                else:
                    students = Student.objects.filter(is_active=True).order_by('-last_name', '-first_name')
            for student in students:
                if found:
                    return HttpResponseRedirect('/studentdb/view_student/' + str(student.id))
                if student == current_student:
                    found = True

    if request.method == 'POST':
        form = StudentLookupForm(request.POST)
        if form.is_valid():
            return HttpResponseRedirect('/studentdb/view_student/' + str(form.cleaned_data['student'].id))

    profile = UserPreference.objects.get_or_create(user=request.user)[0]

    if id:
        student = get_object_or_404(Student, pk=id)
    else:
        messages.warning(request, 'No Student Selected')
        return render(request, 'sis/view_student.html', {
            'include_inactive': profile.include_deleted_students,
        })

    today = date.today()
    parents = student.emergency_contacts.filter(emergency_only=False).order_by('-primary_contact', 'lname', 'fname')
    emergency_contacts = student.emergency_contacts.filter(emergency_only=True).order_by('lname', 'fname')
    siblings = student.siblings.all()
    numbers = student.studentnumber_set.all()

    # Today's attendance
    today_attendance = student.student_attn.filter(date=date.today()).first()

    # Attendance
    years = attendance_years_for_student(student)
    for year in years:
        year.mps = Term.objects.filter(school_year=year).distinct().order_by("start_date")

        # Attendance
        if 'sis.attendance' in settings.INSTALLED_APPS:
            # Temporarily use term start date, not school year
            start = year.mps[0].start_date
            attendances = student.student_attn.filter(date__range=(year.mps[0].start_date, year.end_date))
            year.attendances = attendances
            year.attendance_tardy = attendances.filter(status__tardy=True).count()
            year.attendance_absense = attendances.filter(status__absent=True).count()
            year.attendance_absense_with_half = year.attendance_absense + float(
                attendances.filter(status__half=True).count()) / 2

    # Standard Tests

    return render(request, 'sis/view_student.html', {
        'date': today,
        'student': student,
        'parents': parents,
        'emergency_contacts': emergency_contacts,
        'siblings': siblings,
        'numbers': numbers,
        'years': years,
        'include_inactive': profile.include_deleted_students,
        'today_attendance': today_attendance,
        'school_year': SchoolYear.objects.get(active_year=True),
    })


@permission_required('studentdb.change_student')
def increment_year(request):
    subtitle = "There will be confirmation screen before any changes are made."
    message = "Select the school year to activate"
    form = YearSelectForm()
    if request.POST:
        form = YearSelectForm(request.POST)
        if form.is_valid():
            year = form.cleaned_data['school_year']
            return HttpResponseRedirect(reverse('studentdb:increment_year_confirm', args=[year.id]))
    return render(request, 'sis/generic_form.html', {'subtitle': subtitle, 'form': form, 'msg': message})


class StudentViewDashletView(generic.DetailView):
    model = Student
    template_name = 'sis/view_student_dashlet.html'

    @method_decorator(permission_required('studentdb.view_student'))
    def dispatch(self, *args, **kwargs):
        return super(StudentViewDashletView, self).dispatch(*args, **kwargs)


@transaction.atomic
def increment_year_confirm(request, year_id):
    """ Show user a preview of what increment year will do before making it
    """
    students = Student.objects.filter(is_active=True)
    subtitle = "Are you sure you want to make the following changes?"
    msg = "You can always change students later."
    year = get_object_or_404(SchoolYear, pk=year_id)
    if request.POST:

        activate_year(students, year)

        messages.success(request, 'Successfully incremented student years!')
        return HttpResponseRedirect(reverse('admin:studentdb_student_changelist'))

    old_active_year = SchoolYear.objects.get(active_year=True)
    item_list = ["Change active year from %s to %s" % (old_active_year, year)]
    for student in students:
        row = None
        if student.year:
            new_year = student.year.next_grade
            if not new_year:
                row = '<a target="_blank" href="/admin/studentdb/student/%s">%s</a> (%s) - Graduate and mark inactive.' % (
                    student.id, str(student), str(student.year))
                if 'sis.alumni' in settings.INSTALLED_APPS:
                    row += ' Also make an alumni record.'
            else:
                try:
                    row = '<a target="_blank" href="/admin/studentdb/student/%s">%s</a> (%s) - Make a %s.' % (
                        student.id, str(student), str(student.year), new_year)
                except SchoolYear.DoesNotExist:
                    pass
        if row:
            item_list += [mark_safe(row)]

    return render(request, 'sis/list_with_confirm.html', {'subtitle': subtitle, 'item_list': item_list, 'msg': msg})


def activate_year(students, year):
    prev_year = year.get_current_year()
    year.active_year = True
    year.save()
    for student_class in StudentClass.objects.filter(school_year=prev_year).order_by('id'):
        if StudentClass.objects.filter(school_year=year,
                                       shortname=student_class.shortname).exists():
            continue
        old_id = student_class.id
        student_class.id = None
        student_class.school_year = year
        student_class.save()
        old_class = StudentClass.objects.get(pk=old_id)
        for teacher in old_class.studentclassteacher_set.all():
            teacher.id = None
            teacher.student_classes = student_class
            teacher.save()

        student_class.terms = year.term_set.all()
        student_class.save()
    for student in students:
        if student.year:
            new_year = student.year.next_grade
            if not new_year:
                student.graduate_and_create_alumni()
            else:
                student.year = new_year
                student.classes.add(
                    StudentClass.objects.get(school_year=year, shortname=student.year.shortname))
                student.save()
