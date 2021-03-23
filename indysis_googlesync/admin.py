"""Admins."""

from admintimestamps import TimestampedAdminMixin
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import User
from django.db.models import Q
from django.forms import ModelMultipleChoiceField
from django.shortcuts import redirect
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy

from indysis_googlesync.models import GoogleGroupSync, GoogleGroupSyncLog, ExtraEmailAddress, StudentGradeOUMapping


class ExtraEmailAdminInline(TimestampedAdminMixin, admin.TabularInline):
    model = ExtraEmailAddress
    extra = 1


class GoogleGroupSyncAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    """Google Synchronization Admin."""

    list_display = ('email', 'description', 'auto_sync', 'get_classes')
    filter_horizontal = ['synchronize_classes', 'owners', 'managers', 'staff']
    readonly_fields = ['group_id', 'description', 'email']
    inlines = [ExtraEmailAdminInline]

    def get_classes(self, obj: GoogleGroupSync):
        """Get Grades"""
        return '; '.join([g.name for g in obj.synchronize_classes.all()])

    get_classes.short_description = 'Classes'

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('googlesync:group_sync_index')

    def response_change(self, request, obj):
        return redirect('googlesync:group_sync_index')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name in ('owners', 'managers', 'staff'):

            kwargs["queryset"] = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).exclude(is_active=False)

            kwargs['widget'] = FilteredSelectMultiple(
                db_field.verbose_name,
                db_field.name in self.filter_vertical
            )
            kwargs['required'] = False

            form_field = UsersM2MField(**kwargs)
            msg = gettext_lazy('Hold down "Control", or "Command" on a Mac, to select more than one.')
            help_text = db_field.help_text
            form_field.help_text = format_lazy('{}<br>{}', help_text, msg) if help_text else msg

            return form_field

        return super().formfield_for_manytomany(db_field, request, **kwargs)


class UsersM2MField(ModelMultipleChoiceField):

    def label_from_instance(self, obj: User):
        if obj.last_name:
            return f'{obj.last_name}, {obj.first_name}'
        return obj.username


class ReadOnlyAdmin(admin.ModelAdmin):

    def get_readonly_fields(self, request, obj=None):
        return list(self.readonly_fields) + \
               [field.name for field in obj._meta.fields] + \
               [field.name for field in obj._meta.many_to_many]

    def get_actions(self, request):
        return {}

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        """ customize add/edit form to remove save / save and continue """
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save'] = False
        return super().change_view(request, object_id, extra_context=extra_context)


class GoogleGroupSyncLogAdmin(ReadOnlyAdmin):

    list_display = ['group', 'status', 'created']
    list_filter = ['group']


class StudentGradeOUMappingAdmin(admin.ModelAdmin):
    list_display = ['level', 'ou', 'enable_sync', 'enable_audit']


admin.site.register(GoogleGroupSync, GoogleGroupSyncAdmin)
admin.site.register(GoogleGroupSyncLog, GoogleGroupSyncLogAdmin)
admin.site.register(StudentGradeOUMapping, StudentGradeOUMappingAdmin)
