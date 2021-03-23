from autocomplete_light.shortcuts import AutocompleteModelBase, AutocompleteModelTemplate, register
from django.contrib.auth.context_processors import PermWrapper

from sis.studentdb.models import Student, EmergencyContact, Faculty


class UserAutocomplete(AutocompleteModelBase):
    split_words = True
    search_fields = ['first_name', 'last_name']
    attrs = {
        'placeholder': 'Lookup Student(s)',
    }

    def choices_for_request(self):
        if not self.request.user.is_staff:
            return []
        return super().choices_for_request()


class FacultyAutocomplete(UserAutocomplete):
    attrs = {
        'placeholder': 'Lookup Faculty',
    }


class ActiveStudentAutocomplete(UserAutocomplete):
    choices = Student.objects.filter(is_active=True)

    def choice_label(self, choice):
        return super().choice_label("%s (%s)" % (choice, choice.year.shortname if choice.year else "?"))


class LookupStudentAutocomplete(UserAutocomplete, AutocompleteModelTemplate):
    autocomplete_template = 'studentdb/lookup_student.html'
    choices = Student.objects.filter(is_active=True)
    limit_choices = 10

    class Meta:
        exclude = []

    def choices_for_request(self):
        results = super().choices_for_request()
        contacts = ContactAutocomplete(request=self.request)
        contacts.choices = EmergencyContact.objects.filter(student__is_active=True)
        parents = contacts.choices_for_request()
        return results, parents

    def autocomplete_html(self):
        """
        Overrides autocomplete_html to pass in both choice sets
        """
        students, parents = self.choices_for_request()
        perms = PermWrapper(self.request.user)

        return self.render_template_context(self.autocomplete_template,
            {'choices': students, 'parents': parents, 'perms': perms})


class ContactAutocomplete(AutocompleteModelTemplate):
    split_words = True
    order_by = ['-primary_contact', 'fname', 'lname']
    search_fields = ['fname', 'lname', 'email', 'alt_email']
    attrs = {
        'placeholder': 'Lookup Contact(s)',
    }
    choice_template = 'sis/autocomplete_contact.html'
    limit_choices = 10

    def choices_for_request(self):
        if self.request.user.is_anonymous:
            return []
        return super().choices_for_request()


register(EmergencyContact, ContactAutocomplete)
register(Student, UserAutocomplete)
register(Student, ActiveStudentAutocomplete)
register(Faculty, FacultyAutocomplete)
register(Student, LookupStudentAutocomplete)
