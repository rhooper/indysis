from anonymizer import Anonymizer

from indysis_reportcard.models import ReportCardEntry


class ReportCardEntryAnonymizer(Anonymizer):
    model = ReportCardEntry

    attributes = [
        ('id', "SKIP"),
        ('created', "SKIP"),
        ('modified', "SKIP"),
        ('reportcard_id', "SKIP"),
        ('section_id', "SKIP"),
        ('subject_id', "SKIP"),
        ('strand_id', "SKIP"),
        ('percentile', "SKIP"),
        ('choice_id', "SKIP"),
        ('comment', "similar_lorem"),
        ('completed', "SKIP"),
    ]
