"""Admins."""

from admintimestamps import TimestampedAdminMixin
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from modeltranslation.admin import TranslationStackedInline
from reversion.admin import VersionAdmin

from indysis_reportcard.models import GradingSchemeLevelChoice, ReportCardTerm, SchoolYear, ReportCardTemplateImage, \
    ReportCardSharedTemplate
# Register your models here.
from indysis_reportcard.models import ReportCardSection, ReportCardSubject, \
    ReportCardTemplate, ReportCardAccess
from indysis_reportcard.models import ReportCardStrand, GradingScheme, GradingSchemeLevel
from sis.studentdb.models import Faculty, StudentClass


def copy(modeladmin, request, queryset):
    for object in queryset:
        object.copy_instance(request)


class ReportCardSectionInline(TimestampedAdminMixin, TranslationStackedInline):
    """Admin."""

    model = ReportCardSection
    extra = 1


class ReportCardTemplateAdmin(VersionAdmin, TimestampedAdminMixin, TranslationAdmin):
    """Admin."""

    inlines = [ReportCardSectionInline]
    extra = 1
    save_as = True
    actions = [copy]
    list_display = ('name', 'description', 'interim', 'get_grades', 'is_active')

    def get_grades(self, obj):
        """Get Grades"""
        return '; '.join([g.shortname for g in obj.grades.all()])

    get_grades.short_description = 'Grades'


class ReportCardSharedTemplateAdmin(VersionAdmin, TimestampedAdminMixin, admin.ModelAdmin):
    """Admin."""

    extra = 1
    save_as = True
    list_display = ('name', 'description', 'is_active')


class GradingSchemeLevelChoiceInline(TimestampedAdminMixin, TranslationTabularInline):
    """Admin."""

    model = GradingSchemeLevelChoice


class GradingSchemeLevelChoiceAdmin(VersionAdmin, TimestampedAdminMixin, TranslationAdmin):
    """Admin."""

    model = GradingSchemeLevelChoice
    list_filter = ('gradingschemelevel', 'gradingschemelevel__gradingscheme')
    list_display = (
        'name_en', 'name_fr', 'description_en', 'description_fr', 'sortorder', 'choice', 'gradingschemelevel')


class GradingSchemeLevelInline(TimestampedAdminMixin, TranslationTabularInline):
    """Admin."""

    model = GradingSchemeLevel


class GradingSchemeLevelAdmin(VersionAdmin, TimestampedAdminMixin, TranslationAdmin):
    """Admin."""

    inlines = [GradingSchemeLevelChoiceInline]
    list_filter = ('gradingscheme',)
    list_display = ('range', 'gradingscheme', 'sortorder')


class GradingSchemeAdmin(VersionAdmin, TimestampedAdminMixin, TranslationAdmin):
    """Admin."""

    inlines = [GradingSchemeLevelInline]
    actions = [copy]


class ReportCardStrandAdminInline(TimestampedAdminMixin, TranslationStackedInline):
    """Admin."""

    model = ReportCardStrand
    extra = 1
    list_display = ('text', 'sortorder', 'subject', 'graded')


class ReportCardAccessAdmin(VersionAdmin, admin.ModelAdmin):
    """Admin."""

    list_display = ('description', 'get_student_classes', 'get_subjects', 'get_teachers')
    list_filter = ('subjects__section__template', 'student_classes', 'teachers')
    filter_horizontal = ('student_classes', 'subjects', 'teachers')
    filter_vertical = ('subjects', )
    actions = [copy]
    save_as = True
    exclude = ['sections']

    def get_student_classes(self, obj):
        """Get Classes"""
        return mark_safe("<ul class='list-group'>" + "".join([
            format_html("<li class='list-group-item'>{}<br>[{}]</li>", t.name, t.school_year)
            for t in StudentClass.objects.filter(reportcardaccess=obj).order_by('id')
        ]) + "</ul>")

    def get_sections(self, obj):
        """Get Sections"""

        return mark_safe("<ul class='list-group'>" + "".join([
            format_html("<li class='list-group-item'>{}</li>", t)
            for t in ReportCardSection.objects.filter(reportcardaccess=obj).order_by('sortorder')
        ]) + "</ul>")

    def get_subjects(self, obj):
        """Get Subjects"""
        return mark_safe("<ul class='list-group'>" + "".join([
            format_html("<li class='list-group-item'>{}</li>", t)
            for t in ReportCardSubject.objects.filter(reportcardaccess=obj).order_by('section', 'sortorder')
        ]) + "</ul>")

    def get_teachers(self, obj):
        """Get Teachers"""
        return mark_safe("<ul class='list-group'>" + "".join([
            format_html("<li class='list-group-item'>{}</li>", t)
            for t in Faculty.objects.filter(reportcardaccess=obj)
        ]) + "</ul>")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "student_classes":
            kwargs["queryset"] = StudentClass.objects.order_by('school_year_id', 'name')
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    get_student_classes.short_description = "Classes"
    get_sections.short_description = "Sections"
    get_subjects.short_description = "Subjects"
    get_teachers.short_description = "Teachers"


class ReportCardSubjectAdminInline(TimestampedAdminMixin, TranslationStackedInline):
    """Admin."""

    model = ReportCardSubject
    extra = 1


class ReportCardSectionAdmin(VersionAdmin, TranslationAdmin):
    """Admin."""

    inlines = [ReportCardSubjectAdminInline]
    list_filter = ('template', 'template__grades', 'comments_area')
    list_display = ('name', 'template', 'sortorder', 'comments_area')


class ReportCardSubjectAdmin(VersionAdmin, TranslationAdmin):
    """Admin."""

    inlines = [ReportCardStrandAdminInline]
    list_display = ('name', 'get_template', 'get_section', 'sortorder', 'graded', 'comments_area')
    list_filter = ('section', 'section__template', 'section__template__grades', 'graded', 'comments_area')

    ordering = ('section__template__name', 'section__name', 'sortorder')

    def get_template(self, obj):
        return obj.section.template.name

    get_template.short_description = "Template"
    get_template.admin_order_field = "section__template__name"

    def get_section(self, obj):
        return obj.section.name

    get_section.short_description = "Section"
    get_section.admin_order_field = "section__name"


class ReportCardStrandAdmin(VersionAdmin, TimestampedAdminMixin, TranslationAdmin):
    """Admin."""

    list_display = ('text', 'sortorder', 'subject', 'graded')
    list_filter = ('subject', 'subject__section', 'subject__section__template')


class ReportCardTermAdmin(VersionAdmin, TranslationAdmin):
    """Admin."""

    list_display = ('name_en', 'name_fr', 'school_year', 'interim', 'is_open',)
    list_filter = ('school_year', 'is_open')
    actions = [copy]


class ReportCardYearGradeContentAdmin(VersionAdmin, admin.ModelAdmin):
    """Admin for ReportCardYearGradeContent."""

    list_display = ('school_year', 'grade_level')
    list_filter = ('school_year', 'grade_level')
    ordering = ('-school_year', 'grade_level')
    actions = [copy]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            kwargs['initial'] = SchoolYear.objects.filter(active_year=True)[0].id
        ff = super(ReportCardYearGradeContentAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        if db_field.name == 'item':
            ff.queryset = ff.queryset.filter(active=True)
        return ff


class ReportCardTemplateImageAdmin(VersionAdmin, admin.ModelAdmin):
    list_display = ['name', 'image_tag']

    def image_tag(self, obj):
        if obj.image:
            return '<img style="max-height: 100px" src="%s" />' % obj.image.url_200x200
        else:
            return ''

    image_tag.short_description = 'Signature'
    image_tag.allow_tags = True


admin.site.register(GradingScheme, GradingSchemeAdmin)
admin.site.register(GradingSchemeLevel, GradingSchemeLevelAdmin)
admin.site.register(GradingSchemeLevelChoice, GradingSchemeLevelChoiceAdmin)
admin.site.register(ReportCardSubject, ReportCardSubjectAdmin)
admin.site.register(ReportCardTemplate, ReportCardTemplateAdmin)
admin.site.register(ReportCardSection, ReportCardSectionAdmin)
admin.site.register(ReportCardStrand, ReportCardStrandAdmin)
admin.site.register(ReportCardTerm, ReportCardTermAdmin)
admin.site.register(ReportCardAccess, ReportCardAccessAdmin)
admin.site.register(ReportCardTemplateImage, ReportCardTemplateImageAdmin)
admin.site.register(ReportCardSharedTemplate, ReportCardSharedTemplateAdmin)

# Disabled feature, may purge.
# admin.site.register(ReportCardYearGradeContent, ReportCardYearGradeContentAdmin)
