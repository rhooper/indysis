from django import template
from django.core.exceptions import FieldError
from django.db.models import Q

from indysis_reportcard.models import ReportCardEntry, ReportCard, ReportCardSubject
from indysis_reportcard.templatetags.rc_legacy import reportcard_element

register = template.Library()


@register.filter(name="rc_format")
def rc_format(item, field='grade'):
    if isinstance(item, ReportCardEntry):
        return reportcard_element(None, item, field, notavail_text='&nbsp;', italic=False, for_print=True)
    return ''


@register.simple_tag(takes_context=True)
def rc_item(context, section, subject, strand):
    rc: ReportCard = context['reportcard']
    entries = rc.reportcardentry_set
    query = (
        Q(section__name__iexact=section) |
        Q(section__field_code__iexact=section)
    )
    try:
        if str(int(section)) == section:
            query |= Q(section__sortorder=int(section))
    except ValueError:
        pass

    if subject:
        query &= (
            Q(subject__name__iexact=subject) |
            Q(subject__field_code__iexact=subject)
        )
        try:
            if str(int(subject)) == subject:
                query |= Q(subject__sortorder=int(subject))
        except ValueError:
            pass
    else:
        query &= Q(subject__isnull=True)

    if strand:
        query &= (
            Q(strand__text__iexact=strand) |
            Q(strand__field_code__iexact=strand)
        )
        try:
            if str(int(strand)) == strand:
                query |= Q(strand__sortorder=int(strand))
        except ValueError:
            pass
    else:
        query &= Q(strand__isnull=True)
    return entries.filter(query).first()


@register.simple_tag(takes_context=True)
def rc_item_fmt(context, section, subject, strand, field):
    try:
        item = rc_item(context, section, subject, strand)
    except FieldError:
        return ''
    return rc_format(item, field)


@register.simple_tag(takes_context=True)
def reportcard_element_print(context, item, field='grade'):
    return reportcard_element(context, item, field, notavail_text='&nbsp;', italic=False,
                              for_print=True, show_heading=False)


@register.simple_tag(takes_context=True)
def subject_teachers(context, subject):
    student = context.get('student')
    if not student:
        return ''
    if not isinstance(subject, ReportCardSubject):
        return ''
    teachers = subject.teachers(student)
    return ' / '.join([teacher.fullname_nocomma for teacher in teachers])


@register.simple_tag(name="enfr")
def enfr(item, fieldname):
    en = getattr(item, f"{fieldname}_en")
    fr = getattr(item, f"{fieldname}_fr")
    if not en or not fr:
        return en or fr
    if en == fr:
        return en
    return f"{en} / {fr}"
