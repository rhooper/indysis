# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-29 10:35
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0007_reportcardtemplateimage'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportcard',
            name='grade_level',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='studentdb.GradeLevel'),
        ),
    ]
