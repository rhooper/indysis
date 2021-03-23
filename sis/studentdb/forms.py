import autocomplete_light.shortcuts as autocomplete_light
from django import forms
from django.conf import settings
from django.contrib.admin import widgets as adminwidgets
from django.db.utils import ProgrammingError

from sis.studentdb.models import UserPreference, SchoolYear, GradeLevel, Term

autocomplete_light.autodiscover()


class UserPreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        widgets = {
            'prefered_file_format': forms.Select,
            'include_deleted_students': forms.CheckboxInput,
            'course_sort': forms.Select,
        }
        exclude = []


class DeletedStudentLookupForm(forms.Form):
    # See https://github.com/yourlabs/django-autocomplete-light/issues/315
    try:
        student = autocomplete_light.ModelChoiceField('StudentUserAutocomplete')
    except ProgrammingError:
        pass


class StudentLookupForm(forms.Form):
    try:
        student = autocomplete_light.ModelChoiceField('StudentActiveStudentAutocomplete')
    except ProgrammingError:
        pass


class UploadFileForm(forms.Form):
    file = forms.FileField()


class TermForm(forms.Form):
    term = forms.ModelMultipleChoiceField(queryset=Term.objects.all())


class YearSelectForm(forms.Form):
    school_year = forms.ModelChoiceField(queryset=SchoolYear.objects.all())


class StudentBulkChangeForm(forms.Form):
    grad_date = forms.DateField(widget=adminwidgets.AdminDateWidget(), required=False,
                                validators=settings.DATE_VALIDATORS)
    year = forms.ModelChoiceField(queryset=GradeLevel.objects.all(), required=False)
    individual_education_program = forms.NullBooleanField(required=False)
