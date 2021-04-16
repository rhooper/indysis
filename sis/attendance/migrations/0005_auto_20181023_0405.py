# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-10-23 04:05
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('studentdb', '0008_auto_20181015_2051'),
        ('attendance', '0004_auto_20181023_0302'),
    ]

    operations = [
        migrations.AlterField(
            model_name='officeattendancelog',
            name='student_class',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='studentdb.StudentClass'),
        ),
        migrations.AlterUniqueTogether(
            name='officeattendancelog',
            unique_together=set([('date', 'student_class', 'ampm')]),
        ),
        migrations.RemoveField(
            model_name='officeattendancelog',
            name='grade_level',
        ),
    ]