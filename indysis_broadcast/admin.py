"""Admins."""

from admintimestamps import TimestampedAdminMixin
from django.contrib import admin

from indysis_broadcast.models import Broadcast, BroadcastRecipient


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


class BroadcastRecipientAdmin(admin.TabularInline):
    """
    Broadcast recipients.
    """
    model = BroadcastRecipient
    extra = 0
    readonly_fields = ['recipient', 'phone_number', 'status']
    can_delete = False


class BroadcastAdmin(TimestampedAdminMixin, admin.ModelAdmin):
    """Broadcast Admin."""

    list_display = ('message', 'created_by', 'created')
    filter_horizontal = ['recipients']
    inlines = (BroadcastRecipientAdmin, )


admin.site.register(Broadcast, BroadcastAdmin)
