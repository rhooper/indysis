from django import template
from favicon.models import Favicon

register = template.Library()


@register.inclusion_tag('partials/navbar_brand.html', takes_context=True)
def navbar_brand(context):
    favicon = Favicon.objects.filter(isFavicon=True).first()
    if not favicon:
        return {'config': context['config']}
    default_fav = favicon.get_favicon(size=32, rel='shortcut icon')
    return {'brand_image_url': default_fav.faviconImage.url,
            'config': context['config']}
