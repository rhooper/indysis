# TODO: Translations

from django import forms
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.core.exceptions import SuspiciousOperation
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import ForeignKey
from django.db.models.fields import AutoField
from django.forms.models import inlineformset_factory
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404, redirect
from simple_import.forms import MatchForm, MatchRelationForm
from simple_import.models import ImportSetting, RelationalMatch
from simple_import.utils import get_all_field_names

from .models import ColumnMatch, ImportLog
from .utils import (
    CellException, formatted_cell_exceptions,
    generate_field_choices, get_choices_for_related_field, header_and_sample_rows,
    read_header_row, save_errors, validate_match_formset, write_row)

User = get_user_model()
MatchFormSet = inlineformset_factory(ImportSetting, ColumnMatch, form=MatchForm, extra=0)


@staff_member_required
def match_columns(request, import_log_id):
    """ View to match import spreadsheet columns with database fields
    """
    import_log = get_object_or_404(ImportLog, id=import_log_id)
    if not request.user.is_superuser and import_log.user != request.user:
        raise SuspiciousOperation("Non superuser attempting to view other users import")
    try:
        header_row, sample_row = header_and_sample_rows(import_log)
    except IndexError:
        messages.error(request, 'Error: Spreadsheet was empty.')
        return redirect('simple_import-start_import')

    model_class = import_log.import_setting.content_type.model_class()
    field_names = get_all_field_names(model_class)
    for field_name in field_names:
        field_object = model_class._meta.get_field(field_name)
        # We can't add a new AutoField and specify it's value
        if import_log.import_type == "N" and isinstance(field_object, AutoField):
            field_names.remove(field_name)

    if request.method == 'POST':
        formset = MatchFormSet(request.POST, instance=import_log.import_setting)
        if formset.is_valid():
            formset.save()
            errors = validate_match_formset(
                request=request, import_log=import_log, model_class=model_class, header_row=header_row, formset=formset)
            if not errors:
                return HttpResponseRedirect(reverse(
                    match_relations,
                    kwargs={'import_log_id': import_log.id}))
    else:
        existing_matches = import_log.get_matches()
        formset = MatchFormSet(instance=import_log.import_setting, queryset=existing_matches)
        errors = []

    field_choices = generate_field_choices(field_names=field_names, model_class=model_class)
    for i, form in enumerate(formset):
        form.fields['field_name'].widget = forms.Select(choices=(field_choices))
        form.sample = sample_row[i]

    return render(
        request,
        'simple_import/match_columns.html',
        {'import_log': import_log, 'formset': formset, 'errors': errors})


@staff_member_required
def match_relations(request, import_log_id):
    import_log = get_object_or_404(ImportLog, id=import_log_id)
    model_class = import_log.import_setting.content_type.model_class()
    matches = import_log.get_matches()
    field_names = []
    choice_set = []

    for match in matches.exclude(field_name=""):
        field_name = match.field_name

        if not(field_name.startswith('simple_import_method__') or
               field_name.startswith('simple_import_customfield__')):
            field = model_class._meta.get_field(field_name)
            m2m = field.many_to_many

            if m2m or isinstance(field, ForeignKey):
                RelationalMatch.objects.get_or_create(
                    import_log=import_log,
                    field_name=field_name)

                field_names.append(field_name)
                choice_set += [get_choices_for_related_field(field)]

    existing_matches = import_log.relationalmatch_set.filter(field_name__in=field_names)

    MatchRelationFormSet = inlineformset_factory(
        ImportLog,
        RelationalMatch,
        form=MatchRelationForm, extra=0)

    if request.method == 'POST':
        formset = MatchRelationFormSet(request.POST, instance=import_log)

        if formset.is_valid():
            formset.save()

            url = reverse('simple_import-do_import', kwargs={'import_log_id': import_log.id})

            if 'commit' in request.POST:
                url += "?commit=True"

            return HttpResponseRedirect(url)
    else:
        formset = MatchRelationFormSet(instance=import_log)

    for i, form in enumerate(formset.forms):
        choices = choice_set[i]
        form.fields['related_field_name'].widget = forms.Select(choices=choices)

    return render(
        request,
        'simple_import/match_relations.html',
        {'formset': formset,
         'existing_matches': existing_matches},
    )


@staff_member_required
def do_import(request, import_log_id):
    """ Import the data! """
    import_log = get_object_or_404(ImportLog, id=import_log_id)
    if import_log.import_type == "N" and 'undo' in request.GET and request.GET['undo'] == "True":
        import_log.undo()
        return HttpResponseRedirect(reverse(
            do_import,
            kwargs={'import_log_id': import_log.id}) + '?success_undo=True')

    import_data = import_log.get_import_file_as_list()
    header_row = import_data.pop(0)
    error_data = [header_row + ['Error Type', 'Error Details']]
    create_count = 0
    update_count = 0
    fail_count = 0
    commit = 'commit' in request.GET and request.GET['commit'] == "True"

    key_field_name, key_index, header_row_field_names, header_row_default, header_row_null_on_empty = read_header_row(
        import_log, header_row)

    with transaction.atomic():
        sid = transaction.savepoint()
        for row in import_data:
            try:
                with transaction.atomic(), formatted_cell_exceptions():
                    is_created = write_row(
                        import_log=import_log, row=row, user_id=request.user.pk, key_index=key_index,
                        key_field_name=key_field_name, header_row_field_names=header_row_field_names,
                        header_row_null_on_empty=header_row_null_on_empty, header_row_default=header_row_default)
                    if is_created:
                        create_count += 1
                    else:
                        update_count += 1
            except CellException as e:
                error_data += [row + e.error]
                fail_count += 1
        if not commit:
            transaction.savepoint_rollback(sid)

    if fail_count:
        save_errors(import_log, error_data)

    success_undo = request.GET.get('success_undo', None) == 'True'

    return render(
        request,
        'simple_import/do_import.html',
        {
            'error_data': error_data,
            'create_count': create_count,
            'update_count': update_count,
            'fail_count': fail_count,
            'import_log': import_log,
            'commit': commit,
            'success_undo': success_undo},
    )
