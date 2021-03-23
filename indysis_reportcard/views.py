"""Report card Views."""
import datetime
import logging
import os
import shutil
import tempfile
import zipfile
from copy import deepcopy
from itertools import groupby
from typing import Set

import django.template
import pdfkit
import reversion
from PyPDF2 import PdfFileReader, PdfFileMerger
from constance import config
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, models, transaction
from django.db.models import Q, Count, Subquery, OuterRef, F
from django.forms import modelformset_factory, Select
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.text import slugify
from unidecode import unidecode

from indy_sis.celery import app
from indysis_reportcard.google import GmailSender
from indysis_reportcard.models import (GradingSchemeLevelChoice, ReportCard,
                                       ReportCardEditorTracking, ReportCardEntry,
                                       ReportCardSubject, ReportCardTemplate, ReportCardTerm,
                                       ReportCardYearGradeContent, ReportCardTemplateImage, ReportCardSection,
                                       ReportCardAccess)
from indysis_reportcard.tasks import create_reportcards
from sis.studentdb.models import Faculty, GradeLevel, SchoolYear, Student


def access_allowed(u):
    """Check if access is allowed."""
    return u.groups.filter(name='faculty').count() > 0 or u.is_superuser


def is_reportcard_admin(u):
    """Check if is reportcard admin."""
    return u.groups.filter(name='reportcardadmins').count() > 0 or u.is_superuser


@user_passes_test(access_allowed)
def index(request):
    """Main page."""
    year_id = request.GET.get('year', None)
    if year_id:
        school_year = SchoolYear.objects.get(id=year_id)
        prior_years = SchoolYear.objects.filter(~Q(id=year_id)).order_by('-id')
    else:
        school_year = SchoolYear.objects.get(active_year=True)
        prior_years = SchoolYear.objects.filter(active_year=False).order_by('-id')

    terms = ReportCardTerm.objects.filter(school_year=school_year).order_by('-number').all()
    return render(request, 'index.html', dict(
        terms=terms,
        school_year=school_year,
        config=config,
        is_admin=is_reportcard_admin(request.user),
        past_years=prior_years,
    ))


class CountQuery(Subquery):
    template = "(SELECT COUNT(*) FROM (%(subquery)s) _count)"
    output_field = models.IntegerField()


@user_passes_test(access_allowed)
def view_term(request, id):
    """View report cards for a term as a teacher."""
    teacher = request.user
    try:
        if is_reportcard_admin(request.user):
            if request.GET.get('teacher_id', False):
                teacher = User.objects.get(pk=int(request.GET['teacher_id']))
            else:
                teacher = None
    except Exception:
        pass

    term = get_object_or_404(ReportCardTerm, pk=id)
    this_year = term.school_year

    url_extra = ''
    if is_reportcard_admin(request.user) and request.GET.get('teacher_id', False):
        url_extra = '?teacher_id=%d' % teacher.id

    # Determine which subjects match
    subjects = ReportCardSubject.objects.filter(Q(section__template__reportcardterm=term) & (
        Q(section__reportcardaccess__sections__template__reportcardterm=term) |
        Q(reportcardaccess__subjects__section__template__reportcardterm=term)
    ))
    if teacher:
        subjects = subjects.filter(
            Q(reportcardaccess__teachers=teacher) |
            Q(section__reportcardaccess__teachers=teacher)
        )
    subjects = subjects.distinct()

    student_filter = (Q(is_active=True) &
            Q(year__isnull=False) &
            (
                    Q(classes__reportcardaccess__sections__template__reportcardterm=term) |
                    Q(classes__reportcardaccess__subjects__section__template__reportcardterm=term)
            ) &
            (
                    Q(classes__reportcardaccess__subjects__section__template__grades=F('year')) |
                    Q(classes__reportcardaccess__sections__template__grades=F('year'))
            ) &
            (
                Q(classes__school_year=this_year)
            ))
    if teacher:
        student_filter &= Q(classes__reportcardaccess__teachers=teacher)

    students = Student.objects.filter(student_filter).distinct().prefetch_related('classes')

    grades = students.values('year').order_by().distinct()

    # Generate a list of potential subject-grade pairs
    subject_grades = set([(subject.id, grade['year'])
                          for subject in subjects
                          for grade in grades])

    # At this point, we know what subjects, students and grades
    # There is a risk that we will show extraneous subject/grade pairs
    # So we iterate the access rules for the teacher and build a parallel list,
    # being sure to avoid including subjects not mapped to the student's grade
    teacher_subject_grades = set()
    rules_filter = (
        (
                Q(subjects__in=subjects) |
                Q(sections__in=ReportCardSection.objects.filter(reportcardsubject__in=subjects))
        ) &
        (
                Q(sections__template__reportcardterm=term) |
                Q(subjects__section__template__reportcardterm=term)
        )
    )
    if teacher:
        rules_filter &= Q(teachers=teacher)
    rules = ReportCardAccess.objects.filter(rules_filter)
    rules = rules.prefetch_related('sections',
                                   'student_classes',
                                   'subjects',
                                   'student_classes__students',
                                   'student_classes__students__year')
    for rule in rules:
            for section in rule.sections.filter(template__reportcardterm=term).all():
                for subject in section.subjects.all():
                    for year in rule.student_classes.filter(
                            students__year__reportcardtemplate__reportcardsection__reportcardsubject=subject
                    ).values('students__year').distinct():
                        teacher_subject_grades.add((subject.id, year['students__year']))
            for subject in rule.subjects.filter(section__template__reportcardterm=term).all():
                for year in rule.student_classes.filter(
                    students__year__reportcardtemplate__reportcardsection__reportcardsubject=subject
                ).values('students__year').distinct():
                    teacher_subject_grades.add((subject.id, year['students__year']))
    subject_grades &= teacher_subject_grades

    completed = {}

    # # TODO YUCK
    # for student in subject_students:
    #     rce = ReportCardEntry.objects.filter(
    #         Q(reportcard__term=term) &
    #         Q(reportcard__student=student) &
    #         (
    #             Q(subject__in=grades.get(student.year, {}).get('subject_access', [])) &
    #             Q(subject__isnull=False)
    #         ) &
    #         Q(completed=True)
    #     ).distinct()
    #     if rce.count() > 0 and rce.count() >= grades.get(student.year, {}).get('num_entries', 0):
    #         completed[student] = True

    sorted_students = list(sorted(students, key=lambda x: (x.year.id, x.fullname)))

    # Counts filled student entries for a subject
    subject_info = []

    grade_student_counts = {}

    for grade in GradeLevel.objects.filter(
            student__is_active=True,
            student__classes__isnull=False,
            student__classes__school_year=this_year
    ).annotate(
        num_students=Count('student__year')):
        grade_student_counts[grade.id] = grade

    for grade_id in sorted([x['year'] for x in grades]):
        for subject in subjects.order_by('name'):

            # Skip ones that shouldn't be shown
            if (subject.id, grade_id) not in subject_grades:
                continue

            info = {
                "id": subject.id,
                "grade_id": grade_id,
                "grade": grade_student_counts[grade_id],
                "name": subject.name,
                "num_students": grade_student_counts[grade_id].num_students,
                "filled": 0,
            }

            num_completed = ReportCardEntry.objects.filter(
                completed=True,
                reportcard=OuterRef('pk'),
                subject_id=subject.id,
                reportcard__student__year_id=info['grade_id'],
                reportcard__student__classes__school_year=this_year
            ).values('pk')
            reportcard_metrics = ReportCard.objects.annotate(
                num_completed=CountQuery(num_completed)
            ).filter(
                student__year=info['grade_id'],
                term__school_year=this_year,
                reportcardentry__subject=subject.id
            ).annotate(
                num_total=Count('pk'),
            ).all()

            info['filled'] = sum(1 if s.num_completed == s.num_total else 0 for s in reportcard_metrics)
            subject_info.append(info)

    students = [
        {
            "student": s,
            "completed": s in completed,
            "editable": term.is_open,
        }
        for s in sorted_students
    ]

    teachers = []
    if is_reportcard_admin(request.user):
        teachers = Faculty.objects.filter(
            is_active=True,
            reportcardaccess__isnull=False
        ).distinct().all()

    return render(request, 'term.html', dict(
        teacher=teacher,
        term=term,
        school_year=term.school_year,
        students=students,
        subjects=subjects,
        config=config,
        superuser=is_reportcard_admin(request.user),
        teachers=teachers,
        url_extra=url_extra,
        subject_info=subject_info,
    ))


@user_passes_test(access_allowed)
def term_state(request, id, state):
    """Change the term open/closed state."""
    if not is_reportcard_admin(request.user):
        raise Http404

    term = get_object_or_404(ReportCardTerm, pk=id)
    with reversion.create_revision():
        reversion.set_comment(f"Open/Close term by {request.user}")
        reversion.set_user(request.user)
        term.is_open = bool(int(state))
        term.save()
    messages.success(request, "Changed term %s to %s" % (term, term.status))
    if term.is_open:
        create_reportcards.apply_async((term.id,))
    return redirect(reverse('reportcard:term_admin', args=[id]))


@user_passes_test(access_allowed)
def term_admin(request, id):
    """Term administration page."""
    if not is_reportcard_admin(request.user):
        raise Http404

    term = get_object_or_404(ReportCardTerm, pk=id)
    subjects = term.subjects(None).all()

    all_students = Student.objects.filter(
        is_active=True).order_by('year', 'last_name', 'first_name').all()

    # Compute completion status
    completed = Student.objects.filter(
        reportcard__term=term,
        reportcard__reportcardsubmission__completed=True,
        pk__in=all_students,
    ).order_by('id').values(
        'id',
        'reportcard__reportcardsubmission__teacher__id').all()

    completed = {
        student_id: set(
            item['reportcard__reportcardsubmission__teacher__id'] for item in group)
        for student_id, group in groupby(completed, lambda x: x['id'])
    }

    # Counts filled entries

    filled_entries = {s['id']: s['num'] for s in Student.objects.filter(
        Q(reportcard__reportcardentry__completed=True) &
        Q(reportcard__term=term)
    ).distinct().annotate(
        num=Count('reportcard__reportcardentry')).values('id', 'num').all()}

    # Counts total entries
    total_entries = {s['id']: s['num'] for s in Student.objects.filter(
        Q(reportcard__term=term)
    ).distinct().annotate(
        num=Count('reportcard__reportcardentry')).values('id', 'num').all()}

    # Calculate which teachers are expected to complete cards for each grade
    grade_teachers = {}
    for grade in GradeLevel.objects.all():
        grade_teachers[grade] = Faculty.objects.filter(
            reportcardaccess__student_classes__students__year=grade,
        ).distinct()

    students = [
        {
            "student": s,
            "emailed": ReportCard.objects.filter(student=s, term=term, emailed=True).count(),
            "expecting": len(grade_teachers[s.year]),
            "completed": len(completed.get(s.id, [])),
            "total_entries": total_entries.get(s.id, 0),
            "filled_entries": filled_entries.get(s.id, 0),
            "percent_filled": (float(filled_entries.get(s.id, 0)) /
                               (total_entries.get(s.id, 1) or 1)) * 100,
            "complete_teachers": [t for t in grade_teachers[s.year]
                                  if t.id in completed.get(s.id, [])],
            "incomplete_teachers": [t for t in grade_teachers[s.year]
                                    if t.id not in completed.get(s.id, [])],
        }
        for s in all_students if s.year is not None
    ]

    teachers = []
    teachers = Faculty.objects.filter(teacher=True, is_active=True).all()

    return render(request, 'term_admin.html', dict(
        term=term,
        school_year=term.school_year,
        students=students,
        subjects=subjects,
        config=config,
        superuser=is_reportcard_admin(request.user),
        teachers=teachers,
        templates=ReportCardTemplate.objects.filter(is_active=True).all(),
    ))


class BootstrapPercent(forms.NumberInput):
    """Helper to wrap a percent numeric input in gumby."""

    def render(self, name, value, min=0, attrs=None):
        """Render the input."""
        attrs = attrs or dict()
        if 'class' not in attrs:
            attrs['class'] = ''
        attrs['class'] += ' form-control'
        attrs['placeholder'] = 'percent'
        attrs['max'] = 100
        attrs['min'] = min
        primary = super(BootstrapPercent, self).render(name, value, attrs)
        return mark_safe(
            f'<div class="form-group"><div class="input-group">{primary}'
            f'<div class="input-group-addon">%</div></div></div>')


class BootstrapDropdown(Select):
    """Helper to wrap a select field input in gumby."""

    tabindex = 1

    def render(self, name, value, attrs=None, choices=()):
        """Render the input."""
        items = []
        for choice in self.choices:
            items.append('<option value="{choice}" {selected}>{text}</option>'.format(
                selected="selected='selected'" if choice[0] == value else '',
                choice=choice[0],
                text=choice[1],
            ))
            BootstrapDropdown.tabindex += 1
        return mark_safe(
            '<select class="form-control" name="{name}" id="{id}">{items}</select>'.format(
                items=''.join(items),
                id=name,
                name=name,
                tabindex=BootstrapDropdown.tabindex
            ))


class BootstrapRadio(forms.RadioSelect):
    """Helper to wrap a radio field input in gumby."""

    tabindex = 1

    def render(self, name, value, attrs=None, choices=()):
        """Render the input."""
        radios = []
        for choice in self.choices:
            if not choice[0]:
                continue
            radios.append(u"""
                <label class='{checked}' for='{id}'>
                    <input name="{name}" id="{id}" value="{choice}" type="radio" {checkedfield} tabindex="{tabindex}">
                    <span></span> {text}
                </label>
            """.format(
                checked="checked" if choice[0] == value else '',
                checkedfield="checked='checked'" if choice[0] == value else '',
                id=u"%s_%s" % (name, choice[0]),
                choice=choice[0],
                text=choice[1],
                name=name,
                tabindex=BootstrapRadio.tabindex
            ))
            BootstrapRadio.tabindex += 1
        return mark_safe(u'<div class="radio">' + "".join(radios) + u"</div>")


SubjectFormSet = modelformset_factory(
    ReportCardEntry,
    fields=('choice', 'percentile', 'comment', 'second_choice', 'second_percentile',),
    can_delete=False, extra=0, widgets={
        'choice': BootstrapDropdown(),
        'percentile': BootstrapPercent(),
        'second_choice': BootstrapDropdown(),
        'second_percentile': BootstrapPercent(),
        'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': '10'}),
    },
)

SubjectRadioFormSet = modelformset_factory(
    ReportCardEntry,
    fields=('choice', 'percentile', 'comment', 'second_choice', 'second_percentile',),
    can_delete=False, extra=0, widgets={
        'choice': BootstrapRadio(),
        'percentile': BootstrapPercent(),
        'second_choice': BootstrapRadio(),
        'second_percentile': BootstrapPercent(),
        'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': '10'}),
    },
)


def generate_reportcard(request, student, term, stream=True,
                        output=None, disposition='inline', base_url=None):
    """Generate a report card.

    Returns a PDF to the user if stream is True.
    Creates output if stream is False (or writes to it if output can .write())
    disposition specifies the Content-Disposition type.
    """
    template = term.get_template(grade=student.year)
    reportcard = ReportCard.objects.filter(student=student,
                                           term=term, template=template).first()

    if not reportcard:
        raise Http404('No report card data found for student %s' % student.fullname)

    html = request and request.GET.get('html', False)

    data = deepcopy(reportcard.data)

    past_entries = reportcard.get_past_terms(term)
    term_objects = reportcard.get_past_term_list(term)
    terms = past_entries.keys()
    element_to_past = {tno: {} for tno in terms}
    for tno in terms:
        element_to_past[tno] = {
            rce.most_specific_element: rce for rce in past_entries[tno]
        }
    all_entries = template.get_or_create_all_entries(reportcard)

    inst_to_element = {instance: element for element, instance in all_entries.items()}

    formset = SubjectFormSet(queryset=ReportCardEntry.objects.filter(reportcard=reportcard))
    element_to_entry = {inst_to_element[form.instance]: form.instance for form in formset}

    subjects: Set[ReportCardSubject] = set([item for item in all_entries if isinstance(item, ReportCardSubject)])
    subject_teachers = {
        subject.name_en.replace(" ", "_").lower(): subject.teachers(student) for subject in subjects if subject.name_en
    }
    subject_teachers.update({
        subject.name_fr.replace(" ", "_").lower(): subject.teachers(student) for subject in subjects if subject.name_fr
    })

    head = term.school_year.principal
    head = Faculty.objects.filter(user_ptr=head).first()
    head_title = term.school_year.principal_title or ''
    head_title_en = term.school_year.principal_title_en or ''
    head_title_fr = term.school_year.principal_title_fr or ''
    head_signature = ''
    if head and head.signature:
        head_signature = head.signature
    head = head.fullname_nocomma

    assistant_head = term.school_year.vice_principal
    assistant_head = Faculty.objects.filter(user_ptr=assistant_head).first()
    assistant_head_title = term.school_year.vice_principal_title or ''
    assistant_head_title_en = term.school_year.vice_principal_title_en or ''
    assistant_head_title_fr = term.school_year.vice_principal_title_fr or ''
    assistant_head_signature = ''
    if assistant_head and assistant_head.signature:
        assistant_head_signature = assistant_head.signature
    assistant_head = assistant_head.fullname_nocomma

    data.update(dict(
        reportcard=reportcard,
        student=student,
        term=term,
        template=template,
        element_to_entry=element_to_entry,
        element_to_past=element_to_past,
        terms=terms,
        term_objects=term_objects,
        unseen_terms=range(len(terms) + 1, 3),
        head=head,
        head_title=head_title,
        head_title_en=head_title_en,
        head_title_fr=head_title_fr,
        head_signature=head_signature,
        assistant_head=assistant_head,
        assistant_head_title=assistant_head_title,
        assistant_head_title_en=assistant_head_title_en,
        assistant_head_title_fr=assistant_head_title_fr,
        assistant_head_signature=assistant_head_signature,
        school_name=config.SCHOOL_NAME,
        school_address_line1=config.SCHOOL_ADDRESS_LINE1,
        school_address_line2=config.SCHOOL_ADDRESS_LINE2,
        school_address_city=config.SCHOOL_ADDRESS_CITY,
        school_address_provstate=config.SCHOOL_ADDRESS_PROVSTATE,
        school_address_postcode=config.SCHOOL_ADDRESS_POSTCODE,
        school_email=config.SCHOOL_EMAIL,
        school_phone=config.SCHOOL_PHONE,
        school_fax=config.SCHOOL_FAX,
        html=html,
        subject_teachers=subject_teachers,
        base_url=base_url or request.build_absolute_uri("/").rstrip("/"),
        grading_schemes=reportcard.template.get_grading_schemes()
    ))

    content = ReportCardYearGradeContent.objects.filter(school_year=term.school_year, grade_level=student.year).first()
    if content:
        data['static_content'] = mark_safe(content.content)

    data['images'] = {image.name: image for image in ReportCardTemplateImage.objects.all()}

    def render_string(string):
        tpl = django.template.Template(string)
        ctx = django.template.Context(data)
        return tpl.render(ctx)

    header = render_string(reportcard.template.get_template('header_template'))
    footer = render_string(reportcard.template.get_template('footer_template'))
    cover = render_string(reportcard.template.get_template('coverpage_template'))
    content = render_string(reportcard.template.get_template('body_template'))

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

    # Files
    # for file in ReportCardTemplateImage.objects.all():
    #     filepath = "/tmp/%s" % os.path.basename(file.image.url_300x300)
    #     if not os.path.exists(filepath):
    #         shutil.copy(
    #             os.path.join(settings.MEDIA_ROOT, 'reportcard',
    #                          os.path.basename(
    #                              file.signature.url_300x300)), filepath)

    # Signatures
    for teach in Faculty.objects.filter(is_active=True).all():
        if teach.signature:
            sigpath = "/tmp/%s" % os.path.basename(teach.signature.url_300x60)
            if not os.path.exists(sigpath):
                shutil.copy(
                    os.path.join(settings.MEDIA_ROOT, 'signatures',
                                 os.path.basename(
                                     teach.signature.url_300x60)), sigpath)

    if html:
        return HttpResponse(content)

    files = []
    try:
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as header_html:
            options['header-html'] = header_html.name
            header_html.write(header.encode('utf-8'))
            files.append(header_html)
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as footer_html:
            options['footer-html'] = footer_html.name
            footer_html.write(footer.encode('utf-8'))
            files.append(footer_html)

        pdf_kwargs = {}
        if cover.strip(" \r\n"):
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as cover_html:
                cover_html.write(cover.encode('utf-8'))
                files.append(cover_html)
            pdf_kwargs['cover'] = cover_html.name

        pdf = pdfkit.PDFKit(content, "string",
                            options=options,
                            **pdf_kwargs).to_pdf()

        if stream:
            response = HttpResponse(pdf)
            response['Content-Type'] = 'application/pdf'
            response['Content-Disposition'] = '%s' % disposition
            filename = slugify(reportcard.filename)

            if filename:
                response['Content-Disposition'] += ';filename=\'' + filename + "\'"
            return response
        else:
            # Check if quacks like a file handle
            if output is None:
                return pdf, data
            if hasattr(output, 'write'):
                output.write(pdf)
            else:
                with open(output, "wb"):
                    output.write(pdf)
                return output, data

    finally:
        # Ensure temporary file is deleted after finishing work
        for file in files:
            os.remove(file.name)


@user_passes_test(access_allowed)
def generate_student(request, student_id, term_id, filename=""):
    """Make the report card for one student."""
    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(ReportCardTerm, pk=term_id)
    return generate_reportcard(request, student, term)


@app.task
def email_rc_wrapper(student_id, term_id, to, mark_emailed=False, base_url=None, bcc_ok=False):
    student = Student.objects.get(pk=student_id)
    term = ReportCardTerm.objects.get(pk=term_id)
    return email_rc(student, term, to, mark_emailed, base_url, bcc_ok)


def email_rc(student: Student, term, to, mark_emailed=False, base_url=None, bcc_ok=False):
    template = term.get_template(grade=student.year)
    pdf, data = generate_reportcard(None, student, term, stream=False,
                                    output=None, base_url=base_url)

    def render_string(string):
        tpl = django.template.Template(string)
        ctx = django.template.Context(data)
        return tpl.render(ctx)

    filename = '%s.pdf' % slugify(student.fullname)
    message_body = render_string(term.email_body_template)
    subject = render_string(term.email_subject_template)

    html = get_template("email_wrapper.html").render({
        "school_name": config.SCHOOL_NAME,
        "content": message_body,
    })

    msg = EmailMultiAlternatives(
        subject=subject,
        body=message_body,
        from_email=config.REPORT_CARD_SENDER_EMAIL or settings.DEFAULT_REPORT_CARD_SENDER_EMAIL,
        to=[to])
    msg.attach_alternative(html, "text/html")

    if bcc_ok and config.REPORT_CARD_BCC_EMAIL:
        msg.bcc.append(config.REPORT_CARD_BCC_EMAIL)
    msg.attach(filename=filename, content=pdf, mimetype="application/pdf")

    if not os.environ.get('NO_EMAIL'):
        if config.REPORT_CARD_GMAIL and config.REPORT_CARD_SENDER_EMAIL:
            GmailSender.send_email(msg)
            method = 'gmail'
        else:
            msg.send()
            method = 'smtp'
    else:
        method = 'none'
    logging.info("%s report card using %s to %s",
                 'DID NOT send' if os.environ.get('NO_EMAIL') else 'Sent', method, to,
                 extra={
                     "from": config.REPORT_CARD_SENDER_EMAIL or settings.DEFAULT_REPORT_CARD_SENDER_EMAIL,
                     "to": to,
                     "subject": subject,
                     "student": student.id,
                     "student_name": student.fullname,
                     "grade": student.year.name
                 })

    if mark_emailed:
        template = term.get_template(grade=student.year)
        with reversion.create_revision():
            reversion.set_comment("Emailed")
            reportcard = ReportCard.objects.filter(
                student=student,
                term=term, template=template).first()
            if reportcard:
                reportcard.emailed = True
                reportcard.save()


@user_passes_test(is_reportcard_admin)
def email_rc_to_current_user(request, student_id, term_id):
    """Email the report card to the current user."""
    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(ReportCardTerm, pk=term_id)

    base_url = request.build_absolute_uri("/").rstrip("/")
    email_rc_wrapper.delay(student.id, term.id, request.user.email, mark_emailed=False, base_url=base_url)
    if not os.environ.get('NO_EMAIL'):
        messages.warning(request, "Queued 1 email for %s" % request.user.email)
    else:
        messages.warning(request, "DID NOT send email as NO_EMAIL env var set - %s" % request.user.email)

    return redirect(reverse('reportcard:term_admin', args=[term.id]))


@user_passes_test(is_reportcard_admin)
def email_rc_to_parents(request, student_id, term_id):
    """Email the report card to the current user."""
    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(ReportCardTerm, pk=term_id)

    if term.is_open:
        messages.error(request, "Term is open, not sending emails")
        return

    for parent in student.parents.filter():
        if settings.DEBUG:
            to = request.user.email
        else:
            to = parent.email

        if not to:
            continue

        base_url = request.build_absolute_uri("/").rstrip("/")
        email_rc_wrapper.delay(student.id, term.id, to, mark_emailed=True, base_url=base_url, bcc_ok=True)
        if not os.environ.get('NO_EMAIL'):
            messages.warning(request, "Queued Report card email for %s to %s" % (
                student.fullname, to))
        else:
            messages.warning(request, "DID NOT send email as NO_EMAIL env var set - for %s to %s" % (
                student.fullname, to))

    return redirect(reverse('reportcard:term_admin', args=[term.id]))


@user_passes_test(is_reportcard_admin)
def generate_comment_report(request, grade_id, term_id):
    term = get_object_or_404(ReportCardTerm, pk=term_id)
    grade = get_object_or_404(GradeLevel, pk=grade_id)

    filename = slugify(term.term.name + '-' + grade.name)
    if term.is_open:
        filename += " (Draft)"

    subjects = []
    data = {
        "grade": grade.name,
        "subjects": subjects,
    }

    reportcards = term.reportcard_set.filter(student__year=grade).all()
    tpl = reportcards[0].template

    def mark_or_grade(section, entry):
        if section.gradingscheme.percentile and not entry.choice:
            return entry.percentile if entry.percentile is not None else ''
        else:
            if not entry.choice:
                return '-'
            if entry.strand:
                language = entry.strand.rc_language
            else:
                language = entry.subject.rc_language
            return getattr(entry.choice, 'name_' + language)

    def makegrid_section(section):
        items = ReportCardEntry.objects.filter(
            reportcard__in=reportcards, section=section,
            subject__isnull=True, strand__isnull=True).order_by(
            'reportcard__student__last_name',
            'reportcard__student__first_name').all()
        grid = [{
            "student": i.reportcard.student,
            "marks": [(m.subject.name, mark_or_grade(section, m))
                      for m in ReportCardEntry.objects.filter(
                    reportcard=i.reportcard, section=section,
                    subject__isnull=False,
                    strand__isnull=True,
                    subject__graded=True).order_by(
                    'subject__sortorder').distinct().all()],
            "comments": i.comment}
            for i in items]
        return grid

    def makegrid_subject(section, subject):
        out = []
        for rc in reportcards:

            subjectent = ReportCardEntry.objects.filter(
                reportcard=rc, section=section, subject=subject,
                strand=None).first()
            strands = ReportCardEntry.objects.filter(
                reportcard=rc, section=section,
                subject=subject, strand__isnull=False).order_by(
                'strand__sortorder').distinct().all()

            marks = []
            comments = []

            if subject.comments_area:
                if subject.comments_area and subjectent:
                    comments.append(subjectent.comment
                                    if subjectent.comment is not None else '')
                if subject.graded and subjectent:
                    marks.append((subject.rc_label,
                                  mark_or_grade(section, subjectent)))
            for strand in strands:
                if strand.strand.graded:
                    marks.append((strand.strand.rc_label,
                                  mark_or_grade(section, strand)))

            comments = "\n\n".join(comments)
            out.append({"student": rc.student, "marks": marks,
                        "comments": comments})
        return out

    for section in tpl.sections:
        if section.comments_area:
            subjects.append({
                "name": section.name,
                "grid": makegrid_section(section),
                "teacher": reportcards[0].student.homeroom_teacher,
            })
        for subject in section.subjects:
            out = makegrid_subject(section, subject)
            rce = ReportCardEntry.objects.filter(
                        reportcard=reportcards[0], section=section,
                        subject=subject,
                        strand=None).first()
            teachers = ""
            if rce:
                teachers = " and ".join([
                    t.fullname_nocomma for t in
                    rce.get_teachers()])
            subjects.append({
                "name": subject.name,
                "grid": out,
                "teacher": teachers,
            })

    # from pprint import pprint
    # pprint(data)

    html = render(request, 'comment_report_template.html', dict(
        data=data,
    ))
    options = {
        'load-error-handling': 'skip',
        'page-size': 'Letter',
        'margin-top': '1in',
        'margin-left': '0.5in',
        'margin-right': '0.5in',
        'margin-bottom': '0.8in',
        'encoding': "UTF-8",
        'no-outline': None,
        'no-header-line': None,
        'disable-smart-shrinking': None,
        'zoom': 1,
        'dpi': 300,
    }

    if request.GET.get("html", False):
        return html

    pdf = pdfkit.PDFKit(html.content.decode('utf-8'), "string",
                        options=options).to_pdf()

    response = HttpResponse(pdf)
    response['Content-Type'] = 'application/pdf'
    response['Content-Disposition'] = '%s;filename=\'' % 'inline'
    filename = "Comment Report - %s.pdf" % slugify(grade.name)

    response['Content-Disposition'] += filename + "\'"
    return response


@user_passes_test(is_reportcard_admin)
def comment_report(request, id):
    """Generate a google doc with a comment report."""
    term = get_object_or_404(ReportCardTerm, pk=id)

    return render(request, 'comment_report.html', dict(
        term=term,
        grades=GradeLevel.objects.all(),
        config=config,
        superuser=is_reportcard_admin(request.user),
    ))


@user_passes_test(is_reportcard_admin)
def batch_generate_reportcard(request, id):
    """Generate all report cards for a grade."""
    if not is_reportcard_admin(request.user):
        raise Http404

    term = get_object_or_404(ReportCardTerm, pk=id)

    queued = {}
    if request.session.get('queued_grade'):
        queued[request.session['queued_grade']] = True
    for year in GradeLevel.objects.filter(reportcardtemplate__reportcardterm=term).distinct():
        if ReportCard.objects.filter(emailed=True, term=term, grade_level=year).exists():
            queued[year.id] = True

    return render(request, 'all_reportcards.html', dict(
        term=term,
        school_year=term.school_year,
        config=config,
        superuser=is_reportcard_admin(request.user),
        grades=GradeLevel.objects.order_by('id').all(),
        emails_queued=queued
    ))


@user_passes_test(is_reportcard_admin)
def generate_grade_batch(request, term_id, year_id):
    """Generate report cards for a grade."""
    term = get_object_or_404(ReportCardTerm, pk=term_id)
    year = get_object_or_404(GradeLevel, pk=year_id)

    students = Student.objects.filter(year=year, is_active=True).order_by(
        "last_name", "first_name").all()

    files = []
    try:
        merger = PdfFileMerger()
        for student in students:
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
                generate_reportcard(request, student, term, stream=False,
                                    output=pdf_file.file)
                files.append(pdf_file)
                merger.append(PdfFileReader(pdf_file.file))
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=True) as out_file:
            merger.write(out_file.file)
            out_file.seek(0)
            response = HttpResponse(out_file.file)
            response['Content-Type'] = 'application/pdf'
            response['Content-Disposition'] = 'attachment;filename=\''
            filename = '%s - %s' % (year, term)
            if term.is_open:
                filename += " (Draft)"

            response['Content-Disposition'] += filename + ".pdf\'"
            return response

    finally:
        for file in files:
            file.file.close()
            os.remove(file.name)


@user_passes_test(is_reportcard_admin)
def generate_grade_zip(request, term_id, year_id):
    """Generate report cards for a grade as a zipfile."""
    term = get_object_or_404(ReportCardTerm, pk=term_id)
    year = get_object_or_404(GradeLevel, pk=year_id)

    students = Student.objects.filter(year=year, is_active=True).order_by("last_name", "first_name").all()

    files = []
    try:

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as zip_file:
            files.append(zip_file)
            zip = zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED)

            files = []
            for student in students:
                pdf, data = generate_reportcard(request, student, term, stream=False, output=None)
                zip.writestr(unidecode(data['reportcard'].filename).replace('/', '-'), pdf)

            zip.close()
            zip_file.seek(0)
            response = HttpResponse(zip_file.file)
            response['Content-Type'] = 'application/pdf'
            response['Content-Disposition'] = 'attachment;filename=\''
            filename = '%s - %s' % (year, term)
            if term.is_open:
                filename += " (Draft)"

            response['Content-Disposition'] += filename + ".zip\'"
            return response

    finally:
        for file in files:
            file.file.close()
            os.remove(file.name)


@user_passes_test(is_reportcard_admin)
def email_grade_batch(request, term_id, year_id):
    """Email report cards for a grade."""
    term = get_object_or_404(ReportCardTerm, pk=term_id)
    year = get_object_or_404(GradeLevel, pk=year_id)

    if term.is_open:
        messages.error(request, "Term is open, not sending emails")
        return

    students = Student.objects.filter(year=year, is_active=True).order_by(
        "last_name", "first_name").all()

    sent = 0
    num_students = 0
    for student in students:

        template = term.get_template(grade=student.year)
        reportcard = ReportCard.objects.filter(
            student=student,
            term=term, template=template).first()
        if not reportcard:
            messages.error(request, "No report card found for %s." %
                           (student.fullname,))
            continue
        elif reportcard.emailed:
            messages.error(request, "Report card for %s already emailed."
                                    "  Not sent again as part of batch." %
                           (student.fullname,))
            continue

        for parent in student.parents.filter():
            if settings.DEBUG:
                to = request.user.email
            else:
                to = parent.email

            if not to:
                continue

            base_url = request.build_absolute_uri("/").rstrip("/")
            email_rc_wrapper.delay(student.id, term.id, to, mark_emailed=True, base_url=base_url)
            sent += 1
        num_students += 1

    messages.warning(request, "Processed %d students.  "
                              "Queued %d emails to parents in %s / %s." %
                     (num_students, sent,
                      year.name_fr, year.name))

    request.session['queued_grade'] = year.id

    return redirect(reverse('reportcard:generate_all', args=[term.id]))


@user_passes_test(access_allowed)
def view_student(request, student_id, term_id):
    """View a report card for a student."""
    teacher = request.user
    try:
        if is_reportcard_admin(request.user):
            if request.GET.get('teacher_id', False):
                teacher = User.objects.get(pk=int(request.GET['teacher_id']))
            else:
                teacher = None
    except Exception:
        pass

    url_extra = ''
    if is_reportcard_admin(request.user) and request.GET.get('teacher_id', False):
        url_extra = '?teacher_id=%d' % teacher.id

    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(ReportCardTerm, pk=term_id)

    template = term.get_template(grade=student.year)
    reportcard = ReportCard.objects.filter(student=student,
                                           term=term, template=template).first()

    if not reportcard:
        reportcard = ReportCard(student=student, term=term, template=template)
        try:
            reportcard.save()

        except IntegrityError:
            reportcard = ReportCard.objects.filter(student=student,
                                                   term=term, template=template).first()
            if not reportcard:
                raise Exception("Unable to create or find a report card")

    all_entries = template.get_or_create_all_entries(reportcard)

    inst_to_element = {instance: element for element, instance in all_entries.items()}

    formset = SubjectFormSet(queryset=ReportCardEntry.objects.filter(reportcard=reportcard))
    element_to_entry = {inst_to_element[form.instance]: form.instance for form in formset}

    past_entries = reportcard.get_past_terms(term)
    term_objects = reportcard.get_past_term_list(term)
    terms = past_entries.keys()
    element_to_past = {tno: {} for tno in terms}
    for tno in terms:
        element_to_past[tno] = {
            rce.most_specific_element: rce for rce in past_entries[tno]
        }

    return render(request, 'view_student.html', dict(
        config=config,
        reportcard=reportcard,
        superuser=is_reportcard_admin(request.user),
        student=student,
        term=term,
        template=template,
        request=request,
        element_to_entry=element_to_entry,
        element_to_past=element_to_past,
        terms=terms,
        term_objects=term_objects,
        teacher=teacher,
        url_extra=url_extra,
        colsize='6' if term.interim else '2',
        term_absences='%1.1f' % reportcard.student.days_absent(
            term=reportcard.term.term),
        year_absences='%1.1f' % reportcard.student.days_absent(
            school_year=term.school_year),
        term_lates='%1.1f' % reportcard.student.times_late(
            term=reportcard.term.term),
        year_lates='%1.1f' % reportcard.student.times_late(
            school_year=term.school_year),

    ))


def do_conflict_check_student(request, student_id, term_id, check_only=False, clear=False):
    """Check that there are no conflicting edits."""
    teacher = request.user
    try:
        if is_reportcard_admin(request.user):
            if request.GET.get('teacher_id', False):
                teacher = User.objects.get(pk=int(request.GET['teacher_id']))
            else:
                teacher = None
    except Exception:
        pass

    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(ReportCardTerm, pk=term_id)
    template = term.get_template(grade=student.year)
    reportcard = ReportCard.objects.filter(student=student,
                                           term=term, template=template).first()
    all_entries = template.get_or_create_all_entries(reportcard)
    section_access, subject_access, ok_ids, num_editable = access_for_template(
        template, teacher, term, student, all_entries)

    if not clear:
        conflicting = ReportCardEditorTracking.conflicting_check(
            user=request.user, students=[student],
            subjects=[subject for subject in subject_access if subject_access[subject]],
            check_only=check_only)
    else:
        ReportCardEditorTracking.conflicting_clear(
            user=request.user, students=[student], subjects=subject_access)
        return

    return conflicting, term, student, teacher


@user_passes_test(access_allowed)
def conflicting_edit_student(request, student_id, term_id):
    """Conflicting edit wait screen."""
    conflicts, term, student, teacher = do_conflict_check_student(
        request, student_id, term_id, check_only=True)

    url_extra = ''
    if is_reportcard_admin(request.user) and request.GET.get('teacher_id', False):
        url_extra = '?teacher_id=%d' % teacher.id

    return render(request, 'conflicting_edits.html', dict(
        config=config,
        student=student,
        term=term,
        request=request,
        conflicts=conflicts,
        url_extra=url_extra,
    ))


@user_passes_test(access_allowed)
def ping_student_edit(request, student_id, term_id):
    """Conflicting edit pinger."""
    conflicting, term, student, teacher = do_conflict_check_student(
        request, student_id, term_id, check_only=False)

    return JsonResponse({"ok": not conflicting, "conflicts": [
        p.conflict_str for p in conflicting]}
                        )


@user_passes_test(access_allowed)
def done_student_edit(request, student_id, term_id):
    """Conflicting edit clear."""
    do_conflict_check_student(request, student_id, term_id, clear=True)

    return JsonResponse({"ok": True})


@user_passes_test(access_allowed)
@transaction.atomic
def edit_student(request, student_id, term_id):
    """Edit a single student's full report card.

    Access is limited to subjects a teacher has access to.
    """
    teacher = request.user
    try:
        if is_reportcard_admin(request.user):
            if request.GET.get('teacher_id', False):
                teacher = User.objects.get(pk=int(request.GET['teacher_id']))
            else:
                teacher = None
    except Exception:
        pass

    url_extra = ''
    if is_reportcard_admin(request.user) and request.GET.get('teacher_id', False):
        url_extra = '?teacher_id=%d' % teacher.id

    student = get_object_or_404(Student, pk=student_id)
    term = get_object_or_404(ReportCardTerm, pk=term_id)

    template = term.get_template(grade=student.year)
    reportcard = ReportCard.objects.filter(student=student,
                                           term=term, template=template).first()

    if not term.is_open:
        messages.info(request, "Term is not open")
        return redirect(reverse('reportcard:view_term', args=[term.id]) + url_extra)

    if not reportcard:
        reportcard = ReportCard(student=student, term=term, template=template)
        try:
            reportcard.save()

        except IntegrityError:
            reportcard = ReportCard.objects.filter(student=student,
                                                   term=term, template=template).first()
            if not reportcard:
                raise Exception("Unable to create or find a report card")

    all_entries = template.get_or_create_all_entries(reportcard)
    past_entries = reportcard.get_past_terms(term)
    terms = past_entries.keys()
    element_to_past = {tno: {} for tno in terms}
    term_objects = reportcard.get_past_term_list(term)
    for tno in terms:
        element_to_past[tno] = {
            rce.most_specific_element: rce for rce in past_entries[tno]
        }

    inst_to_element = {instance: element for element, instance in all_entries.items()}

    section_access, subject_access, ok_ids, num_editable = access_for_template(
        template, teacher, term, student, all_entries)

    if not reportcard.editable(teacher):
        return redirect(
            reverse('reportcard:view_student', args=[student.id, term.id]) + url_extra)

    conflicting = ReportCardEditorTracking.conflicting_check(
        user=request.user, students=[student],
        subjects=[subject for subject in subject_access if subject_access[subject]],
        edit_type='student')
    if conflicting:
        messages.warning(request, "Edit prevented due to conflicting edits")
        return redirect(
            reverse('reportcard:conflicting_edit_student', args=[student.id, term.id]) + url_extra)

    formset_class = SubjectFormSet if not reportcard.term.interim else SubjectRadioFormSet
    valid = True
    if request.method == 'POST':
        formset = formset_class(request.POST, request.FILES,
                                queryset=ReportCardEntry.objects.filter(id__in=ok_ids))

        if formset.is_valid():
            for form in formset:
                form.instance.check_completed()
                form.changed_data.append('completed')

            with reversion.create_revision():
                reversion.set_comment(f"Save student {student.id} {student.fullname} by {request.user}")
                reversion.set_user(request.user)
                formset.save()
                completed = reportcard.set_completed(
                    teacher, all([form.instance.completed for form in formset]))
                reportcard.modified = datetime.datetime.now()
                reversion.add_to_revision(reportcard)
                reportcard.save()

            if completed:
                messages.success(request,
                                 'All fields have been filled in for %s.' %
                                 reportcard.student.fullname)

            if request.GET.get('autosave', 0):
                messages.warning(request,
                                 'Your work on "%s" was automatically saved.' %
                                 reportcard.student.fullname)
                return redirect(reverse('reportcard:view_term', args=[term.id]) + url_extra)

            if 'save' in request.POST or 'save_review' in request.POST:
                messages.info(request, 'Report card for %s saved' %
                              reportcard.student.fullname)
                ReportCardEditorTracking.conflicting_clear(
                    user=request.user, students=[student], subjects=subject_access)
                if 'save_review' in request.POST:
                    return redirect(
                        reverse('reportcard:view_student',
                                args=[student.id, term.id]) + url_extra)

                return redirect(reverse('reportcard:view_term', args=[term.id]) + url_extra)

            else:
                messages.info(request, 'Report card for %s saved' %
                              reportcard.student.fullname)
                return redirect(reverse('reportcard:edit_student',
                                args=[student.id, term.id]) + url_extra)

        else:
            valid = False
    else:
        formset = formset_class(queryset=ReportCardEntry.objects.filter(id__in=ok_ids))

    element_to_form = {inst_to_element[form.instance]: form for form in formset}
    instance_errors = {
        inst_to_element[formset[n].instance]:
            formset.errors[n] if len(formset.errors) > n else {}
        for n in range(0, len(formset))}

    subj_teacher = {}
    sect_teacher = {}

    for section in template.sections:
        teachers = Faculty.objects.filter(
            reportcardaccess__sections=section
        ).distinct()
        sect_teacher[section] = {
            "teachers": teachers.all(),
            "num": teachers.count(),
        }

        for subject in section.subjects:

            if subject not in element_to_form:
                continue

            teachers = Faculty.objects.filter(
                Q(reportcardaccess__sections=section) |
                Q(reportcardaccess__subjects__section=section)
            ).distinct()
            subj_teacher[subject] = {
                "teachers": teachers.all(),
                "num": teachers.count(),
            }

            if subject.graded:
                element_to_form[subject].fields['choice'].queryset = (
                    GradingSchemeLevelChoice.objects.filter(
                        gradingschemelevel__gradingscheme=section.gradingscheme).order_by(
                        'sortorder'))
                if section.second_gradingscheme:
                    element_to_form[subject].fields['second_choice'].queryset = (
                        GradingSchemeLevelChoice.objects.filter(
                            gradingschemelevel__gradingscheme=section.second_gradingscheme).order_by(
                            'sortorder'))

            for strand in subject.strands:
                if strand in element_to_form:
                    element_to_form[strand].fields['choice'].queryset = (
                        GradingSchemeLevelChoice.objects.filter(
                            gradingschemelevel__gradingscheme=section.gradingscheme).order_by(
                            'sortorder'))
                    if section.second_gradingscheme:
                        element_to_form[strand].fields['second_choice'].queryset = (
                            GradingSchemeLevelChoice.objects.filter(
                                gradingschemelevel__gradingscheme=section.second_gradingscheme).order_by(
                                'sortorder'))

    return render(request, 'edit_student.html', dict(
        config=config,
        reportcard=reportcard,
        superuser=is_reportcard_admin(request.user),
        student=student,
        term=term,
        template=template,
        formset=formset,
        element_to_form=element_to_form,
        request=request,
        section_access=section_access,
        subject_access=subject_access,
        instance_errors=instance_errors,
        valid=valid,
        completed=reportcard.is_completed(teacher),
        url_extra=url_extra,
        subj_teachers=subj_teacher,
        sect_teachers=sect_teacher,
        element_to_past=element_to_past,
        terms=terms,
        term_objects=term_objects,
        colsize='col-xs-3' if not term.interim else 'col-xs-7',
        maincolsize='col-xs-6' if not term.interim else 'col-xs-5',
        pushcolsize='col-xs-push-6' if not term.interim else 'col-xs-push-5',
        term_absences='%1.1f' % reportcard.student.days_absent(
            term=reportcard.term.term),
        year_absences='%1.1f' % reportcard.student.days_absent(
            school_year=term.school_year),
        term_lates='%1.1f' % reportcard.student.times_late(
            term=reportcard.term.term),
        year_lates='%1.1f' % reportcard.student.times_late(
            school_year=term.school_year),
    ))


def access_for_template(template, teacher, term, student, entries):
    """Check if access for template."""
    section_access = {}
    subject_access = {}
    ok_ids = []
    num_editable = 0
    for section in template.sections:
        section_access[section] = section.may_edit(teacher)
        if section_access[section]:
            ok_ids.append(entries[section].id)
            if section.comments_area:
                num_editable += 1

            teacher_subjects = term.subject_objs(teacher)
            for subject in section.subjects:
                subject_access[subject] = subject in teacher_subjects
                if subject_access[subject]:
                    if subject.graded or subject.comments_area:
                        num_editable += 1
                    ok_ids.append(entries[subject].id)
                    for strand in subject.strands:
                        if strand.graded:
                            num_editable += 1
                        ok_ids.append(entries[strand].id)

    return section_access, subject_access, ok_ids, num_editable


def do_conflict_check_subject(request, subject_id, grade_id, term_id,
                              check_only=False, clear=False):
    """Check for conflicting edits on subjects."""
    teacher = request.user
    try:
        if is_reportcard_admin(request.user):
            if request.GET.get('teacher_id', False):
                teacher = User.objects.get(pk=int(request.GET['teacher_id']))
            else:
                teacher = None
    except Exception:
        pass

    term = get_object_or_404(ReportCardTerm, pk=term_id)
    grade = get_object_or_404(GradeLevel, pk=grade_id)
    subject = get_object_or_404(ReportCardSubject, pk=subject_id)
    students = subject.students(grade=grade, teacher=teacher)

    # get/create report cards and find completed students
    ok_students = []
    for student in students:
        if not teacher:
            ok_students.append(student)
        else:
            ok_students.append(student)

    if not clear:
        conflicting = ReportCardEditorTracking.conflicting_check(
            user=request.user, students=ok_students, subjects=[subject],
            edit_type='subject')
    else:
        ReportCardEditorTracking.conflicting_clear(
            user=request.user, students=ok_students, subjects=[subject])
        return

    return conflicting, term, grade, subject, teacher


@user_passes_test(access_allowed)
def conflicting_edit_subject(request, subject_id, grade_id, term_id):
    """Conflicting edit wait screen."""
    conflicts, term, grade, subject, teacher = do_conflict_check_subject(
        request, subject_id, grade_id, term_id, check_only=True)

    url_extra = ''
    if is_reportcard_admin(request.user) and request.GET.get('teacher_id', False):
        url_extra = '?teacher_id=%d' % teacher.id

    return render(request, 'conflicting_edits_subject.html', dict(
        config=config,
        subject=subject,
        term=term,
        grade=grade,
        request=request,
        conflicts=conflicts,
        url_extra=url_extra,
    ))


@user_passes_test(access_allowed)
def ping_subject_edit(request, subject_id, grade_id, term_id):
    """Conflicting edit pinger."""
    conflicts, term, grade, subject, teacher = do_conflict_check_subject(
        request, subject_id, grade_id, term_id, check_only=False)

    return JsonResponse({"ok": not conflicts, "conflicts": [
        p.conflict_str for p in conflicts]}
                        )


@user_passes_test(access_allowed)
def done_subject_edit(request, subject_id, grade_id, term_id):
    """Conflicting edit clear."""
    do_conflict_check_subject(request, subject_id, grade_id, term_id, clear=True)

    return JsonResponse({"ok": True})


@user_passes_test(access_allowed)
@transaction.atomic
def edit_subject(request, subject_id, grade_id, term_id):
    """Edit all students for a subject (and it's strands) all at once."""
    teacher = request.user
    try:
        if is_reportcard_admin(request.user):
            if request.GET.get('teacher_id', False):
                teacher = User.objects.get(pk=int(request.GET['teacher_id']))
            else:
                teacher = None
    except Exception:
        pass

    url_extra = ''
    if is_reportcard_admin(request.user) and request.GET.get('teacher_id', False):
        url_extra = '?teacher_id=%d' % teacher.id

    term = get_object_or_404(ReportCardTerm, pk=term_id)
    grade = get_object_or_404(GradeLevel, pk=grade_id)
    subject = get_object_or_404(ReportCardSubject, pk=subject_id)

    if not term.is_open:
        messages.info(request, "Term is not open")
        return redirect(reverse('reportcard.view_term', args=[term.id]) + url_extra)

    students = subject.students(grade=grade)
    if len(students) == 0:
        messages.warning(request,
                         'No students found for subject %s' %
                         subject)
        return redirect(reverse('reportcard:view_term', args=[term.id]) + url_extra)

    template = term.get_template(grade=students[0].year)

    teachers = Faculty.objects.filter(
        Q(classes__students__year=grade) &
        (
                Q(reportcardaccess__subjects=subject) |
                Q(reportcardaccess__sections=subject.section)
        )).distinct()

    # get/create report cards and find completed students
    ok_students = []
    for student in students:
        reportcard = ReportCard.objects.filter(student=student,
                                               term=term, template=template).first()
        if not reportcard:
            reportcard = ReportCard(student=student, term=term, template=template)
            reportcard.save()
        template.get_or_create_all_entries(reportcard)
        reportcard.save()
        if not teacher:
            ok_students.append(student)
        elif reportcard.editable(teacher):
            ok_students.append(student)

    conflicting = ReportCardEditorTracking.conflicting_check(
        user=request.user, students=ok_students, subjects=[subject],
        edit_type='subject')
    if conflicting:
        messages.warning(request, "Edit prevented due to conflicting edits")
        return redirect(
            reverse('reportcard:conflicting_edit_subject',
                    args=[subject_id, grade_id, term_id]) + url_extra)

    valid = True
    if request.method == 'POST':
        formset = SubjectFormSet(request.POST, request.FILES)
        if formset.is_valid():

            seen_students = set()

            with reversion.create_revision():
                reversion.set_comment(f"Save subject {subject.id} {subject.name} by {request.user}")
                reversion.set_user(request.user)
                for form in formset:
                    form.instance.check_completed()
                    form.changed_data.append('completed')
                    seen_students.add(form.instance.reportcard.student)
                    form.instance.reportcard.modified = datetime.datetime.now()
                    reversion.add_to_revision(form.instance.reportcard)
                    form.instance.reportcard.save()
                formset.save()

            for student in seen_students:
                reportcard = ReportCard.objects.get(
                    student=student, term=term, template=template)
                completed = reportcard.calculate_completed(teacher)
                if completed:
                    messages.success(
                        request,
                        "Reportcard for %s is now complete" % student)

            extra = ''
            if is_reportcard_admin(request.user) and request.GET.get('teacher_id', False):
                extra = '?teacher_id=%d' % teacher.id

            if request.GET.get('autosave', 0):
                messages.warning(request,
                                 'Your work on "%s" was automatically saved.' %
                                 subject)
                return redirect(reverse('reportcard:view_term', args=[term.id]) + extra)

            if 'save_edit' not in request.POST:
                ReportCardEditorTracking.conflicting_clear(
                    user=request.user, students=ok_students, subjects=[subject])
                return redirect(reverse('reportcard:view_term', args=[term.id]) + extra)

        else:
            valid = False

    if valid:
        formset = SubjectFormSet(
            queryset=ReportCardEntry.objects.filter(subject=subject,
                                                    reportcard__term=term,
                                                    reportcard__student__in=ok_students)
        )

    for form in formset:
        section = form.instance.section
        form.fields['choice'].queryset = (
            GradingSchemeLevelChoice.objects.filter(
                gradingschemelevel__gradingscheme=section.gradingscheme).order_by(
                'sortorder'))
        if section.second_gradingscheme:
            form.fields['second_choice'].queryset = (
                GradingSchemeLevelChoice.objects.filter(
                    gradingschemelevel__gradingscheme=section.second_gradingscheme).order_by(
                    'sortorder'))

    instance_lookup = {form.instance: form for form in formset}
    instance_errors = {
        formset[n].instance:
            formset.errors[n] if n < len(formset.errors) else {}
        for n in range(0, len(formset))}

    student_map = {}
    student_errors = {}

    for instance, form in instance_lookup.items():
        student = instance.reportcard.student
        errors = instance_errors[instance]
        if student not in student_map:
            student_map[student] = {}
            student_errors[student] = {}
        if instance.strand and instance.strand not in student_map[student]:
            student_map[student][instance.strand] = form
            student_errors[student][instance.strand] = errors
        elif instance.subject and instance.subject not in student_map[student]:
            student_map[student][instance.subject] = form
            student_errors[student][instance.subject] = errors

    return render(request, 'edit_subject.html', dict(
        config=config,
        superuser=is_reportcard_admin(request.user),
        term=term,
        grade=grade,
        students=ok_students,
        request=request,
        subject=subject,
        formset=formset,
        student_map=student_map,
        scheme='percentile' if subject.section.gradingscheme.percentile else 'choice',
        student_errors=student_errors,
        valid=valid,
        url_extra=url_extra,
        teachers=teachers.all(),
        num_teachers=teachers.count(),
    ))
