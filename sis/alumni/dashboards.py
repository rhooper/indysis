from report_builder.models import Report
from responsive_dashboard.dashboard import Dashboard, ListDashlet, AdminListDashlet, dashboards

from sis.alumni.models import Alumni, AlumniNote
from sis.studentdb.dashboards import ReportBuilderDashlet


class AlumniDashlet(ListDashlet):
    model = Alumni
    require_permissions = ('alumni.change_alumni',)
    fields = ('__str__', 'college', 'status')
    columns = 2
    first_column_is_link = True


class AlumniNoteDashlet(ListDashlet):
    model = AlumniNote
    require_permissions = ('alumni.change_alumninote',)
    fields = ('alumni', 'get_note', 'date')
    columns = 3
    order_by = ('-date',)


class AlumniReportBuilderDashlet(ReportBuilderDashlet):
    """ django-report-builder starred reports """
    show_custom_link = '/admin/report_builder/report/?root_model__app_label=alumni'
    custom_link_text = "Reports"

    def get_context_data(self, **kwargs):
        self.queryset = Report.objects.filter(root_model__app_label='alumni')
        # Show only starred when there are a lot of reports
        if self.queryset.count() > self.count:
            self.queryset = self.queryset.filter(starred=self.request.user)
        return super(ReportBuilderDashlet, self).get_context_data(**kwargs)


class AlumniDashboard(Dashboard):
    app = 'alumni'
    dashlets = [
        AlumniDashlet(title="Alumni"),
        AlumniNoteDashlet(title='Latest Notes'),
        AlumniReportBuilderDashlet(title="Reports", ),
        AdminListDashlet(title="Edit", app_label="alumni"),
    ]
    template_name = "sis_dashboard.html"


dashboards.register('alumni', AlumniDashboard())
