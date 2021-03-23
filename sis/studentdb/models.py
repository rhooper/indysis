"""Models for School Information System."""
from contextlib import suppress
import copy
from datetime import date, datetime
import logging
import re
from random import choice
from string import ascii_letters

from constance import config
from custom_field.custom_field import CustomFieldModel
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, m2m_changed, pre_save
from django.utils.translation import gettext_lazy
from localflavor.ca.ca_provinces import PROVINCE_CHOICES
from localflavor.us.models import USStateField
from localflavor.us.us_states import STATE_CHOICES
from phonenumber_field.modelfields import PhoneNumberField

from sis.studentdb.thumbs import ImageWithThumbsField

logger = logging.getLogger(__name__)


class CAUSStateField(USStateField):
    """
    Canadian Province or US State Field.

    A model field that forms represent as a ``forms.CAUSStateField`` field and
    stores the two-letter U.S. state or Canadian province abbreviation in the
    studentdb.
    """

    description = "U.S. state or Canadian province (two uppercase letters)"

    def __init__(self, *args, **kwargs):
        """Setup."""
        kwargs['choices'] = kwargs.get(
            'choices', list(PROVINCE_CHOICES) + list(STATE_CHOICES))
        kwargs['max_length'] = 2
        super(USStateField, self).__init__(*args, **kwargs)


def create_faculty(instance, make_user_group=True):
    """Create a studentdb.Faculty object.

    Create a studentdb.Faculty object that is linked to the given
    auth_user instance. Important as there is no way to do this
    from Django admin. See
    http://stackoverflow.com/questions/4064808/django-model-inheritance-create-sub-instance-of-existing-instance-downcast
    """
    if not hasattr(instance, "student") and not hasattr(instance, "faculty"):
        faculty = Faculty(user_ptr_id=instance.id)
        faculty.__dict__.update(instance.__dict__)
        faculty.save(make_user_group=make_user_group)


def create_student(instance):
    """Create a studentdb.Student object.

    Create a studentdb.Student object that is linked to the given auth_user
    instance. See create_faculty for more details.
    """
    if not hasattr(instance, "student") and not hasattr(instance, 'faculty'):
        student = Student(user_ptr_id=instance.id)
        student.__dict__.update(instance.__dict__)
        student.save()


def create_faculty_profile(sender, instance, created, **kwargs):
    """Create faculty profile."""
    if instance.groups.filter(name="faculty").count():
        create_faculty(instance, make_user_group=False)
    if instance.groups.filter(name="students").count():
        create_student(instance)


def create_faculty_profile_m2m(sender, instance, action, reverse, model,
                               pk_set, **kwargs):
    """Create faculty profile m2m helper."""
    if instance.__class__.__name__ == 'Group':
        return
    if action == 'post_add' and instance.groups.filter(name="faculty").count():
        create_faculty(instance, make_user_group=False)
    if action == 'post_add' and instance.groups.filter(
            name="students").count():
        create_student(instance)


post_save.connect(create_faculty_profile, sender=User)
m2m_changed.connect(create_faculty_profile_m2m, sender=User.groups.through)


class UserPreference(models.Model):
    """User Preferences."""

    include_deleted_students = models.BooleanField(
        default=False,
        help_text="When searching for students, include past students.")
    user = models.OneToOneField(User, editable=False, on_delete=models.CASCADE)
    first = True

    def get_format(self, type="document"):
        """Return format extension.

        type: type of format (document or spreadsheet)
        """
        if type == "document":
            if self.prefered_file_format == "o":
                return "odt"
            elif self.prefered_file_format == "m":
                return "doc"
            elif self.prefered_file_format == "x":
                return "docx"
        elif type == "spreadsheet":
            if self.prefered_file_format == "o":
                return "ods"
            elif self.prefered_file_format == "m":
                return "xls"
            elif self.prefered_file_format == "x":
                return "xlsx"


class PhoneNumber(models.Model):
    """Phone Number model."""

    number = PhoneNumberField()
    ext = models.CharField(max_length=10, blank=True, null=True)
    type = models.CharField(
        max_length=2, choices=(
            ('H', 'Home'), ('C', 'Cell'), ('W', 'Work'), ('O', 'Other')),
        blank=True)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        """Meta."""

        abstract = True

    @property
    def number_reformatted(self):
        num = u"%s" % self.number
        if num.startswith("+1"):
            num = re.sub(r'^\+1(\d\d\d)(\d\d\d)(\d\d\d\d)', r'\1-\2-\3', num)
        return num

    def full_number(self):
        """Full phone number."""
        if self.ext:
            return self.number_reformatted + " x" + self.ext
        else:
            return self.number_reformatted


def get_city():
    """Get default city from config."""
    return config.DEFAULT_CITY


class EmergencyContact(models.Model):
    """Parents and emergency contact model."""

    honorific = models.CharField(
        max_length=16, verbose_name="Honorific", default='', blank=True,
        help_text='Prefix such as Dr. Mme. Mrs. M. Mlle. Mr.')
    fname = models.CharField(max_length=255, verbose_name="First Name")
    mname = models.CharField(max_length=255, blank=True, null=True,
                             verbose_name="Middle Name")
    lname = models.CharField(max_length=255, verbose_name="Last Name")
    employer = models.CharField(max_length=255, verbose_name="Employer",
                                blank=True)
    job_title = models.CharField(max_length=255, verbose_name="Job Title",
                                 blank=True)
    notes = models.TextField(verbose_name='Notes', blank=True)
    relationship_to_student = models.CharField(
        max_length=500, blank=True,
        choices=tuple(
            (x, x) for x in (
                'Mother', 'Father',
                'Grandparent', 'Grandmother', 'Grandfather',
                'Aunt/Uncle', 'Aunt', 'Uncle',
                'Sibling', 'Sister', 'Brother', 'Legal Guardian', 'Physician',
                'Nanny', 'Babysitter', 'Other', 'Emergency', 'Friend',
                'Neighbour')
        ) + (('', '(Unspecified)'),)
    )
    street = models.CharField(
        max_length=255, blank=True, null=True, help_text="Include apt number")
    city = models.CharField(max_length=255, blank=True, null=True, default=get_city)
    state = CAUSStateField(blank=True, null=True, verbose_name="Province")
    zip = models.CharField(max_length=10, blank=True, null=True,
                           verbose_name="Postal Code")
    email = models.EmailField(
        blank=True,
        help_text="Primary email.")
    alt_email = models.EmailField(
        blank=True, help_text='Alternate email address.')
    primary_contact = models.BooleanField(
        default=True,
        help_text="This contact is where mailings should be sent to. "
                  "In the event of an emergency, this is the person that "
                  "will be contacted first.")
    emergency_only = models.BooleanField(
        default=False, help_text="Only contact in case of emergency")
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    long = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        """Class metadata."""

        ordering = ('primary_contact', 'lname')
        verbose_name = "Student contact"

    def __str__(self):
        """Return unicode version of contact."""
        txt = ' '.join(filter(lambda x: x and x != '', (
            self.honorific, self.fname, self.lname)))
        for number in self.emergencycontactnumber_set.all():
            txt += " " + number.full_number()
        return txt

    def save(self, *args, **kwargs):
        """Save."""
        super(EmergencyContact, self).save(*args, **kwargs)
        self.cache_student_addresses()

    def cache_student_addresses(self):
        """Cache student addresses.

        Cache these for the student for primary contact only
        There is another check on Student in case all contacts where deleted.
        """
        try:
            if self.primary_contact:
                for student in self.student_set.all():
                    student.parent_guardian = self.fname + " " + self.lname
                    student.city = self.city
                    student.street = self.street
                    student.state = self.state
                    student.zip = self.zip
                    student.parent_email = self.email
                    student.save()
                    for contact in student.emergency_contacts.exclude(
                            id=self.id):
                        # There should only be one primary contact!
                        if contact.primary_contact:
                            contact.primary_contact = False
                            contact.save()
                # cache these for the applicant
                if hasattr(self, 'applicant_set'):
                    for applicant in self.applicant_set.all():
                        applicant.set_cache(self)
        except ValueError:
            pass

    def show_student(self):
        """Method."""
        students = ""
        for student in self.student_set.all():
            students += "{}, ".format(student)
        return students[:-2]

    @property
    def fullname_comma(self):
        """Fullname: Last, Hon. First."""
        parts = [self.lname]
        if self.honorific and not self.honorific.strip() == '':
            parts.append('%s %s' % (self.honorific, self.fname))
        else:
            parts.append(self.fname)
        return ', '.join(parts)

    def fullname(self):
        """Fullname: Hon. First Middle Last."""
        return ' '.join(x for x in [self.honorific, self.fname,
                                    self.mname, self.lname]
                        if x is not None and x is not '').replace('  ', ' ')

    def fullname_hon_dr(self):
        """Fullname: Hon. First Middle Last (Dr.) ."""
        return ' '.join(x.strip() for x in [
            self.honorific if self.honorific.startswith('Dr') else '',
            self.fname,
            self.mname,
            self.lname]
                        if x is not None and x is not '').replace('  ', ' ')

    @property
    def primary_phone(self):
        """Primary phone number."""
        return self.emergencycontactnumber_set.filter(primary=True).first()

    def get_phone(self, type):
        """Get a phone number by type."""
        ph = self.emergencycontactnumber_set.filter(type=type).first()
        if ph:
            return ph.full_number()
        else:
            return ""

    @property
    def phones(self):
        return self.emergencycontactnumber_set.all()

    def phone_cell(self):
        """Cell phone number"""
        return self.get_phone('C')

    def phone_work(self):
        """Work phone number"""
        return self.get_phone('W')

def address_changed(sender, instance, raw, using, update_fields, **kwargs):
    """Clear lat/long on address change."""
    try:
        obj = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        pass  # Object is new, so field hasn't technically changed, but you may want to do something else here.
    else:
        if not (obj.street == instance.street) or not (
                obj.zip == instance.zip):  # Field has changed
            instance.lat = instance.long = None


pre_save.connect(address_changed, sender=EmergencyContact)


class EmergencyContactNumber(PhoneNumber):
    """Phone numbers for a contact."""

    contact = models.ForeignKey(EmergencyContact, on_delete=models.CASCADE)
    primary = models.BooleanField(default=False, )

    class Meta:
        """Meta."""

        verbose_name = "Student contact phone number"

    def save(self, *args, **kwargs):
        """Save."""
        if self.primary:
            for contact in self.contact.emergencycontactnumber_set.exclude(
                    id=self.id).filter(primary=True):
                contact.primary = False
                contact.save()
        super(EmergencyContactNumber, self).save(*args, **kwargs)

    def __str__(self):
        return self.get_type_display() + ":" + self.full_number()

    @property
    def number_ext(self):
        """Number with ext or just number."""
        if self.ext:
            return self.number + "x" + self.ext
        else:
            return self.number


class Faculty(User):
    """Faculty Model."""

    number = PhoneNumberField(blank=True)
    ext = models.CharField(max_length=10, blank=True, null=True)
    cell = PhoneNumberField(blank=True,
                            help_text="Cellular number (used for emergency broadcasts)")
    teacher = models.BooleanField(default=False, )
    teaching_language = models.ForeignKey(
        'studentdb.LanguageChoice',
        blank=True,
        null=True,
        on_delete=models.SET_NULL)
    signature = ImageWithThumbsField(upload_to="signatures", blank=True,
                                     null=True,
                                     sizes=((200, 40), (300, 60)),
                                     help_text="Signature for Report Cards")

    def signature_tag(self):
        return u'<img src="%s" />' % self.signature.url_200x40

    signature_tag.short_description = 'Signature'
    signature_tag.allow_tags = True

    def teacherhomeroom(self):
        return ', '.join([str(x) for x in self.teacherhomeroom_set.all()])

    class Meta:
        """Metaclass."""

        verbose_name_plural = "Faculty"
        ordering = ("last_name", "first_name")

    def save(self, make_user_group=True, *args, **kwargs):
        """Save."""
        self.is_staff = True
        super(Faculty, self).save(*args, **kwargs)
        if make_user_group:
            group, created = Group.objects.get_or_create(name="faculty")
            self.groups.add(group)

    def __str__(self):
        """Unicode representation."""
        if self.last_name:
            return u"{0}, {1}".format(self.last_name, self.first_name)
        return self.username

    @property
    def fullname(self):
        """Fullname: Last, First."""
        return u"{0}, {1}".format(self.last_name, self.first_name)

    @property
    def fullname_nocomma(self):
        """Fullname: First Last."""
        return u"{1} {0}".format(self.last_name, self.first_name)


class TeacherHomeroom(models.Model):
    """Homeroom grades for a teacher."""
    teacher = models.ForeignKey('Faculty', on_delete=models.PROTECT)
    grade_level = models.ForeignKey('GradeLevel', on_delete=models.PROTECT)
    primary = models.BooleanField(default=True)

    def __str__(self):
        """Unicode representation."""
        name = self.grade_level.name
        if not self.primary:
            name = "(" + name + ")"
        return name


class ReasonLeft(models.Model):
    """ReasonLeft Model."""

    reason = models.CharField(max_length=255, unique=True)

    def __str__(self):
        """Unicode representation."""
        return self.reason


class GradeLevelManager(models.Manager):
    def get_queryset(self):
        return super(GradeLevelManager, self).get_queryset().filter(is_active=True)


class GradeLevel(models.Model):
    """Grade Model."""

    objects = GradeLevelManager()

    id = models.IntegerField(unique=True, primary_key=True,
                             verbose_name="Grade Number")
    name = models.CharField(max_length=150, unique=True,
                            verbose_name="Grade Name")
    shortname = models.CharField(
        max_length=20, unique=True,
        verbose_name='Abbreviation', blank=True, null=True)
    # name_fr = models.CharField(
    #     max_length=150, verbose_name="Grade Name FR", blank=True, null=True)
    # shortname_fr = models.CharField(
    #     max_length=20, verbose_name='Abbreviation FR', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    next_grade = models.ForeignKey('GradeLevel', null=True,
                                   help_text="Next grade level when rolling over years")

    class Meta:
        """Metaclass."""

        ordering = ('id',)

    def __str__(self):
        """Unicode representation."""
        return str(self.name)  # noqa

    @property
    def grade(self):
        """Grade."""
        return self.id

    @property
    def mailing_list_name(self):
        """Name of mailing list."""
        if self.name in ('Maternelle', 'Jardin'):
            return "parents-%s" % self.name.lower()
        else:
            return "parents-%s" % self.shortname.replace('Gr', '').lower()

    @property
    def mailing_list_displayname(self):
        """Name of mailing list."""
        sy = SchoolYear.objects.filter(active_year=True).first()

        return "Parents %s (%s)" % (self.name, sy.name)

    @property
    def really_short_name(self):
        return re.sub(r'Gr(ade)?[. ]*', '', self.shortname)


class LanguageChoice(models.Model):
    """Language Choice Model."""

    name = models.CharField(unique=True, max_length=255)
    iso_code = models.CharField(
        blank=True, max_length=2,
        help_text="ISO 639-1 Language code "
                  " http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes")
    default = models.BooleanField(default=False, )

    def __str__(self):
        """Unicode representation."""
        return str(self.name)  # noqa

    def save(self, *args, **kwargs):
        """Save."""
        if self.default:
            for language in LanguageChoice.objects.filter(default=True):
                language.default = False
                language.save()
        super(LanguageChoice, self).save(*args, **kwargs)


class IntegerRangeField(models.IntegerField):
    """Integer range field."""

    def __init__(self, verbose_name=None, name=None, min_value=None,
                 max_value=None, **kwargs):
        """Init."""
        self.min_value, self.max_value = min_value, max_value
        models.IntegerField.__init__(self, verbose_name, name, **kwargs)

    def formfield(self, **kwargs):
        """Formfield overrides."""
        defaults = {'min_value': self.min_value, 'max_value': self.max_value}
        defaults.update(kwargs)
        return super(IntegerRangeField, self).formfield(**defaults)


def get_default_language():
    """Get configured default language."""
    if LanguageChoice.objects.filter(default=True).count():
        return LanguageChoice.objects.filter(default=True)[0]


if settings.MIGRATIONS_DISABLED is True:
    family_ref = 'auth.User'
else:
    family_ref = 'FamilyAccessUser'


class Student(User, CustomFieldModel):
    """A student."""

    mname = models.CharField(max_length=150, blank=True, null=True,
                             verbose_name="Middle Name(s)")
    grad_date = models.DateField(blank=True, null=True,
                                 validators=settings.DATE_VALIDATORS,
                                 help_text="MM/DD/YYYY")
    pic = ImageWithThumbsField(upload_to="student_pics", blank=True,
                               null=True, sizes=((70, 65), (530, 400)))
    alert = models.CharField(
        max_length=500, blank=True,
        help_text="Warn any user who accesses this record with this text")
    sex = models.CharField(
        max_length=1,
        choices=(('M', 'Male'), ('F', 'Female')), blank=True, null=True,
        default='F')
    bday = models.DateField(
        blank=True, null=True, verbose_name="Birth Date",
        validators=settings.DATE_VALIDATORS,
        help_text="MM/DD/YYYY")
    year = models.ForeignKey(
        GradeLevel,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="Grade level")
    date_dismissed = models.DateField(blank=True, null=True,
                                      validators=settings.DATE_VALIDATORS,
                                      help_text="MM/DD/YYYY")
    reason_left = models.ForeignKey(ReasonLeft, blank=True, null=True, on_delete=models.SET_NULL)
    unique_id = models.IntegerField(
        blank=True, null=True, unique=True,
        help_text="For integration with outside databases")

    healthcard_no = models.CharField(
        max_length=20, blank=True, null=True, verbose_name='Health Card No')
    activation_date = models.DateField(
        blank=True, null=True,
        verbose_name="Registration Date", validators=settings.DATE_VALIDATORS,
        help_text="MM/DD/YYYY")

    # These fields are cached from emergency contacts
    parent_guardian = models.CharField(max_length=150, blank=True,
                                       editable=False)
    street = models.CharField(max_length=150, blank=True, null=True, editable=False)
    state = CAUSStateField(blank=True, editable=False, null=True)
    city = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=10, blank=True, null=True,
                           editable=False)
    parent_email = models.EmailField(blank=True, editable=False, null=True)

    family_preferred_language = models.ForeignKey(
        LanguageChoice, blank=True, null=True, default=get_default_language,
        on_delete=models.SET_NULL
    )
    alt_email = models.EmailField(
        blank=True,
        help_text="Alternative student email that is not their school email.")
    notes = models.TextField(blank=True)
    emergency_contacts = models.ManyToManyField(
        EmergencyContact, verbose_name="Student contact", blank=True)
    siblings = models.ManyToManyField('self', blank=True)
    individual_education_program = models.BooleanField(default=False)
    photo_permission = models.CharField(max_length=20, choices=(
        ('Yes', 'Yes'),
        ('No', 'No'),
        ('Unknown', 'Unknown')
    ), default='Yes', null=True, blank=True)
    afterschool_only = models.BooleanField(default=False)
    afterschool_grade = models.ForeignKey(
        GradeLevel,
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="ASP attendance grade level",
        related_name="asp_grade")

    student_account_email = models.CharField(
        max_length=150, blank=True, null=True,
        help_text="Full email address for school provided student email account. eg. Google Apps")
    student_account_initial_pw = models.CharField(
        max_length=30, blank=True, null=True,
        help_text="Initial password for system-created student accounts"
    )

    class Meta:
        """Metaclass."""

        permissions = (
            ("view_student", "View student"),
            ("reports", "View reports"),
        )
        ordering = ("last_name", "first_name")

    def __str__(self):
        """Unicode representation."""
        return u"{0}, {1}".format(self.last_name, self.first_name)

    @classmethod
    def pick_username(cls):
        return 'student-' + ''.join([choice(ascii_letters) for i in range(20)])

    def get_absolute_url(self):
        """Unknown purpose."""
        pass

    @property
    def health_concerns(self):
        """Health Concerns as a string, comma separated."""
        return ", ".join(['{}'.format(x)
                          for x in self.studenthealthconcern_set.all()])

    @property
    def health_concerns_nl(self):
        """Health Concerns as a string, newline delimited."""
        return "\n".join(['{}'.format(x)
                          for x in self.studenthealthconcern_set.all()])

    @property
    def age(self):
        """Student Age."""
        if not self.bday:
            return ''
        return '{}'.format(relativedelta(datetime.now(), self.bday).years)

    @property
    def phone(self):
        """Student Tel no via primary contact."""
        try:
            parent = self.emergency_contacts.order_by('-primary_contact')[0]
            phone = parent.emergencycontactnumber_set.filter(type='H').first()
            if phone:
                return phone.number
            return None
        except IndexError:
            return None

    @property
    def he_she(self):
        """"he" or "she"."""
        return self.gender_to_word("he", "she")

    @property
    def homeroom_teacher(self):
        """Homeroom teacher."""
        obj = self.year.teacherhomeroom_set.filter(
            primary=True, teacher__is_active=True).first()
        if obj:
            return obj.teacher
        return obj

    @property
    def son_daughter(self):
        """"son" or "daughter"."""
        return self.gender_to_word("son", "daughter")

    def get_phone_number(self):
        """Phone number."""
        if self.studentnumber_set.filter(type="C"):
            return self.studentnumber_set.filter(type="C")[0]
        elif self.studentnumber_set.all():
            return self.studentnumber_set.all()[0]

    def get_primary_emergency_contact(self):
        """Primary emergency contact."""
        if self.emergency_contacts.filter(primary_contact=True):
            return self.emergency_contacts.filter(primary_contact=True)[0]

    def gender_to_word(self, male_word, female_word):
        """String based on the sex of student."""
        if self.sex == "M":
            return male_word
        elif self.sex == "F":
            return female_word
        else:
            return male_word + "/" + female_word

    @property
    def mother(self):
        """Find the mother."""
        return self.emergency_contacts.filter(
            relationship_to_student='Mother').first()

    @property
    def father(self):
        """Find the father."""
        return self.emergency_contacts.filter(
            relationship_to_student='Father').first()

    @property
    def parents(self):
        """Find the guardians."""
        return self.emergency_contacts.filter(
            emergency_only=False,
        ).filter(~Q(relationship_to_student__in=('Physician', '')))  # Deals with bad data

    @property
    def primary_parent(self):
        parents = self.parents
        primary = parents.filter(primary_contact=True).first()
        if primary:
            return primary
        if not primary:
            return parents.first()

    @property
    def emergency_contact(self):
        """Find the Emerg contact."""
        return self.emergency_contacts.filter(emergency_only=True).first()

    @property
    def emerg_contacts(self):
        """For API."""
        ec = self.emergency_contacts.filter(
            Q(emergency_only=True) &
            ~Q(relationship_to_student__in=('Physician',))).first()
        if not ec:
            return []
        return [ec]

    def save(self, *args, **kwargs):
        """Save."""
        super(Student, self).save(*args, **kwargs)

        group, gcreated = Group.objects.get_or_create(name="students")
        self.user_ptr.groups.add(group)

    def clean(self, *args, **kwargs):
        """Check if a Faculty exists.

        Can't have someone be a Student and Faculty.
        """
        if Faculty.objects.filter(id=self.id).count():
            raise ValidationError('Cannot be a student AND faculty')
        super(Student, self).clean(*args, **kwargs)

    def graduate_and_create_alumni(self):
        """Graduate a student and move them to Alumni."""
        self.inactive = True
        self.reason_left = ReasonLeft.objects.get_or_create(
            reason="Graduated")[0]
        if not self.grad_date:
            self.grad_date = date.today()
        if 'sis.alumni' in settings.INSTALLED_APPS:
            from sis.alumni.models import Alumni
            Alumni.objects.get_or_create(student=self)
        self.save()

    @property
    def fullname(self):
        """Name: Last, First."""
        return ', '.join((self.last_name, self.first_name))

    @property
    def longname(self):
        """Name: First Last."""
        return ' '.join([n for n in (self.first_name, self.last_name)
                         if n is not None and n != ''])

    def volunteer_hours(self, school_year=None):
        """Calculate volunteer hours for a given school year."""
        if not school_year:
            school_year = SchoolYear.objects.filter(active_year=True).first()
        hours = 0
        for student in set([self]).union(set(s for s in self.siblings.all())):
            hours += sum(vh.hours for vh in student.volunteerhour_set.filter(
                school_year=school_year).all())
        return hours

    def days_absent(self, term=None, school_year=None):
        """Calculate days absent for a given school year/term."""
        if term:
            filter_args = dict(date__gte=term.start_date,
                               date__lte=term.end_date)
        elif school_year:
            filter_args = dict(date__gte=school_year.start_date,
                               date__lte=school_year.end_date)
        else:
            filter_args = {}

        halfs = self.student_attn.filter(
            status__half=True, **filter_args).count() * 0.5
        fulls = self.student_attn.filter(
            status__absent=True, **filter_args).count() * 1.0
        return halfs + fulls

    def times_late(self, term=None, school_year=None):
        """Calculate times late for a given school year/term."""
        if term:
            filter_args = dict(date__gte=term.start_date,
                               date__lte=term.end_date)
        elif school_year:
            filter_args = dict(date__gte=school_year.start_date,
                               date__lte=school_year.end_date)
        else:
            filter_args = {}

        return self.student_attn.filter(
            status__tardy=True, status__excused=False, **filter_args).count()

    @property
    def next_gradelevel(self):
        """Detmine what grade level is next."""
        year = self.year
        if not year:
            return None
        next_id = year.id + 1
        try:
            return GradeLevel.objects.get(pk=next_id)
        except Exception:
            return None

    @property
    def primary_phone(self):
        """Get primary phone number."""
        contact = self.get_primary_emergency_contact()
        if not contact:
            return None
        return contact.primary_phone

    @property
    def rc_filename(self):
        """Generate a filename string."""
        path = [self.year.name, "-", self.fullname]
        return ' '.join(path) + ".pdf"

    def get_all_custom_values(self):
        """Return all custom field values."""
        return [
            {
                "name": field.name,
                "value": self.get_custom_value(field.name)
            }
            for field in self.get_custom_fields if self.get_custom_value(field.name) is not None
        ]


def after_student_m2m(sender, instance, action, reverse, model, pk_set,
                      **kwargs):
    """Handle ECs on student m2m."""
    if hasattr(instance, 'emergency_contacts'):
        if not instance.emergency_contacts.filter(
                primary_contact=True).count():
            # No contacts, set cache to None
            instance.parent_guardian = ""
            instance.city = ""
            instance.street = ""
            instance.state = ""
            instance.zip = ""
            instance.parent_email = ""
            instance.save()
        for ec in instance.emergency_contacts.filter(primary_contact=True):
            ec.cache_student_addresses()


m2m_changed.connect(after_student_m2m,
                    sender=Student.emergency_contacts.through)


class StudentNumber(PhoneNumber):
    """Student's phone number."""

    student = models.ForeignKey(Student, blank=True, null=True, on_delete=models.CASCADE)

    def __str__(self):
        """Unicode representation."""
        return self.number


class StudentFile(models.Model):
    """Student files."""

    file = models.FileField(upload_to="student_files")
    student = models.ForeignKey(Student, on_delete=models.CASCADE)


class StudentHealthRecord(models.Model):
    """Student health records."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    record = models.TextField()


HEALTH_CONCERN_TYPE = (
    ('Allergy', "Allergy"),
    ('Intolerance', "Food intolerance"),
    ('Condition', 'Medical condition/disease/syndrome'),
    ('Diet', 'Dietary restriction(s)'),
    ('Other', 'Other')
)


class StudentHealthConcern(models.Model):
    """Student Heath Concerns."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=HEALTH_CONCERN_TYPE)
    name = models.CharField(
        max_length=255,
        help_text="Short description of health concern")
    notes = models.TextField(
        blank=True,
        help_text="Treatment or condition details")

    def __str__(self):
        """Unicode representation."""
        if self.type:
            return u'{}: {}'.format(self.type, self.name)
        else:
            return 'n/a'


class FoodOrderEvent(models.Model):
    """Food orders."""

    name = models.CharField(
        max_length=255,
        help_text="Short description of food order event")
    date = models.DateField(
        blank=True, null=True,
        validators=settings.DATE_VALIDATORS, help_text='Event Date')
    notes = models.CharField(max_length=4000, blank=True, null=True)

    def __str__(self):
        """Unicode representation."""
        if self.date:
            return u'{} ({})'.format(self.name, self.date.strftime("%Y-%m-%d"))
        else:
            return str(self.name)  # noqa


class FoodOrderItem(models.Model):
    """Food order choices."""

    item = models.CharField(max_length=255, help_text="Name of item")
    active = models.BooleanField(
        default=True, help_text="Whether to list in the data entry form")
    event = models.ForeignKey(FoodOrderEvent, on_delete=models.CASCADE)

    def __str__(self):
        """Unicode representation."""
        return str(self.item)  # noqa


class BulkFoodOrderEntry(models.Model):
    """Wrapper model to make bulk food item entry easy."""

    date = models.DateField(blank=True, null=True,
                            validators=settings.DATE_VALIDATORS)
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str(self):
        """Unicode representation."""
        return "Bulk Food Order Entry"

    def item_count(self):
        """Number of items."""
        return self.studentfoodorder_set.count()


class StudentFoodOrder(models.Model):
    """Food order model."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    school_year = models.ForeignKey('studentdb.SchoolYear', on_delete=models.CASCADE)
    item = models.ForeignKey(FoodOrderItem, blank=False, null=False, on_delete=models.CASCADE)
    quantity = IntegerRangeField(
        unique=False, min_value=1, max_value=10, default=1)
    bulkentry = models.ForeignKey(BulkFoodOrderEntry, blank=True, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        """Unicode representation."""
        return u"{}: {}".format(self.student, self.item)


class VolunteerHour(models.Model):
    """Volunteer Hours model."""

    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    school_year = models.ForeignKey('studentdb.SchoolYear', on_delete=models.PROTECT)
    hours = IntegerRangeField(
        unique=False, min_value=1, max_value=400, default=1)
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        """Unicode representation."""
        return u"{}".format(self.student.fullname)


class SchoolYear(models.Model):
    """School year."""

    name = models.CharField(max_length=255, unique=True)
    start_date = models.DateField(validators=settings.DATE_VALIDATORS)
    end_date = models.DateField(validators=settings.DATE_VALIDATORS)
    grad_date = models.DateField(blank=True, null=True,
                                 validators=settings.DATE_VALIDATORS)
    active_year = models.BooleanField(
        default=False,
        help_text="DANGER!! This is the current school year. There can only "
                  "be one and setting this will remove it from other years. "
                  "If you want to change the active year you almost certainly "
                  "want to click Management, Change School Year.")

    principal = models.ForeignKey(
        User, blank=True, null=True,
        related_name='principal',
        help_text="This school year's headmaster/principal",
        on_delete=models.SET_NULL)

    principal_title = models.CharField(
        max_length=80,
        default="Head of School / Directeur"
    )

    vice_principal = models.ForeignKey(
        User, blank=True, null=True,
        related_name='vice_principal',
        help_text="This school year's assistant headmaster/vice principal",
        on_delete=models.SET_NULL
    )

    vice_principal_title = models.CharField(
        max_length=80,
        default="Assistant Head / Directeur adjointe"
    )

    class Meta:
        """Metaclass."""

        ordering = ('-start_date',)

    def __str__(self):
        """Unicode representation."""
        return self.name

    def save(self, *args, **kwargs):
        """Save."""
        super(SchoolYear, self).save(*args, **kwargs)
        if self.active_year:
            SchoolYear.objects.exclude(id=self.id).update(active_year=False)

    @classmethod
    def get_current_year(self):
        """
        Get the currently active year.
        :return: SchoolYear
        """
        return self.objects.get(active_year=True)


class AfterschoolRegsitrationPeriod(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT)
    start_date = models.DateField(default=date.today,
                                  validators=settings.DATE_VALIDATORS)
    end_date = models.DateField(default=date.today,
                                validators=settings.DATE_VALIDATORS)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        """Unicode representation."""
        return u"{o.start_date} to {o.end_date}".format(o=self)


class AfterschoolPackage(models.Model):
    class Meta:
        ordering = ["-monday", "-tuesday", "-wednesday", "-thursday", "-friday"]

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, null=True, blank=True)
    period = models.ForeignKey(AfterschoolRegsitrationPeriod, on_delete=models.PROTECT, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    cost = models.DecimalField(max_digits=6, decimal_places=2, help_text="List Price", null=True, blank=True)
    days = models.IntegerField(default=1, help_text="Number of days included")
    usage_code = models.CharField(max_length=2, default='1',
                                  help_text="Code to show in aftershool usage report")
    unit_value = models.DecimalField(max_digits=6, decimal_places=2, help_text="Unit value for drop-in programs",
                                     default=1.0)
    carryover = models.BooleanField(default=False,
                                    help_text="Do days carry over during the schoolyear")
    pooled = models.BooleanField(default=False,
                                 help_text="Package is a pool of prepaid days")
    shared = models.BooleanField(default=False,
                                 help_text="Pooled days shared with siblings")
    drop_in = models.BooleanField(default=False,
                                  help_text="Available on a drop-in basis")
    monday = models.BooleanField(default=True)
    tuesday = models.BooleanField(default=True)
    wednesday = models.BooleanField(default=True)
    thursday = models.BooleanField(default=True)
    friday = models.BooleanField(default=True)

    def __str__(self):
        """Unicode representation."""
        if self.period:
            return u"{o.period}: {o.name}".format(o=self)
        else:
            return u"{o.name}".format(o=self)


class AfterschoolPackagesPurchased(models.Model):
    class Meta:
        """Class metadata."""

        verbose_name = "Afterschool packages purchased"
        verbose_name_plural = "Afterschool packages purchased"

    student = models.ForeignKey(Student, on_delete=models.PROTECT)
    package = models.ForeignKey(AfterschoolPackage, on_delete=models.PROTECT)
    date_registered = models.DateField(
        blank=True, null=True,
        validators=settings.DATE_VALIDATORS,
        help_text="MM/DD/YYYY",
        default=datetime.now)

    def __str__(self):
        """Unicode representation."""
        return u"{o.student} - {o.package}".format(o=self)


class BulkAfterschoolAttendanceEntry(models.Model):
    """Wrapper model to make bulk food item entry easy."""

    date = models.DateField(blank=True, null=True,
                            validators=settings.DATE_VALIDATORS,
                            default=datetime.now)
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str(self):
        """Unicode representation."""
        return "Bulk Attendance Entry"

    def item_count(self):
        """Number of items."""
        return self.afterschoolprogramattendance_set.count()


class BulkBeforeschoolAttendanceEntry(models.Model):
    date = models.DateField(blank=True, null=True,
                            validators=settings.DATE_VALIDATORS,
                            default=datetime.now)
    notes = models.CharField(max_length=255, blank=True, null=True)

    def __str(self):
        """Unicode representation."""
        return "Bulk Before school attendance Entry"

    def item_count(self):
        """Number of items."""
        return self.beforeschoolprogramattendance_set.count()


class AfterschoolProgramAttendance(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT)
    student = models.ForeignKey(Student, on_delete=models.PROTECT)
    date = models.DateField(blank=True, null=True,
                            validators=settings.DATE_VALIDATORS,
                            help_text="MM/DD/YYYY",
                            default=datetime.now, db_index=True)
    bulkentry = models.ForeignKey(BulkAfterschoolAttendanceEntry, blank=True, null=True, on_delete=models.SET_NULL)
    package = models.ForeignKey(AfterschoolPackage, on_delete=models.PROTECT, null=True, blank=True)

    def __str__(self):
        """Unicode representation."""
        return u"{o.student} - {o.date} - {o.days}".format(o=self)

    class Meta:
        unique_together = ('student', 'date')

    @property
    def days(self):
        if self.package:
            return self.package.unit_value
        return 1

    @property
    def symbol(self):
        if self.package and self.package.usage_code:
            return self.package.usage_code
        else:
            return 'X'


class BeforeschoolProgramAttendance(models.Model):
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT)
    student = models.ForeignKey(Student, on_delete=models.PROTECT)
    date = models.DateField(blank=True, null=True,
                            validators=settings.DATE_VALIDATORS,
                            help_text="MM/DD/YYYY",
                            default=datetime.now, db_index=True)
    bulkentry = models.ForeignKey(BulkBeforeschoolAttendanceEntry, blank=True, null=True,
                                  on_delete=models.SET_NULL)

    def __str__(self):
        """Unicode representation."""
        return u"{o.student} - {o.date} - {o.days}".format(o=self)

    class Meta:
        unique_together = ('student', 'date')

    @property
    def days(self):
        return 1


def duplicate(obj, changes=None):
    """ Duplicates any object including m2m fields
    changes: any changes that should occur, example
    changes = (('fullname','name (copy)'), ('do not copy me', ''))"""
    if not obj.pk:
        raise ValueError('Instance must be saved before it can be cloned.')
    duplicate = copy.copy(obj)
    duplicate.pk = None
    for change in changes:
        duplicate.__setattr__(change[0], change[1])
    duplicate.save()
    # trick to copy ManyToMany relations.
    for field in obj._meta.many_to_many:
        source = getattr(obj, field.attname)
        destination = getattr(duplicate, field.attname)
        for item in source.all():
            with suppress(Exception):  # m2m, through fields will fail.
                destination.add(item)
    return duplicate


class Term(models.Model):
    name = models.CharField(max_length=255, unique=True)
    shortname = models.CharField(max_length=255)
    start_date = models.DateField(validators=settings.DATE_VALIDATORS)
    end_date = models.DateField(validators=settings.DATE_VALIDATORS)
    school_year = models.ForeignKey(SchoolYear, on_delete=models.PROTECT)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ('-start_date',)

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        # Don't allow draft entries to have a pub_date.
        if self.start_date > self.end_date:
            raise ValidationError('Cannot end before starting!')


class StudentClass(models.Model):

    class Meta:
        verbose_name = "Class"
        verbose_name_plural = "Classes"
        ordering = ('sortorder', 'name', )

    def __str__(self):
        return "%s %s" % (self.shortname, self.school_year)

    def active_students(self):
        return self.students.filter(is_active=True)

    name = models.CharField(max_length=255, unique=False, null=False, blank=False)
    sortorder = models.IntegerField(default=0)
    shortname = models.CharField(max_length=32, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    school_year = models.ForeignKey(SchoolYear, related_name='classes')
    terms = models.ManyToManyField(Term, related_name='classes')
    students = models.ManyToManyField(Student, related_name='classes', blank=True)
    teachers = models.ManyToManyField(Faculty, through='StudentClassTeacher', related_name='classes')


class StudentClassTeacher(models.Model):

    def __str__(self):
        return "%s%s" % (self.teacher.fullname, gettext_lazy(" (Homeroom)") if self.homeroom else "")

    class Meta:
        verbose_name = "Class teachers"

    homeroom = models.BooleanField(default=False)
    teacher = models.ForeignKey(Faculty)
    student_classes = models.ForeignKey(StudentClass)
