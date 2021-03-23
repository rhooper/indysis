#!/usr/bin/python
# -*- coding: utf8 -*-

"""JOA Reports."""
import locale
import re
from datetime import datetime, date, timedelta

from constance import config
from dateutil.relativedelta import relativedelta
from django.db.models import Q
from django.db.models import Sum
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.pagesizes import letter, legal, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm, cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, SimpleDocTemplate, TableStyle, PageBreak

from .models import AfterschoolPackagesPurchased, AfterschoolProgramAttendance
from .models import GradeLevel, SchoolYear, Student, FoodOrderItem, StudentFoodOrder, BeforeschoolProgramAttendance


# from http://www.blog.pythonlibrary.org/2013/08/09/reportlab-how-to-combine-static-content-and-multipage-tables/  # noqa


class BaseReport(object):
    """Base class for PDF reports."""

    report_name = "Sample Report"
    report_title = "Sample Report"
    title_on_every_page = False
    page_size = letter
    top_margin = inch
    left_margin = inch
    right_margin = inch
    bottom_margin = inch
    grid_thickness = 0.25
    school_year = None

    def __init__(self, **kwargs):
        """Constructor."""
        self.school_year = SchoolYear.objects.get(active_year=True)
        self.width, self.height = self.page_size
        self.styles = getSampleStyleSheet()
        self.kwargs = kwargs
        self.normal_style = ParagraphStyle(name='tablecell', fontName='Helvetica',
                                           fontSize=11)
        self.heading_style = ParagraphStyle(name='tablecell', fontName='Helvetica-Bold',
                                            fontSize=11)

    def coord(self, x, y, unit=1):
        """Coordinate.

        http://stackoverflow.com/questions/4726011/wrap-text-in-a-table-reportlab
        Helper class to help position flowables in Canvas objects
        """
        x, y = x * unit, self.height - y * unit
        return x, y

    def run(self, response):
        """Run the report."""
        self.doc = SimpleDocTemplate(response,
                                     pagesize=self.page_size,
                                     leftMargin=self.left_margin,
                                     rightMargin=self.right_margin,
                                     topMargin=self.top_margin,
                                     bottomMargin=self.bottom_margin,
                                     )
        self.pageNo = 1
        self.story = []
        self.add_content(**self.kwargs)

        self.doc.build(self.story, onFirstPage=self.create_page, onLaterPages=self.create_page)
        return response

    def footer(self, canvas, doc):
        """Add footer."""
        canvas.saveState()
        w = (self.width - self.left_margin - self.right_margin) / 3
        time = datetime.now().strftime(u"%Y/%m/%d %T")
        t = Table(
            [["%s - %s" % (config.SCHOOL_NAME, time), "Page %d" % self.pageNo, self.report_name]],
            colWidths=(w, w, w))
        t.setStyle(TableStyle([
            ('SIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('ALIGN', (-1, 0), (-1, 0), 'RIGHT'),
        ]))
        w, h = t.wrap(doc.width, doc.bottomMargin)
        t.drawOn(canvas, doc.leftMargin, h)
        canvas.restoreState()

    def create_page(self, canvas, doc):
        """Create a page."""
        self.c = canvas
        self.footer(self.c, self.doc)
        if self.pageNo == 1 or self.title_on_every_page:
            title = self.styles["Title"]
            header_text = "<b>%s</b>" % self.report_title
            p = Paragraph(header_text, title)
            p.wrapOn(self.c, self.width, self.height)
            p.drawOn(self.c, *self.coord(0, 0, mm))
        self.pageNo += 1

    def add_content(self):
        """ABC method."""
        pass

    def add_heading(self, heading):
        """Heading helper."""
        self.story.append(Paragraph(u"<b>{0}</b>".format(heading),
                                    self.styles['Heading2']))

    def add_text(self, text):
        """Add text."""
        style = ParagraphStyle(name='tablecell', fontName='Helvetica', fontSize=11)
        self.story.append(Paragraph(text, style))

    def page_break(self):
        """Next page."""
        self.story.append(PageBreak())

    def add_table(self, columns, rows, column_widths=None, font_size=11, padding=0,
                  extra_formats=None, bold_headings=True):
        """Add a table that flows over pages."""
        data = [columns] + rows

        table = Table(data, hAlign='LEFT', colWidths=column_widths or [None for c in columns])
        table_style = []
        table_style.append(('FONT', (0, 1), (-1, -1), 'Helvetica'))
        if bold_headings:
            table_style.append(('FONT', (0, 0), (-1, 0), 'Helvetica-Bold'))
        table_style.append(('FONTSIZE', (0, 0), (-1, -1), font_size))
        table_style.append(('VALIGN', (0, 0), (-1, -1), 'TOP'))
        table_style.append(('ALIGN', (0, 0), (-1, -1), 'LEFT'))
        table_style.append(('BOTTOMPADDING', (0, 0), (-1, -1), 3 + padding))
        table_style.append(('TOPPADDING', (0, 0), (-1, -1), 1 + padding))
        table_style.append(('INNERGRID', (0, 0), (-1, -1), self.grid_thickness,
                            colors.darkgray))
        table_style.append(('BOX', (0, 0), (-1, 0), 1, colors.black))
        table_style.append(('BOX', (0, 0), (-1, -1), 1, colors.black))
        if extra_formats:
            table_style.extend(extra_formats)

        table.setStyle(TableStyle(table_style))

        self.story.append(table)


class ClassRoster(BaseReport):
    """Class list."""

    title_on_every_page = True

    def __init__(self, **kwargs):
        """Super."""
        super(ClassRoster, self).__init__(**kwargs)
        self.report_name = "Class Roster / Liste de classe - %s" % self.school_year.name
        self.report_title = self.report_name
        if self.kwargs.get('attendance', False):
            self.page_size = landscape(letter)
            self.top_margin = inch * 0.5
            self.left_margin = inch * 0.5
            self.right_margin = inch * 0.5
            self.bottom_margin = inch * 0.5
            self.grid_thickness = 1

    def add_content(self, grade=None, attendance=False):
        """Content for report."""
        if grade:
            grade_levels = GradeLevel.objects.filter(id=grade)
        else:
            grade_levels = GradeLevel.objects.all()

        column_widths = [25, 250]

        for grade in grade_levels:
            if attendance:
                self.story.append(Paragraph("""<font size=16><b>%s</b> - Attendance</font><br />
                    <br />
                    <br />
                    Teacher: ________________________________________  &nbsp&nbsp&nbsp
                    &nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp&nbsp
                    &nbsp&nbsp&nbsp&nbsp&nbsp&nbsp
                    Date: ________________________  &nbsp&nbsp&nbsp
                    AM: ______  &nbsp&nbsp&nbsp  PM: ______
                    <br/>
                    <br/>
                    <br/>
                """ % grade.name, style=self.normal_style))

            classmates = Student.objects.filter(
                year=grade, is_active=True).order_by('last_name', 'first_name')
            headings = ['#', 'Name']
            if attendance:
                headings.extend(['Present', 'Absent', 'Late', 'Notes'])
                column_widths.extend([70, 70, 70, 200])
                attextra = ('', '', '', '')
            else:
                attextra = ()
            rows = list(enumerate(classmates, 1))
            rows = [(item[0], item[1].fullname) + attextra for item in rows]
            if attendance:
                self.add_table(headings, rows, column_widths=column_widths, font_size=13,
                               padding=4)
            else:
                self.add_heading(grade.name)
                self.add_table(headings, rows, column_widths=column_widths)

            self.page_break()


class AfterschoolAttendance(BaseReport):
    """Afterschool Attendance form."""

    title_on_every_page = True

    def __init__(self, **kwargs):
        """Custom init."""
        super(AfterschoolAttendance, self).__init__(**kwargs)

        # WeThFrSa (3,4,5,6), use next week's monday
        # SuMoTu, use this week's monday
        self.start_of_week = datetime.now()
        weekday = self.start_of_week.isoweekday()
        if weekday >= 3:
            self.start_of_week += timedelta(days=8 - weekday)
        elif weekday == 0:  # Sunday
            self.start_of_week += timedelta(days=1)
        else:  # Monday and Tuesday
            self.start_of_week -= timedelta(days=5 - (6 - weekday))
        self.end_of_week = self.start_of_week + timedelta(days=4)
        self.report_name = "Afterschool Attendance - %s to %s" % (
            self.start_of_week.strftime("%a %b %e, %Y"),
            self.end_of_week.strftime("%a %b %e, %Y"),)
        self.report_title = self.report_name

        self.top_margin = inch * 0.5
        self.left_margin = inch * 0.5
        self.right_margin = inch * 0.5
        self.bottom_margin = inch * 0.5
        self.grid_thickness = 1

    def add_content(self, grade=None):
        """Add content."""
        if grade:
            grade_levels = GradeLevel.objects.filter(id=grade)
        else:
            grade_levels = GradeLevel.objects.all()

        column_widths = [225]

        num_on_page = 0
        self.add_heading(self.report_title)

        for grade in list(grade_levels) + ["ASP"]:

            if grade == "ASP":
                classmates = Student.objects.filter(
                    afterschool_grade=None,
                    afterschool_only=True,
                    is_active=True).order_by('last_name', 'first_name').all()
                heading = "Afterschool Only"
                if len(classmates) == 0:
                    continue
            else:
                classmates = Student.objects.filter(
                    Q(
                        Q(year=grade) |
                        Q(afterschool_grade=grade)
                    ), is_active=True).order_by('last_name', 'first_name').all()
                heading = str(grade)

            packages = AfterschoolPackagesPurchased.objects.filter(
                Q(package__period__start_date__lte=self.end_of_week) &
                Q(package__period__end_date__gte=self.start_of_week) &
                Q(Q(package__monday=True) |
                  Q(package__tuesday=True) |
                  Q(package__wednesday=True) |
                  Q(package__thursday=True) |
                  Q(package__friday=True))
            )
            registration_map = {}
            for package in packages:
                sid = package.student.id
                if sid not in registration_map:
                    registration_map[sid] = [False, False, False, False, False]
                for n, day in enumerate(('monday', 'tuesday', 'wednesday',
                                         'thursday', 'friday')):
                    registration_map[sid][n] = (registration_map[sid][n] or
                                                getattr(package.package,
                                                        day))

            if num_on_page + 2 + len(classmates) > 30:
                self.page_break()
                self.add_heading(self.report_title)
                self.add_heading(heading)
                num_on_page = 2
            else:
                num_on_page += 2
                self.add_heading(heading)

            headings = ['Name']
            headings.extend([
                (self.start_of_week + timedelta(days=a)).strftime("%a %e")
                for a in range(0, 5)])
            column_widths.extend([60 for n in range(0, 5)])
            rows = []
            small_style = ParagraphStyle(name='small_style', fontName='Helvetica',
                                         fontSize=8)
            for item in classmates:
                if item.user_ptr_id in registration_map:
                    attextra = tuple([Paragraph('R', small_style) if day else ''
                                      for day in registration_map[item.user_ptr_id]])
                else:
                    attextra = ('', '', '', '', '')
                name = item.fullname
                if item.afterschool_only:
                    name += "  (ASP Only)"
                rows.append((name,) + attextra)

            num_on_page += len(classmates)
            self.add_table(headings, rows, column_widths=column_widths, font_size=12,
                           padding=3)


class BirthdayList(BaseReport):
    """Birthday list."""

    title_on_every_page = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_name = "Birthdays / Dates de naissance - %s" % self.school_year.name
        self.report_title = self.report_name

    def add_content(self, grade=None, setlocale=locale.setlocale(locale.LC_TIME, "fr_CA.UTF-8")):
        """Content."""
        today = datetime.today()

        if grade:
            if grade == 'by_grade':
                grades = GradeLevel.objects.order_by('id').all()
            else:
                grades = GradeLevel.objects.filter(id=grade)
            for grade in grades:
                birthdays = Student.objects.filter(
                    year=grade,
                    is_active=True).order_by('bday', 'last_name', 'first_name')
                headings = ['Birthday', 'Age', 'Name']
                rows = [(item.bday.strftime("%B %-d, %Y"), item.age, item.fullname)
                        for item in birthdays]
                self.add_heading('%s Birthdays' % (grade,))

                self.add_table(headings, rows, column_widths=(120, 40, 250))
                self.add_text("Age as of %s" % datetime.now().strftime("%b %d, %Y"))
                self.page_break()

        else:
            for month in range(1, 13):
                en_mname = date(today.year, month, 1).strftime(u"%B")
                locale.setlocale(locale.LC_TIME, "fr_CA.UTF-8")
                fr_mname = date(today.year, month, 1).strftime(u"%B")
                locale.resetlocale(locale.LC_TIME)
                # NOTE: This doesn't work on sqlite
                birthdays = Student.objects.extra(
                    select={"day_of_month": "EXTRACT(DAY FROM bday)"}).filter(
                    bday__month=month, is_active=True,
                    year__isnull=False).order_by(
                    'day_of_month', 'last_name', 'first_name')
                headings = ['Birthday', 'Age', 'Name', 'Grade']
                rows = [(item.bday, item.age, item.fullname, item.year.name)
                        for item in birthdays]
                self.add_heading('%s / %s' % (en_mname, fr_mname))

                self.add_table(headings, rows, column_widths=(75, 40, 250, 120))
                self.add_text("Age as of %s" % datetime.now().strftime("%b %d, %Y"))
                self.page_break()


class PhotoPermission(BaseReport):
    """Photo permission report."""

    title_on_every_page = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_name = "Photo Permission - %s" % self.school_year.name
        self.report_title = self.report_name

    def add_content(self, grade=None):
        """Content."""
        if grade:
            grade_levels = GradeLevel.objects.filter(id=grade)
        else:
            grade_levels = GradeLevel.objects.all()
        for grade in grade_levels:
            classmates = Student.objects.filter(
                year=grade, is_active=True).order_by('last_name', 'first_name')
            rows = []
            headings = ['Name', 'Photo Permission']
            red_style = ParagraphStyle(name='tablecell', fontName='Helvetica-Bold',
                                       fontSize=13, textColor=colors.red)
            for st in classmates:
                if st.photo_permission == 'No':
                    style = red_style
                    txt = "NO"
                else:
                    txt = st.photo_permission
                    style = self.normal_style
                permission = Paragraph(txt, style)
                rows.append((st.fullname, permission))
            self.add_heading(grade.name)
            if len(rows) == 0:
                none = ['' for i in headings]
                none[0] = 'None'
                rows.append(none)
            self.add_table(headings, rows, column_widths=(220, 120))
            self.page_break()


def get_phone(obj, type):
    """Get a phone number."""
    item = obj.emergencycontactnumber_set.filter(type=type).first()
    return item.full_number() if item else ''


def expand(obj, emails=False, wrap_email=lambda x: x):
    """Expand a parent object."""
    if obj:
        honorific = obj.honorific.strip('.')
        if honorific in ('Mrs', 'Mr', 'M', 'Mlle', 'Ms', ''):
            honorific = ''
        else:
            honorific = honorific + '. '
        if emails:
            return ('%s, %s%s' % (obj.lname, honorific, obj.fname),
                    [wrap_email(e) for e in
                     filter(lambda x: x, [obj.email, obj.alt_email])])
        else:
            return ('%s, %s%s' % (obj.lname, honorific, obj.fname),
                    get_phone(obj, 'C'), get_phone(obj, 'W'))
    else:
        if emails:
            return ('n/a', '')
        else:
            return ('n/a', '', '')


class ParentList(BaseReport):
    """Parent list."""

    title_on_every_page = True
    page_size = landscape(legal)
    top_margin = 1 * cm
    left_margin = 0.25 * inch
    right_margin = 0.25 * inch
    bottom_margin = 1 * cm

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_name = "Parent list / Liste de parents - %s" % self.school_year.name
        self.report_title = self.report_name

    def add_content(self, grade=None, emails=False):
        """Add content."""
        if emails:
            self.report_title = 'Email Book / Carnet de courriels - %s' % self.school_year.name
            self.report_name = self.report_title

        if grade == 'by_grade':
            for grade in GradeLevel.objects.order_by('id'):
                self._add_content(grade.id, emails)
                self.page_break()
        else:
            self._add_content(grade, emails)

    def _add_content(self, grade, emails):
        heading_override = None
        students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')
        if grade:
            students = students.filter(year__id=grade)
            heading_override = ' - %s' % GradeLevel.objects.get(id=grade).name

        if emails:
            headings = ['Name', 'Gr',
                        'Mother Name', 'Mother Email',
                        'Father Name', 'Father Email']
            column_widths = (160, 30, 150, 220, 140, 220)
        else:
            headings = ['Name', 'Gr',
                        'Mother Name', 'Mother Cell', 'Mother Bus Phone',
                        'Father Name', 'Father Cell', 'Father Bus Phone',
                        'Home Phone']
            column_widths = (160, 30, 150, 80, 115, 140, 80, 115, 80)

        rows = []

        def expand_parent(obj):
            return expand(obj, emails, lambda e: Paragraph(e, self.normal_style))

        def emit_table(rows):
            page_range = (rows[0][0], rows[-1][0])
            rows = [x[1] for x in rows]
            heading_range = '  -   ' + ' to '.join([x.last_name for x in page_range])
            self.add_heading(self.report_title + (heading_override or heading_range))
            self.add_table(headings, rows, column_widths=column_widths, font_size=10)

        for st in students:
            mother = st.emergency_contacts.filter(
                emergency_only=False, relationship_to_student='Mother').first()
            father = st.emergency_contacts.filter(
                emergency_only=False, relationship_to_student='Father').first()

            if st.year:
                grade = st.year.really_short_name
                stdata = (st.fullname, grade) + expand_parent(mother) + expand_parent(father)
            else:
                stdata = (st.fullname, "???") + expand_parent(mother) + expand_parent(father)

            if not emails:
                stdata += (st.phone,)

            rows.append([st, stdata])

            if len(rows) > 25:
                emit_table(rows)
                self.page_break()
                rows = []
        if rows:
            emit_table(rows)


def student_export():
    """Student list for CSV."""
    students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')

    headings = ['ID',
                'Name', 'Gr',
                'Mother Name', 'Mother Cell', 'Mother Work',
                'Father Name', 'Father Cell', 'Father Work',
                'Address', 'City', 'Province', 'Postal Code',
                'Primary Phone',
                'Date of Birth',
                'Health Card No',
                'Registered'
                ]
    data = [headings]

    for student in students:  # type: Student
        mother = student.mother
        father = student.father

        if student.year:
            stdata = (student.user_ptr_id, student.fullname, student.year.shortname
                      ) + expand(mother) + expand(father)
        else:
            stdata = (student.user_ptr_id, student.fullname, "???") + expand(mother) + expand(father)

        primary = student.get_primary_emergency_contact()
        if not primary:
            primary = mother or father

        if not primary:
            stdata += ('', '', '', '',)
            stdata += ('',)
        else:
            stdata += (primary.street, primary.city, primary.state, primary.zip,)
            if primary.primary_phone:
                stdata += (primary.primary_phone.number_ext,)
            else:
                stdata += ('',)

        stdata += (student.bday.strftime("%B %-d, %Y") if student.bday else "", student.healthcard_no)
        stdata += (student.date_joined.strftime("%Y-%m-%d") if student.date_joined is not None else "",)
        data.append(list(str(col) for col in stdata))

    return data


def gerri_export():
    """Student list for CSV."""
    students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')

    headings = [
        'Values',
        'OEN',
        'Grade',
        'Class',
        'First Name', 'Middle Name', 'Last Name',
        'Alias First Name', 'Alias Middle Name', 'Alias Last Name',
        'Gender',
        'Birthdate',
        'Language',
        'Country of Origin',
        'Unit',
        'Street Number',
        'Street Name',
        'Street Type',
        'Street Direction',
        'Rural Route',
        'PoBoxNumber',
        'City',
        'Province',
        'Postal Code',
        'Phone Number',
        'Phone Type',
        'Guardian First Name',
        'Guardian Last Name',
        'Guardian Relationship',
        'Guardian Phone Number',
        'Guardian Phone Type',
        'Guardian2 First Name',
        'Guardian2 Last Name',
        'Guardian2 Relationship',
        'Guardian2 Phone Number',
        'Guardian2 Phone Type'
    ]
    data = [headings]

    for st in students:
        mother = st.mother
        father = st.father

        stdata = ('Values', '',)

        grade_labels = ('JK', 'SK', 'GR1', 'GR2', 'GR3', 'GR4', 'GR5', 'GR6', 'GR7', 'GR8')

        if st.year:
            try:
                stdata += (grade_labels[st.year.id - 1],)
            except IndexError:
                stdata += ('',)
        else:
            stdata += ('',)

        stdata += ('', st.first_name, st.mname, st.last_name)
        stdata += ('', '', '')
        stdata += ('F',)
        bday = st.bday.strftime("%Y-%m-%d") if st.bday else ''
        stdata += (bday, '', '')

        primary = st.get_primary_emergency_contact()
        if not primary:
            primary = mother or father

        if not primary:
            for n in range(0, 11):
                stdata += ('',)

        else:

            street_types = {
                'abbey': 'ABBEY',
                'acres': 'ACRES',
                'allée': 'ALLÉE',
                'alley': 'ALLEY',
                'autoroute': 'AUT',
                'avenue': 'AVE',
                'av': 'AV',
                'ave': 'AV',
                'bay': 'BAY',
                'beach': 'BEACH',
                'bend': 'BEND',
                'boulevard (english)': 'BLVD',
                'boulevard (french)': 'BOUL',
                'by-pass': 'BYPASS',
                'byway': 'BYWAY',
                'campus': 'CAMPUS',
                'cape': 'CAPE',
                'carré': 'CAR',
                'carrefour': 'CARREF',
                'cul-de-sac': 'CDS',
                'cercle': 'CERCLE',
                'chemin': 'CH',
                'chase': 'CHASE',
                'circle': 'CIR',
                'circuit': 'CIRCT',
                'close': 'CLOSE',
                'common': 'COMMON',
                'concession': 'CONC',
                'côte': 'CÔTE',
                'cour': 'COUR',
                'cours': 'COURS',
                'cove': 'COVE',
                'cres': 'CRES',
                'crescent': 'CRES',
                'corners': 'CRNRS',
                'croissant': 'CROIS',
                'crossing': 'CROSS',
                'court': 'CRT',
                'centre': 'CTR',
                'dale': 'DALE',
                'dell': 'DELL',
                'diversion': 'DIVERS',
                'downs': 'DOWNS',
                'drive': 'DR',
                'échangeur': 'ÉCH',
                'end': 'END',
                'esplanade': 'ESPL',
                'estates': 'ESTATE',
                'expressway': 'EXPY',
                'extension': 'EXTEN',
                'farm': 'FARM',
                'field': 'FIELD',
                'forest': 'FOREST',
                'front': 'FRONT',
                'freeway': 'FWY',
                'gate': 'GATE',
                'gardens': 'GDNS',
                'glade': 'GLADE',
                'glen': 'GLEN',
                'green': 'GREEN',
                'grounds': 'GRNDS',
                'grove': 'GROVE',
                'harbour': 'HARBR',
                'heath': 'HEATH',
                'highlands': 'HGHLDS',
                'hill': 'HILL',
                'hollow': 'HOLLOW',
                'heights': 'HTS',
                'highway': 'HWY',
                'île': 'ÎLE',
                'impasse': 'IMP',
                'inlet': 'INLET',
                'island': 'ISLAND',
                'key': 'KEY',
                'knoll': 'KNOLL',
                'landing': 'LANDNG',
                'lane': 'LANE',
                'line': 'LINE',
                'link': 'LINK',
                'lookout': 'LKOUT',
                'limits': 'LMTS',
                'loop': 'LOOP',
                'mall': 'MALL',
                'manor': 'MANOR',
                'maze': 'MAZE',
                'meadow': 'MEADOW',
                'mews': 'MEWS',
                'montée': 'MONTÉE',
                'moor': 'MOOR',
                'mount': 'MOUNT',
                'mountain': 'MTN',
                'orchard': 'ORCH',
                'parade': 'PARADE',
                'parc': 'PARC',
                'passage': 'PASS',
                'path': 'PATH',
                'pines': 'PINES',
                'park': 'PK',
                'parkway': 'PKY',
                'place': 'PL',
                'plateau': 'PLAT',
                'plaza': 'PLAZA',
                'pointe': 'POINTE',
                'port': 'PORT',
                'promenade': 'PROM',
                'point': 'PT',
                'pathway': 'PTWAY',
                'private': 'PVT',
                'quai': 'QUAI',
                'quay': 'QUAY',
                'ramp': 'RAMP',
                'rang': 'RANG',
                'road': 'RD',
                'rd': 'RD',
                'rond-point': 'RDPT',
                'range': 'RG',
                'ridge': 'RIDGE',
                'rise': 'RISE',
                'ruelle': 'RLE',
                'row': 'ROW',
                'route': 'RTE',
                'rue': 'RUE',
                'run': 'RUN',
                'sentier': 'SENT',
                'square': 'SQ',
                'street': 'ST',
                'st': 'ST',
                'subdivision': 'SUBDIV',
                'terrace': 'TERR',
                'thicket': 'THICK',
                'townline': 'TLINE',
                'towers': 'TOWERS',
                'trail': 'TRAIL',
                'turnabout': 'TRNABT',
                'terrasse': 'TSSE',
                'vale': 'VALE',
                'via': 'VIA',
                'view': 'VIEW',
                'villas': 'VILLAS',
                'village': 'VILLGE',
                'vista': 'VISTA',
                'voie': 'VOIE',
                'walk': 'WALK',
                'way': 'WAY',
                'wharf': 'WHARF',
                'wood': 'WOOD',
                'wynd': 'WYND',
            }
            dirs = {
                'north': 'N',
                'east': 'E',
                'south': 'S',
                'west': 'W',
            }
            street_types.update({abbrev.lower(): st_type for st_type, abbrev in street_types.items()})

            addrmatch = re.match(
                r'(\d+)\s+(.*)\s+(\S+)(\s+(N|E|W|S|North|East|West|South))?$',
                primary.street or '', re.IGNORECASE)

            street_type = ''

            if addrmatch:
                if re.search(r'(\d+)$', addrmatch.group(3)):
                    res = re.match(r'(.*)(\d+)$', addrmatch.group(3))
                    stdata += (res.group(2),)
                    street_type = res.group(1)
                else:
                    stdata += ('',)
                    street_type = addrmatch.group(3)
                stdata += (
                    addrmatch.group(1), addrmatch.group(2),
                    street_types.get(street_type.strip(".").lower(), street_type))
                if addrmatch.group(4):
                    stdata += (
                        dirs.get(addrmatch.group(5).strip(".").lower(),
                                 addrmatch.group(5).upper()),)
                else:
                    stdata += ('',)

                stdata += ('', '',)
            else:
                stdata += ('', '', primary.street, '', '', '', '')

        ph_type_map = {
            'C': 'MOBILE',
            'W': 'WORK',
            'H': 'HOME',
            'O': 'HOME'
        }

        if primary:
            stdata += (primary.city, primary.state,
                       primary.zip.replace(' ', '') if primary.zip else '',)
            if primary.primary_phone:
                stdata += (primary.primary_phone.number, 'HOME')
            else:
                stdata += ('', 'HOME')
        else:
            stdata += ('', '')

        if mother:
            stdata += (mother.fname, mother.lname, 'PARENT')
            if mother.primary_phone:
                stdata += (mother.primary_phone.number,
                           ph_type_map.get(mother.primary_phone.type, 'HOME'))
            else:
                stdata += ('', '')
        else:
            stdata += ('', '', '', '', '')

        if father:
            stdata += (father.fname, father.lname, 'PARENT')
            if father.primary_phone:
                stdata += (father.primary_phone.number,
                           ph_type_map.get(father.primary_phone.type, 'HOME'))
            else:
                stdata += ('', '')
        else:
            stdata += ('', '', '', '', '')

        data.append(list(str(col) for col in stdata))

    return data


class HealthConcerns(BaseReport):
    """Allergy report."""

    title_on_every_page = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_name = u"Health Problems / Problèmes de santé - %s" % self.school_year.name
        self.report_title = self.report_name

    page_size = landscape(letter)

    def add_content(self, grade=None):
        """Content."""
        if grade:
            grade_levels = GradeLevel.objects.filter(id=grade)
        else:
            grade_levels = GradeLevel.objects.all()
        for grade in grade_levels:
            classmates = Student.objects.filter(
                year=grade, is_active=True).order_by('last_name', 'first_name')
            rows = []
            headings = ['Name', 'Health issues']
            for st in classmates:
                if st.studenthealthconcern_set.all():
                    concerns = [Paragraph("%s: %s %s" % (
                        hc.type,
                        hc.name,
                        '- %s' % hc.notes if hc.notes else ''), self.normal_style)
                                for hc in st.studenthealthconcern_set.all()]
                    rows.append((st.fullname, concerns))
            self.add_heading(grade.name)
            if len(rows) == 0:
                none = ['' for i in headings]
                none[0] = 'None'
                rows.append(none)
            self.add_table(headings, rows, column_widths=(220, 400))
            self.page_break()


class HealthCards(BaseReport):
    """Health card report."""

    title_on_every_page = True
    page_size = landscape(letter)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_name = u"Health Card Numbers - %s" % self.school_year.name
        self.report_title = self.report_name

    def add_content(self, grade=None):
        """Content."""
        if grade:
            grade_levels = GradeLevel.objects.filter(id=grade)
        else:
            grade_levels = GradeLevel.objects.all()
        for grade in grade_levels:
            classmates = Student.objects.filter(
                year=grade, is_active=True).order_by('last_name', 'first_name')
            rows = []
            headings = ['Name', 'Health Card']
            for st in classmates:
                rows.append((st.fullname, st.healthcard_no))
            self.add_heading(grade.name)
            if len(rows) == 0:
                none = ['' for i in headings]
                none[0] = 'None'
                rows.append(none)
            self.add_table(headings, rows, column_widths=(220, 400))
            self.page_break()


class VolunteerHours(BaseReport):
    """Volunteer Hours report."""

    title_on_every_page = True
    page_size = landscape(letter)

    @property
    def report_name(self):
        """Title."""
        return u"Volunteer Hours - %s" % self.school_year.name

    @property
    def report_title(self):
        """Title."""
        return u"Volunteer Hours - %s" % self.school_year.name

    def add_content(self, grade=None):
        """Content."""
        if grade:
            grade = GradeLevel.objects.filter(id=grade).first()
        else:
            grade = None

        family_seen = set()
        if grade:
            classmates = Student.objects.filter(
                year=grade, is_active=True).order_by('last_name', 'first_name')
        else:
            classmates = Student.objects.filter(is_active=True).order_by(
                'last_name', 'first_name')

        rows = []
        headings = ['Student', 'Hours Accumulated', 'Siblings']
        n = 0
        for st in classmates:
            n += 1
            if n % 29 == 0:
                if grade:
                    self.add_heading(grade.name)
                else:
                    self.add_heading(self.report_name)
                self.add_table(headings, rows, column_widths=(220, 120, 250))
                self.page_break()
                rows = []
            if st in family_seen:
                continue
            siblings = '; '.join([sis.fullname for sis in
                                  st.siblings.filter(is_active=True).all()])
            rows.append((st.fullname, st.volunteer_hours(school_year=self.school_year),
                         siblings))
            family_seen.add(st)
            for sib in st.siblings.filter(is_active=True).all():
                family_seen.add(sib)
        if grade:
            self.add_heading(grade.name)
        else:
            self.add_heading(self.report_name)

        if len(rows) == 0:
            none = ['' for i in headings]
            none[0] = 'None'
            rows.append(none)
        self.add_table(headings, rows, column_widths=(220, 120, 250))
        self.page_break()


class Siblings(BaseReport):
    """Volunteer Hours report."""

    title_on_every_page = True
    page_size = landscape(letter)

    @property
    def report_name(self):
        """Title."""
        return u"Siblings - %s" % self.school_year.name

    @property
    def report_title(self):
        """Title."""
        return u"Siblings - %s" % self.school_year.name

    def add_content(self):
        """Content."""
        family_seen = set()
        siblings = Student.objects.filter(
            is_active=True,
            siblings__isnull=False).order_by('last_name', 'first_name')

        rows = []
        headings = ['Family', 'Siblings']
        n = 0
        for st in siblings:
            if st in family_seen:
                continue
            n += 1
            if n % 29 == 0:
                self.add_heading(self.report_name)
                self.add_table(headings, rows, column_widths=(200, 400))
                self.page_break()
                rows = []

            def sibling_name(family, sibling):
                if family.last_name != sibling.last_name:
                    if sibling.year:
                        return sibling.fullname + " (" + sibling.year.shortname + ")"
                    else:
                        return sibling.fullname + " (???)"
                else:
                    if sibling.year:
                        return sibling.first_name + " (" + sibling.year.shortname + ")"
                    else:
                        return sibling.first_name + " (???)"

            siblings = '; '.join(
                [sibling_name(st, sis) for sis in sorted([sis for sis in
                                                     st.siblings.filter(is_active=True).all()] + [st],
                                                    key=lambda x: x.year)])
            rows.append((st.last_name, siblings))
            family_seen.add(st)
            for sib in st.siblings.filter(is_active=True).all():
                family_seen.add(sib)

        self.add_heading(self.report_name)

        if len(rows) == 0:
            none = ['' for i in headings]
            none[0] = 'None'
            rows.append(none)
        self.add_table(headings, rows, column_widths=(200, 400))
        self.page_break()


class FoodOrders(BaseReport):
    """Food order report."""

    title_on_every_page = True
    page_size = landscape(letter)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.report_name = u"Food Orders - %s" % self.school_year.name
        self.report_title = self.report_name

    def add_content(self, event, grade=None, keyword=None):
        """Content."""
        self.report_name = u"Food Orders%s- %s - %s" % (
            ' (%s) ' % keyword.capitalize() if keyword else '',
            event,
            self.school_year.name
        )

        if grade == 'school':
            grade_levels = [None]
        elif grade:
            grade_levels = GradeLevel.objects.filter(id=grade)
        else:
            grade_levels = GradeLevel.objects.all()

        items = FoodOrderItem.objects.filter(active=True, event=event).order_by('item')
        if keyword:
            items = filter(lambda x: keyword.lower().strip() in x.item.lower(), items)
        sums = [0 for item in items]

        headings = ['Name']
        if grade == 'school':
            headings.append('Grade')
            cw = (200, 50)
        else:
            cw = (220,)

        headings.extend([Paragraph(item.item, self.heading_style) for item in items])
        cw += tuple(400 / len(items) for n in range(0, len(items)))

        def print_table(rows, extra_formats=None):
            if grade:
                if keyword:
                    self.add_heading('%s - %s' % (grade.name, keyword.capitalize()))
                else:
                    self.add_heading(grade.name)

            if len(rows) == 0:
                none = ['' for i in headings]
                none[0] = 'None'
                rows.append(none)
            self.add_table(headings, rows, column_widths=cw, extra_formats=extra_formats)
            self.page_break()

        for grade in grade_levels:

            if grade is not None:
                sums = [0 for item in items]

            classmates = Student.objects.filter(
                is_active=True,
                studentfoodorder__school_year=self.school_year,
                studentfoodorder__item__event=event
            ).order_by('last_name', 'first_name')
            if grade:
                classmates = classmates.filter(year=grade)

            rows = []
            rowcount = 0

            for st in classmates.distinct():
                rowcount += 1

                if rowcount % 25 == 0:
                    print_table(rows)
                    rows = []

                record = [st.fullname]
                if grade is None:
                    record.append(st.year.shortname)
                for n, item in enumerate(items):
                    num = StudentFoodOrder.objects.filter(
                        student=st,
                        school_year=self.school_year,
                        item=item
                    ).aggregate(Sum('quantity'))['quantity__sum']
                    if num:
                        sums[n] += num
                    record.append(num or '')
                rows.append(record)

            totals = ['Total']
            if grade is None:
                totals.append('')
            totals.extend(str(n) for n in sums)

            rows.append([Paragraph(s, self.heading_style) for s in totals])
            print_table(rows, extra_formats=[
                ('BOX', (0, -1), (-1, -1), 1, colors.black),
            ])


class Avery5160(object):
    """Avery 5160 labels."""

    width = 2.6 * inch
    sep = 2.75 * inch
    height = 1 * inch
    rows = 10
    cols = 3
    top = 0.5 * inch
    ltopmargin = 0.1 * inch
    lrightmargin = 0.1 * inch


class Avery5161(object):
    """Avery 5161 labels."""

    width = 3.95 * inch
    sep = 4.15 * inch
    height = 1 * inch
    rows = 10
    cols = 2
    top = 0.7 * inch
    left = 0.2 * inch
    ltopmargin = 0.1 * inch
    lrightmargin = 0.25 * inch


class AveryLabels(object):
    """Avery labels base class."""

    labeldef = Avery5160()

    def __init__(self, response, **kwargs):
        """Setup label."""
        self.canv = canvas.Canvas(response, pagesize=LETTER)

        # scale for office printer
        scale = kwargs.get('scale', None)
        offset = kwargs.get('offset', None)
        if scale:
            self.canv.scale(float(scale), float(scale))
        if offset:
            self.canv.translate(0, -LETTER[1] * float(offset))
        self.scale = scale
        self.offset = offset

        self.canv.setPageCompression(0)
        self.kwargs = kwargs
        self.response = response
        self.font_size = 10.5

    def get_contents(self):
        """Contents."""
        return ()

    def run(self):
        """Make label."""
        labeldef = self.labeldef

        def label_position(ordinal):
            y, x = divmod(ordinal, labeldef.cols)
            x = labeldef.left + x * labeldef.sep
            y = LETTER[1] - labeldef.top - y * labeldef.height
            return x, y

        items = iter(self.get_items())
        perpage = labeldef.rows * labeldef.cols

        pos = 0
        try:
            while True:
                item = next(items)
                x, y = label_position(pos)
                # For debugging/testing
                # self.canv.rect(x, y, labeldef.width, -labeldef.height)
                tx = self.canv.beginText(x + labeldef.lrightmargin,
                                         y - 11 - labeldef.ltopmargin)
                tx.setFont('Helvetica', self.font_size, self.font_size + 2.5)
                tx.textLines("\n".join(item))
                self.canv.drawText(tx)
                pos += 1
                if pos >= perpage:
                    self.canv.showPage()
                    pos = 0
                    if self.scale:
                        self.canv.scale(float(self.scale), float(self.scale))
                    if self.offset:
                        self.canv.translate(0, -LETTER[1] * float(self.offset))

        except StopIteration:
            pass

        self.canv.showPage()
        self.canv.save()

        return self.response


class ParentLabels(AveryLabels):
    """Parent labels - Avery 5161."""

    labeldef = Avery5161()

    def get_items(self):
        """Get label content."""

        def format_label(s, parents):
            return [
                " & ".join(p.fullname().strip() for p in parents),
                parents[0].street or '',
                '%s, %s' % (parents[0].city or '', parents[0].state or ''),
                parents[0].zip or ''
            ]

        pseen = set()
        out = []
        students = Student.objects.filter(is_active=True)
        if self.kwargs.get('grade', None):
            students = students.filter(year__id=self.kwargs['grade'])
        for student in students:
            parents = student.emergency_contacts.filter(
                emergency_only=False).order_by('-primary_contact')
            if len(parents) and parents[0] in pseen:
                continue
            if len(parents):
                out.append((parents[0], format_label(student, parents)))

        return [x[1] for x in sorted(out, key=lambda x: x[0].lname)]


class StudentLabels(AveryLabels):
    """Student Labels."""

    labeldef = Avery5161()

    def get_items(self):
        """Get label content."""
        no_grades = self.kwargs.get('no_grades', False)
        students = Student.objects.filter(is_active=True).order_by(
            'year__id', 'last_name', 'first_name')

        if self.kwargs.get('grade', None):
            students = students.filter(year__id=self.kwargs['grade'])

        if no_grades:
            self.font_size = 20
            self.labeldef.ltopmargin = 0.42 * inch
            return [(s.fullname,) for s in students]
        else:
            self.font_size = 15
        return [(s.fullname, s.year.shortname.replace("Gr", "Gr. ") if s.year else '') for s in students]


class AfterSchoolMonthlyUsage(BaseReport):
    """Monthly ASP usage report."""

    title_on_every_page = True
    page_size = landscape(letter)
    month = None

    left_margin = 0.7 * inch
    right_margin = 0.7 * inch
    top_margin = 0.8 * inch

    @property
    def report_name(self):
        """Title."""
        return u"Afterschool Usage - %s" % self.month.strftime("%b %Y")

    @property
    def report_title(self):
        """Title."""
        return u"Afterschool Usage - %s" % self.month.strftime("%b %Y")

    def add_content(self, month=None):
        """Content."""
        if month:
            start = datetime.strptime(month, "%Y-%m-%d")
            school_year = SchoolYear.objects.filter(
                start_date__gte=start, end_date__lte=start).first()
            if school_year:
                self.school_year = school_year
            end = start + relativedelta(months=1) - timedelta(days=1)
        else:
            start = datetime(datetime.now().year, datetime.now().month, 1)
            end = start + relativedelta(months=1) - timedelta(days=1)
        self.month = start

        students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')

        extraspecialstyles = [
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('FONT', (2, 0), (-1, 0), 'Helvetica'),
        ]

        weekdays = []
        curday = start
        headings = ['Student', "Package"]
        while curday <= end:
            if curday.isoweekday() in (1, 2, 3, 4, 5):
                weekdays.append(curday)
                headings.append(str(curday.day))
            curday += timedelta(days=1)
            if curday.isoweekday() == 1:
                extraspecialstyles.append(('BOX', (len(headings), 0),
                                           (len(headings) - 1, -1),
                                           2, colors.black))
        extraspecialstyles.append(('LINEAFTER', (-3, 0),
                                   (-3, -1),
                                   2, colors.black))
        headings += ["Total", "Extra"]
        widths = (150, 70) + tuple([19 for n in weekdays]) + (30, 30)

        rows = []
        cellstyles = []
        n = 0
        for st in students:
            n += 1
            if n % 26 == 0:
                self.add_heading(self.report_name)
                self.add_table(headings, rows, column_widths=widths,
                               font_size=10,
                               extra_formats=extraspecialstyles + cellstyles)
                self.page_break()
                rows = []
                cellstyles = []

            asp = AfterschoolProgramAttendance.objects.filter(
                student=st, date__gte=start, date__lte=end).all()

            packages = AfterschoolPackagesPurchased.objects.filter(
                Q(package__period__start_date__lte=end) &
                Q(package__period__end_date__gte=start) &
                Q(student=st)).all()
            pooled = sum([p.package.days for p in packages if p.package.pooled])

            highlight_days = []
            pkg_day_labels = ['', 'Mo', 'Tu', 'We', 'Th', 'Fr', '']
            for p in packages:
                if p.package.monday:
                    highlight_days.append(1)
                if p.package.tuesday:
                    highlight_days.append(2)
                if p.package.wednesday:
                    highlight_days.append(3)
                if p.package.thursday:
                    highlight_days.append(4)
                if p.package.friday:
                    highlight_days.append(5)

            pkg_days = []
            for dayno in range(1, 6):
                if dayno in highlight_days:
                    pkg_days.append(pkg_day_labels[dayno])

            pkg = ''
            if pooled:
                pkg = "%s days" % pooled
            elif pkg_days:
                pkg = ''.join(pkg_days)

            usage = []
            highlight = {}
            used = {}

            anomaly = ParagraphStyle(name='tablecell', fontName='Helvetica',
                                     fontSize=10, textColor=colors.red)
            normal = ParagraphStyle(name='tablecell', fontName='Helvetica',
                                    fontSize=10)

            total = 0
            extra = 0
            for d in asp:
                dd = datetime(d.date.year, d.date.month, d.date.day)
                if dd not in weekdays:
                    for numdays in (1, -1, -2, 2):
                        if dd + timedelta(days=numdays) in weekdays:
                            dd = dd + timedelta(days=numdays)
                            highlight[dd] = anomaly
                            break
                used[dd] = d.symbol
                if dd.isoweekday() not in highlight_days and not pooled:
                    extra += d.days
                total += d.days

            for weekday in weekdays:
                coords = (len(usage) + 2, len(rows) + 1)
                style = normal
                if weekday in highlight:
                    style = highlight[weekday]
                elif weekday.isoweekday() in highlight_days:
                    cellstyles.append(('BACKGROUND', coords, coords,
                                       colors.Color(0.8, 0.8, 0.8)))

                if weekday in used:
                    usage.append(Paragraph(str(used[weekday]), style))
                    cellstyles.append(('GRID', coords, coords,
                                       1, colors.black))
                else:
                    usage.append(' ')

            rows.append([st.fullname, pkg] + usage + [total if total else '',
                                                      extra if extra else ''])

        self.add_heading(self.report_name)
        self.add_table(headings, rows, column_widths=widths, font_size=10,
                       extra_formats=extraspecialstyles + cellstyles)


class BeforeSchoolMonthlyUsage(BaseReport):
    """Monthly BSP usage report."""

    title_on_every_page = True
    page_size = landscape(letter)
    month = None

    left_margin = 0.7 * inch
    right_margin = 0.7 * inch
    top_margin = 0.8 * inch

    @property
    def report_name(self):
        """Title."""
        return u"Before School Usage - %s" % self.month.strftime("%b %Y")

    @property
    def report_title(self):
        """Title."""
        return u"Before School Usage - %s" % self.month.strftime("%b %Y")

    def add_content(self, month=None):
        """Content."""
        if month:
            start = datetime.strptime(month, "%Y-%m-%d")
            school_year = SchoolYear.objects.filter(
                start_date__gte=start, end_date__lte=start).first()
            if school_year:
                self.school_year = school_year
            end = start + relativedelta(months=1) - timedelta(days=1)
        else:
            start = datetime(datetime.now().year, datetime.now().month, 1)
            end = start + relativedelta(months=1) - timedelta(days=1)
        self.month = start

        students = Student.objects.filter(is_active=True).order_by('last_name', 'first_name')

        extraspecialstyles = [
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('FONT', (2, 0), (-1, 0), 'Helvetica'),
        ]

        weekdays = []
        curday = start
        headings = ['Student']
        while curday <= end:
            if curday.isoweekday() in (1, 2, 3, 4, 5):
                weekdays.append(curday)
                headings.append(str(curday.day))
            curday += timedelta(days=1)
            if curday.isoweekday() == 1:
                extraspecialstyles.append(('BOX', (len(headings), 0),
                                           (len(headings) - 1, -1),
                                           2, colors.black))
        extraspecialstyles.append(('LINEAFTER', (-2, 0),
                                   (-2, -1),
                                   2, colors.black))
        headings += ["Total"]
        widths = (150,) + tuple([19 for n in weekdays]) + (30,)

        rows = []
        cellstyles = []
        n = 0
        for st in students:
            n += 1
            if n % 26 == 0:
                self.add_heading(self.report_name)
                self.add_table(headings, rows, column_widths=widths,
                               font_size=10,
                               extra_formats=extraspecialstyles + cellstyles)
                self.page_break()
                rows = []
                cellstyles = []

            asp = BeforeschoolProgramAttendance.objects.filter(
                student=st, date__gte=start, date__lte=end).all()

            usage = []
            used = {}

            normal = ParagraphStyle(name='tablecell', fontName='Helvetica',
                                    fontSize=10)

            total = 0
            for d in asp:
                dd = datetime(d.date.year, d.date.month, d.date.day)
                if dd not in weekdays:
                    for numdays in (1, -1, -2, 2):
                        if dd + timedelta(days=numdays) in weekdays:
                            dd = dd + timedelta(days=numdays)
                            break
                if dd not in used:
                    used[dd] = d.days
                else:
                    used[dd] += d.days
                total += d.days

            for weekday in weekdays:
                coords = (len(usage) + 1, len(rows) + 1)
                style = normal

                if weekday in used:
                    usage.append(Paragraph(str(used[weekday]), style))
                    cellstyles.append(('GRID', coords, coords,
                                       1, colors.black))
                else:
                    usage.append(' ')

            rows.append([st.fullname] + usage + [total if total else ''])

        self.add_heading(self.report_name)
        self.add_table(headings, rows, column_widths=widths, font_size=10,
                       extra_formats=extraspecialstyles + cellstyles)
