import base64
import json
from json import JSONDecodeError

from django.core.mail import EmailMessage
from googleapiclient import discovery
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials
from constance import config

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
]


class NotConfigured(Exception):
    """Improperly Configured"""
    pass


class GmailSender(object):

    @staticmethod
    def get_credentials():
        """Get credentials from google using service acccount."""
        if config.REPORT_CARD_SENDER_EMAIL in (None, ''):
            raise NotConfigured("REPORT_CARD_SENDER_EMAIL not set")

        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                json.loads(config.GOOGLE_SYNC_CREDENTIALS), scopes=SCOPES)
            delegated_credentials = credentials.create_delegated(config.REPORT_CARD_SENDER_EMAIL)
        except JSONDecodeError:
            if config.GOOGLE_SYNC_CREDENTIALS in (None, ""):
                raise NotConfigured("GOOGLE_SYNC_CREDENTIALS not set")
            else:
                raise NotConfigured("Invalid GOOGLE_SYNC_CREDENTIALS")
        http = delegated_credentials.authorize(Http())
        delegated_credentials.get_access_token()  # Tests token
        return http

    @classmethod
    def get_gmail_service(cls, creds=None):
        if not creds:
            creds = cls.get_credentials()
        service = discovery.build('gmail', 'v1', http=creds, cache_discovery=False)
        return service

    @classmethod
    def send_email(cls, message: EmailMessage, creds=None):
        if not creds:
            creds = cls.get_credentials()
        gmail = cls.get_gmail_service(creds)
        body = message.message().as_bytes()
        b64body = {'raw': base64.urlsafe_b64encode(body).decode('utf-8')}
        gmail.users().messages().send(userId=config.REPORT_CARD_SENDER_EMAIL, body=b64body).execute()
