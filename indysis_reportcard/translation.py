from modeltranslation.translator import register, TranslationOptions

from indysis_reportcard.models import GradingScheme, GradingSchemeLevel, ReportCardSection, \
    ReportCardSubject, ReportCardTerm
from indysis_reportcard.models import ReportCardStrand, GradingSchemeLevelChoice, ReportCardTemplate


@register(GradingScheme)
class GradingSchemeTO(TranslationOptions):
    fields = ('range_heading', 'descr_heading')


@register(GradingSchemeLevel)
class GradingSchemeLevelTO(TranslationOptions):
    fields = ('description',)


@register(ReportCardSection)
class ReportCardSectionTO(TranslationOptions):
    fields = ('heading', 'text', 'comments_heading')


@register(ReportCardSubject)
class ReportCardSubjectTO(TranslationOptions):
    fields = ('name', 'text', 'comments_heading')


@register(ReportCardStrand)
class ReportCardStrandTO(TranslationOptions):
    fields = ('text',)


@register(GradingSchemeLevelChoice)
class GradingSchemeLevelChoiceTO(TranslationOptions):
    fields = ('name', 'description')


@register(ReportCardTemplate)
class ReportCardTemplateTO(TranslationOptions):
    fields = ()


@register(ReportCardTerm)
class ReportCardTermTO(TranslationOptions):
    fields = ('name', 'title')
