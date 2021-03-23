from modeltranslation.translator import register, TranslationOptions

from sis.studentdb.models import SchoolYear, GradeLevel, StudentClass


@register(SchoolYear)
class SchoolYearTO(TranslationOptions):
    fields = ('principal_title', 'vice_principal_title')


@register(GradeLevel)
class GradeLevelTO(TranslationOptions):
    fields = ('name', 'shortname')


@register(StudentClass)
class StudentClassTO(TranslationOptions):
    fields = ('name', 'shortname', 'description')

