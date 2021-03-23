"""
Forms for the Emergency broadcast module.
"""
from django import forms
from django.core.exceptions import ValidationError
from phonenumber_field.formfields import PhoneNumberField
from django.utils.translation import gettext_lazy as _

from indysis_broadcast.models import Broadcast


class BroadcastForm(forms.ModelForm):
    """
    Form to create an emergency Broadcast.
    """

    class Meta:
        model = Broadcast
        fields = ['message']

    include_staff = forms.BooleanField(required=False, initial=False)
    include_parents = forms.BooleanField(required=False, initial=True)
    extra_numbers = forms.CharField(help_text="Extra numbers, 1 per line, format +16138881234",
                                    widget=forms.Textarea(attrs={'cols': 20, 'rows': 8}),
                                    required=False)


class BroadcastTestForm(forms.Form):
    """
    Form to test a broadcast.
    """

    broadcast_id = forms.IntegerField(widget=forms.HiddenInput(), required=True)
    phone_number = PhoneNumberField(label="Test Phone Number", help_text="Format +16138881234 or 6138881234")


def validate_yes(value):
    if value and value.lower() != 'yes':
        raise ValidationError(_("%(value)s must be YES"), params={'value': value})


class ConfirmForm(forms.Form):
    """
    Form to test a broadcast.
    """

    broadcast_id = forms.IntegerField(widget=forms.HiddenInput(), required=True)
    yes = forms.CharField(min_length=3, max_length=3, validators=[validate_yes],
                          label="Are you sure you want to send this broadcast?")
