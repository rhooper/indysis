# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-15 14:40
from __future__ import unicode_literals

from django.db import migrations, models
import django_extensions.db.fields
import sis.studentdb.thumbs


class Migration(migrations.Migration):

    dependencies = [
        ('indysis_reportcard', '0006_auto_20181013_2340'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportCardTemplateImage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', django_extensions.db.fields.CreationDateTimeField(auto_now_add=True, verbose_name='created')),
                ('modified', django_extensions.db.fields.ModificationDateTimeField(auto_now=True, verbose_name='modified')),
                ('name', models.CharField(help_text='Image name for report card template.', max_length=40)),
                ('image', sis.studentdb.thumbs.ImageWithThumbsField(help_text='Image assets for report cards.', upload_to='reportcard')),
            ],
            options={
                'ordering': ('-modified', '-created'),
                'get_latest_by': 'modified',
                'abstract': False,
            },
        ),
    ]
