from django.core.exceptions import ObjectDoesNotExist
from simple_import import models


class ImportLog(models.ImportLog):
    class Meta:
        proxy = True

    def get_matches(self):
        """ Get each matching header row to database match
        Returns a ColumnMatch queryset"""
        header_row = self.get_import_file_as_list(only_header=True)
        match_ids = []

        for i, cell in enumerate(header_row):
            # Sometimes we get blank headers, ignore them.
            if self.is_empty(cell):
                continue

            try:
                match = ColumnMatch.objects.get(
                    import_setting=self.import_setting,
                    column_name=cell,
                )
            except ColumnMatch.DoesNotExist:
                match = ColumnMatch(
                    import_setting=self.import_setting,
                    column_name=cell,
                )
                match.guess_field()

            match.header_position = i
            match.save()

            match_ids += [match.id]

        return ColumnMatch.objects.filter(
            pk__in=match_ids).order_by('header_position')


class ColumnMatch(models.ColumnMatch):
    class Meta:
        proxy = True

    def guess_field(self):
        super().guess_field()
        if self.field_name:
            return
        model = self.import_setting.content_type.model_class()
        try:
            field = model().get_custom_field(self.column_name)
        except (AttributeError, ObjectDoesNotExist):
            return
        self.field_name = f'simple_import_customfield__{field.id}'
