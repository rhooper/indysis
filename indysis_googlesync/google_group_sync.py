import json
from datetime import datetime, timedelta
from json import JSONDecodeError
from typing import Generator, Dict, Tuple, NamedTuple, Optional

from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.template.defaultfilters import pluralize
from googleapiclient import discovery
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from constance import config
from raven.contrib.django.raven_compat.models import client

from indysis_googlesync.models import GoogleGroupSync, GoogleGroupSyncLog

SCOPES = [
    'https://www.googleapis.com/auth/admin.directory.user',
    'https://www.googleapis.com/auth/admin.directory.group'
]


class NotConfigured(Exception):
    """Improperly Configured"""
    pass


class GroupMember(NamedTuple):
    email: str
    role: str
    member_id: Optional[str]


class ListChange(NamedTuple):
    change_type: str
    member: GroupMember


class GoogleSync(object):

    @staticmethod
    def get_credentials():
        """Get credentials from google using service acccount."""
        if config.GOOGLE_SYNC_GROUP_ADMIN_EMAIL in (None, ''):
            raise NotConfigured("GOOGLE_SYNC_GROUP_ADMIN_EMAIL not set")

        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.loads(config.GOOGLE_SYNC_CREDENTIALS), scopes=SCOPES)
            delegated_credentials = credentials.create_delegated(config.GOOGLE_SYNC_GROUP_ADMIN_EMAIL)
        except JSONDecodeError:
            if config.GOOGLE_SYNC_CREDENTIALS in (None, ""):
                raise NotConfigured("GOOGLE_SYNC_CREDENTIALS not set")
            else:
                raise NotConfigured("Invalid GOOGLE_SYNC_CREDENTIALS")
        http = delegated_credentials.authorize(Http())
        delegated_credentials.get_access_token()  # Tests token
        return http

    @classmethod
    def list_groups(cls):
        """Lists groups."""

        if config.GOOGLE_SYNC_GROUP_DOMAIN in (None, ""):
            raise NotConfigured("GOOGLE_SYNC_GROUP_DOMAIN not set")

        service = cls.get_directory_service()
        groups = service.groups().list(domain=config.GOOGLE_SYNC_GROUP_DOMAIN).execute()
        return groups['groups']

    @classmethod
    def get_directory_service(cls, creds=None):
        if not creds:
            creds = cls.get_credentials()
        service = discovery.build('admin', 'directory_v1', http=creds, cache_discovery=False)
        return service

    @classmethod
    def sync_group(cls, group: GoogleGroupSync):
        """Sync a group."""

        log_lines = []

        added = 0
        removed = 0
        updated = 0
        errors = 0
        count = 0

        try:

            creds = cls.get_credentials()
            service = cls.get_directory_service(creds)

            list_members = cls.get_members_dict(creds, group)
            expected_members = cls.get_expected_members_dict(group)
            count = len(list_members)

            for change in cls.compare_members(list_members, expected_members):
                try:
                    EmailValidator()(change.member.email)
                except ValidationError:
                    log_lines.append(f"Invalid email: {change.member.email}")
                    errors += 1
                    continue

                try:
                    if change.change_type == 'role':
                        cls.update_role(group, change, service)
                        updated += 1
                        log_lines.append(f'Updated role for {change.member.email} to {change.member.role}')
                    elif change.change_type == 'add':
                        cls.add_member(group, change, service)
                        added += 1
                        log_lines.append(f'Added {change.member.email} with role {change.member.role}')
                    elif change.change_type == 'del':
                        cls.del_member(group, change, service)
                        removed += 1
                        log_lines.append(f'Removed {change.member.email}')
                except Exception as err:
                    try:
                        content = json.loads(err.content)
                        if content["error"]["code"] == 409:
                            for erritem in content['error']['errors']:
                                log_lines.append(
                                    f'Google Error: {change.member.email}: {content["error"]["code"]} '
                                    f'{erritem["reason"]}: {erritem["message"]}')
                        else:
                            raise err
                    except Exception:
                        log_lines.append(
                            f'Failed to process change type={change.change_type} email={change.member.email}:')
                        log_lines.append(f'    {err}')
                        client.captureException()
                    errors += 1

        except Exception as err:
            log_lines.append(f'Unexpected error processing batch:')
            log_lines.append(f'    {err}')

        finally:
            strings = []
            if errors:
                strings += [f'{errors} error{pluralize(errors)}']
            if added:
                strings += [f'{added} added']
            if removed:
                strings += [f'{removed} removed']
            if updated:
                strings += [f'{updated} updated']
            if not strings:
                strings = ['no changes']
                log_lines.append("All %d members are in sync" % count)
            GoogleGroupSyncLog.objects.create(
                group=group,
                status=', '.join(strings),
                messages='\n'.join(log_lines)
            )

            # Purge old logs
            try:
                days = int(config.GOOGLE_SYNC_KEEP_LOGS)
            except ValueError:
                days = 91
            delete_range=datetime.now() - timedelta(days=days)
            GoogleGroupSyncLog.objects.filter(created__lte=delete_range).delete()

    @classmethod
    def list_members(cls, creds, group: GoogleGroupSync) -> Generator[GroupMember, None, None]:
        """Generate a list of current google group members and their role."""

        done = False
        token = None
        service = cls.get_directory_service(creds)
        while not done:
            members = service.members().list(groupKey=group.group_id, pageToken=token).execute()
            token = members.get('nextPageToken', None)
            done = token is None

            for member in members.get('members', []):
                yield GroupMember(member['email'], member['role'], member['id'])

    @classmethod
    def get_members_dict(cls, creds, group: GoogleGroupSync) -> Dict[str, GroupMember]:
        """Get a list of google group members."""

        return {member.email.strip().lower(): member for member in cls.list_members(creds, group)}

    @classmethod
    def get_expected_members_dict(cls, group: GoogleGroupSync) -> Dict[str, GroupMember]:
        """Get a dictionary of expected members and their roles."""

        return {member.email.strip().lower(): member for member in cls.expected_members(group)}

    @classmethod
    def expected_members(cls, group: GoogleGroupSync) -> Generator[GroupMember, None, None]:
        """Generate a list of expected members and their role."""

        for parent in group.get_parents():
            yield GroupMember(parent.email, 'MEMBER', None)
            if parent.alt_email:
                yield GroupMember(parent.alt_email, 'MEMBER', None)
        for user in group.staff.filter(is_active=True).all():
            yield GroupMember(user.email, 'MEMBER', None)
        for user in group.managers.filter(is_active=True).all():
            yield GroupMember(user.email, 'MANAGER', None)
        for user in group.owners.filter(is_active=True).all():
            yield GroupMember(user.email, 'OWNER', None)
        for user in group.extra_emails.all():
            yield GroupMember(user.email, user.role.upper(), None)

    @classmethod
    def compare_members(cls,
                        list_members: Dict[str, GroupMember],
                        expected_members: Dict[str, GroupMember]) -> Generator[ListChange, None, None]:
        """Compare the current members and expected members and yield a stream of changes to apply."""

        for email, member in expected_members.items():
            if email in list_members:
                # Check role
                if list_members[email].role != member.role:
                    updated_member = GroupMember(email, member.role, list_members[email].member_id)
                    yield ListChange('role', updated_member)
            else:
                yield ListChange('add', member)

        remove = set([email for email in list_members.keys()]) - set([email for email in expected_members.keys()])
        for email in remove:
            yield ListChange('del', list_members[email])

    @classmethod
    def update_role(cls, group: GoogleGroupSync, change: ListChange, service):
        service.members().patch(groupKey=group.group_id, memberKey=change.member.member_id, body={
            "role": change.member.role
        }).execute()

    @classmethod
    def add_member(cls, group, change, service):
        service.members().insert(groupKey=group.group_id, body={
            "email": change.member.email,
            "role": change.member.role
        }).execute()

    @classmethod
    def del_member(cls, group, change, service):
        service.members().delete(groupKey=group.group_id, memberKey=change.member.member_id).execute()
