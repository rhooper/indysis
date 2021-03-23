#!/usr/bin/env python
"""Synchronize Student Users."""
import json

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

APPLICATION_NAME = 'Google Student User Sync'


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
    """Synchronizes email auditing for students."""

    help = 'Synchronizes student users'

    def allocate_userid(self, student):
        """Assign a Username."""
        base_uid = '%s%s' % (student.first_name.lower()[0],
                              student.last_name.lower().replace(" ", ""))
        base_uid = unidecode(base_uid)
        uid = base_uid
        n = 1
        while uid in self.uids:
            uid = "%s%d" % (base_uid, n)
            n += 1
        return uid

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
                Q(year__google_ou_mapping__enable_sync=True)
        ).all():
            # print(student.student_account_email, student.student_account_email in users)
            if not student.year.google_ou_mapping.enable_sync:
                continue

            if not student.student_account_email:
                # Allocate unique Userid and passwords for new users
                print("Allocating new user", student, student.year, student.student_account_email)
                self.create_user(student)
            elif student.student_account_email not in users:
                print("User %s not found - creating" % student.student_account_email)
                self.create_user(student)
            else:
                seen.add(student.student_account_email)

                # 1. Check Grade (OU)
                udata = users[student.student_account_email]
                if udata[u'orgUnitPath'] != student.year.google_ou_mapping.ou:
                    print("Fixing OU mismatch: %s should be %s" % (udata[u'orgUnitPath'], ou))
                    self.update_user(udata, {'orgUnitPath': ou})

                if udata['suspended']:
                    print(">> %s is suspended - fixing" % student)
                    self.update_user(udata, {'suspended': False})

            # 2. Check Email Auditing
            try:
                if student.student_account_email and student.year.google_ou_mapping.enable_audit:
                    self.enable_email_auditing(student)
            except gdata.apps.service.AppsForYourDomainException as e:
                print(str(e))
                print(users[student.student_account_email])

        # TODO Check for Removed students to deactivate
        for u in set(users.keys()) - seen:
            udata = users[u]
            student = Student.objects.filter(student_account_email=u).first()
            if (not student or not student.is_active) and not udata['suspended']:
                print(u, "needs suspending")
                self.update_user(udata, {'suspended': True})

    def create_user(self, student):
        """Create a new user."""
        uid = self.allocate_userid(student)
        pwd = generate_pw()

        user = {
            u'includeInGlobalAddressList': True,
            u'orgUnitPath': student.year.google_ou_mapping.ou,
            u'primaryEmail': u'%s@%s' % (uid, config.GOOGLE_USER_SYNC_STUDENT_DOMAIN),
            u'emails': [{
                u'primary': True,
                u'address': u'%s@%s' % (uid, config.GOOGLE_USER_SYNC_STUDENT_DOMAIN)}],
            u'organizations': [{u'customType': u'',
                                u'type': u'unknown',
                                u'primary': True}],
            u'kind': u'admin#directory#user',
            u'name': {u'fullName': student.longname,
                      u'givenName': student.first_name,
                      u'familyName': student.last_name},
            u'password': pwd,
            u'notes': {u'value': u''},
            u'changePasswordAtNextLogin': False,
            u'customerId': u'C01o4zmet'
        }
        svc = discovery.build('admin', 'directory_v1', http=self.http, cache_discovery=False)
        try:
            userinfo = svc.users().insert(body=user).execute()
            student.student_account_email = u'%s@%s' % (uid, config.GOOGLE_USER_SYNC_STUDENT_DOMAIN)
            student.student_account_initial_pw = pwd
            student.save()
            print("Created", userinfo)
        except googleapiclient.errors.HttpError as e:
            print("Failed to create", uid, str(e))

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

    def enable_email_auditing(self, student, state=True):
        """..."""
        if not student.year:
            return

        svc = gdata.apps.audit.service.AuditService(
            additional_headers={u"Authorization": u'Bearer {0}'.format(
                self.creds.access_token)})
        svc.domain = config.GOOGLE_USER_SYNC_STUDENT_DOMAIN
        username = student.student_account_email.split('@')[0]
        # print username

        def enable():
            svc.createEmailMonitor(
                source_user=username,
                destination_user=config.GOOGLE_USER_SYNC_AUDIT_ACCOUNT,
                end_date=(datetime.datetime.now() + datetime.timedelta(
                          days=50 * 365)).strftime("%Y-%m-%d %H:%m"),
                incoming_headers_only=False,
                outgoing_headers_only=False,
                drafts=True,
                drafts_headers_only=False,
                chats=True,
                chats_headers_only=False
            )

        try:
            audits = svc.getEmailMonitors(username)
            if len(audits) == 0:
                print("Enabling email auditing for %s" % username)
                enable()
        except gdata.apps.service.AppsForYourDomainException as e:
            if 'InvalidMailbox' not in str(e):
                print(username, "exception", str(e))
                enable()
