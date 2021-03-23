import logging

from django.db import transaction
from raven.contrib.django.raven_compat.models import client

from indy_sis.celery import app
from indysis_reportcard.models import ReportCardTerm, ReportCard, ReportCardTemplate
from sis.studentdb.models import Student


@app.task
def create_reportcards(term_id):
    term = ReportCardTerm.objects.get(pk=term_id)
    for student in Student.objects.filter(is_active=True, year__isnull=False):
        template = term.get_template(grade=student.year)
        with transaction.atomic():
            try:
                reportcard = ReportCard.objects.get_or_create(student=student, term=term, template=template)
                print("checking report card %s, %s, %s, %s" % (student, term, template, reportcard))
                template.get_or_create_all_entries(reportcard[0])
            except Exception as e:
                client.captureException()
