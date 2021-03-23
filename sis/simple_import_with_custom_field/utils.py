from contextlib import contextmanager
import logging
import sys

from custom_field.models import CustomField
from django.conf import settings
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.db.models import ForeignKey
from django.db.models.fields import BooleanField
from django.utils.encoding import smart_text
from simple_import.models import ImportedObject, RelationalMatch
from simple_import.views import is_foreign_key_id_name, validate_match_columns
from simple_import.utils import get_all_field_names


User = get_user_model()


@contextmanager
def formatted_cell_exceptions():
    try:
        yield
    except IntegrityError as e:
        exc = sys.exc_info()
        raise CellException(["Integrity Error", smart_text(exc[1])]) from e
    except ObjectDoesNotExist as e:
        exc = sys.exc_info()
        raise CellException(["No Record Found to Update", smart_text(exc[1])]) from e
    except ValueError as e:
        exc = sys.exc_info()
        if str(exc[1]).startswith('invalid literal for int() with base 10'):
            raise CellException(
                ["Incompatible Data - A number was expected, but a character was used",
                 smart_text(exc[1])]) from e
        else:
            raise CellException(["Value Error", smart_text(exc[1])]) from e
    except Exception as e:
        logging.exception("Unknown Error")
        raise CellException(["Unknown Error"]) from e


class CellException(Exception):
    def __init__(self, error):
        self.error = error


def generate_custom_field_choices(model_class):
    return tuple(
        (f'simple_import_customfield__{field.id}', f'{field.name} (Custom field)')
        for field in model_class().get_custom_fields)


def generate_field_choices(*, field_names, model_class):
    field_choices = (('', 'Do Not Use'),)
    for field_name in field_names:
        field_object = model_class._meta.get_field(field_name)
        direct = field_object.concrete
        m2m = field_object.many_to_many
        if direct:
            field_verbose = field_object.verbose_name
        else:
            field_verbose = field_name

        if direct and not field_object.blank:
            field_verbose += " (Required)"
        if direct and field_object.unique:
            field_verbose += " (Unique)"
        if m2m or isinstance(field_object, ForeignKey):
            field_verbose += " (Related)"
        elif not direct:
            continue
        if is_foreign_key_id_name(field_name, field_object):
            continue
        field_choices += ((field_name, field_verbose),)
    # Include defined methods
    # Model must have a simple_import_methods defined
    for import_method in getattr(model_class, 'simple_import_methods', []):
        field_choices += ((f"simple_import_method__{import_method}", f"{import_method} (Method)"),)
    # User model should allow set password
    if issubclass(model_class, User):
        field_choices += (("simple_import_method__set_password", "Set Password (Method)"),)
    field_choices += generate_custom_field_choices(model_class)
    return field_choices


def get_choices_for_related_field(field):
    choices = ()
    if hasattr(field, 'related'):
        try:
            parent_model = field.related.parent_model()
        except AttributeError:  # Django 1.8+
            parent_model = field.related.model
    else:
        parent_model = field.related_model
    for field in get_direct_fields_from_model(parent_model):
        if field.unique:
            choices += ((field.name, str(field.verbose_name)),)
    return choices


def get_direct_fields_from_model(model_class):
    direct_fields = []
    all_field_names = get_all_field_names(model_class)
    for field_name in all_field_names:
        field = model_class._meta.get_field(field_name)
        direct = field.concrete
        m2m = field.many_to_many
        if direct and not m2m and field.__class__.__name__ != "ForeignKey":
            direct_fields += [field]
    return direct_fields


def get_new_object_for_import(*, import_log, model_class, filters: dict):
    is_created = True
    if import_log.import_type == "N":
        new_object = model_class()
    elif import_log.import_type == "O":
        new_object = model_class.objects.get(**filters)
        is_created = False
    elif import_log.import_type == "U":
        new_object = model_class.objects.filter(**filters).first()
        if new_object is None:
            new_object = model_class()
            is_created = False
    return new_object, is_created


def header_and_sample_rows(import_log):
    import_data = import_log.get_import_file_as_list()
    header_row = [x.lower() for x in import_data[0]]
    sample_row = import_data[1]
    return header_row, sample_row


def read_header_row(import_log, header_row):
    header_row_field_names = []
    header_row_default = []
    header_row_null_on_empty = []
    key_column_name = None
    key_field_name = None
    key_index = 0
    if import_log.update_key and import_log.import_type in ["U", "O"]:
        key_match = import_log.import_setting.columnmatch_set.get(column_name=import_log.update_key)
        key_column_name = key_match.column_name
        key_field_name = key_match.field_name
    for i, cell in enumerate(header_row):
        match = import_log.import_setting.columnmatch_set.get(column_name=cell)
        header_row_field_names += [match.field_name]
        header_row_default += [match.default_value]
        header_row_null_on_empty += [match.null_on_empty]
        if key_column_name is not None and key_column_name.lower() == cell.lower():
            key_index = i
    return key_field_name, key_index, header_row_field_names, header_row_default, header_row_null_on_empty


def save_errors(import_log, error_data: list):
    from django.core.files.base import ContentFile
    from openpyxl.workbook import Workbook
    from openpyxl.writer.excel import save_virtual_workbook

    wb = Workbook()
    ws = wb.worksheets[0]
    ws.title = "Errors"
    filename = 'Errors.xlsx'
    for row in error_data:
        ws.append(row)
    import_log.error_file.save(filename, ContentFile(save_virtual_workbook(wb)))
    import_log.save()


def set_custom_field_from_cell(import_log, new_object, header_row_field_name, cell):
    _, custom_field_id = header_row_field_name.split('__')
    custom_field = CustomField.objects.get(pk=int(custom_field_id))
    new_object.set_custom_value(custom_field.name, cell)


def set_from_cell(import_log, new_object, header_row_field_name, cell):
    if header_row_field_name.startswith('simple_import_method__'):
        set_method_from_cell(import_log, new_object, header_row_field_name, cell)
        return
    if header_row_field_name.startswith('simple_import_customfield__'):
        set_custom_field_from_cell(import_log, new_object, header_row_field_name, cell)
        return
    set_field_from_cell(import_log, new_object, header_row_field_name, cell)


def set_field_from_cell(import_log, new_object, header_row_field_name, cell):
    """Set a field from import cell.

    Use referenced fields if the field is m2m or a foreign key.
    """
    field = new_object._meta.get_field(header_row_field_name)
    m2m = field.many_to_many
    if m2m:
        new_object.simple_import_m2ms[header_row_field_name] = cell
        return
    if isinstance(field, ForeignKey):
        related_field_name = RelationalMatch.objects.get(
            import_log=import_log,
            field_name=field.name,
        ).related_field_name
        related_model = field.remote_field.parent_model
        related_object = related_model.objects.get(**{related_field_name: cell})
        setattr(new_object, header_row_field_name, related_object)
        return
    if field.choices and getattr(settings, 'SIMPLE_IMPORT_LAZY_CHOICES', True):
        # Trim leading and trailing whitespace from cell values
        if getattr(settings, 'SIMPLE_IMPORT_LAZY_CHOICES_STRIP', False):
            cell = cell.strip()
        # Prefer database values over choices lookup
        database_values, verbose_values = zip(*field.choices)
        if cell not in database_values and cell in verbose_values:
            for choice in field.choices:
                if smart_text(cell) == smart_text(choice[1]):
                    setattr(new_object, header_row_field_name, choice[0])
                    return
    if isinstance(field, BooleanField) and cell == 'FALSE':
        # Some formats/libraries report booleans as strings
        setattr(new_object, header_row_field_name, False)
        return
    setattr(new_object, header_row_field_name, cell)


def set_method_from_cell(import_log, new_object, header_row_field_name, cell):
    """Run a method from import cell."""
    getattr(new_object, header_row_field_name[22:])(cell)


def update_import_log(*, update_key, import_log, model_class):
    if update_key:
        field_name = import_log.import_setting.columnmatch_set.get(column_name=update_key).field_name
        if field_name:
            field_object = model_class._meta.get_field(field_name)
            direct = field_object.concrete
            if direct and field_object.unique:
                import_log.update_key = update_key
                import_log.save()
            else:
                raise ValidationError('Update key must be unique. Please select a unique field.')
        else:
            raise ValidationError('Update key must matched with a column.')
    else:
        raise ValidationError('Please select an update key. This key is used to linked records for updating.')


def validate_field_names(formset):
    errors = []
    all_field_names = []
    for clean_data in formset.cleaned_data:
        if clean_data['field_name']:
            if clean_data['field_name'] in all_field_names:
                errors += ["{0} is duplicated.".format(clean_data['field_name'])]
            all_field_names += [clean_data['field_name']]
    return errors


def validate_match_formset(*, request, import_log, model_class, header_row, formset):
    errors = []
    if import_log.import_type in ["U", "O"]:
        update_key = request.POST.get('update_key', '')
        try:
            update_import_log(update_key=update_key, import_log=import_log, model_class=model_class)
        except ValidationError as e:
            errors.append(e.message)
    errors += validate_match_columns(import_log, model_class, header_row)
    errors += validate_field_names(formset)
    return errors


class ValidationError(ValueError):
    def __init__(self, message):
        self.message = message


def write_row(*, import_log, row, user_id, key_index, key_field_name,
              header_row_field_names, header_row_null_on_empty, header_row_default):
    model_class = import_log.import_setting.content_type.model_class()
    new_object, is_created = get_new_object_for_import(
        import_log=import_log, model_class=model_class, filters={key_field_name: row[key_index]})
    if is_created:
        action_flag = ADDITION
    else:
        action_flag = CHANGE

    new_object.simple_import_m2ms = {}  # Need to deal with these after saving
    for i, cell in enumerate(row):
        if not header_row_field_names[i]:  # skip blank
            continue
        if not import_log.is_empty(cell) or header_row_null_on_empty[i]:
            set_from_cell(import_log, new_object, header_row_field_names[i], cell)
        elif header_row_default[i]:
            set_from_cell(import_log, new_object, header_row_field_names[i], header_row_default[i])
    new_object.save()

    for key, value in new_object.simple_import_m2ms.items():
        m2m = getattr(new_object, key)
        m2m_model = type(m2m.model())
        related_field_name = RelationalMatch.objects.get(
            import_log=import_log, field_name=key).related_field_name
        m2m_object = m2m_model.objects.get(**{related_field_name: value})
        m2m.add(m2m_object)

    LogEntry.objects.log_action(
        user_id=user_id,
        content_type_id=ContentType.objects.get_for_model(new_object).pk,
        object_id=new_object.pk,
        object_repr=smart_text(new_object),
        action_flag=action_flag
    )
    ImportedObject.objects.create(
        import_log=import_log,
        object_id=new_object.pk,
        content_type=import_log.import_setting.content_type)
    return is_created
