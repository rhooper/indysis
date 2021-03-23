from anonymizer import Anonymizer

from sis.alumni.models import College, CollegeEnrollment, AlumniStatus, Withdrawl, AlumniNoteCategory, AlumniNote, \
    AlumniAction, AlumniEmail, AlumniPhoneNumber, Alumni


class CollegeAnonymizer(Anonymizer):
    model = College

    attributes = [
        ('id', "SKIP"),
        ('code', "varchar"),
        ('name', "name"),
        ('state', "SKIP"),
        ('type', "SKIP"),
    ]


class CollegeEnrollmentAnonymizer(Anonymizer):
    model = CollegeEnrollment

    attributes = [
        ('id', "SKIP"),
        ('search_date', "date"),
        ('college_id', "SKIP"),
        ('program_years', "SKIP"),
        ('begin', "date"),
        ('end', "date"),
        ('status', "SKIP"),
        ('graduated', "bool"),
        ('graduation_date', "date"),
        ('degree_title', "varchar"),
        ('major', "varchar"),
        ('alumni_id', "SKIP"),
        ('college_sequence', "integer"),
    ]


class AlumniStatusAnonymizer(Anonymizer):
    model = AlumniStatus

    attributes = [
        ('id', "SKIP"),
        ('name', "name"),
    ]


class WithdrawlAnonymizer(Anonymizer):
    model = Withdrawl

    attributes = [
        ('id', "SKIP"),
        ('college_id', "SKIP"),
        ('alumni_id', "SKIP"),
        ('date', "date"),
        ('semesters', "decimal"),
        ('from_enrollment', "bool"),
    ]


class AlumniNoteCategoryAnonymizer(Anonymizer):
    model = AlumniNoteCategory

    attributes = [
        ('id', "SKIP"),
        ('name', "name"),
    ]


class AlumniNoteAnonymizer(Anonymizer):
    model = AlumniNote

    attributes = [
        ('id', "SKIP"),
        ('category_id', "SKIP"),
        ('note', "lorem"),
        ('alumni_id', "SKIP"),
        ('date', "date"),
        ('user_id', "SKIP"),
    ]


class AlumniActionAnonymizer(Anonymizer):
    model = AlumniAction

    attributes = [
        ('id', "SKIP"),
        ('title', "varchar"),
        ('note', "lorem"),
        ('date', "date"),
        ('user_id', "SKIP"),
    ]


class AlumniEmailAnonymizer(Anonymizer):
    model = AlumniEmail

    attributes = [
        ('id', "SKIP"),
        ('email', "email"),
        ('type', "SKIP"),
        ('alumni_id', "SKIP"),
    ]


class AlumniPhoneNumberAnonymizer(Anonymizer):
    model = AlumniPhoneNumber

    attributes = [
        ('id', "SKIP"),
        ('phone_number', "phonenumber"),
        ('type', "SKIP"),
        ('alumni_id', "SKIP"),
    ]


class AlumniAnonymizer(Anonymizer):
    model = Alumni

    attributes = [
        ('id', "SKIP"),
        ('student_id', "SKIP"),
        ('college_id', "SKIP"),
        ('graduated', "bool"),
        ('graduation_date', "date"),
        ('college_override', "bool"),
        ('status_id', "SKIP"),
        ('program_years', "SKIP"),
        ('semesters', "varchar"),
        ('on_track', "bool"),
    ]
