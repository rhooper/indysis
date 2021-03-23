from django.apps import AppConfig

__version__ = "1.4.2"

from django.conf import settings

settings.CKEDITOR_CONFIGS.update({'reportcard': {
        'toolbar': [
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            {'name': 'insert',
             'items': ['Table', 'HorizontalRule', 'Smiley', 'SpecialChar', 'PageBreak']},
            '/',
            {'name': 'basicstyles',
             'items': ['Bold', 'Italic', 'Underline', 'Strike', 'Subscript', 'Superscript', '-', 'RemoveFormat']},
            {'name': 'paragraph',
             'items': ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'Blockquote', 'CreateDiv', '-',
                       'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock', '-', 'BidiLtr', 'BidiRtl']},
            {'name': 'links', 'items': ['Link', 'Unlink']},
            '/',
            {'name': 'styles', 'items': ['Styles', 'Format', 'Font', 'FontSize']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'tools', 'items': ['Maximize', 'ShowBlocks', 'RemoveFormat', 'Source']},
            '/',  # put this to force next toolbar on new line
        ],
        'height': 300,
        'width': 800,
        'disableNativeSpellChecker': False,
        'resize_enabled': True,
        'extraPlugins': ','.join([
            'div', 'tabletools',
        ])
    }})

settings.CONSTANCE_CONFIG['REPORT_CARD_SENDER_EMAIL'] = ('', 'Email address to send report cards from')
settings.CONSTANCE_CONFIG['REPORT_CARD_BCC_EMAIL'] = ('', 'Email address to send BCCs to')
settings.CONSTANCE_CONFIG['REPORT_CARD_GMAIL'] = (False, "Send report cards using the Google Gmail API", bool)


class ReportCardAppConfig(AppConfig):
    name = 'indysis_reportcard'
    verbose_name = 'Report card'


default_app_config = 'indysis_reportcard.ReportCardAppConfig'
