import datetime

import autocomplete_light.shortcuts as autocomplete_light
from django import forms
from django.conf import settings
from django.contrib.admin import widgets as adminwidgets
from django.db.utils import ProgrammingError

from sis.attendance.models import StudentAttendance, AttendanceStatus


class StudentAttendanceForm(forms.ModelForm):
    class Meta:
        model = StudentAttendance
        widgets = {
            'student': forms.HiddenInput(),
            'date': forms.HiddenInput(),
            'notes': forms.TextInput(attrs={'tabindex': "-1", }),
        }
        exclude = []

    status = forms.ModelChoiceField(widget=forms.Select(attrs={'class': 'status', }),
                                    queryset=AttendanceStatus.objects.filter(teacher_selectable=True))


class StudentMultpleAttendanceForm(autocomplete_light.ModelForm):
    """ Form accepts multiple students """

    class Meta:
        model = StudentAttendance
        widgets = {
            'date': adminwidgets.AdminDateWidget(),
            'time': adminwidgets.AdminTimeWidget(),
        }
        fields = ('date', 'status', 'time', 'notes', 'private_notes')

    student = autocomplete_light.ModelMultipleChoiceField('StudentUserAutocomplete')


class AttendanceViewForm(forms.Form):
    all_years = forms.BooleanField(required=False,
                                   help_text="If check report will contain all student records. Otherwise it will only show current year.")
    order_by = forms.ChoiceField(initial=0, choices=(('Date', 'Date'), ('Status', 'Status'),))
    include_private_notes = forms.BooleanField(required=False)
    try:
        student = autocomplete_light.ModelChoiceField('StudentUserAutocomplete')
    except ProgrammingError:
        pass


class AttendanceDailyForm(forms.Form):
    date = forms.DateField(widget=adminwidgets.AdminDateWidget(), initial=datetime.date.today,
                           validators=settings.DATE_VALIDATORS)
    include_private_notes = forms.BooleanField(required=False)


class AttendanceBulkChangeForm(forms.Form):
    date = forms.DateField(widget=adminwidgets.AdminDateWidget(), required=False, validators=settings.DATE_VALIDATORS)
    status = forms.ModelChoiceField(queryset=AttendanceStatus.objects.all(), required=False)
    notes = forms.CharField(max_length=255, required=False)
    private_notes = forms.CharField(max_length=255, required=False)
