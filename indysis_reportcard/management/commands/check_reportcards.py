from django.core.management.base import BaseCommand

from indysis_reportcard.models import ReportCard, ReportCardEntry


class Command(BaseCommand):
    help = """
    Check report cards for duplicate grade entries.
    """

    def handle(self, *args, **options):
        rc: ReportCard
        for rc in ReportCard.objects.all():
            out = False
            items = dict()
            dupes = set()
            entry: ReportCardEntry
            for entry in rc.reportcardentry_set.order_by('section', 'subject', 'strand', 'id').all():
                key = entry.unique_key()
                if key in items:
                    if key not in dupes:
                        print(items[key].dump())
                    print(entry.dump())
                    out = True
                    dupes.add(key)
                else:
                    items[key] = entry
            if out:
                print("----------------------------------------------------------------")