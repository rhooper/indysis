import datetime

from constance import config
from django.conf import settings
from django.urls import reverse_lazy, reverse
from django.utils.functional import lazy
from report_builder.models import Report
from responsive_dashboard.dashboard import AdminListDashlet, LinksListDashlet, dashboards
from responsive_dashboard.dashboard import Dashboard, Dashlet, ListDashlet

from sis.attendance.models import StudentAttendance
from sis.studentdb.models import Term
from .models import SchoolYear


class ViewStudentDashlet(Dashlet):
    template_name = 'sis/view_student_dashlet.html'


class EventsDashlet(Dashlet):
    template_name = 'sis/events_dashlet.html'

    def get_context_data(self, **kwargs):
        context = super(EventsDashlet, self).get_context_data(**kwargs)
        today = datetime.date.today()
        news_alerts = []

        try:
            school_year = SchoolYear.objects.filter(active_year=True)[0]
        except IndexError:
            school_year = None

        terms = Term.objects.filter(end_date__gte=today).order_by('start_date')
        if terms:
            term = terms[0]
        else:
            term = None

        future_terms = terms.filter(start_date__gte=today)
        if future_terms:
            next_term = future_terms[0]
        else:
            next_term = None

        new_year = None
        if school_year:
            date_delta = school_year.start_date - today
            date_delta = date_delta.days
            if date_delta <= 0 and date_delta > -30:
                news_alerts += ["A new school year has started on {}.".format(school_year.start_date)]
            elif date_delta < 60:
                news_alerts += ['A new school year will start on {}.'.format(school_year.start_date)]

        context.update({
            'term': term,
            'next_term': next_term,
            'school_year': school_year,
            'news_alerts': news_alerts,
        })
        return context


class ReportBuilderDashlet(ListDashlet):
    """ django-report-builder starred reports """
    model = Report
    fields = ('edit', 'name', 'download_xlsx')
    require_apps = ('report_builder',)
    require_permissions = ('report_builder.change_report',)

    def get_context_data(self, **kwargs):
        context = super(ReportBuilderDashlet, self).get_context_data(**kwargs)
        self.queryset = Report.objects.filter(starred=self.request.user)
        return context


class AttendanceDashlet(ListDashlet):
    model = StudentAttendance
    require_permissions_or = ('attendance.admin_studentattendance', 'attendance.take_studentattendance')
    fields = ('student', 'date', 'status')
    first_column_is_link = True
    count = 10

    def get_context_data(self, **kwargs):
        context = super(ListDashlet, self).get_context_data(**kwargs)
        object_list = self.model.objects.filter(date__gte=datetime.datetime.now() - datetime.timedelta(days=7),
                                                date__lte=datetime.date.today() + datetime.timedelta(days=1))

        if self.order_by:
            object_list = object_list.order_by(*self.order_by)

        object_list = object_list[:self.count]

        results = []
        for obj in object_list:
            result_row = []
            for field in self.fields:
                result_row += [getattr(obj, field)]
            obj.result_row = result_row
            results += [obj]

        headers = []
        for field in self.fields:
            if field == '__str__':
                headers += [self.model._meta.verbose_name]
            else:
                try:
                    if getattr(getattr(self.model, field, None), 'short_description', None):
                        headers += [getattr(getattr(self.model, field), 'short_description')]
                    else:
                        headers += [self.model._meta.get_field(field).verbose_name]
                except FieldDoesNotExist:
                    headers += [field]

        opts = self.model._meta
        has_add_permission = self.request.user.has_perm('{}.add_{}'.format(opts.app_label, opts.model_name))
        has_change_permission = self.request.user.has_perm('{}.change_{}'.format(opts.app_label, opts.model_name))

        context.update({
            'opts': opts,
            'object_list': object_list,
            'results': results,
            'headers': headers,
            'show_change': self.show_change,
            'has_add_permission': has_add_permission,
            'has_change_permission': has_change_permission,
            'show_custom_link': self.show_custom_link,
            'custom_link_text': self.custom_link_text,
            'first_column_is_link': self.first_column_is_link,
            'extra_links': self.extra_links,
        })
        return context


class AttendanceLinksListDashlet(LinksListDashlet):
    require_permissions = ('studentdb.admin', )
    title = "Quick Actions"
    links = [
        {
            'text': 'Take attendance',
            'link': reverse_lazy('attendance:daily_attendance'),
            'perm': ('attendance.admin_studentattendance',),
        },
        {
            'text': 'Attendance exception report',
            'link': reverse_lazy('attendance:exception_report'),
            'perm': ('attendance.admin_studentattendance',),
        },
        {
            'text': 'Add attendance record',
            'link': reverse_lazy('admin:attendance_studentattendance_add'),
            'perm': ('attendance.add_studentattendance',),
        },
        {
            'text': 'Afterschool Attendance',
            'link': reverse_lazy('studentdb:afterschool_bulk_form',
                                 kwargs={"grade_id": 1}),
            'perm': ('studentdb.change_bulkafterschoolattendanceentry',),
        },
        {
            'text': 'Before School Attendance',
            'link': reverse_lazy('studentdb:beforeschool_bulk_form',
                                 kwargs={"grade_id": 1}),
            'perm': ('studentdb.change_bulkbeforeschoolattendanceentry',),
        },
        {
            'text': 'Food Order Entry',
            'link': '/admin/studentdb/bulkfoodorderentry/add/',
            'perm': ('studentdb.change_bulkfoodorderentry',),
        },

    ]


# class AttendanceReportBuilderDashlet(ReportBuilderDashlet):
#     show_custom_link = '/admin/report_builder/report/?root_model__app_label=attendance'
#     custom_link_text = "Reports"
#
#     def get_context_data(self, **kwargs):
#         self.queryset = Report.objects.filter(root_model__app_label='attendance')
#         # Show only starred when there are a lot of reports
#         if self.queryset.count() > self.count:
#             self.queryset = self.queryset.filter(starred=self.request.user)
#         return super(ReportBuilderDashlet, self).get_context_data(**kwargs)


class AttendanceAdminListDashlet(AdminListDashlet):
    require_permissions = ('attendance.admin_studentattendance',)


class IndySisReportsDashlet(LinksListDashlet):
    template_name = 'sis/student_reports_dashlet.html'
    require_permissions = 'studentdb.reports'

    links = [
                {
                    'text': 'Class Roster',
                    'link': reverse_lazy('studentdb:class_roster', args='0'),
                },
                {
                    'text': 'Birthdays',
                    'link': reverse_lazy('studentdb:birthdays', args='0'),
                },
                {
                    'text': 'Parent List',
                    'link': reverse_lazy('studentdb:parents', args='0'),
                },
                {
                    'text': 'Health Concerns',
                    'link': reverse_lazy('studentdb:healthconcerns', args='0'),
                },
                {
                    'text': 'Paper Attendance',
                    'link': lazy(lambda: reverse('studentdb:class_roster', args='0') + '?attendance=1'),
                }
            ] + [
                {
                    'text': 'Map',
                    'link': reverse_lazy('studentdb:geocode'),
                    'perm': ('studentdb.view_student',),
                } for n in range(0 if not settings.GOOGLE_MAPS_KEY else 1)
            ] + [
                {
                    'text': 'More reports ...',
                    'link': reverse_lazy('studentdb:student_reports'),
                },
            ]


class SIDashlet(AdminListDashlet):
    require_permissions = ('studentdb.admin', )

    links = [
        {
            'text': 'Import',
            'link': reverse_lazy('simple_import-do_import'),
            'perm': ('studentdb.admin',)
        }
    ]


class SisDashboard(Dashboard):
    app = 'studentdb'
    dashlets = [
        EventsDashlet(title="School Events"),
        ViewStudentDashlet(title="Student"),
        AttendanceLinksListDashlet(title="Links"),
        IndySisReportsDashlet(title="Student Reports"),
        # ReportBuilderDashlet(title="Starred Reports", model=Report),
        AttendanceDashlet(title="Recent Attendance"),
        #AttendanceAdminListDashlet(title="Attendance", app_label="attendance"),
        #SIDashlet(title="School Information", app_label="studentdb"),
    ]
    template_name = "sis_dashboard.html"


dashboards.register('studentdb', SisDashboard)
