# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2018-09-09 22:18
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('studentdb', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentClass',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('shortname', models.CharField(max_length=32)),
                ('description', models.TextField(blank=True, null=True)),
                ('school_year', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='classes', to='studentdb.SchoolYear')),
                ('students', models.ManyToManyField(related_name='classes', to='studentdb.Student')),
            ],
            options={
                'verbose_name': 'Class',
                'verbose_name_plural': 'Classes',
            },
        ),
        migrations.CreateModel(
            name='StudentClassTeacher',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('homeroom', models.BooleanField(default=False)),
                ('student_classes', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='studentdb.StudentClass')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='studentdb.Faculty')),
            ],
            options={
                'verbose_name': 'Class teachers',
            },
        ),
        migrations.AddField(
            model_name='studentclass',
            name='teachers',
            field=models.ManyToManyField(related_name='classes', through='studentdb.StudentClassTeacher', to='studentdb.Faculty'),
        ),
        migrations.AddField(
            model_name='studentclass',
            name='terms',
            field=models.ManyToManyField(related_name='classes', to='studentdb.Term'),
        ),
    ]
