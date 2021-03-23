# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


def set_year(apps, schema_editor):
    ReportCard = apps.get_model('indysis_reportcard', 'ReportCard')
    for rc in ReportCard.objects.all():
        rc.grade_level = rc.student.year
        rc.save()


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0008_reportcard_grade_level'),
    ]

    operations = [
        migrations.RunPython(set_year),
    ]
