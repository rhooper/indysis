# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-08 23:27
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0004_auto_20181007_2120'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportcard',
            name='locked',
        ),
    ]
