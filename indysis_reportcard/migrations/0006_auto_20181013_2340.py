# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-10-13 23:40
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0005_remove_reportcard_locked'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='reportcardaccess',
            options={'verbose_name': 'Access rule'},
        ),
    ]