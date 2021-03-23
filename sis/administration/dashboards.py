from django.contrib.admin.models import LogEntry
from django.urls import reverse_lazy
from responsive_dashboard.dashboard import Dashboard, ListDashlet, AdminListDashlet, LinksListDashlet, dashboards


class LogEntryDashlet(ListDashlet):
    model = LogEntry
    fields = ('user', 'action_time', 'content_type', 'object_repr', 'action_flag', 'change_message')
    columns = 2
    count = 8
    require_permissions_or = ('admin.change_log', 'admin.view_log')
    order_by = ('-action_time',)


class AdministrationLinksListDashlet(LinksListDashlet):
    links = [
        {
            'text': 'Import Data',
            'link': reverse_lazy('simple_import-start_import'),
            'desc': '',
            'perm': ('simple_import.change_importlog',),
        },
        {
            'text': 'Configuration',
            'link': '/admin/constance/config',
            'desc': '',
            'perm': ('administration.change_constance',),
        },
        {
            'text': 'Site Logo',
            'link': '/admin/favicon/favicon/',
            'desc': '',
            'perm': ('administration.change_favicon',),
        },
        {
            'text': 'Change School Year',
            'link': reverse_lazy('studentdb:increment_year'),
            'desc': '',
            'perm': ('studentdb.change_student', 'studentdb.change_schoolyear'),
        },
        {
            'text': 'Database Dump',
            'link': '/admin/dump',
            'desc': '',
            'perm': ('admin',),
        },
        {
            'text': 'All Data',
            'link': '/admin',
            'desc': '',
            'perm': ('admin',),
        },
    ]

    def get_verbose_name(self):
        return "Management"


class SortedAdminListDashlet(AdminListDashlet):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_types'] = sorted(context['content_types'], key=lambda x: x.name)
        return context


class AdminDashboard(Dashboard):
    app = 'administration'
    dashlets = [
        # LogEntryDashlet(title="Latest Actions"),
        AdministrationLinksListDashlet(title="Links"),
        SortedAdminListDashlet(title="User Management", app_label="auth"),
        SortedAdminListDashlet(title="Student Data Management", app_label="studentdb"),
        SortedAdminListDashlet(title="Attendance Data Management", app_label="attendance"),
        SortedAdminListDashlet(title="Custom Fields", app_label="custom_field"),
        # ReportBuilderDashlet(title="Report Builder"),
    ]
    template_name = "sis_dashboard.html"


dashboards.register('administration', AdminDashboard)
