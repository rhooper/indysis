import sys

from autocomplete_light.shortcuts import modelform_factory
from custom_field.custom_field import CustomFieldAdmin, CustomInline
from django import forms
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy
from modeltranslation.admin import TranslationAdmin
from rest_framework.authtoken.admin import TokenAdmin
from reversion.admin import VersionAdmin

from sis.studentdb.models import (Student, StudentNumber, EmergencyContactNumber,
                                  StudentFile, EmergencyContact,
                                  StudentHealthRecord, Faculty, GradeLevel,
                                  LanguageChoice,
                                  ReasonLeft,
                                  SchoolYear,
                                  StudentHealthConcern, StudentFoodOrder,
                                  FoodOrderItem, BulkFoodOrderEntry,
                                  FoodOrderEvent, VolunteerHour,
                                  AfterschoolPackage,
                                  AfterschoolRegsitrationPeriod,
                                  AfterschoolPackagesPurchased,
                                  AfterschoolProgramAttendance,
                                  BulkAfterschoolAttendanceEntry,
                                  BeforeschoolProgramAttendance,
                                  BulkBeforeschoolAttendanceEntry, Term, StudentClass, StudentClassTeacher)

TokenAdmin.raw_id_fields = ('user',)


def mark_inactive(modeladmin, request, queryset):
    for object in queryset:
        object.is_active = False
        LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=ContentType.objects.get_for_model(object).pk,
            object_id=object.pk,
            object_repr=str(object),
            action_flag=CHANGE
        )
        object.save()


class StudentNumberInline(admin.TabularInline):
    model = StudentNumber
    extra = 0


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContactNumber
    extra = 1
    verbose_name = "Student contact phone number"
    verbose_name_plural = "Student contact phone numbers"
    from django.forms import TextInput
    from django.db import models
    formfield_overrides = {
        models.CharField: {'widget': TextInput()},
    }


class StudentFileInline(admin.TabularInline):
    model = StudentFile
    extra = 0


class StudentHealthRecordInline(admin.TabularInline):
    model = StudentHealthRecord
    extra = 0


class StudentHealthConcernInline(admin.StackedInline):
    model = StudentHealthConcern
    extra = 0
    verbose_name = "Health Concern"
    verbose_name_plural = "Health Concerns"


class StudentECInline(admin.TabularInline):
    model = Student.emergency_contacts.through
    extra = 0
    verbose_name = "Student for Contact"
    verbose_name_plural = "Students for Contact"


class TermInline(admin.StackedInline):
    model = Term
    extra = 0
    fieldsets = (
        ('', {
            'fields': ('active', 'name', 'shortname', ('start_date', 'end_date'),
                       'school_year'),
        },),
    )


class StudentFoodOrderInline(admin.TabularInline):
    model = StudentFoodOrder
    extra = 0
    verbose_name = "Food Order"
    verbose_name_plural = "Food Orders"
    radio_fields = {'item': admin.HORIZONTAL}
    fields = ('student', 'school_year', 'item', 'quantity')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            kwargs['initial'] = SchoolYear.objects.filter(active_year=True)[0].id
        ff = super(StudentFoodOrderInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        if db_field.name == 'item':
            ff.queryset = ff.queryset.filter(active=True)
        return ff


class StudentFoodOrderInlineAC(StudentFoodOrderInline):
    form = modelform_factory(StudentFoodOrder, fields='__all__',
                             autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})


class StudentFoodOrderAdmin(admin.ModelAdmin):
    model = 'Student Food Orders'
    list_display = ('school_year', 'student', 'item', 'quantity')
    list_filter = ('school_year', 'student__year', 'item')
    exclude = ('bulkentry',)
    extra = 0


class VolunteerHourAdmin(admin.ModelAdmin):
    model = VolunteerHour
    form = modelform_factory(VolunteerHour, fields='__all__',
                             autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})
    list_display = ('school_year', 'student', 'hours')
    list_filter = ('school_year', 'student__year')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            kwargs['initial'] = SchoolYear.objects.filter(active_year=True)[0].id
        ff = super(VolunteerHourAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff


class VolunteerHourAdminInline(admin.TabularInline):
    model = VolunteerHour
    list_display = ('school_year', 'student', 'hours')
    list_filter = ('school_year', 'student__year')
    extra = 0


class BFOAdmin(admin.ModelAdmin):
    verbose_name = 'Bulk Food Order Entry'
    verbose_name_plural = 'Bulk Food Order Entry'
    extra = 0
    inlines = [StudentFoodOrderInlineAC]

    search_fields = []
    actions = []
    list_display = ['date', 'notes', 'item_count']


class AfterschoolPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'period', 'days', 'cost', 'pooled', 'is_active')
    list_filter = ('period', 'period__school_year', 'is_active')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'period':
            try:
                kwargs['initial'] = AfterschoolRegsitrationPeriod.objects.filter(
                    is_active=True).order_by('-start_date')[0].id
            except IndexError:
                # No active registration periods
                pass
        ff = super(AfterschoolPackageAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff


class AfterschoolRegsitrationPeriodAdmin(admin.ModelAdmin):
    list_display = ('school_year', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active',)


class AfterschoolPackagesPurchasedAdmin(admin.ModelAdmin):
    model = AfterschoolPackagesPurchased
    form = modelform_factory(
        AfterschoolPackagesPurchased, fields='__all__',
        autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})
    list_display = ('student', 'date_registered', 'package')
    list_filter = ('package', 'package__period', 'student__year')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'period':
            kwargs['initial'] = AfterschoolRegsitrationPeriod.objects.filter(
                is_active=True).order_by('-start_date')[0].id
        ff = super(AfterschoolPackagesPurchasedAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff


class AfterschoolPackagesPurchasedAdminInline(admin.TabularInline):
    model = AfterschoolPackagesPurchased
    form = modelform_factory(
        AfterschoolPackagesPurchased, fields='__all__',
        autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})
    list_display = ('student', 'date_registered', 'package')
    list_filter = ('package', 'package__period', 'student__year')
    extra = 0

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'period':
            kwargs['initial'] = AfterschoolRegsitrationPeriod.objects.filter(
                is_active=True).order_by('-start_date')[0].id
        ff = super(AfterschoolPackagesPurchasedAdminInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff


class AfterschoolProgramAttendanceAdmin(admin.ModelAdmin):
    model = AfterschoolProgramAttendance
    form = modelform_factory(
        AfterschoolPackagesPurchased, fields='__all__',
        autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})
    list_display = ('school_year', 'student', 'date', 'package')
    list_filter = ('school_year', 'student__year', 'student', 'date', 'package')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            kwargs['initial'] = SchoolYear.objects.filter(active_year=True)[0].id
        ff = super(AfterschoolProgramAttendanceAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff

    def render_change_form(self, request, context, *args, **kwargs):
         context['adminform'].form.fields['package'].queryset = AfterschoolPackage.objects.filter(drop_in=True)
         return super(AfterschoolProgramAttendanceAdmin, self).render_change_form(request, context, *args, **kwargs)


class AfterschoolProgramAttendanceInline(admin.TabularInline):
    model = AfterschoolProgramAttendance
    extra = 0
    verbose_name = "Afterschool Attendance"
    verbose_name_plural = "Afterschool Attendance"
    fields = ('school_year', 'student', 'date', 'package')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            kwargs['initial'] = SchoolYear.objects.filter(active_year=True)[0].id
        ff = super(AfterschoolProgramAttendanceInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff


class AfterschoolProgramAttendanceInlineAC(AfterschoolProgramAttendanceInline):
    form = modelform_factory(
        AfterschoolProgramAttendance,
        fields='__all__', autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})


class BASPAAdmin(admin.ModelAdmin):
    verbose_name = 'Bulk Afterschool Attendance Entry'
    verbose_name_plural = 'Bulk Afterschool Attendance Entry'
    extra = 0
    inlines = [AfterschoolProgramAttendanceInlineAC]

    search_fields = []
    actions = []
    list_display = ['date', 'notes', 'item_count']


class BeforeSchoolProgramAttendanceAdmin(admin.ModelAdmin):
    model = BeforeschoolProgramAttendance
    form = modelform_factory(
        BeforeschoolProgramAttendance, fields='__all__',
        autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})
    list_display = ('school_year', 'student', 'date')
    list_filter = ('school_year', 'student__year', 'student', 'date')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            kwargs['initial'] = SchoolYear.objects.filter(active_year=True)[0].id
        ff = super(BeforeSchoolProgramAttendanceAdmin, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff


class BeforeschoolProgramAttendanceInline(admin.TabularInline):
    model = BeforeschoolProgramAttendance
    extra = 0
    verbose_name = "Before School Attendance"
    verbose_name_plural = "Before School Attendance"
    fields = ('school_year', 'student', 'date')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            kwargs['initial'] = SchoolYear.objects.filter(active_year=True)[0].id
        ff = super(BeforeschoolProgramAttendanceInline, self).formfield_for_foreignkey(
            db_field, request, **kwargs
        )
        return ff


class BeforeschoolProgramAttendanceInlineAC(BeforeschoolProgramAttendanceInline):
    form = modelform_factory(
        BeforeschoolProgramAttendance,
        fields='__all__', autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})


class BBSPAAdmin(admin.ModelAdmin):
    verbose_name = 'Bulk Before School Attendance Entry'
    verbose_name_plural = 'Bulk Before School Attendance Entry'
    extra = 0
    inlines = [BeforeschoolProgramAttendanceInlineAC]

    search_fields = []
    actions = []
    list_display = ['date', 'notes', 'item_count']


class StudentClassStudentInlineAdmin(admin.TabularInline):
    model = StudentClass.students.through
    extra = 0
    verbose_name = "class"
    verbose_name_plural = "classes"


class StudentAdmin(VersionAdmin, CustomFieldAdmin, admin.ModelAdmin):

    def changelist_view(self, request, extra_context=None):
        """override to hide inactive students by default"""
        try:
            test = request.META['HTTP_REFERER'].split(request.META['PATH_INFO'])
            if (
                    test and test[-1] and not test[-1].startswith('?') and
                    'is_active__exact' not in request.GET and 'id__in' not in request.GET):
                return HttpResponseRedirect("/admin/studentdb/student/?is_active__exact=1")
        except Exception:
            pass  # In case there is no referer
        return super(StudentAdmin, self).changelist_view(request, extra_context=extra_context)

    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup in ('id', 'id__in', 'year__id__exact'):
            return True
        return super(StudentAdmin, self).lookup_allowed(lookup, *args, **kwargs)

    def render_change_form(self, request, context, *args, **kwargs):
        if 'original' in context and context['original'] is not None:
            if context['original'].alert:
                messages.add_message(request, messages.INFO, 'ALERT: {0}'.format(context["original"].alert))
            for record in context['original'].studenthealthrecord_set.all():
                messages.add_message(request, messages.INFO, 'HEALTH RECORD: {0}'.format(record.record))
            try:
                if context['original'].pic:
                    txt = '<img src="' + str(context['original'].pic.url_70x65) + '"/>'
                    context['adminform'].form.fields['pic'].help_text += txt
            except Exception:
                print("Error in StudentAdmin render_change_form", file=sys.stderr)

        return super(StudentAdmin, self).render_change_form(request, context, *args, **kwargs)

    def save_model(self, request, obj, form, change):
        if not obj.username:
            obj.username = Student.pick_username()
        super(StudentAdmin, self).save_model(request, obj, form, change)
        form.save_m2m()

    def get_form(self, request, obj=None, **kwargs):
        exclude = []
        if not request.user.has_perm('studentdb.view_ssn_student'):
            exclude.append('ssn')
        if len(exclude):
            kwargs['exclude'] = exclude
        form = super(StudentAdmin, self).get_form(request, obj, **kwargs)
        return form

    def get_fieldsets(self, request, obj=None):
        return ((
                    None,
                    {
                        'fields': (
                            ('is_active', 'year'),
                            ('last_name', 'first_name'),
                            ('mname', 'bday'),
                            ('healthcard_no', 'sex'),
                            ('pic', 'photo_permission'),
                            ('emergency_contacts', 'siblings'),
                            ('date_dismissed', 'reason_left'),
                            ('activation_date', 'grad_date'),
                            'individual_education_program',
                            'notes',
                            ('afterschool_only', 'afterschool_grade'),
                            ('student_account_email', 'student_account_initial_pw')
                        )
                    }
                ),)

    change_list_template = "admin/studentdb/student/change_list.html"
    form = modelform_factory(Student, fields='__all__')
    search_fields = ['first_name', 'last_name', 'username', 'unique_id', 'street', 'state', 'zip', 'id',
                     'studentnumber__number', 'studenthealthconcern__name']
    inlines = [StudentClassStudentInlineAdmin, CustomInline, StudentHealthConcernInline, StudentFoodOrderInline, VolunteerHourAdminInline,
               AfterschoolPackagesPurchasedAdminInline, AfterschoolProgramAttendanceInline,
               StudentNumberInline,
               StudentFileInline, StudentHealthRecordInline]
    actions = [mark_inactive]
    list_filter = ['is_active', 'year']
    list_display = ['first_name', 'last_name', 'year', 'is_active', 'sex', 'bday', 'phone', 'health_concerns']


class EmergencyContactAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': [
            ('relationship_to_student', 'primary_contact'),
            ('honorific', 'fname', 'mname', 'lname'),
            ('email', 'alt_email'),
            ('emergency_only', ),
            'notes',

        ]}),
        ('Address', {'fields': ['street', ('city', 'state',), 'zip'], 'classes': ['collapse']}),
        ('Employment', {'fields': ['employer', 'job_title']}),
    ]
    list_filter = ['primary_contact', ]
    inlines = [EmergencyContactInline, StudentECInline]
    search_fields = ['fname', 'lname', 'email', 'student__first_name', 'student__last_name', 'employer', 'job_title']
    list_display = ['fname', 'lname', 'primary_contact', 'relationship_to_student', 'email', 'show_student']


class SchoolYearAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'active_year')

    def get_form(self, request, obj=None, **kwargs):
        form = super(SchoolYearAdmin, self).get_form(request, obj, **kwargs)
        return form

    inlines = [TermInline]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name in ('vice_principal', 'principal'):
            kwargs['queryset'] = User.objects.filter(is_staff=True)
        return super(SchoolYearAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class StudentHealthConcernAdmin(admin.ModelAdmin):
    list_display = ('student', 'type', 'name', 'notes')
    fields = ['student', 'type', 'name', 'notes', 'symptoms', 'actions']
    search_fields = ['type', 'name', 'notes']


# Customize the User admin to exclude students
def custom_admin_user_queryset(self, request):
    qs = super(UserAdmin, self).get_queryset(request)
    return qs.filter(student__isnull=True)


UserAdmin.get_queryset = custom_admin_user_queryset


class TermAdmin(admin.ModelAdmin):
    list_display = ['name', 'shortname', 'school_year', 'start_date', 'end_date', 'active']
    fieldsets = (
        ('', {
            'fields': ('active', 'name', 'shortname', ('start_date', 'end_date'), 'school_year'),
        },),
    )


class StudentClassTeacherInlineAdmin(admin.TabularInline):
    model = StudentClassTeacher
    extra = 0
    verbose_name = "class teacher"
    verbose_name_plural = "class teachers"

    # fields = ('teacher', 'homeroom')
    fieldsets = (
        ('', {'fields': ('teacher', 'homeroom')},),
    )


def get_num_students(obj):
    return "%d" % obj.students.count()


def get_teachers(obj):
    return ", ".join(teacher.fullname for teacher in obj.teachers.all())


def get_terms(obj):
    return ", ".join(term.shortname for term in obj.terms.all())


get_num_students.short_description = gettext_lazy("No. Students")
get_teachers.short_description = gettext_lazy("Teachers")
get_terms.short_description = gettext_lazy("Terms")


class StudentClassAdmin(admin.ModelAdmin):
    inlines = [StudentClassTeacherInlineAdmin]
    verbose_name = "Class"
    verbose_name_plural = "Classes"
    filter_horizontal = ["students"]
    list_filter = ['school_year']

    list_display = ['shortname', 'school_year', get_terms, get_num_students, get_teachers]

    class CustomModelChoiceField(forms.ModelMultipleChoiceField):
        def label_from_instance(self, obj):
            return "%s (%s)" % (str(obj), obj.year.shortname if obj.year else "???")

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "students":
            return self.CustomModelChoiceField(
                queryset=Student.objects.filter(is_active=True).order_by('year__id', 'last_name', 'first_name'),
                widget=FilteredSelectMultiple(db_field.verbose_name, False))
        elif db_field.name == "teachers":
            kwargs["queryset"] = Faculty.objects.filter(is_active=True)
        elif db_field.name == "terms":
            kwargs["queryset"] = Term.objects.filter(active=True, school_year__active_year=True)
            kwargs['initial'] = Term.objects.filter(active=True, school_year__active_year=True)
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'school_year':
            school_year = SchoolYear.objects.filter(active_year=True).first()
            if school_year:
                kwargs['initial'] = school_year.id
        return super(StudentClassAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)


class StudentClassTeacherFacultyInlineAdmin(admin.TabularInline):
    model = StudentClassTeacher
    extra = 0
    verbose_name = "class"
    verbose_name_plural = "classes"

    # fields = ('teacher', 'homeroom')
    fieldsets = (
        ('', {'fields': ('student_classes', 'homeroom')},),
    )


class FacultyAdmin(admin.ModelAdmin):
    fields = ['username', 'is_active', 'first_name', 'last_name', 'email', 'number', 'ext',
              'teacher', 'teaching_language', 'signature', 'cell']
    search_fields = list_display = ['username', 'first_name', 'last_name', 'teaching_language', 'is_active',
                                    'signature_tag']
    inlines = [StudentClassTeacherFacultyInlineAdmin]


class GradeLevelAdmin(TranslationAdmin, admin.ModelAdmin):
    list_display = ['name_en', 'name_fr', 'shortname_en', 'shortname_fr', 'next_grade']


admin.site.register(AfterschoolPackage, AfterschoolPackageAdmin)
admin.site.register(AfterschoolPackagesPurchased, AfterschoolPackagesPurchasedAdmin)
admin.site.register(AfterschoolProgramAttendance, AfterschoolProgramAttendanceAdmin)
admin.site.register(AfterschoolRegsitrationPeriod, AfterschoolRegsitrationPeriodAdmin)
admin.site.register(BeforeschoolProgramAttendance, BeforeSchoolProgramAttendanceAdmin)
admin.site.register(BulkAfterschoolAttendanceEntry, BASPAAdmin)
admin.site.register(BulkBeforeschoolAttendanceEntry, BBSPAAdmin)
admin.site.register(BulkFoodOrderEntry, BFOAdmin)
admin.site.register(EmergencyContact, EmergencyContactAdmin)
admin.site.register(EmergencyContactNumber)
admin.site.register(Faculty, FacultyAdmin)
admin.site.register(FoodOrderEvent)
admin.site.register(FoodOrderItem)
admin.site.register(GradeLevel, GradeLevelAdmin)
admin.site.register(LanguageChoice)
admin.site.register(ReasonLeft)
admin.site.register(Student, StudentAdmin)
admin.site.register(SchoolYear, SchoolYearAdmin)
admin.site.register(StudentClass, StudentClassAdmin)
admin.site.register(StudentFoodOrder, StudentFoodOrderAdmin)
admin.site.register(StudentHealthConcern, StudentHealthConcernAdmin)
admin.site.register(Term, TermAdmin)
admin.site.register(VolunteerHour, VolunteerHourAdmin)
