# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-11-17 13:07
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0014_auto_20181117_1227'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportcardsubject',
            name='comments_heading',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='reportcardsubject',
            name='comments_heading_en',
            field=models.TextField(blank=True, default='', null=True),
        ),
        migrations.AddField(
            model_name='reportcardsubject',
            name='comments_heading_fr',
            field=models.TextField(blank=True, default='', null=True),
        ),
    ]
