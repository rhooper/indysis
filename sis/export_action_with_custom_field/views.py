from contextlib import suppress

from export_action import report
from export_action.views import AdminExport as AdminExportBase


class AdminExport(AdminExportBase):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['fields'].sort(
            key=lambda x: (x.verbose_name or x.name).lower() if x.name.lower() != 'id' else '0')
        context['related_fields'].sort(
            key=lambda x: (f'{x.verbose_name} {x.description}'
                           if getattr(x, 'verbose_name', None) else x.get_accessor_name()).lower())
        item = context['queryset'].first()
        with suppress(AttributeError):
            context['custom_fields'] = item.get_custom_fields.order_by('name')
        return context

    def post(self, request, **kwargs):
        context = self.get_context_data(**kwargs)
        fields = [field_name for field_name, value in request.POST.items() if value == 'on']
        data_list, _ = report.report_to_list(
            QuerySetWithCustomFields(context['queryset']), fields, self.request.user)
        format = request.POST.get("__format")
        if format == "html":
            return report.list_to_html_response(data_list, header=fields)
        elif format == "csv":
            return report.list_to_csv_response(data_list, header=fields)
        else:
            return report.list_to_xlsx_response(data_list, header=fields)


class QuerySetWithCustomFields:
    def __init__(self, queryset):
        self.queryset = queryset

    def values_list(self, *fields):
        no_custom_fields, ordinary_fields = True, []
        instance = self.queryset.first()
        all_custom_fields = {field.name for field in instance.get_custom_fields}
        for field in fields:
            if field in all_custom_fields:
                # BUG: Can have collisions with existing model fields.
                no_custom_fields = False
            else:
                ordinary_fields.append(field)
        if no_custom_fields:
            yield from self.queryset.values_list(*fields)
            return
        models = self.queryset.all()
        rows = self.queryset.values_list(*ordinary_fields, 'id')
        for instance, row in zip(models, rows):
            assert instance.id == row[-1]
            new_row = tuple(
                row[ordinary_fields.index(field)]
                if field in ordinary_fields
                else instance.get_custom_value(field)
                for field in fields)
            yield new_row

    @property
    def model(self):
        return self.queryset.model
