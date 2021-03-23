
__version__ = "1.0.0"

from django.conf import settings

settings.CONSTANCE_CONFIG['TWILIO_ACCOUNT_SID'] = ('', 'Twilio Account SID')
settings.CONSTANCE_CONFIG['TWILIO_AUTH_TOKEN'] = ('', 'Twilio Auth Token')
settings.CONSTANCE_CONFIG['TWILIO_PHONE_NUMBER'] = ('', 'Outbound phone number as registered in Twilio')

