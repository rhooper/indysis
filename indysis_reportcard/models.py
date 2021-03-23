# -*- coding: utf-8 -*-
"""Report card models."""

import locale
import logging
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List

import reversion
from ckeditor.fields import RichTextField
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.core import serializers
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Count, Q, F
from django.utils.translation import gettext as _
from django_extensions.db.models import TimeStampedModel

from sis.studentdb.models import Faculty, GradeLevel, SchoolYear, Student, StudentClass
from sis.studentdb.models import duplicate, Term
from sis.studentdb.thumbs import ImageWithThumbsField
from raven.contrib.django.raven_compat.models import client

LOCALE_LOCK = threading.Lock()

LOCK_TIMEOUT = getattr(settings, 'REPORTCARD_LOCK_TIMEOUT', 300)


@contextmanager
def setlocale(name):
    """Change locale."""
    with LOCALE_LOCK:
        saved = locale.setlocale(locale.LC_ALL)
        try:
            yield locale.setlocale(locale.LC_ALL, name)
        finally:
            locale.setlocale(locale.LC_ALL, saved)


RC_LANGUAGES = (('en', 'English'), ('fr', 'French'))

@reversion.register()
class GradingScheme(TimeStampedModel):
    """Grading schemes - Eg ABC, percentiles, or other schemes."""

    name = models.CharField(max_length=255, unique=True)
    percentile = models.BooleanField(default=False)
    range_heading = models.CharField(max_length=255, blank=True)
    descr_heading = models.CharField(max_length=255, blank=True)
    min_value = models.IntegerField(default=0,
                                    help_text="Minimum value for percentile mode")

    def __str__(self):
        """Unicode representation."""
        return self.name

    def copy_instance(self, request):
        """Make a copy of this scheme and all it's subordinate objects."""
        changes = (('name', self.name + " (copy)"),)
        new: GradingScheme = duplicate(self, changes)
        for level in self.gradingschemelevel_set.all():
            level_copy: GradingSchemeLevel = duplicate(level, ())
            for choice in level.gradingschemelevelchoice_set.all():
                choice_copy: GradingSchemeLevelChoice = duplicate(choice, ())
                level_copy.gradingschemelevelchoice_set.add(choice_copy)
            new.gradingschemelevel_set.add(level_copy)

        new.save()
        messages.success(request, 'Copy successful!')


@reversion.register()
class GradingSchemeLevel(TimeStampedModel):
    """Grading Scheme level."""

    sortorder = models.PositiveIntegerField(default=0)
    range = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    gradingscheme = models.ForeignKey(GradingScheme, on_delete=models.CASCADE)

    class Meta:
        ordering = ['sortorder']

    def __str__(self):
        """Unicode representation."""
        return self.range


@reversion.register()
class GradingSchemeLevelChoice(TimeStampedModel):
    """Grading Scheme level choice."""

    sortorder = models.PositiveIntegerField(default=0)
    choice = models.CharField(max_length=8)
    gradingschemelevel = models.ForeignKey(GradingSchemeLevel, on_delete=models.CASCADE)
    name = models.CharField(max_length=40, blank=True, null=True)
    description = models.CharField(max_length=80, blank=True, null=True)
    view_fullname = models.BooleanField(
        default=False,
        help_text="Use the name instead of the choice code when "
                  "reviewing entries.")

    class Meta:
        ordering = ['sortorder']

    @property
    def view_choice(self):
        """View mode choice."""
        if self.view_fullname:
            return ' - '.join(filter(None, (self.name_en, self.name_fr)))
        return self.choice

    def __str__(self):
        """Unicode representation."""
        if self.view_fullname:
            return ' / '.join(filter(None, (self.name_en, self.name_fr)))
        if self.name:
            if self.name == self.choice:
                return self.choice
            if self.name_en == self.name_fr == self.choice:
                return self.name_en
            return '{}: {}'.format(
                self.choice,
                ' / '.join(filter(None, (self.name_en, self.name_fr))))
        return self.choice

    def get_all_choices(self):
        """All choices."""
        gs = self.gradingschemelevel.gradingscheme
        return self.__class__.objects.filter(
            gradingschemelevel__gradingscheme=gs).order_by('sortorder')


@reversion.register()
class ReportCardSharedTemplate(TimeStampedModel):
    """Defines content templates that can be shared between templates."""

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    coverpage_template = models.TextField(blank=True, null=True)
    header_template = models.TextField(blank=True, null=True)
    footer_template = models.TextField(blank=True, null=True)
    body_template = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Shared template"

    def __str__(self):
        """Unicode representation."""
        return self.name

    def __repr__(self):
        """String representation."""
        return f'<ReportCardTemplate: {self.__str__()}>'


@reversion.register()
class ReportCardTemplate(TimeStampedModel):
    """Defines a specific report card template."""

    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True)
    grades = models.ManyToManyField(GradeLevel, blank=True)
    interim = models.BooleanField(default=False)

    coverpage_template = models.TextField(blank=True, null=True)
    header_template = models.TextField(blank=True, null=True)
    footer_template = models.TextField(blank=True, null=True)
    body_template = models.TextField(blank=True, null=True)

    shared_template = models.ForeignKey(ReportCardSharedTemplate, null=True, blank=True)

    class Meta:
        verbose_name = "Template"

    def get_template(self, name):
        template = getattr(self, name)
        if self.shared_template and template in (None, ''):
            return getattr(self.shared_template, name)
        return template

    def copy_instance(self, request):
        """Make a copy of this template and all it's subordinate objects."""
        changes = ()
        new = duplicate(self, changes)
        new.name += " (copy)"
        for section in self.reportcardsection_set.all():
            section_copy = duplicate(section, changes)
            section_copy.name = section.name
            for subject in section.reportcardsubject_set.all():
                subject_copy = duplicate(subject, changes)
                subject_copy.name = subject.name
                for strand in subject.reportcardstrand_set.all():
                    strand_copy = duplicate(strand, changes)
                    subject_copy.reportcardstrand_set.add(strand_copy)
                section_copy.reportcardsubject_set.add(subject_copy)
            new.reportcardsection_set.add(section_copy)

        new.save()
        messages.success(request, 'Copy successful!')

    def __str__(self):
        """Unicode representation."""
        return self.name

    def __repr__(self):
        """String representation."""
        return '<ReportCardTemplate: %s>' % str(self).encode('utf-8')

    @property
    def sections(self):
        """Sections."""
        return self.reportcardsection_set.order_by('sortorder')

    @transaction.atomic
    def get_or_create_all_entries(self, reportcard):
        """Get or create all report card entries."""
        fields = {}

        for section in self.sections:
            fields[section] = section.get_entry(reportcard)
            for subject in section.subjects:
                fields[subject] = subject.get_entry(reportcard)
                for strand in subject.strands:
                    fields[strand] = strand.get_entry(reportcard)

        return fields

    def get_grading_schemes(self):
        """Return a unique list of graing schemes in use in this template."""
        seen = set()
        schemes = GradingScheme.objects.filter(
            reportcardsection__template=self).order_by('reportcardsection__sortorder').all()
        ok = []
        for item in schemes:
            if item.id not in seen:
                seen.add(item.id)
                ok.append(item)

        return ok


@reversion.register()
class ReportCardSection(TimeStampedModel):
    """A group of subjects & strands."""

    sortorder = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=255)
    heading = models.CharField(max_length=255, blank=True)
    text = models.TextField(max_length=255, blank=True)
    gradingscheme = models.ForeignKey(GradingScheme, on_delete=models.CASCADE)
    gradingscheme_label = models.CharField(max_length=20, default="", blank=True)
    second_gradingscheme = models.ForeignKey(GradingScheme, on_delete=models.CASCADE, null=True, blank=True,
                                             related_name='second_gradingscheme')
    second_gradingscheme_label = models.CharField(max_length=20, default="", blank=True)
    template = models.ForeignKey(ReportCardTemplate, on_delete=models.CASCADE)
    comments_area = models.BooleanField(default=False)
    comments_heading = models.TextField(blank=True)
    field_code = models.CharField(max_length=20, blank=True,
                                  help_text='Prefix for fields in Document template')
    page_break_after = models.BooleanField(default=False)

    class Meta:
        ordering = ['template__name', 'sortorder']
        verbose_name = "Template section"

    def __repr__(self):
        """String representaiton."""
        return f"<ReportCardSection: id={self.id} {self.name}>"

    def __str__(self):
        """Unicode representation."""
        return f"<ReportCardSection: id={self.id} {self.name}>"

    @property
    def subjects(self):
        """Sorted list of subjects."""
        return self.reportcardsubject_set.order_by('sortorder')

    def get_entry(self, reportcard):
        """Get a reportcard entry for this section."""
        return get_or_create_reportcard_entry(
            reportcard=reportcard,
            section=self,
            subject=None,
            strand=None)

    def may_edit(self, teacher):
        """Check if teacher can edit this term/student."""
        if not teacher:
            return True

        return ReportCardAccess.objects.filter(
            Q(teachers=teacher) &
            (
                    Q(sections=self) |
                    Q(subjects__section=self)
            )).exists()

    def subject_dict(self):
        return {subject.name.replace(" ", "_").lower().strip(): subject for subject in self.subjects}


@reversion.register()
class ReportCardSubject(TimeStampedModel):
    """A subject."""

    sortorder = models.PositiveIntegerField(default=0)
    name = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)
    section = models.ForeignKey(ReportCardSection, on_delete=models.CASCADE)
    comments_area = models.BooleanField(default=True)
    comments_heading = models.TextField(blank=True, default="")
    graded = models.BooleanField(default=False)
    field_code = models.CharField(max_length=20, blank=True,
                                  help_text='Prefix for fields in Document template')
    rc_language = models.CharField(max_length=8, choices=RC_LANGUAGES, default='en')
    page_break_after = models.BooleanField(default=False)

    class Meta:
        ordering = ['sortorder']
        verbose_name = "Template subject"

    def __str__(self):
        """Unicode representation."""
        return f"{self.section.template.name}: {self.section.name}: {self.name}"

    def __repr__(self):
        """String representation."""
        return f"<ReportCardSubject: id={self.id} {self.__str__()}>"

    @property
    def rc_label(self):
        """Label for printed report cards."""
        return getattr(self, 'name_' + self.rc_language)

    @property
    def strands(self):
        """Sorted list of strands for subject."""
        return self.reportcardstrand_set.order_by('sortorder')

    def get_entry(self, reportcard):
        """Get report card entry for strand."""
        return get_or_create_reportcard_entry(
            reportcard=reportcard,
            section=self.section,
            subject=self,
            strand=None)

    def students(self, grade=None, teacher=None):
        """List of students that have this subject."""

        if grade:
            has_grade = self.section.template.grades.filter(id=grade.id).count()
            if not has_grade:
                return []
            students = Student.objects.filter(year=grade, is_active=True)
        else:
            students = Student.objects.filter(is_active=True)

        if teacher:
            return students.filter(
                Q(classes__reportcardaccess__teachers=teacher) &
                (
                        Q(classes__reportcardaccess__subjects=self) |
                        Q(classes__reportcardaccess__sections=self.section)
                )
            ).distinct()

        return students.order_by('last_name', 'first_name')

    def may_edit(self, teacher, student):
        """Whether or not the teacher can edit."""
        return (
                self.teacher_teaches(teacher) and
                student in self.students(grade=student.year)
        )

    def teacher_teaches(self, teacher):
        """Whether or not a teacher teaches this subject."""
        return ReportCardAccess.objects.filter(
            Q(teachers=teacher) &
            (
                    Q(subjects=self) |
                    Q(sections__subject=self)
            ))

    def teachers(self, student=None, school_year=None):
        """List of teachers assigned to this subject (and student)."""
        if not school_year:
            school_year = SchoolYear.get_current_year()
        if student:
            result = Faculty.objects.filter(
                Q(is_active=True) &
                Q(classes__students=student) &
                Q(reportcardaccess__student_classes__students=student) &
                Q(reportcardaccess__student_classes__school_year=school_year) &
                Q(reportcardaccess__teachers__in=F('reportcardaccess__student_classes__teachers')) &
                (
                        Q(reportcardaccess__sections=self.section) |
                        Q(reportcardaccess__subjects=self))).distinct().all()
            return result
        return Faculty.objects.filter(
                Q(is_active=True) &
                Q(classes__school_year=school_year) &
                Q(reportcardaccess__student_classes__school_year=school_year) & (
                Q(reportcardaccess__sections=self.section) |
                Q(reportcardaccess__subjects=self)
            )
        ).distinct().all()

    def entry_form_label(self):
        parts = []
        if self.name_en:
            parts.append(self.name_en)
        if self.name_fr and self.name_fr != self.name_en:
            parts.append(self.name_fr)
        return ' / '.join(parts)

    def entry_form_text(self):
        parts = []
        if self.text_en:
            parts.append(self.text_en)
        if self.text_fr and self.text_fr != self.text_en:
            parts.append(self.text_fr)
        return ' / '.join(parts)

    def teachers_string(self, student=None):
        teachers = self.teachers(student)
        return ' / '.join([teacher.fullname_nocomma for teacher in teachers])


@reversion.register()
class ReportCardStrand(TimeStampedModel):
    """A strand.  The smallest unit of measurement/comments."""

    sortorder = models.PositiveIntegerField(default=0)
    text = models.TextField(blank=True)
    subject = models.ForeignKey(ReportCardSubject, on_delete=models.CASCADE)
    graded = models.BooleanField(default=True)
    field_code = models.CharField(max_length=20, blank=True,
                                  help_text='Prefix for fields in Document template')
    rc_language = models.CharField(max_length=8, choices=RC_LANGUAGES, default='en')

    class Meta:
        ordering = ['sortorder']
        verbose_name = "Template strand"

    @property
    def rc_label(self):
        """Label for printed report cards."""
        return getattr(self, 'text_' + self.rc_language)

    def __str__(self):
        """Unicode representation."""
        return self.text

    def __repr__(self):
        """String representation."""
        return f"<ReportCardStrand: id={self.id} {self.__str__()}>"

    def get_entry(self, reportcard):
        """Get report card entry for strand."""
        return get_or_create_reportcard_entry(
            reportcard=reportcard,
            section=self.subject.section,
            subject=self.subject,
            strand=self)

    def entry_form_label(self):
        parts = []
        if self.text_en:
            parts.append(self.text_en)
        if self.text_fr and self.text_fr != self.text_en:
            parts.append(self.text_fr)
        return ' / '.join(parts)

    @property
    def comments_area(self):
        return False


@reversion.register()
class ReportCardYearGradeContent(TimeStampedModel):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE)
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE)
    content = RichTextField(config_name='reportcard')

    class Meta:
        verbose_name_plural = "Static report card content"
        verbose_name = "Static report card content"

    def __str__(self):
        return "<StaticContent id=%d %s %s>" % (self.id, self.school_year, self.grade_level)

    def copy_instance(self, request):
        """Make a copy of this."""

        school_year = SchoolYear.objects.filter(active_year=True).first()
        max_year = GradeLevel.objects.order_by('-id').first()
        max_used = GradeLevel.objects.order_by('-id').filter(
            reportcardyeargradecontent__school_year=school_year).distinct().first()
        max_used_id = 0
        if max_used:
            max_used_id = max_used.id
        try:

            if max_used_id == max_year.id:
                raise Exception("An entry exists for %s already" % max_year)

            new = self.__class__()
            new.school_year = school_year
            new.content = self.content
            new.grade_level = GradeLevel.objects.get(pk=max_used_id + 1)
            new.grade_level_id = new.grade_level.id
            new.save()
            messages.success(request, 'Created a content entry for %s.' % new.grade_level)
        except Exception as e:
            messages.error(request, "Failed to make copy: %s" % e)


@reversion.register()
class ReportCardTerm(TimeStampedModel):
    """A report card term.  Each school year will have multiple of these."""

    school_year = models.ForeignKey(SchoolYear, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="", help_text="Title for report card")
    is_open = models.BooleanField(default=True)
    interim = models.BooleanField(default=False)
    name = models.CharField(null=False, blank=True, default='', max_length=80,
                            help_text="Name as shown on report cards")

    submission_deadline = models.DateTimeField(blank=True, null=True,
                                               verbose_name='Due to Administration')
    review_deadline = models.DateTimeField(blank=True, null=True,
                                           verbose_name='Revision Deadline')
    delivery_date = models.DateTimeField(blank=True, null=True)
    shortcode = models.CharField(
        max_length=20, blank=True,
        help_text='Short code for fields in Document template (eg t1)')
    number = models.PositiveIntegerField(default=1)
    displabel = models.CharField(max_length=20, default="1",
                                 help_text="Value to show on data entry")
    templates = models.ManyToManyField(ReportCardTemplate, blank=True)

    email_subject_template = models.TextField(
        default="{{ rc.term.name_en }} Report Card / {{ rc.term.name_fr }}"
                " Bulletin: {{ rc.student.longname }}")
    email_body_template = models.TextField(
        default="The report card for {{ rc.student.longname }} is attached.")

    class Meta:
        verbose_name = "Term"

    def __str__(self):
        """Unicode representation."""
        if self.name:
            return self.name + " " + str(self.school_year)
        if self.interim:
            return ' '.join(
                [self.name, '(Interim)', str(self.term)])
        else:
            return ' '.join([self.name, str(self.term)])

    def __repr__(self):
        return f'<ReportCardTerm id={self.id} {self.__str__()}>'

    def get_template(self, grade):
        """Get a template for this term for a given grade."""
        return self.templates.filter(
            grades=grade, interim=self.interim).get()

    @property
    def status(self):
        """Open or Closed based on is_open."""
        return "Open" if self.is_open else "Closed"

    def subjects(self, teacher=None):
        """Get a list of subjects for this report card term."""

        if teacher:
            faculty = Faculty.objects.get(pk=teacher.id)
            access = ReportCardSubject.objects.filter(
                (
                        Q(reportcardaccess__teachers=faculty) |
                        Q(section__reportcardaccess__teachers=faculty)
                ) &
                Q(section__template__reportcardterm=self) &
                Q(section__template__grades__student__is_active=True)
            )

            return access.values(
                'id', 'name', 'section__reportcardaccess__student_classes__shortname',
                'section__reportcardaccess__student_classes__id',
                'reportcardaccess__student_classes__shortname',
                'reportcardaccess__student_classes__id',
            ).annotate(
                num_students=Count(
                    'section__reportcardaccess__student_classes__students', distinct=True),
                num_students_subject=Count(
                    'reportcardaccess__student_classes__students', distinct=True)
            ).order_by(
                'section__reportcardaccess__student_classes__id',
                'reportcardaccess__student_classes__id',
                'sortorder')

        access = ReportCardSubject.objects.filter(
            Q(section__template__reportcardterm=self) &
            Q(section__template__grades__student__is_active=True)
        )

        return access.values(
            'id', 'name', 'section__reportcardaccess__student_classes__shortname',
            'section__reportcardaccess__student_classes__id',
            'reportcardaccess__student_classes__shortname',
            'reportcardaccess__student_classes__id',
        ).annotate(
            num_students=Count(
                'section__reportcardaccess__student_classes__students', distinct=True),
            num_students_subject=Count(
                'reportcardaccess__student_classes__students', distinct=True)
        ).order_by(
            'section__reportcardaccess__student_classes__id',
            'reportcardaccess__student_classes__id',
            'sortorder')

    def subject_objs(self, teacher=None):
        """Return subject objects for the report card term."""

        if teacher:
            return ReportCardSubject.objects.filter(
                (
                        Q(section__reportcardaccess__teachers=teacher) |
                        Q(reportcardaccess__teachers=teacher)
                ) &
                Q(section__template__reportcardterm=self)
            )
        else:
            return ReportCardSubject.objects.filter(
                section__template__reportcardterm=self)

    def copy_instance(self, request):
        """Make a copy of this object."""
        changes = ()
        new = duplicate(self, changes)
        new.is_open = False
        new.name += " (copy)"
        new.save()
        messages.success(request, 'Copy successful!')


@reversion.register()
class ReportCard(TimeStampedModel):
    """Report cards are one per student per term (per schoolyear)."""

    student = models.ForeignKey(Student, on_delete=models.PROTECT)
    term = models.ForeignKey(ReportCardTerm, on_delete=models.PROTECT)
    template = models.ForeignKey(ReportCardTemplate, on_delete=models.PROTECT)
    emailed = models.BooleanField(default=False)
    grade_level = models.ForeignKey(GradeLevel, default=1)

    class Meta:
        """
        Metadata.

        Report cards are one per term per student.
        """

        unique_together = ('student', 'term', 'template')
        verbose_name = "Report card"

    def __repr__(self):
        """String representation."""
        return f'<ReportCard: id={self.id} {self.__str__()}>'

    def __str__(self):
        """Unicode representation."""
        return ('ReportCard for {term} '
                '{student.fullname}').format(
            term=self.term,
            student=self.student
        )

    def get_submission(self, teacher):
        """Get report card submission information."""
        if teacher:
            sub, created = ReportCardSubmission.objects.get_or_create(
                reportcard=self,
                teacher=Faculty.objects.get(pk=teacher.id))
            if created:
                sub.save()
            return sub
        return None

    def set_completed(self, teacher, completed):
        """Set completed flag on report card."""
        if not teacher:
            return False
        sub = self.get_submission(teacher)
        sub.completed = completed
        sub.save()
        return completed

    def calculate_completed(self, teacher):
        """Calculate completed status."""

        # TODO this doesn't behave the same as the form save based completion metrics
        # TODO this will probably not calculate accurately with the classes concept
        subjects = [x['id'] for x in self.term.subjects(teacher).all()]
        hr_sections = ReportCardSection.objects.filter(template__grades__student__classes__teachers=teacher).distinct()

        entries = self.reportcardentry_set.filter(subject_id__in=subjects).count()
        filled = self.reportcardentry_set.filter(
            subject_id__in=subjects, completed=True).count()
        if hr_sections:
            entries += self.reportcardentry_set.filter(section__in=hr_sections).count()
            filled += self.reportcardentry_set.filter(
                section__in=hr_sections, completed=True).count()

        if entries == filled:
            self.set_completed(teacher, True)
            return True
        return False

    def is_completed(self, teacher):
        """Check if completed (and recompute)."""
        if teacher:
            return self.get_submission(teacher).completed

        subs = self.reportcardsubmission_set.all()
        if not len(subs):
            return False
        return all(x.completed for x in subs)

    def editable(self, teacher):
        """Check if report card may be edited."""
        if not self.term.is_open:
            return False
        return True

    def get_past_terms(self, term):
        """Gather prior term report card entries.

        If the term is interim, only include other interim terms.
        """
        terms = self.get_past_term_list(term)

        ret = {}

        for t in terms:
            rc = ReportCard.objects.filter(
                student=self.student,
                term=t,
            ).first()
            ret[t.number] = ReportCardEntry.objects.filter(
                reportcard=rc
            )
        return ret

    def get_past_term_list(self, term):
        """Get a list of prior terms.

        If the term is interim, only include other interim terms.
        """
        return ReportCardTerm.objects.filter(
            school_year=term.school_year,
            number__lt=term.number,
            interim=term.interim,
        ).order_by('number')

    def get_past_reportcards(self, term, include_cur=False):
        """Get past report cards."""
        filters = dict(school_year=term.school_year)
        if include_cur:
            filters['number__lte'] = term.number
        else:
            filters['number__lt'] = term.number
        terms = ReportCardTerm.objects.filter(**filters).order_by('number')

        ret = []

        for t in terms:
            rc = ReportCard.objects.filter(
                student=self.student,
                term=t,
            ).first()
            ret.append(rc)
        return ret

    @property
    def tpl(self):
        """Return Template."""
        return self.template

    @property
    def data(self):
        """Get report card data as a dictionary."""
        rc = self

        """Make Report Card Data."""
        with setlocale('fr_CA.UTF-8'):
            date_fr = rc.term.delivery_date.strftime("%-d %B %Y") if rc.term.delivery_date else ''

        hrt = rc.student.homeroom_teacher
        if hrt:
            homeroom_teacher = hrt.teacher.fullname_nocomma
        else:
            homeroom_teacher = ""

        basics = {"Year": rc.term.school_year.name,
                  "TermNo": rc.term.number,
                  "StudentName": rc.student.longname,
                  "TermAbsences": '%1.1f' % rc.student.days_absent(term=rc.term.term),
                  "YearAbsences": '%1.1f' % rc.student.days_absent(school_year=rc.term.school_year),
                  "TermLates": '%1d' % rc.student.times_late(term=rc.term.term),
                  "YearLates": '%1d' % rc.student.times_late(school_year=rc.term.school_year),
                  "GradeEN": rc.student.year.name or "",
                  "GradeFR": rc.student.year.name_fr or "",
                  "GradeCodeEN": rc.student.year.shortname or "",
                  "GradeCodeFR": rc.student.year.shortname_fr or "",
                  "DeliveryDateEN": rc.term.delivery_date.strftime("%B %-d, %Y") if rc.term.delivery_date else '',
                  "DeliveryDateNN": rc.term.delivery_date.strftime("%d-%m-%Y") if rc.term.delivery_date else '',
                  "DeliveryDateFR": date_fr or "",
                  "StudentDOB": (rc.student.bday.strftime("%d-%m-%Y")
                                 if rc.student.bday else ""),
                  "Addr1": rc.student.street or "",
                  "Addr2": ', '.join([rc.student.city or "", rc.student.state or ""]),
                  "Addr3": rc.student.zip or "",
                  "HomeRoomTeacher": homeroom_teacher,
                  "Draft": 'DRAFT / PRÉLIMINAIRE' if rc.term.is_open else '',
                  'rc': self}

        return basics

    @property
    def filename(self):
        """Generate a filename string."""
        path = [self.student.year.name, "-", self.student.fullname]
        if self.term.is_open:
            path += ["(Draft)"]
        return ' '.join(path) + ".pdf"

    def change_template(self, new_template):
        """Change from one template to another.

        Iterates report card entries and finds equivalents in the new one.
        If no equivalent is found, the entry is deleted, with the output printed to JSON.
        """
        for entry in self.reportcardentry_set.all():
            if entry.strand:

                new = ReportCardStrand.objects.filter(
                    subject__section__template=new_template,
                    subject__name_en=entry.subject.name_en,
                    subject__name_fr=entry.subject.name_fr,
                    subject__section__name=entry.section.name,
                    text_en=entry.strand.text_en,
                    text_fr=entry.strand.text_fr).first()
                if not new:
                    print("Unmatched strand %s - deleted" % entry.strand)
                    print(serializers.serialize('json', [entry]))
                    entry.delete()
                else:
                    print("Update strand %s to %s" % (entry.strand, new))
                    entry.strand = new
                    entry.subject = new.subject
                    entry.section = new.subject.section
                    entry.save()

            elif entry.subject:

                new = ReportCardSubject.objects.filter(
                    section__template=new_template,
                    section__name=entry.section.name,
                    name_en=entry.subject.name_en,
                    name_fr=entry.subject.name_fr).first()
                if not new:
                    print("Unmatched subject %s - deleted" % entry.subject)
                    print(serializers.serialize('json', [entry]))
                    entry.delete()
                else:
                    print("Update subject %s to %s" % (entry.subject, new))
                    entry.subject = new
                    entry.section = new.section
                    entry.save()

            elif entry.section:
                new = ReportCardSection.objects.filter(
                    template=new_template,
                    name=entry.section.name).first()
                if not new:
                    print("Unmatched section - deleted")
                    print(serializers.serialize('json', [entry]))
                    entry.delete()
                else:
                    print("Update section %s to %s" % (entry.section, new))
                    entry.section = new
                    entry.save()

            else:
                # Huh
                print("Unmatched entry (not strand, subject, or section) - deleted")
                print(serializers.serialize('json', [entry]))
                entry.delete()

        self.template = new_template
        self.save()


@reversion.register()
class ReportCardSubmission(TimeStampedModel):
    """Track teacher completions."""

    class Meta:
        """Metadata."""

        unique_together = ('teacher', 'reportcard')
        verbose_name = "Report card submission"

    teacher = models.ForeignKey(Faculty, blank=True, null=True, on_delete=models.SET_NULL)
    completed = models.BooleanField(default=False)
    reportcard = models.ForeignKey(ReportCard, on_delete=models.PROTECT)


@reversion.register()
class ReportCardEntry(TimeStampedModel):
    """Report Card entries.

    These are where student grades and comments are stored.
    """

    class Meta:
        """Metadata."""

        unique_together = ('reportcard', 'section', 'subject', 'strand')
        verbose_name = "Report card mark data"

    reportcard = models.ForeignKey(ReportCard, on_delete=models.CASCADE)
    section = models.ForeignKey(ReportCardSection, null=True, blank=True, on_delete=models.CASCADE)
    subject = models.ForeignKey(ReportCardSubject, null=True, blank=True, on_delete=models.CASCADE)
    strand = models.ForeignKey(ReportCardStrand, null=True, blank=True, on_delete=models.CASCADE)
    percentile = models.PositiveIntegerField(validators=[
        MaxValueValidator(100),
        MinValueValidator(0)
    ], blank=True, null=True, verbose_name='Mark')
    choice = models.ForeignKey(GradingSchemeLevelChoice, null=True, blank=True,
                               verbose_name='Mark', on_delete=models.CASCADE)
    second_percentile = models.PositiveIntegerField(validators=[
        MaxValueValidator(100),
        MinValueValidator(0)
    ], blank=True, null=True, verbose_name='2nd Mark')
    second_choice = models.ForeignKey(GradingSchemeLevelChoice, null=True, blank=True,
                                      verbose_name='2nd Mark', on_delete=models.CASCADE,
                                      related_name='second_choice')
    comment = models.TextField(null=True, blank=True)
    completed = models.BooleanField(default=False)

    def clean(self):
        """Django clean method.  Performs validation on save."""
        if self.section.gradingscheme.percentile and self.section.gradingscheme.min_value:
            if self.percentile and self.percentile < self.section.gradingscheme.min_value:
                raise ValidationError(_("Minimum percentile is %d, select a choice instead") % self.section.gradingscheme.min_value)
        if self.percentile and self.choice:
            raise ValidationError(
                _("Percentage cannot be combined with choice '%s'") % self.choice.choice)

        if self.section.second_gradingscheme and \
                self.section.second_gradingscheme.percentile and self.section.second_gradingscheme.min_value:
            if self.second_percentile and self.second_percentile < self.section.second_gradingscheme.min_value:
                raise ValidationError(_("Minimum percentile is %d, select a choice instead") % self.section.second_gradingscheme.min_value)
        if self.second_percentile and self.second_choice:
            raise ValidationError(
                _("Percentage cannot be combined with choice '%s'") % self.choice.choice)

    def check_completed(self):
        """Check if an entry is completed."""
        completed = []
        if self.strand:
            if self.section.gradingscheme.percentile:
                completed.append(self.choice is not None or (
                        self.percentile is not None and self.percentile != ""))
            else:
                completed.append(self.choice is not None)
            if self.section.second_gradingscheme:
                if self.section.gradingscheme.percentile:
                    completed.append(self.second_choice is not None or (
                            self.second_percentile is not None and self.second_percentile != ""))
                else:
                    completed.append(self.second_choice is not None)
        elif self.subject:
            if self.subject.comments_area:
                completed.append(self.comment and self.comment.strip(" \t\n\r") != "")
            if self.subject.graded:
                if self.section.gradingscheme.percentile:
                    completed.append(self.choice is not None or (
                            self.percentile is not None and self.percentile != ""))
                else:
                    completed.append(self.choice is not None)
            if self.section.second_gradingscheme:
                if self.subject.graded:
                    if self.section.gradingscheme.percentile:
                        completed.append(self.second_choice is not None or (
                                self.second_percentile is not None and self.second_percentile != ""))
                    else:
                        completed.append(self.second_choice is not None)

        else:
            if self.section.comments_area:
                completed.append(self.comment and self.comment.strip(" \t\n\r") != "")
        self.completed = len(completed) == 0 or all(completed)
        return self.completed

    def __str__(self):
        """Unicode representation."""
        return ('<ReportCardEntry: id={id} {rc} {sect} {subj} {str} {comp} = ch={ch} pc={pc} ch2={ch2} pc2={pc2}>'.format(
            id=self.id,
            rc=str(self.reportcard),
            sect=str(self.section),
            subj=str(self.subject) or '',
            str=str(self.strand) or '',
            comp='[completed]' if self.completed else '',
            ch=self.choice,
            pc=self.percentile,
            ch2=self.second_choice,
            pc2=self.second_percentile,
        ))

    def get_teachers(self) -> List[Faculty]:
        """Teacher objects for the report card entry."""
        access_set = set()
        for item in self.section.reportcardaccess_set.all():
            for teacher in item.teachers.all():
                access_set.add(teacher)
        if self.subject:
            for item in self.subject.reportcardaccess_set.all():
                for teacher in item.teachers.all():
                    access_set.add(teacher)

        return list(access_set)

    @property
    def most_specific_element(self):
        """Return either the strand, subject or section for the entry."""
        if self.strand:
            return self.strand
        elif self.subject:
            return self.subject
        return self.section

    @property
    def teacher_name(self):
        """Return string of teachers for this entry."""
        if self.subject:
            teachers = self.get_teachers()
            if teachers:
                return ', '.join([teacher.fullname_nocomma for teacher
                                  in teachers.distinct().order_by(
                        'last_name').all()])
            else:
                return ''

    def unique_key(self):
        """A unique string identifying this entry.
        This is to help with the fact that NULLs may not be able to be used to prevent duplicates (eg postgresql).
        """
        return '-'.join([f"{i}" if i else "" for i in (
            self.reportcard_id, self.section_id, self.subject_id, self.strand_id)])

    def dump(self):
        details = [
            f"ID:      {self.id}",
            f"Created: {self.created}",
            f"Mod:     {self.modified}",
            f"Term:    {self.reportcard.term.name}",
            f"Student: {self.reportcard.student.fullname}",
            f"Section: {self.section.name}",
        ]
        if self.subject:
            details.append(f"Subject: {self.subject.name}")
        if self.strand:
            details.append(f"Strand:  {self.strand.text}")
        if self.choice:
            details.append(f"Mark:    {self.choice.name}")
        if self.percentile is not None:
            details.append(f"Percent: {self.percentile}")
        if self.second_choice:
            details.append(f"2nd Mrk: {self.second_choice.name}")
        if self.second_percentile is not None:
            details.append(f"2nd Pct: {self.second_percentile}")
        if self.comment is not None:
            details.append(f"Comment: {self.comment}")
        return "\n".join(details) + "\n"


@reversion.register()
class ReportCardAccess(TimeStampedModel):
    """Report card subject and/or section access mapping."""

    description = models.CharField(max_length=80, default='')
    student_classes = models.ManyToManyField(StudentClass, limit_choices_to={'school_year__active_year': True},
                                             blank=True)
    teachers = models.ManyToManyField(Faculty, limit_choices_to={'is_active': True}, blank=True)
    subjects = models.ManyToManyField(ReportCardSubject,
                                      help_text='Choose one of Subject or Section', blank=True)
    sections = models.ManyToManyField(ReportCardSection,
                                      help_text='Choose one of Subject or Section', blank=True)

    class Meta:
        verbose_name = "Access rule"

    def copy_instance(self, request):
        """Make a copy of this object."""
        changes = (('description', self.description + " (copy)"), )
        new = duplicate(self, changes)
        new.save()
        messages.success(request, 'Copy successful!')

    def __str__(self):
        return f"<{self.__class__.__name__} id={self.id} \"{self.description}\">"


@reversion.register()
class ReportCardTemplateImage(TimeStampedModel):
    name = models.CharField(max_length=40,
                            help_text="Image name for report card template.")
    image = ImageWithThumbsField(upload_to="reportcard", blank=False, null=False,
                                 sizes=((200, 200), (300, 300)),
                                 help_text="Image assets for report cards.")

    class Meta:
        verbose_name = "Template image"


class ReportCardEditorTracking(TimeStampedModel):
    """Tracking of active editing."""

    class Meta:
        """Metadata."""

        unique_together = ('user', 'student', 'subject')

    user = models.ForeignKey(User, blank=True, null=True, db_index=True,
                             related_name='editor_locks', on_delete=models.CASCADE)
    student = models.ForeignKey(Student, blank=True, null=True, db_index=True, on_delete=models.CASCADE)
    subject = models.ForeignKey(ReportCardSubject, blank=True, null=True, db_index=True, on_delete=models.CASCADE)
    edit_type = models.CharField(max_length=64, null=True, blank=True)
    last_ping = models.DateTimeField(auto_now_add=True)

    @classmethod
    def conflicting_check(cls, user, subjects, students, edit_type=None, check_only=False):
        """Check for conflicting edits."""
        ping_since = datetime.now() - timedelta(seconds=LOCK_TIMEOUT)

        # Obtain list of locks for other faculty
        locks = cls.objects.filter(
            subject__in=subjects,
            student__in=students,
            last_ping__gte=ping_since).exclude(user=user).all()

        if locks or check_only:
            return locks

        # Set/Update locks
        for subject in subjects:
            for student in students:
                obj, created = cls.objects.get_or_create(
                    user=user,
                    student=student,
                    subject=subject)
                obj.last_ping = datetime.now()
                obj.edit_type = edit_type
                obj.save()

        return locks

    @classmethod
    def conflicting_clear(cls, user, subjects, students):
        """Clear conflicts."""
        for s in students:
            cls.objects.filter(
                user=user,
                student=s,
                subject__in=subjects,
            ).delete()

    def __repr__(self):
        """String representation."""
        return '<ReportCardEditorTracking: %s>' % self.conflict_str.encode('utf-8')

    @property
    def conflict_str(self):
        """Compute a descriptive string for conflict object."""
        age = datetime.now() - self.last_ping
        seconds = age.total_seconds()
        if seconds > 60:
            minutes = int(seconds / 60)
            timestr = '- last seen %d minutes ago' % minutes
        else:
            timestr = ''

        return "%s is editing %s %s - %s %s" % (
            self.user.get_full_name() or self.user.username,
            self.edit_type or '',
            self.student.fullname,
            self.subject.name, timestr)


def get_or_create_reportcard_entry(reportcard, section=None, subject=None,
                                   strand=None, fieldtype=None):
    """Helper to get or create a report card entry."""
    try:
        obj, created = ReportCardEntry.objects.get_or_create(
            reportcard=reportcard,
            section=section,
            subject=subject,
            strand=strand,
        )
    except MultipleObjectsReturned:
        client.captureException()
        logging.error("Multiple objects found", exc_info=True, extra={
            "found": ReportCardEntry.objects.filter(
                reportcard=reportcard,
                section=section,
                subject=subject,
                strand=strand,
            ).order_by('id').all()
        })
        return ReportCardEntry.objects.filter(
            reportcard=reportcard,
            section=section,
            subject=subject,
            strand=strand,
        ).order_by('id').first()
    if created:
        obj.save()
    return obj
