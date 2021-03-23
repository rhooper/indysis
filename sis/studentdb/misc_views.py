import csv
from datetime import datetime, timedelta

import django.forms
import pdfkit
from constance import config
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import (
    user_passes_test, permission_required)
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils.html import escape

from sis.studentdb import google_geocode
from sis.studentdb.models import (
    AfterschoolPackage, AfterschoolProgramAttendance, BeforeschoolProgramAttendance,
    FoodOrderEvent, GradeLevel, SchoolYear, Student, StudentClass)
from .reports import AfterSchoolMonthlyUsage, student_export, Siblings, \
    gerri_export, BeforeSchoolMonthlyUsage
from .reports import ClassRoster, BirthdayList, ParentList, HealthConcerns
from .reports import HealthCards, PhotoPermission, AfterschoolAttendance
from .reports import ParentLabels, StudentLabels, FoodOrders, VolunteerHours


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def class_roster(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    attendance = request.GET.get('attendance', None)
    response['Content-Disposition'] = 'inline; filename=%s' % "class_roster%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")

    return ClassRoster(grade=grade, attendance=attendance).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def afterschool_attendance(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "afterschool_attendance%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")

    return AfterschoolAttendance(grade=grade).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def birthdays(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "birthdays%s.pdf" % (
        "-%s" % grade if grade else "")

    return BirthdayList(grade=grade).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def parents(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "parents%s.pdf" % (
        "-%s" % grade if grade else "")

    return ParentList(grade=grade, emails=request.GET.get('emails', False)).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def healthconcerns(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "health_concerns%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")
    return HealthConcerns(grade=grade).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def photopermission(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "photopermission%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")
    return PhotoPermission(grade=grade).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def foodorders(request, id, grade):
    event = get_object_or_404(FoodOrderEvent, pk=id)
    response = HttpResponse(content_type="application/pdf")
    keyword = request.GET.get('keyword', None)
    filename_parts = ['foodorders', event.name]
    if grade in (0, "0", "", "all"):
        grade = None
    elif grade == 'school':
        filename_parts.append(grade)
    elif grade:
        filename_parts.append(GradeLevel.objects.get(id=grade).shortname)
    if keyword is not None:
        filename_parts.append(keyword.lower())
    filename = '%s.pdf' % ('-'.join(filename_parts))
    response['Content-Disposition'] = 'inline; filename=%s' % filename
    return FoodOrders(event=event, grade=grade, keyword=keyword).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def parent_labels(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "parent_labels%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")
    labelscale = {
        "offset": request.GET.get('offset', ''),
        "scale": request.GET.get('scale', ''),
    }
    return ParentLabels(response, grade=grade, **labelscale).run()


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def volunteerhours(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "volunteerhours%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")
    report = VolunteerHours(grade=grade)
    school_year = request.GET.get('school_year', None)
    if school_year:
        report.school_year = SchoolYear.objects.get(id=school_year)
    return report.run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def siblings(request):
    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = 'inline; filename=%s' % "siblings.pdf"
    report = Siblings()
    school_year = request.GET.get('school_year', None)
    if school_year:
        report.school_year = SchoolYear.objects.get(id=school_year)
    return report.run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def healthcards(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "volunteerhours%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")
    return HealthCards(grade=grade).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def student_labels(request, grade):
    response = HttpResponse(content_type="application/pdf")
    if grade in (0, "0", "", "all"):
        grade = None
    response['Content-Disposition'] = 'inline; filename=%s' % "parent_labels%s.pdf" % (
        "-%s" % GradeLevel.objects.get(id=grade).shortname if grade else "")
    kwargs = {
        "offset": request.GET.get('offset', ''),
        "scale": request.GET.get('scale', ''),
        "no_grades": request.GET.get("no_grades", False),
    }
    return StudentLabels(response, grade=grade,
                         **kwargs).run()


@user_passes_test(lambda u: u.has_perm("studentdb.reports"))
def student_reports(request):
    cur_sy = SchoolYear.objects.get(active_year=True)
    last_sy = SchoolYear.objects.filter(id=cur_sy.id - 1).first()
    start = cur_sy.start_date
    if last_sy:
        start = last_sy.start_date
    end = cur_sy.end_date
    months = []
    start = datetime(start.year, start.month, 1)
    end = datetime(end.year, end.month, 1)
    cur = datetime(datetime.now().year, datetime.now().month, 1)
    month = start
    while month <= end:
        months.append((month.strftime("%Y-%m-01"), month.strftime("%b %Y")))
        month += relativedelta(months=1)

    return render(request, 'sis/student_reports.html', {
        'grades': GradeLevel.objects.order_by('id').all(),
        'labelscales':
            [
                ('office', 'offset=0&scale=1.04'),
                ('regular', ''),
            ],
        'events': FoodOrderEvent.objects.all(),
        'schoolyears': SchoolYear.objects.order_by('-id').all(),
        'months': months,
        'cur_month': cur.strftime("%Y-%m-01")
    })


@user_passes_test(lambda u: u.has_perm('studentdb.reports'))
def parents_export(request):
    """Parents Export."""

    # data = [[str(col).encode('utf-8') for col in row] for row in student_export()]
    data = student_export()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="parent_export.csv"'
    writer = csv.writer(response)
    writer.writerows(data)

    return response


@user_passes_test(lambda u: u.has_perm('studentdb.reports'))
def gerri_csv(request):
    """Parents Export."""

    # data = [[str(col).encode('utf-8') for col in row] for row in student_export()]
    data = gerri_export()

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="gerri_export.csv"'
    writer = csv.writer(response)
    writer.writerows(data)

    return response


@permission_required('studentdb.view_student')
def class_list(request, id=None):
    student_class = StudentClass.objects.get(id=id)
    students = student_class.active_students().order_by('last_name', 'first_name')
    pics = request.GET.get('pics', False)
    return render(request, 'sis/class_list_photos.html' if pics else 'sis/class_list.html', {
        'class': student_class,
        'students': students,
    })


@permission_required('studentdb.view_student')
def list_classes(request):
    classes = StudentClass.objects.filter(school_year=SchoolYear.objects.get(active_year=True)).order_by('id')
    return render(request, 'sis/list_classes.html', {
        'classes': classes,
        'total_students': sum(c.active_students().count() for c in classes)
    })


@user_passes_test(lambda u: u.has_perm("studentdb.view_afterschoolprogramattendance"))
def afterschool_usage(request):
    response = HttpResponse(content_type="application/pdf")
    month = request.GET.get("month", None)
    response['Content-Disposition'] = 'inline; filename=%s' % "afterschool_usage.pdf"

    return AfterSchoolMonthlyUsage(month=month).run(response)


@user_passes_test(lambda u: u.has_perm("studentdb.view_beforeschoolprogramattendance"))
def beforeschool_usage(request):
    response = HttpResponse(content_type="application/pdf")
    month = request.GET.get("month", None)
    response['Content-Disposition'] = 'inline; filename=%s' % "afterschool_usage.pdf"

    return BeforeSchoolMonthlyUsage(month=month).run(response)


def default_date_for_asp():
    """Find the nearest Monday."""
    start_date = datetime.now()
    weekday = start_date.isoweekday()
    if weekday >= 3:
        start_date += timedelta(days=8 - weekday)
    elif weekday == 0:  # Sunday
        start_date += timedelta(days=1)
    else:  # Monday and Tuesday
        start_date -= timedelta(days=5 - (6 - weekday))

    return start_date


class AfterschoolBulkForm(django.forms.Form):
    """Afterschool Bulk Form row."""

    student_id = django.forms.IntegerField()
    student_name = django.forms.CharField()
    monday = django.forms.BooleanField(required=False)
    tuesday = django.forms.BooleanField(required=False)
    wednesday = django.forms.BooleanField(required=False)
    thursday = django.forms.BooleanField(required=False)
    friday = django.forms.BooleanField(required=False)


class AfterschoolWithAlternateRateBulkForm(django.forms.Form):
    """Afterschool Bulk Form row (with alternate rate)."""

    student_id = django.forms.IntegerField()
    student_name = django.forms.CharField()
    monday = django.forms.BooleanField(required=False)
    monday_alt = django.forms.BooleanField(required=False)
    tuesday = django.forms.BooleanField(required=False)
    tuesday_alt = django.forms.BooleanField(required=False)
    wednesday = django.forms.BooleanField(required=False)
    wednesday_alt = django.forms.BooleanField(required=False)
    thursday = django.forms.BooleanField(required=False)
    thursday_alt = django.forms.BooleanField(required=False)
    friday = django.forms.BooleanField(required=False)
    friday_alt = django.forms.BooleanField(required=False)


class BeforeschoolBulkForm(django.forms.Form):
    """Beforeschool Bulk Form row."""

    student_id = django.forms.IntegerField()
    student_name = django.forms.CharField()
    monday = django.forms.BooleanField(required=False)
    tuesday = django.forms.BooleanField(required=False)
    wednesday = django.forms.BooleanField(required=False)
    thursday = django.forms.BooleanField(required=False)
    friday = django.forms.BooleanField(required=False)


def make_afterschool_formset(form_class, grade_id, start_date, drop_in):
    """Create a AfterschoolBulkForm formset for a grade."""

    students = Student.objects.filter(year_id=grade_id, is_active=True).all()
    asp_attendance = AfterschoolProgramAttendance.objects.filter(
        date__gte=start_date,
        date__lt=start_date + timedelta(days=5))

    if drop_in:
        step = 2
    else:
        step = 1
    form_set = django.forms.formset_factory(form_class, extra=0)

    attendance_matrix = {}
    for att in asp_attendance:
        attendance_matrix.setdefault(att.student_id, {})
        if drop_in and att.package and att.package.id == drop_in.id:
            attendance_matrix[att.student_id][(att.date.isoweekday() * step) + 1] = True
        else:
            attendance_matrix[att.student_id][att.date.isoweekday() * step] = True

    def get_attendance(st, dow, get_drop_in=False):
        offset = 1 if get_drop_in else 0
        return attendance_matrix.get(st.user_ptr_id, {}).get((dow * step) + offset, False)

    data = []
    for student in students:
        datum = {'student_id': student.user_ptr_id,
                 'student_name': student.fullname,
                 'monday': get_attendance(student, 1),
                 'tuesday': get_attendance(student, 2),
                 'wednesday': get_attendance(student, 3),
                 'thursday': get_attendance(student, 4),
                 'friday': get_attendance(student, 5)}
        if drop_in:
            datum['monday_alt'] = get_attendance(student, 1, True)
            datum['tuesday_alt'] = get_attendance(student, 2, True)
            datum['wednesday_alt'] = get_attendance(student, 3, True)
            datum['thursday_alt'] = get_attendance(student, 4, True)
            datum['friday_alt'] = get_attendance(student, 5, True)

        data.append(datum)
    return form_set(initial=data)


def make_beforeschool_formset(grade_id, start_date):
    """Create a Beforeschool formset for a grade."""

    students = Student.objects.filter(year_id=grade_id, is_active=True).all()
    asp_attendance = BeforeschoolProgramAttendance.objects.filter(
        date__gte=start_date,
        date__lt=start_date + timedelta(days=5))
    form_set = django.forms.formset_factory(BeforeschoolBulkForm, extra=0)

    attendance_matrix = {}
    for att in asp_attendance:
        attendance_matrix.setdefault(att.student_id, {})
        attendance_matrix[att.student_id][att.date.isoweekday()] = True

    def get_attendance(st, dow):
        return attendance_matrix.get(st.user_ptr_id, {}).get(dow, False)

    data = []
    for student in students:
        data.append({'student_id': student.user_ptr_id,
                     'student_name': student.fullname,
                     'monday': get_attendance(student, 1),
                     'tuesday': get_attendance(student, 2),
                     'wednesday': get_attendance(student, 3),
                     'thursday': get_attendance(student, 4),
                     'friday': get_attendance(student, 5)})
    return form_set(initial=data)


@user_passes_test(lambda u: u.has_perm("studentdb.change_bulkafterschoolattendanceentry"))
@transaction.atomic
def afterschool_bulk_form(request, grade_id, start_date=None):
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_date = default_date_for_asp()

    end_date = start_date + timedelta(days=4)
    drop_in = AfterschoolPackage.objects.filter(drop_in=True).first()
    if drop_in:
        form_class = AfterschoolWithAlternateRateBulkForm
    else:
        form_class = AfterschoolBulkForm

    if request.method != 'POST':
        formset = make_afterschool_formset(form_class, grade_id, start_date=start_date, drop_in=drop_in)
    else:
        form_set = django.forms.formset_factory(form_class, extra=0)
        formset = form_set(request.POST)

        students = []
        for form in formset:
            form.is_valid()
            students.append(form.cleaned_data['student_id'])

        current_school_year = SchoolYear.objects.get(active_year=True)
        days = (('monday', 0), ('tuesday', 1), ('wednesday', 2),
                ('thursday', 3), ('friday', 4))

        # Delete existing
        AfterschoolProgramAttendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            student_id__in=students).delete()

        num = 0
        for form in formset:
            form.is_valid()  # Ignore invalid
            for day, offset in days:
                if form.cleaned_data.get(day, False):
                    AfterschoolProgramAttendance.objects.create(
                        school_year=current_school_year,
                        student_id=form.cleaned_data['student_id'],
                        date=start_date + timedelta(days=offset)
                    )
                    num += 1
                if drop_in and form.cleaned_data.get(day + "_alt", False):
                    AfterschoolProgramAttendance.objects.create(
                        school_year=current_school_year,
                        student_id=form.cleaned_data['student_id'],
                        date=start_date + timedelta(days=offset),
                        package=drop_in,
                    )
                    num += 1
        messages.info(request, "Saved %d attendance items" % num)

    return render(request, 'sis/aspbsp_attendance.html', {
        'formset': formset,
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - timedelta(days=7),
        'next_week': start_date + timedelta(days=7),
        'grade': GradeLevel.objects.get(id=grade_id),
        'grades': GradeLevel.objects.all(),
        'title': "After",
        'link_target': 'studentdb:afterschool_bulk_form',
        'drop_in': drop_in,
    })


@user_passes_test(lambda u: u.has_perm("studentdb.change_bulkbeforeschoolattendanceentry"))
@transaction.atomic
def beforeschool_bulk_form(request, grade_id, start_date=None):
    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        start_date = default_date_for_asp()

    end_date = start_date + timedelta(days=4)

    if request.method != 'POST':
        formset = make_beforeschool_formset(grade_id, start_date=start_date)
    else:
        form_set = django.forms.formset_factory(BeforeschoolBulkForm, extra=0)
        formset = form_set(request.POST)

        students = []
        for form in formset:
            form.is_valid()
            students.append(form.cleaned_data['student_id'])

        current_school_year = SchoolYear.objects.get(active_year=True)
        days = (('monday', 0), ('tuesday', 1), ('wednesday', 2),
                ('thursday', 3), ('friday', 4))

        # Delete existing
        BeforeschoolProgramAttendance.objects.filter(
            date__gte=start_date,
            date__lte=end_date,
            student_id__in=students).delete()

        num = 0
        for form in formset:
            form.is_valid()  # Ignore invalid
            for day, offset in days:
                if form.cleaned_data.get(day, False):
                    BeforeschoolProgramAttendance.objects.create(
                        school_year=current_school_year,
                        student_id=form.cleaned_data['student_id'],
                        date=start_date + timedelta(days=offset),
                    )
                    num += 1
        messages.info(request, "Saved %d attendance items" % num)

    return render(request, 'sis/aspbsp_attendance.html', {
        'formset': formset,
        'start_date': start_date,
        'end_date': end_date,
        'prev_week': start_date - timedelta(days=7),
        'next_week': start_date + timedelta(days=7),
        'grade': GradeLevel.objects.get(id=grade_id),
        'grades': GradeLevel.objects.all(),
        'title': "Before",
        'link_target': 'studentdb:beforeschool_bulk_form'
    })


@user_passes_test(lambda u: all((u.has_perm("studentdb.view_student"), settings.GOOGLE_MAPS_KEY)))
def geocode(request):
    return render(request, 'sis/geocoding.html', {
    })


def do_geocode(student):
    pp = student.primary_parent
    if pp:
        ll = google_geocode.geocode(pp)
        # Skip no results and 0, 0
        if ll is not None and ll != (0, 0):
            if student.year:
                grade = student.year.name
                gsn = student.year.really_short_name
            else:
                grade = "??"
                gsn = "?"
            content = u"""
            <div>
                <h4>{stfn}</h4>
                <p>Grade: {grade}<br>
                {pst}<br>
                Primary parent: {pfn}<br>
                Phone: {pph}</p>
            </div>""".format(pfn=escape(pp.fullname()), grade=grade, stfn=escape(student.fullname),
                             pst=escape(pp.street),
                             pph=escape("%s (%s)" % (
                                 pp.primary_phone,
                                 pp.primary_phone.type if pp.primary_phone else "?")))
            return ll + (student.fullname, gsn, content)
    return None


@user_passes_test(lambda u: all((u.has_perm("studentdb.view_student"), settings.GOOGLE_MAPS_KEY)))
def student_map(request):
    students = Student.objects.filter(is_active=True).all()
    geoinfo = map(do_geocode, students)

    return render(request, 'sis/student_map.html', {
        "students": [g for g in geoinfo if g],
        "apikey": settings.GOOGLE_MAPS_KEY,
        "latlong": {"lat": float(config.SCHOOL_LAT), "lng": float(config.SCHOOL_LONG)}
    })


@user_passes_test(lambda u: all((u.has_perm("studentdb.view_student"), settings.GOOGLE_MAPS_KEY)))
def student_information_report(request):
    students = Student.objects.filter(is_active=True).order_by('year').all()

    def render_string(string, data={}):
        tpl = django.template.Template(string)
        ctx = django.template.Context(data)
        return tpl.render(ctx)

    content = render_to_string('sis/pdf_student_information.html', {
        'students': students,
        'header': render_string(config.STUDENT_INFORMATION_HEADER),
        'footer': render_string(config.STUDENT_INFORMATION_FOOTER),
    }, request)

    options = {
        'load-error-handling': 'skip',
        'page-size': 'Letter',
        'margin-top': '0.6in',
        'margin-left': '0.5in',
        'margin-right': '0.5in',
        'margin-bottom': '0.6in',
        'encoding': "UTF-8",
        'no-outline': None,
        'no-header-line': None,
        'disable-smart-shrinking': None,
        'zoom': 1,
    }

    pdf = pdfkit.PDFKit(content, "string", options=options).to_pdf()

    response = HttpResponse(pdf)
    response['Content-Type'] = 'application/pdf'
    response['Content-disposition'] = '%s;filename=' % 'inline'
    filename = 'Student-Data-Report-%d.pdf' % SchoolYear.get_current_year().start_date.year

    response['Content-disposition'] += filename + ""
    return response
