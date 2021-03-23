from django.conf import settings
from sis.version import BUILD_ID, BRANCH, COMMIT
from indy_sis import __version__ as inysis_version

def global_stuff(request):
    """Global context Add-ons
    """
    context = {
        'GOOGLE_ANALYTICS': settings.GOOGLE_ANALYTICS,
        'INSTALLED_APPS': settings.INSTALLED_APPS,
        'BUILD_ID': BUILD_ID,
        'BRANCH': BRANCH,
        'COMMIT': COMMIT,
        'VERSION': inysis_version,
    }
    return context
