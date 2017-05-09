from django import forms
from django.forms import ValidationError, ModelForm
from django.utils.translation import ugettext_lazy as _

from aristotle_mdr import models as MDR
from aristotle_mdr.forms.creation_wizards import UserAwareForm
from aristotle_mdr.contrib.links.models import Link, LinkEnd, Relation, RelationRole
from aristotle_mdr.contrib.autocomplete import widgets


class LinkEndEditorBase(UserAwareForm, forms.Form):
    def __init__(self, roles, *args, **kwargs):
        self.roles = roles
        super(LinkEndEditorBase, self).__init__(*args, **kwargs)
        for role in self.roles:
            if role.multiplicity == 1:
                self.fields['role_' + str(role.pk)] = forms.ModelChoiceField(
                    queryset=MDR._concept.objects.all().visible(self.user),
                    label=role.name,
                    widget=widgets.ConceptAutocompleteSelect(model=MDR._concept),
                )
            else:
                self.fields['role_' + str(role.pk)] = forms.ModelMultipleChoiceField(
                    queryset=MDR._concept.objects.all().visible(self.user),
                    label=role.name,
                    widget=widgets.ConceptAutocompleteSelectMultiple(model=MDR._concept),
                )

    def clean(self, *args, **kwargs):
        cleaned_data = super(LinkEndEditorBase, self).clean(*args, **kwargs)
        for role in self.roles:
            field_name = 'role_' + str(role.pk)
            d = cleaned_data.get(field_name)
            if role.multiplicity is not None and 1 < role.multiplicity < len(d):
                msg = _("Only %s concepts are valid for this link" % role.multiplicity)
                self.add_error(field_name, msg)


class LinkEndEditor(LinkEndEditorBase):
    def __init__(self, link, roles, *args, **kwargs):
        super(LinkEndEditor, self).__init__(roles, *args, **kwargs)
        for role in self.roles:
            if role.multiplicity == 1:
                self.fields['role_' + str(role.pk)].initial = MDR._concept.objects.get(
                    linkend__link=link, linkend__role=role
                )
            else:
                self.fields['role_' + str(role.pk)].initial = MDR._concept.objects.filter(
                    linkend__link=link, linkend__role=role
                )


class AddLink_SelectRelation_1(UserAwareForm, forms.Form):
    relation = forms.ModelChoiceField(
        queryset=Relation.objects.none(),
        widget=widgets.ConceptAutocompleteSelect(model=Relation)
    )

    def __init__(self, *args, **kwargs):
        super(AddLink_SelectRelation_1, self).__init__(*args, **kwargs)
        self.fields['relation'].queryset = Relation.objects.all().visible(self.user)


class AddLink_SelectConcepts_2(LinkEndEditorBase):
    pass


class AddLink_Confirm_3(forms.Form):
    pass
