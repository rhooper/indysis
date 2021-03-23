#!/usr/bin/env python
"""Synchronize Student Users."""
import json
from pprint import pprint

import gdata
import gdata.gauth
import gdata.apps.audit.service
from django.core.management.base import BaseCommand
from oauth2client.service_account import ServiceAccountCredentials
from django.db.models import Q
from httplib2 import Http
import random
import googleapiclient.errors
import datetime
from apiclient import discovery
from unidecode import unidecode
from constance import config

from indysis_googlesync.models import StudentGradeOUMapping
from sis.studentdb.models import Student

SCOPES = [
    'https://apps-apis.google.com/a/feeds/compliance/audit/',
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.orgunit',
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.group'
]

APPLICATION_NAME = 'Password reset - Grade 5 to 8'


def generate_pw():
    """Generate a random password."""
    chars = 'abcdefghjkmnopqrstuvwxyz-.234567890'
    pw = ""
    pick = ""
    for charno in range(0, 12):
        ok = False
        while not ok:
            pick = chars[random.randint(0, len(chars) - 1)]
            if pick not in pw:
                ok = True
        pw += pick
    return pw


class Command(BaseCommand):
    """Resets passwords for Grade 5 to 8."""

    help = 'Resets passwords for Grade 5 to 8'

    def handle(self, *args, **options):
        """Handle the command."""
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.loads(config.GOOGLE_USER_SYNC_SVC_ACCT_CREDS), scopes=SCOPES)
        delegated_credentials = credentials.create_delegated(config.GOOGLE_USER_SYNC_ADMIN_USER)
        self.http = delegated_credentials.authorize(Http())
        self.creds = delegated_credentials.get_access_token()

        # Get list of current students
        users = {}
        for ou in StudentGradeOUMapping.objects.filter(enable_sync=True):
            users.update(self.list_users(ou.ou))
        self.uids = {u.split("@")[0]: u for u in users.keys()}
        self.ids = {u: u.split("@")[0] for u in users.keys()}

        # Get current students
        seen = set()
        for student in Student.objects.filter(
                Q(is_active=True) &
                Q(year__isnull=False) &
                Q(year__google_ou_mapping__enable_sync=True) &
                Q(year_id__gte=7)
        ):

            udata = users[student.student_account_email]
            if student.student_account_initial_pw in (None, ""):
                print("Would set pw for", student.year, student)
                new_pw = generate_pw()
                self.update_user(udata, {
                    'password': new_pw,
                    'changePasswordAtNextLogin': True
                    })
                student.student_account_initial_pw = new_pw
                student.save()

    def list_users(self, oupath):
        """Get a list of users in an OU."""
        svc = discovery.build('admin', 'directory_v1', http=self.http, cache_discovery=False)
        users = svc.users().list(customer='my_customer',
                                 query='orgUnitPath=\'%s\'' % oupath,
                                 maxResults=500).execute()
        # pprint(users)

        return {u[u'primaryEmail']: u for u in users.get('users', [])}

    def update_user(self, user_data, changes):
        """Update a user and a dict of changes to apply."""
        svc = discovery.build('admin', 'directory_v1', http=self.http, cache_discovery=False)
        return svc.users().patch(userKey=user_data['id'],
                                 body=changes).execute()
