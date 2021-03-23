# -*- coding: utf-8 -*-
import re
from datetime import date, datetime, timedelta

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

from indysis_reportcard.models import ReportCardEntry, ReportCard

register = template.Library()


def reportcard_element_generic(context, item, field, entry,
                               notavail_class='rc-novalue',
                               notavail_text='(n/a)',
                               valclass='rc-value',
                               gradeclass='grade',
                               italic=True,
                               for_print=False,
                               show_heading=True):
    heading = ""
    if not entry:
        value = None
        # raise KeyError('item %s not found' % item)
    elif field == 'comment':
        value = entry.comment
    elif field == 'grade_full' and entry.choice:
        return mark_safe(entry.choice.view_choice)
    elif field == "grade_full_en" and entry.choice:
        return mark_safe(entry.choice.name_en)
    elif field == "grade_full_fr" and entry.choice:
        return mark_safe(entry.choice.name_fr)

    elif field == 'second_grade_full' and entry.second_choice:
        return mark_safe(entry.second_choice.view_choice)
    elif field == "second_grade_full_en" and entry.second_choice:
        return mark_safe(entry.second_choice.name_en)
    elif field == "second_grade_full_fr" and entry.second_choice:
        return mark_safe(entry.second_choice.name_fr)

    elif field == 'second_grade':
        heading = entry.section.second_gradingscheme_label
        value = entry.second_choice
        if entry.section.second_gradingscheme.percentile and not value:
            value = entry.second_percentile
        elif value:
            if for_print:
                value = entry.second_choice.choice
            else:
                value = entry.second_choice.view_choice
    else:  # Grade
        heading = entry.section.gradingscheme_label
        value = entry.choice
        if entry.section.gradingscheme.percentile and not value:
            value = entry.percentile
        elif value:
            if for_print:
                value = entry.choice.choice
            else:
                value = entry.choice.view_choice


    extraclass = ' ' + (
        'comment' if field == 'comment' else gradeclass)

    if italic:
        italstr = '<i>%s</i>'
    else:
        italstr = '%s'

    if not show_heading:
        heading = ""

    if value is None or (isinstance(value, str) and value.strip() == ''):
        return mark_safe(("%s <p class='%s'>" + italstr + "</p>") % (heading,
            notavail_class + extraclass, notavail_text))

    return mark_safe(
        ("{} <p class='{cl}'>" + (italstr % "{value}") + "</p>").format(heading,
            value=escape(value).replace("\n", "<br>"),
            cl=valclass + extraclass))


@register.simple_tag(takes_context=True)
def reportcard_element(context, item, field='grade', notavail_text='(n/a)',
                       italic=True, for_print=False, show_heading=False):
    if isinstance(item, ReportCardEntry):
        entry = item
    else:
        entry = context['element_to_entry'].get(item, None)
    if hasattr(entry, field) and field not in (
            'grade', 'comment', 'choice', 'grade_full', 'grade_full_en',
            'grade_full_fr',
            'second_grade', 'second_choice', 'second_grade_full', 'second_grade_full_en',
            'second_grade_full_fr'):
        return getattr(entry, field)
    return reportcard_element_generic(context, item, field, entry,
                                      notavail_text=notavail_text, italic=italic,
                                      for_print=for_print, show_heading=show_heading)


@register.simple_tag(takes_context=True)
def reportcard_past_element(context, term, item, field='grade', notavail_text='n/a',
                            italic=True, for_print=False):
    entry = context['element_to_past'][term].get(item, None)
    if hasattr(entry, field) and field not in ('grade', 'comment', 'choice', 'second_grade', 'second_choice'):
        return getattr(entry, field)
    return reportcard_element_generic(
        context, item, field, entry,
        notavail_text=notavail_text,
        notavail_class='past rc-novalue',
        valclass='past rc-value',
        italic=italic, for_print=for_print)


@register.simple_tag(takes_context=True)
def reportcard_element_print(context, item, field='grade'):
    return reportcard_element(context, item, field, notavail_text='&nbsp;', italic=False,
                              for_print=True)


@register.simple_tag(takes_context=True)
def reportcard_element_print_if_equal(context, item, field='grade',
                                      value=None, print_value='X', for_print=True):
    entry = context['element_to_entry'].get(item, None)
    if field == 'grade':
        rc_value = entry.choice
        if entry.section.gradingscheme.percentile and not rc_value:
            rc_value = entry.percentile
        elif rc_value:
            if for_print:
                rc_value = entry.choice.choice
            else:
                rc_value = entry.choice.view_choice
    else:
        rc_value = getattr(entry, field)
    if str(rc_value) == str(value):
        return print_value
    else:
        return ''


@register.simple_tag(takes_context=True)
def reportcard_past_element_print(context, term, item, field='grade'):
    return reportcard_past_element(context, term, item, field, notavail_text='&nbsp;',
                                   italic=False, for_print=True)


def td_unit(delta):
    if delta.days:
        return delta.days, 'days'
    if delta.seconds > 3600:
        return int(delta.seconds / 3600), 'hours'
    return int(delta.seconds / 60), 'minutes'


@register.filter(name="countdown")
def countdown(obj):
    now = datetime.now()
    if type(obj) == date:
        obj = datetime.combine(obj, datetime.max.time())
    delta = obj - now
    if delta < timedelta(seconds=0):
        amount, unit = td_unit(now - obj)
        return mark_safe("<span class='label label-default'>%d %s ago</span>" % (amount, unit))

    amount, unit = td_unit(delta)
    level = 'primary'
    if unit == 'hours' or unit == 'minutes':
        level = 'danger'
    elif unit == 'days' and amount < 2:
        level = 'warning'
    return mark_safe("<span class='label label-%s'>%d %s to go</span>" % (level, amount, unit))


@register.filter()
def ulify(text):
    """Turn a list into a ul."""
    strs = ["<ul>"] + [
        "<li><span>%s</span></li>" % escape(re.sub(r'•\s*', '', x))
        for x in re.split(r'[\r\n]+', text)] + ["</ul>"]
    return mark_safe("\n".join(strs))


@register.filter(name="rc_format")
def rc_format(item, field='grade'):
    if isinstance(item, ReportCardEntry):
        return reportcard_element(None, item, field, notavail_text='&nbsp;', italic=False, for_print=True)
    return ''


@register.simple_tag(takes_context=True)
def rc_item(context, section, subject, strand):
    rc: ReportCard = context['reportcard']
    entries = rc.reportcardentry_set
    filter_args=dict(
        section__name__iexact=section,
    )
    if subject:
        filter_args['subject__name__iexact'] = subject
    else:
        filter_args['subject__isnull'] = True
    if strand:
        filter_args['strand__name__iexact'] = subject
    else:
        filter_args['strand__isnull'] = True
    return entries.filter(**filter_args).first()
