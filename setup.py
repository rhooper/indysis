import codecs
import os
import re

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    with codecs.open(os.path.join(here, *parts), 'r') as fp:
        return fp.read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name="indysis",
    version=find_version("indy_sis", "__init__.py"),
    author="Roy Hooper",
    author_email="rhooper@toybox.ca",
    description=("Independent School Student Information System"),
    license="GPLv3",
    keywords="django school student information system",
    url="https://gitlab.toybox.ca/indysis/indysis",
    packages=find_packages(),
    include_package_data=True,
    test_suite='setuptest.setuptest.SetupTestSuite',
    tests_require=(
        'django-setuptest',
    ),
    install_requires=[
        'django<2',
        'django-autocomplete-light==2.3.6',
        'django-favicon-plus',
        'social-auth-app-django',
        'django-reversion',
        'django-localflavor',
        'django-daterange-filter',
        'django-mass-edit',
        'django-report-builder<6.2',
        'django-export-action',
        'django-ckeditor',
        'django-simple-import',
        'django-widget-tweaks',
        'djangorestframework',
        'drf-url-filters',
        'django-compressor',
        'django-modeltranslation',
        'django-impersonate',
        'django-constance[database]',
        'django-jsonify',
        'django-debug-toolbar',
        'django-extensions',
        'social-auth-app-django',
        'psycopg2-binary',
        'httpagentparser',
        'django-phonenumber-field',
        'django-picklefield',
        'django-admin-timestamps',
        'openpyxl<2.4',
        'celery',
        'django-libsass',
        'django-environ',
        'django-responsive-dashboard',
        'django-settings-export',
        'django-bootstrap3',
        'bootstrap-admin',
        'django-bootstrap-form',
        'dateparser',
        'redis',
        'django-custom-field',
        'django-smuggler',
        'django-navutils',
        'django-celery-beat',
        "django-inlinecss",

        # Google APIs
        'oauth2client',
        'google-api-python-client',

        # Error reporting & APM
        'raven',

        # Reporting/Report cards
        'PyPDF2',
        'pdfkit',
        'reportlab',

        # Deployment
        'uwsgi',

    ],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        'Environment :: Web Environment',
        'Framework :: Django',
        'Programming Language :: Python',
        "License :: OSI Approved :: GPLv3 License",
    ],
)
