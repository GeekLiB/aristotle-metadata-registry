from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

import aristotle_mdr.models as MDR
from aristotle_mdr.contrib.autocomplete import widgets


class AddMembers(forms.Form):
    roles = forms.MultipleChoiceField(
        label=_("Workgroup roles"),
        choices=sorted(MDR.Workgroup.roles.items()),
        widget=forms.CheckboxSelectMultiple
    )
    users = forms.ModelMultipleChoiceField(
        label=_("Select users"),
        queryset=User.objects.filter(is_active=True),
        widget=widgets.UserAutocompleteSelectMultiple()
    )

    def clean_roles(self):
        roles = self.cleaned_data['roles']
        roles = [role for role in roles if role in MDR.Workgroup.roles.keys()]
        return roles
