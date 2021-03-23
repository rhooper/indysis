import re
from contextlib import suppress
import csv
from typing import Dict

import dateparser
from django.core.management.base import BaseCommand

from sis.studentdb import models
from sis.studentdb.models import EmergencyContactNumber, EmergencyContact


class Command(BaseCommand):
    help = """
    Import student and parent contact information from CSV/spreadsheet files.

    Assumes a student in a grade will have a unique first name and last name.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('filename')

    def handle(self, *args, **options):
        with open(options['filename'], newline='') as csv_file:
            reader = csv.DictReader(csv_file)
            # self.stdout.write(repr(reader.fieldnames))
            # TODO: Get these field names from input.
            import_students_from_csv(
                reader,
                student_search_fields=['year', 'last_name', 'first_name'],
                student_field_mappings={
                    'year': 'Grade',
                    'last_name': 'Student last name',
                    'first_name': 'Student first name',
                    'notes': 'NOTES',
                    'sex': 'Gender'},
                first_parent_search_fields=['email'],
                first_parent_field_mappings={
                    'email': 'Parent 1 email',
                    'lname': 'Parent 1 last name',
                    'fname': 'Parent 1 first name',
                    'street': 'Street',
                    'city': 'City',
                    'state': 'Province',
                    'zip': 'Postal code',
                },
                second_parent_search_fields=['email'],
                second_parent_field_mappings={
                    'email': 'Parent 2 e-mail',
                    'lname': 'Parent 2 last name',
                    'fname': 'Parent 2 first name',
                    'street': 'Street',
                    'city': 'City',
                    'state': 'Province',
                    'zip': 'Postal code',
                })


def add_number(row: Dict, fieldname: str, type: str, contact: EmergencyContact, is_primary: bool):
    """
    Adds a phone number to a contact, if it can be parsed.

    Return value is the value of is_primary on failure, or False on success.
    This is so that the value of is_primary can be passed on to the next phone number for a contact, ensuring
    only the first number added is set to primary.

    :param row:
    :param fieldname:
    :param type:
    :param contact:
    :param is_primary:
    :return: bool
    """
    if fieldname not in row:
        return is_primary

    if row[fieldname].strip() == '':
        return is_primary

    match = re.match(r'^([+0-9 ()-.]+)((\s*e?xt?(ension)?\s*)(\d+))?\s*$', row[fieldname], flags=re.IGNORECASE)
    if not match:
        print("Unable to parse phone number %s in row %s" % (row[fieldname], row))
        return is_primary

    number = EmergencyContactNumber(type=type)
    number.number = match.group(1).strip()
    if match.group(5):
        number.ext = match.group(5)
    number.contact = contact
    number.primary = is_primary
    number.save()

    return False


def import_students_from_csv(
        csv_reader, *, student_search_fields, student_field_mappings,
        first_parent_search_fields, first_parent_field_mappings,
        second_parent_search_fields, second_parent_field_mappings):
    for row in csv_reader:
        row = {key: value.strip() if isinstance(value, str) else value for key, value in row.items()}
        row['Gender'] = row['Gender'].upper()
        if not row['Student first name']:
            continue
        student = populate_obj(
            model=models.Student, row=row,
            search_fields=student_search_fields,
            defaults={'username': models.Student.pick_username},
            field_mappings=student_field_mappings)
        student.bday = dateparser.parse(row['Student date of Birth'])
        if student.bday is None:
            print("Failed to parse DOB %s in %s" % (row['Student date of Birth'], row))
        student.save()

        if row['Parent 1 first name']:
            first_parent = populate_obj(
                model=models.EmergencyContact, row=row,
                search_fields=first_parent_search_fields,
                field_mappings=first_parent_field_mappings)
            first_parent.relationship_to_student = 'Mother'
            first_parent.primary_contact = True
            first_parent.save()
            first_parent.emergencycontactnumber_set.all().delete()
            is_primary = add_number(row, 'Parent 1 Cell. phone', 'C', first_parent, True)
            is_primary = add_number(row, 'Parent 1 Home phone', 'H', first_parent, is_primary)
            add_number(row, 'Parent 1 Work phone', 'W', first_parent, is_primary)
            student.emergency_contacts.add(first_parent)

        if row['Parent 2 first name']:
            second_parent = populate_obj(
                model=models.EmergencyContact, row=row,
                search_fields=second_parent_search_fields,
                field_mappings=second_parent_field_mappings)
            second_parent.relationship_to_student = 'Father'
            second_parent.primary_contact = True
            second_parent.save()
            second_parent.emergencycontactnumber_set.all().delete()
            is_primary = add_number(row, 'Parent 2 Cell. phone', 'C', second_parent, True)
            is_primary = add_number(row, 'Parent 2 Home phone', 'H', second_parent, is_primary)
            add_number(row, 'Parent 2 Work phone', 'W', second_parent, is_primary)
            student.emergency_contacts.add(second_parent)


def populate_obj(*, model, row, search_fields, field_mappings, defaults={}):
    row = row.copy()
    for attrname, fieldname in field_mappings.items():
        if attrname in deserializers:
            row[fieldname] = deserializers[attrname](row[fieldname])
    object, _ = model.objects.get_or_create(
        **{attrname: row[field_mappings[attrname]] for attrname in search_fields},
        defaults=defaults)
    for attrname, fieldname in field_mappings.items():
        try:
            setattr(object, attrname, row[fieldname])
        except KeyError:
            pass
    object.save()
    return object


def deserialize_grade(grade):
    with suppress(models.GradeLevel.DoesNotExist):
        return models.GradeLevel.objects.get(shortname=grade)


deserializers = {'year': deserialize_grade}
