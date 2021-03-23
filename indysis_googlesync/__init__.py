
__version__ = "1.0.0"

from django.conf import settings

settings.CONSTANCE_CONFIG['GOOGLE_SYNC_CREDENTIALS'] = (
    '', 'JSON encoded Google Service Account credentials for Google sync')
settings.CONSTANCE_CONFIG['GOOGLE_SYNC_GROUP_DOMAIN'] = ('', 'Email Domain name for Google Groups synchronization')
settings.CONSTANCE_CONFIG['GOOGLE_SYNC_GROUP_ADMIN_EMAIL'] = (
    '', 'Email address of an administrative user or role account with access to all google groups')
settings.CONSTANCE_CONFIG['GOOGLE_SYNC_KEEP_LOGS'] = ('91', 'Keep google sync logs for this many days')

# Google Account Sync and Audit
settings.CONSTANCE_CONFIG['GOOGLE_USER_SYNC_SVC_ACCT_CREDS'] = (
    '', 'JSON encoded Service Account credentials for Google User synchronization')
settings.CONSTANCE_CONFIG['GOOGLE_USER_SYNC_ADMIN_USER'] = (
    '', 'Admin account to use for performing user creations/suspensions')
settings.CONSTANCE_CONFIG['GOOGLE_USER_SYNC_STUDENT_DOMAIN'] = (
    '', 'Domain name to use for new student accounts')
settings.CONSTANCE_CONFIG['GOOGLE_USER_SYNC_AUDIT_ACCOUNT'] = (
    '', 'Mailbox to use for email auditing - must exist in the same domain as the student domain')

if not hasattr(settings, 'GOOGLE_SYNC_INITIAL_CRON_SCHEDULE'):
    settings.GOOGLE_SYNC_INITIAL_CRON_SCHEDULE = '30 15 * * *'
