# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-02-12 13:46
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('studentdb', '0010_faculty_cell'),
        ('indysis_broadcast', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='broadcastrecipient',
            name='faculty',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='studentdb.Faculty'),
        ),
        migrations.AlterField(
            model_name='broadcastrecipient',
            name='recipient',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='studentdb.EmergencyContact'),
        ),
    ]
