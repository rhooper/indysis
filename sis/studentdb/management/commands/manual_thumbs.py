from django.core.management.base import BaseCommand

from sis.studentdb.models import Student


class Command(BaseCommand):
    help = """
    Manually generate thumbnail pictures if it doesn't work for whatever reason from a media file.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(['format', 'f'])

    def handle(self, *args, **options):
        from sis.studentdb.thumbs import generate_thumb
        students = Student.objects.filter(pic__isnull=False)
        if options['format']:
            format = options['format']
        else:
            format = 'jpeg'
        for student in students:
            if student.pic != '':
                generate_thumb(student.pic, (70, 65), format)
                generate_thumb(student.pic, (530, 400), format)
        # path = os.path.join(settings.MEDIA_ROOT,'student_pics/')
        # pictures = glob.glob(os.path.join(path,'*.jpg'))
        #

        # for infile in pictures:
        #    #file = os.open(infile, os.O_RDWR)
        #    generate_thumb(infile, (70,65), format)
        #    generate_thumb(infile, (530,400), format)
        #    #os.close(infile)
