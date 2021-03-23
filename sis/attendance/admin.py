from autocomplete_light.shortcuts import modelform_factory
from daterange_filter.filter import DateRangeFilter
from django import forms
from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect

from sis.attendance.models import AttendanceStatus
from sis.attendance.models import StudentAttendance


class StudentAttendanceAdmin(admin.ModelAdmin):
    form = modelform_factory(StudentAttendance, fields='__all__',
                             autocomplete_names={'student': 'StudentActiveStudentAutocomplete'})
    readonly_fields = ('recorded_by_name',)
    exclude = ('recorded_by',)
    list_display = ['student', 'date', 'status', 'recorded_by_name', 'notes', 'time']
    list_filter = [
        ('date', DateRangeFilter),
        'status'
    ]
    search_fields = ['student__first_name', 'student__last_name', 'notes', 'status__name']

    def recorded_by_name(self, obj):
        return obj.recorded_by.get_full_name() or obj.recorded_by.username if obj.recorded_by else '(none)'

    recorded_by_name.short_description = 'Recorded By'

    def save_model(self, request, obj, form, change):
        # HACK to work around bug 13091
        try:
            obj.recorded_by = request.user
            obj.full_clean()
            obj.save()
        except forms.ValidationError as e:
            messages.warning(request, 'Could not save %s - %s' % (obj, e))

    def lookup_allowed(self, lookup, *args, **kwargs):
        if lookup in ('student', 'student__id__exact',):
            return True
        return super(StudentAttendanceAdmin, self).lookup_allowed(lookup, *args, **kwargs)

    def response_change(self, request, obj):
        if 'return_url' in request.GET or 'return_url' in request.POST:
            ret = request.GET.get('return_url', '') or request.POST.get('return_url', '')
            return HttpResponseRedirect(ret)
        return super(StudentAttendanceAdmin, self).response_change(request, obj)

    def response_add(self, request, obj):
        if 'return_url' in request.GET or 'return_url' in request.POST:
            ret = request.GET.get('return_url', '') or request.POST.get('return_url', '')
            return HttpResponseRedirect(ret)
        return super(StudentAttendanceAdmin, self).response_add(request, obj)


admin.site.register(StudentAttendance, StudentAttendanceAdmin)


class AttendanceStatusAdmin(admin.ModelAdmin):
    list_display = ['name', 'order', 'code', 'excused', 'absent', 'tardy', 'half', 'teacher_selectable']

    list_filter = [
        'teacher_selectable',
    ]


admin.site.register(AttendanceStatus, AttendanceStatusAdmin)
