# -*- coding: utf-8 -*-
import re
from datetime import date, datetime, timedelta

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter(name="index")
def index(obj, i):
    return obj[i]


@register.filter(name="attr")
def attr(obj, i):
    return getattr(obj, i)


@register.filter(name="indexnone")
def indexnone(obj, i):
    if i in obj:
        return obj[i]
    return None
