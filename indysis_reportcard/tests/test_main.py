# Create your tests here.
from datetime import timedelta, datetime

from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from sis.studentdb.models import Faculty, SchoolYear


class ReportCardTestCase(TestCase):
    def setUp(self):
        self.user = Faculty.objects.create_user(username='testuser', password='12345')
        self.group: Group = Group.objects.create(name='Report Card Admins')
        perm = Permission.objects.get(codename='change_reportcard')
        self.group.permissions.add(perm)
        self.user.groups.add(self.group)
        login = self.client.login(username='testuser', password='12345')
        SchoolYear.objects.create(name="Current Year", start_date=datetime.now(), end_date=datetime.now() + timedelta(days=90),
                                  active_year=True)

    def test_index(self):
        # This will not work until templates are bundled in indysis installs
        # self.client.get('/reportcard/')
        pass

    def test_admin(self):
        self.client.get('/admin/indysis_reportcard/')

