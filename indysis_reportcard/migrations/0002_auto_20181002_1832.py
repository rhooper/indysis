# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-02 18:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='gradingschemelevelchoice',
            name='description',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name='gradingschemelevelchoice',
            name='description_en',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
        migrations.AddField(
            model_name='gradingschemelevelchoice',
            name='description_fr',
            field=models.CharField(blank=True, max_length=80, null=True),
        ),
    ]