from django.db import OperationalError, ProgrammingError
from django.urls import reverse
from django.utils.translation import gettext as _
from sis.studentdb.menu import menu

from indysis_reportcard.models import ReportCardTerm
from indysis_reportcard.views import is_reportcard_admin, access_allowed as rc_access_allowed
from sis.studentdb.models import SchoolYear

main_menu = menu.registry.get("main")
if main_menu is None:
    main_menu = menu.Menu('main')
    menu.register(main_menu)


def is_rc_admin(user, context):
    return is_reportcard_admin(user)


def access_allowed(user, context):
    return rc_access_allowed(user)


rc = menu.PassTestNode(
    id='rc',
    label=_('Report Cards'),
    order=3,
    pattern_name='reportcard:index',
    test=access_allowed
)
try:
    rc.add(menu.PassTestNode(
        id='manage_data',
        label=_('Term List'),
        pattern_name="reportcard:index",
        test=is_rc_admin
    ))
    rc.add(menu.PassTestNode(
        id='manage_data',
        label=_('Manage Data'),
        url=reverse('admin:app_list', kwargs={"app_label": 'indysis_reportcard'}),
        test=is_rc_admin
    ))
except (OperationalError, ProgrammingError):
    # Ignore errors looking up the school year during menu generation
    pass

main_menu.register(rc)
