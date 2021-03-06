# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-14 11:11
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0010_auto_20181113_2248'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportcardsection',
            name='gradingscheme_label',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='reportcardsection',
            name='second_gradingscheme_label',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AlterField(
            model_name='reportcardentry',
            name='second_choice',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='second_choice', to='indysis_reportcard.GradingSchemeLevelChoice', verbose_name='2nd Mark'),
        ),
        migrations.AlterField(
            model_name='reportcardsection',
            name='second_gradingscheme',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='second_gradingscheme', to='indysis_reportcard.GradingScheme'),
        ),
    ]
