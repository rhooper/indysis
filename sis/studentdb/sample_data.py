# never import * except test data (because who cares about clean tests)

from sis.attendance.models import *
from sis.studentdb.models import *


class SisData(object):
    """ Put data creation code here. sample data code not here is punishible by death .
    """

    def create_all(self):
        """ This will populate all sample data """
        self.create_basics()

    def create_required(self):
        """ A place for 100% required data """

    def create_basics(self):
        """ A very simple school, probably want this in mosts tests
        Depends on create_required
        """
        # Run dependencies first
        self.create_required()

        # Use bulk create a few so it looks good in demo
        SchoolYear.objects.bulk_create([
            SchoolYear(name="2013-2014", start_date=datetime.date(2013, 7, 1), end_date=datetime.date(2014, 5, 1)),
            SchoolYear(name="2014-long time", start_date=datetime.date(2014, 7, 1), end_date=datetime.date(2050, 5, 1),
                       active_year=True),
            SchoolYear(name="2015-16", start_date=datetime.date(2015, 7, 1), end_date=datetime.date(2016, 5, 1)),
        ])
        # Set one archetypal object. If I want a year I will use this
        self.school_year = SchoolYear.objects.get(active_year=True)

        # Note bulk does not call save() and other limitations
        # so it's ok to not use bulk
        # Don't change the order, other objects depend on the id being in this order
        self.student = Student.objects.create(first_name="Joe", last_name="Student", username="jstudent")
        self.student2 = Student.objects.create(first_name="Jane", last_name="Student", username="jastudent")
        self.student3 = Student.objects.create(first_name="Tim", last_name="Duck", username="tduck")
        Student.objects.create(first_name="Molly", last_name="Maltov", username="mmaltov")

        Term.objects.bulk_create([
            Term(name="tri1 2014", start_date=datetime.date(2014, 7, 1), end_date=datetime.date(2014, 9, 1),
                 school_year=self.school_year, monday=True, friday=True),
            Term(name="tri2 2014", start_date=datetime.date(2014, 9, 2), end_date=datetime.date(2015, 3, 1),
                 school_year=self.school_year, monday=True, friday=True),
            Term(name="tri3 2014", start_date=datetime.date(2015, 3, 2), end_date=datetime.date(2050, 5, 1),
                 school_year=self.school_year, monday=True, friday=True),
        ])
        self.term = Term.objects.get(name="tri1 2014")
        self.term2 = Term.objects.get(name="tri2 2014")
        self.term3 = Term.objects.get(name="tri3 2014")

        self.teacher1 = self.faculty = Faculty.objects.create(username="dburke", first_name="david", last_name="burke",
                                                              teacher=True)
        self.teacher2 = Faculty.objects.create(username="jbayes", first_name="jeff", last_name="bayes", teacher=True)
        aa = Faculty.objects.create(username="aa", first_name="aa", is_superuser=True, is_staff=True)
        aa.set_password('aa')
        aa.save()
        admin = Faculty.objects.create(username="admin", first_name="admin", is_superuser=True, is_staff=True)
        admin.set_password('admin')
        admin.save()

        self.present = AttendanceStatus.objects.create(name="Present", code="P", teacher_selectable=True)
        self.absent = AttendanceStatus.objects.create(name="Absent", code="A", teacher_selectable=True, absent=True)
        self.excused = AttendanceStatus.objects.create(name="Absent Excused", code="AX", absent=True, excused=True)

    def create_aa_superuser(self):
        aa = Faculty.objects.create(username="aa", first_name="aa", is_superuser=True, is_staff=True)
        aa.set_password('aa')
        aa.save()

    def create_years_and_terms(self):
        self.year = year = SchoolYear.objects.create(name="balt year", start_date=datetime.date(2014, 7, 1),
                                                     end_date=datetime.date(2050, 5, 1), active_year=True)
        self.mp1 = Term.objects.create(name="1st", weight=0.4, start_date=datetime.date(2014, 7, 1),
                                       end_date=datetime.date(2014, 9, 1), school_year=year)
        self.mp2 = Term.objects.create(name="2nd", weight=0.4, start_date=datetime.date(2014, 7, 2),
                                       end_date=datetime.date(2014, 9, 2), school_year=year)
        self.mps1x = Term.objects.create(name="S1X", weight=0.2, start_date=datetime.date(2014, 7, 2),
                                         end_date=datetime.date(2014, 9, 2), school_year=year)
        self.mp3 = Term.objects.create(name="3rd", weight=0.4, start_date=datetime.date(2014, 7, 3),
                                       end_date=datetime.date(2014, 9, 3), school_year=year)
        self.mp4 = Term.objects.create(name="4th", weight=0.4, start_date=datetime.date(2014, 7, 4),
                                       end_date=datetime.date(2014, 9, 4), school_year=year)
        self.mps2x = Term.objects.create(name="S2X", weight=0.2, start_date=datetime.date(2014, 7, 4),
                                         end_date=datetime.date(2014, 9, 4), school_year=year)

    def create_sample_students(self):
        self.create_sample_normal_student()

    def create_sample_normal_student(self):
        self.student = Student.objects.create(first_name="Anon", last_name="Student", username="someone")
