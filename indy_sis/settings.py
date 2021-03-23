# coding=utf8
# flake8: noqa
from __future__ import absolute_import

import datetime
import logging
import os
import sys
from collections import OrderedDict
from os.path import dirname

from django.core.validators import MinValueValidator  # Could use MaxValueValidator too
from environ import environ
from django.contrib.messages import constants as message_constants

# -------------------------------------------------------------------
# Config from Environment
# -------------------------------------------------------------------
env = environ.Env()
# reading .env file
environ.Env.read_env(env_file=os.path.join(dirname(dirname(__file__)), ".env"))
RAVEN_DSN = env('RAVEN_DSN', default="")
SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', False)
DEBUG_TOOLBAR = env.bool('DEBUG_TOOLBAR', DEBUG)
ALLOWED_HOSTS = ["*"]
ENVIRONMENT_NAME = env('ENVIRONMENT_NAME', default='devel')

# Celery
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default='redis://redis:6379/0')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND', default='redis://redis:6379/0')
CELERY_TASK_ALWAYS_EAGER = env('CELERY_TASK_ALWAYS_EAGER', default=False)
CELERY_TASK_EAGER_PROPAGATES = env('CELERY_TASK_EAGER_PROPAGATES', default=False)

# Celery Beat
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Google
GOOGLE_MAPS_KEY = env('GOOGLE_MAPS_KEY', default='')
GOOGLE_ANALYTICS = env('GOOGLE_ANALYTICS', default='')
GOOGLE_GEOCODER_KEY = env('GOOGLE_GEOCODER_KEY', default='')

# Amazon SES
EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
EMAIL_PORT = 465
EMAIL_HOST_USER = env("EMAIL_USERNAME", default='')
EMAIL_HOST_PASSWORD = env("EMAIL_PASSWORD", default='')
EMAIL_USE_SSL = True
DEFAULT_REPORT_CARD_SENDER_EMAIL = env('REPORT_CARD_SENDER_EMAIL', default='')

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static_files/'),
)
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
STATIC_URL = '/static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')


# -------------------------------------------------------------------
# Localization
# -------------------------------------------------------------------
USE_TZ = False
TIME_ZONE = env('TIME_ZONE', default='America/New_York')
TIME_INPUT_FORMATS = ('%I:%M %p', '%I:%M%p', '%H:%M:%S', '%H:%M')
TIME_FORMAT = 'h:i A'
DATE_INPUT_FORMATS = (
    '%m/%d/%Y', '%Y-%m-%d', '%m/%d/%y', '%b %d %Y',
    '%b %d, %Y', '%d %b %Y', '%d %b, %Y', '%B %d %Y',
    '%B %d, %Y', '%d %B %Y', '%d %B, %Y', '%b. %d, %Y')
DATE_FORMAT = 'M j, Y'
USE_I18N = True
USE_L10N = False
PHONENUMBER_DEFAULT_FORMAT = 'NATIONAL'
PHONENUMBER_DEFAULT_REGION = 'CA'

# Global date validators, to help prevent data entry errors
DATE_VALIDATORS = [MinValueValidator(datetime.date(1970, 1, 1))]  # Unix epoch!

MODELTRANSLATION_DEFAULT_LANGUAGE = 'en'
MODELTRANSLATION_FALLBACK_LANGUAGES = ('en', 'fr')

LANGUAGE_CODE = 'en-us'
LANGUAGES = (
    ('en', 'English'),
    ('fr', 'Français'),
)


# -------------------------------------------------------------------
# Database configuration
# -------------------------------------------------------------------
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'indysis.db',
    }
}


# -------------------------------------------------------------------
# Application configuration
# -------------------------------------------------------------------
SITE_ID = 1
SETTINGS_EXPORT = [
    'RAVEN_DSN',
    'DEBUG',
]
LOGIN_REDIRECT_URL = "/"
LOGIN_URL = '/login/'


ROOT_URLCONF = 'indy_sis.urls'
WSGI_APPLICATION = 'sis.wsgi.application'

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'impersonate.middleware.ImpersonateMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates/'),
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'sis.studentdb.context_processors.global_stuff',
                'django_settings_export.settings_export',
                'django.template.context_processors.debug',
                "django.template.context_processors.request",
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'constance.context_processors.config',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'navutils.context_processors.menus',
            ],
        }
    },
]

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

AUTH_PROFILE_MODULE = 'studentdb.UserPreference'


IMPERSONATE_ALLOW_SUPERUSER = True
IMPERSONATE_REQUIRE_SUPERUSER = True

AUTHENTICATION_BACKENDS = (
    'sis.studentdb.backends.CaseInsensitiveModelBackend',
)

# CKEDITOR
CKEDITOR_MEDIA_PREFIX = "/static/ckeditor/"
CKEDITOR_UPLOAD_PATH = os.path.join(BASE_DIR, 'media/uploads')
CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': [
            ['Bold', 'Italic', 'Underline', 'Subscript', 'Superscript',
             '-', 'Image', 'Link', 'Unlink', 'SpecialChar',
             '-', 'Format',
             '-', 'Maximize',
             '-', 'Table',
             '-', 'BulletedList', 'NumberedList',
             '-', 'PasteText', 'PasteFromWord',
             ]
        ],
        'height': 120,
        'width': 640,
        'disableNativeSpellChecker': False,
        'removePlugins': 'scayt,menubutton,contextmenu,liststyle,tabletools,tableresize,elementspath',
        'resize_enabled': False,
    }
}

CSRF_FAILURE_VIEW = 'indy_sis.views.csrf_failure'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'root': {
        'level': 'WARNING',
        'handlers': ['console', 'sentry'],
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'ERROR',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'filters': [],
        },
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'raven': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },

}

# django-navutils
NAVUTILS_MENU_CONFIG = {
    'CURRENT_MENU_ITEM_CLASS': 'active',
    'CURRENT_MENU_ITEM_PARENT_CLASS': 'active',
}

# django-report-builder
REPORT_BUILDER_GLOBAL_EXPORT = True
REPORT_BUILDER_ASYNC_REPORT = False

COMPRESS_PRECOMPILERS = (
    ('text/coffeescript', 'coffee --compile --stdio'),
    ('text/x-scss', 'django_libsass.SassCompiler'),
)

# These are required add ons that we always want to have
INSTALLED_APPS = (

    # I18N/L18N
    'modeltranslation',

    # Utilities
    'autocomplete_light',
    'reversion',
    'localflavor',
    'jsonify',

    # Configuration
    'constance',
    'constance.backends.database',
    'django_celery_beat',

    # Admin UI Replacement
    'django.contrib.contenttypes',
    'bootstrap_admin',
    'bootstrap3',

    # Base
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'django.contrib.auth',
    'django.contrib.admin',
    'django.contrib.sites',

    # Authentication
    'social_django',

    # Our apps
    'sis.studentdb',
    'sis.alumni',
    'sis.attendance',
    'sis.administration',
    'sis.export_action_with_custom_field',
    'sis.simple_import_with_custom_field',

    # Assets
    'compressor',
    'django_inlinecss',

    # Admin interface enhancements
    'daterange_filter',
    'massadmin',
    'export_action',
    'impersonate',
    'custom_field',
    'smuggler',

    # Data model enhancements
    'phonenumber_field',

    # UI
    'ckeditor',
    'report_builder',
    'responsive_dashboard',
    'simple_import',
    'widget_tweaks',
    'bootstrapform',
    'favicon',
    'navutils',

    # API
    'rest_framework',
    'rest_framework.authtoken',
    'api',
    'filters',
)

BOOTSTRAP_ADMIN_SIDEBAR_MENU = False

INSTALLED_APPS += ('raven.contrib.django.raven_compat',)
if RAVEN_DSN:
    RAVEN_CONFIG = {
        'dsn': RAVEN_DSN,
    }
    SENTRY_CELERY_LOGLEVEL = logging.ERROR
    SENTRY_CELERY_IGNORE_EXPECTED = True

    if DEBUG:
        RAVEN_CONFIG['environment'] = ENVIRONMENT_NAME
        RAVEN_CONFIG['tags'] = {'debug': DEBUG}

    MIDDLEWARE = ('raven.contrib.django.raven_compat.middleware.Sentry404CatchMiddleware',) + MIDDLEWARE


EMAIL_DOMAIN = 'example.com'

CONSTANCE_CONFIG = OrderedDict([
    ('SCHOOL_NAME', ('Unnamed School', 'School name')),
    ('SCHOOL_NAME_MENU', ('Unnamed School', 'School name for menubar')),
    ('SCHOOL_ADDRESS_LINE1', ('', 'School address')),
    ('SCHOOL_ADDRESS_LINE2', ('', 'School address')),
    ('SCHOOL_ADDRESS_CITY', ('', 'School city')),
    ('SCHOOL_ADDRESS_PROVSTATE', ('', 'School province/state')),
    ('SCHOOL_ADDRESS_POSTCODE', ('', 'School postal code/zipcode')),
    ('SCHOOL_EMAIL', ('', 'School email (for some reports, eg report cards)')),
    ('SCHOOL_PHONE', ('', 'School phone number')),
    ('SCHOOL_FAX', ('', 'School fax number')),
    ('DEFAULT_CITY', ('', 'Default city for new contacts')),
    ('ALLOW_GOOGLE_AUTH', (False, 'Allow users to log in with Google Apps.')),
    ('SOCIAL_AUTH_GOOGLE_OAUTH2_KEY', ('', 'OAuth2 Key for Google Authentication')),
    ('SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET', ('', 'OAuth2 secret Key for Google Authentication')),
    ('SOCIAL_AUTH_WHITELISTED_DOMAINS', ('', "Comma separated list of domains permitted to log in via Google Auth")),
    ('SCHOOL_LAT', ("45.4215", "School's latitude.  Used for student map.")),
    ('SCHOOL_LONG', ("-75.6972", "School's longitude  Used for student map.")),
    ('NAVBAR_CLASS', ('navbar-inverse', "CSS Class for navbar")),
    ('ATTENDANCE_FREQUENCY', ('ampm', 'Attendance form behaviour', 'attendance_frequency')),
    ('STUDENT_INFORMATION_HEADER', ('', 'Content to put at start of the Student Information PDF report')),
    ('STUDENT_INFORMATION_FOOTER', ('', 'Content to put at end of the Student Information PDF report')),
])
CONSTANCE_ADDITIONAL_FIELDS = {
    'attendance_frequency': ['django.forms.fields.ChoiceField', {
        'widget': 'django.forms.Select',
        'choices': (("ampm", "Morning and Afternoon"), ("once", "Once per day"))
    }],
}

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

REST_FRAMEWORK = {
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
}

MESSAGE_TAGS = {
    message_constants.DEBUG: 'alert alert-light',
    message_constants.INFO: 'alert alert-info',
    message_constants.SUCCESS: 'alert alert-success',
    message_constants.WARNING: 'alert alert-warning',
    message_constants.ERROR: 'alert alert-danger'
}


# -------------------------------------------------------------------
# Debug Settings
# -------------------------------------------------------------------
INTERNAL_IPS = ('127.0.0.1',)

if DEBUG:
    INSTALLED_APPS += ('django_extensions',)

if DEBUG_TOOLBAR:
    INSTALLED_APPS = INSTALLED_APPS + ('debug_toolbar',)
    MIDDLEWARE += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INTERNAL_IPS = ['127.0.0.1', ]
    DEBUG_TOOLBAR_CONFIG = {
        'JQUERY_URL': 'https://code.jquery.com/jquery-2.2.4.min.js'
    }


# -------------------------------------------------------------------
# Test Settings
# -------------------------------------------------------------------
MIGRATIONS_DISABLED = False
if 'test' in sys.argv:
    # Don't take fucking years to run a test
    class DisableMigrations(object):
        def __contains__(self, item):
            return True

        def __getitem__(self, item):
            pass


    MIGRATION_MODULES = DisableMigrations()
    MIGRATIONS_DISABLED = True


# -------------------------------------------------------------------
# Social Auth (Google OAuth) Login
# -------------------------------------------------------------------
SOCIAL_AUTH_POSTGRES_JSONFIELD = True
AUTHENTICATION_BACKENDS = ('social_core.backends.google.GoogleOAuth2',) + AUTHENTICATION_BACKENDS

# See https://python-social-auth-docs.readthedocs.io/en/latest/pipeline.html
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    # 'social_core.pipeline.mail.mail_validation',
    'social_core.pipeline.social_auth.associate_by_email',
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)
SOCIAL_AUTH_DISCONNECT_PIPELINE = (
    'social_core.pipeline.disconnect.allowed_to_disconnect',
    'social_core.pipeline.disconnect.get_entries',
    'social_core.pipeline.disconnect.revoke_tokens',
    'social_core.pipeline.disconnect.disconnect',
)
SOCIAL_AUTH_LOGIN_ERROR_URL = '/login_error/'
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'first_name', 'email']
SOCIAL_AUTH_GOOGLE_OAUTH2_AUTH_EXTRA_ARGUMENTS = {
    'prompt': 'select_account',
    # 'approval_prompt': 'auto',
    # 'access_type': 'offline',
}
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]
SOCIAL_AUTH_PROTECTED_USER_FIELDS = ['first_name', 'last_name']
TEMPLATES[0]['OPTIONS']['context_processors'] += [
    'social_django.context_processors.backends',
    'social_django.context_processors.login_redirect',
]
MIDDLEWARE += (
    'social_django.middleware.SocialAuthExceptionMiddleware',
    'indy_sis.social_auth.ExceptionMessageMiddleware',
)
SOCIAL_AUTH_STRATEGY = 'indy_sis.social_auth.ConstanceStrategy'


SMUGGLER_FORMAT = 'json'
SMUGGLER_INDENT = 2
SMUGGLER_EXCLUDE_LIST = [
    "admin.logentry",
    "auth.permission",
    "auth.group",
    "contenttypes.contenttype",
    "impersonate.impersonationlog",
    "responsive_dashboard.userdashboard",
    "responsive_dashboard.userdashlet",
    "reversion.revision",
    "reversion.version",
    "sessions.session",
    "simple_import.columnmatch",
    "simple_import.importsetting",
    "sites.site",
    "social_django.usersocialauth",
    "studentdb.userpreference",
    "favicon.faviconimg",
    "favicon.favicon"
]

EXTRA_APPS = (
    'indysis_reportcard',
    'indysis_broadcast',
    'indysis_googlesync',
)


# -------------------------------------------------------------------
# Local Settings
# -------------------------------------------------------------------
# this will load additional settings from the file settings_local.py
try:
    from .settings_local import *
    logging.info("Loaded settings from settings_local.py")
except ImportError:
    pass

# -------------------------------------------------------------------
# Server Settings
# -------------------------------------------------------------------
# this will load server-wide settings from the file settings_server.py
try:
    from .settings_server import *
    logging.info("Loaded settings from settings_server.py")
except ImportError:
    pass

# -------------------------------------------------------------------
# Merge in additional apps
# -------------------------------------------------------------------
if EXTRA_APPS:
    INSTALLED_APPS = INSTALLED_APPS + EXTRA_APPS


EXTRA_APPS = (
    'indysis_reportcard',
    'indysis_broadcast',
    'indysis_googlesync',
)

ADDITIONAL_SIS_URLS = [
    (r'^reportcard/', 'indysis_reportcard.urls', "reportcard"),
    (r'^sync/google/', 'indysis_googlesync.urls', "googlesync"),
    (r'^emergency-broadcast/', 'indysis_broadcast.urls', "broadcast"),
]
