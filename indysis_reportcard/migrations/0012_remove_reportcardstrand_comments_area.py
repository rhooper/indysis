# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-14 17:07
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0011_auto_20181114_1111'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='reportcardstrand',
            name='comments_area',
        ),
    ]
