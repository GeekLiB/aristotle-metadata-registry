from __future__ import division

from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from bootstrap3_datetime.widgets import DateTimePicker

import aristotle_mdr.models as MDR
from aristotle_mdr.perms import user_can_edit, user_can_view
from aristotle_mdr.forms.creation_wizards import UserAwareForm
from aristotle_mdr.contrib.autocomplete import widgets


class UserSelfEditForm(forms.Form):
    template = "aristotle_mdr/userEdit.html"

    first_name = forms.CharField(required=False, label=_('First Name'))
    last_name = forms.CharField(required=False, label=_('Last Name'))
    email = forms.EmailField(required=False, label=_('Email Address'))


# For stating that an item deprecates other items.
class DeprecateForm(forms.Form):
    olderItems = forms.ModelMultipleChoiceField(
        queryset=MDR._concept.objects.all(),
        label="Supersede older items",
        required=False,
        widget=widgets.ConceptAutocompleteSelectMultiple()
    )

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item')
        self.qs = kwargs.pop('qs')
        self.user = kwargs.pop('user')
        super(DeprecateForm, self).__init__(*args, **kwargs)

        self.fields['olderItems'] = forms.ModelMultipleChoiceField(
            queryset=self.qs,
            label=_("Supersede older items"),
            required=False,
            initial=self.item.supersedes.all(),
            widget=widgets.ConceptAutocompleteSelectMultiple(
                model=self.item._meta.model
            )
        )

    def clean_olderItems(self):
        olderItems = self.cleaned_data['olderItems']
        if self.item in olderItems:
            raise forms.ValidationError("An item may not supersede itself")
        for i in olderItems:
            if not user_can_edit(self.user, i):
                raise forms.ValidationError("You cannot supersede an item that you do not have permission to edit")
        return olderItems


# For superseding an item with a newer one.
class SupersedeForm(forms.Form):
    newerItem = forms.ModelChoiceField(
        queryset=MDR._concept.objects.all(),
        empty_label="None",
        label=_("Superseded by"),
        required=False,
        widget=widgets.ConceptAutocompleteSelect()
    )

    def __init__(self, *args, **kwargs):
        self.item = kwargs.pop('item')
        self.qs = kwargs.pop('qs')
        self.user = kwargs.pop('user')
        super(SupersedeForm, self).__init__(*args, **kwargs)

        self.fields['newerItem']=forms.ModelChoiceField(
            queryset=self.qs,
            empty_label="None",
            label=_("Superseded by"),
            initial=self.item.superseded_by,
            required=False,
            widget=widgets.ConceptAutocompleteSelect(
                model=self.item._meta.model
            )
        )

    def clean_newerItem(self):
        item = self.cleaned_data['newerItem']
        if not item:
            return None
        if self.item.id == item.id:
            raise forms.ValidationError("An item may not supersede itself")
        if not user_can_edit(self.user, item):
            raise forms.ValidationError("You cannot supersede with an item that you do not have permission to edit")
        return item


class ChangeStatusForm(UserAwareForm):
    state = forms.ChoiceField(choices=MDR.STATES, widget=forms.RadioSelect)
    registrationDate = forms.DateField(
        required=False,
        label=_("Registration date"),
        widget=DateTimePicker(options={"format": "YYYY-MM-DD"}),
        initial=timezone.now()
    )
    cascadeRegistration = forms.ChoiceField(
        initial=False,
        choices=[(0, _('No')), (1, _('Yes'))],
        label=_("Do you want to update the registration of associated items?")
    )
    changeDetails = forms.CharField(
        max_length=512,
        required=False,
        label=_("Why is the status being changed for these items?"),
        widget=forms.Textarea
    )

    def add_registration_authority_field(self):
        ras = [(ra.id, ra.name) for ra in self.user.profile.registrarAuthorities]
        self.fields['registrationAuthorities']=forms.MultipleChoiceField(
            label="Registration Authorities",
            choices=ras,
            widget=forms.CheckboxSelectMultiple
        )

    # Thanks to http://jacobian.org/writing/dynamic-form-generation/
    def __init__(self, *args, **kwargs):
        # self.user = kwargs.pop('user')
        super(ChangeStatusForm, self).__init__(*args, **kwargs)
        self.add_registration_authority_field()

    def clean_cascadeRegistration(self):
        return self.cleaned_data['cascadeRegistration'] == "1"

    def clean_registrationAuthorities(self):
        return [
            MDR.RegistrationAuthority.objects.get(id=int(ra)) for ra in self.cleaned_data['registrationAuthorities']
        ]

    def clean_state(self):
        state = self.cleaned_data['state']
        state = int(state)
        MDR.STATES[state]
        return state


# Thanks http://stackoverflow.com/questions/6958708/grappelli-to-hide-sortable-field-in-inline-sortable-django-admin
class PermissibleValueForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(PermissibleValueForm, self).__init__(*args, **kwargs)

    class Meta:
        model = MDR.PermissibleValue
        fields = "__all__"


class CompareConceptsForm(forms.Form):
    item_a = forms.ModelChoiceField(
        queryset=MDR._concept.objects.none(),
        empty_label="None",
        label=_("First item"),
        required=True,
        widget=widgets.ConceptAutocompleteSelect()
    )
    item_b = forms.ModelChoiceField(
        queryset=MDR._concept.objects.none(),
        empty_label="None",
        label=_("Second item"),
        required=True,
        widget=widgets.ConceptAutocompleteSelect()
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user')
        self.qs = kwargs.pop('qs').visible(self.user)
        super(CompareConceptsForm, self).__init__(*args, **kwargs)

        self.fields['item_a'] = forms.ModelChoiceField(
            queryset=self.qs,
            empty_label="None",
            label=_("First item"),
            required=True,
            widget=widgets.ConceptAutocompleteSelect()
        )
        self.fields['item_b']=forms.ModelChoiceField(
            queryset=self.qs,
            empty_label="None",
            label=_("Second item"),
            required=True,
            widget=widgets.ConceptAutocompleteSelect()
        )
