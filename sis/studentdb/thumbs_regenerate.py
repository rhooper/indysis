#!/usr/bin/python

from django.conf import settings
from django.core.management import setup_environ

from sis.studentdb import thumbs

setup_environ(settings)
thumbs.regenerate_thumbs()
