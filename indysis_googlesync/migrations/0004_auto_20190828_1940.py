# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2019-08-28 19:40
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('studentdb', '0012_auto_20190828_1918'),
        ('indysis_googlesync', '0003_auto_20181125_1053'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentGradeOUMapping',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('ou', models.CharField(max_length=100)),
                ('level', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='google_ou_mapping', to='studentdb.GradeLevel')),
            ],
            options={
                'verbose_name': 'Grade level to Google OU mapping',
                'ordering': ['level'],
            },
        ),
        migrations.AlterField(
            model_name='extraemailaddress',
            name='group',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extra_emails', to='indysis_googlesync.GoogleGroupSync'),
        ),
    ]
