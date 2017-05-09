from django import forms
from django.forms.models import BaseModelFormSet


class HiddenOrderModelFormSet(BaseModelFormSet):
    def add_fields(self, form, index):
        super(HiddenOrderModelFormSet, self).add_fields(form, index)
        form.fields["ORDER"].widget = forms.HiddenInput()
