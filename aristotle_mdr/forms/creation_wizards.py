from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.utils import timezone, dateparse
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

import aristotle_mdr.models as MDR
from aristotle_mdr.exceptions import NoUserGivenForUserForm
from aristotle_mdr.perms import user_can_move_between_workgroups, user_can_move_any_workgroup, user_can_remove_from_workgroup, user_can_move_to_workgroup
from aristotle_mdr.contrib.autocomplete import widgets

from dal import autocomplete
from bootstrap3_datetime.widgets import DateTimePicker
from aristotle_mdr.widgets import BootstrapDateTimePicker


class UserAwareForm(forms.Form):
    def __init__(self, *args, **kwargs):
        if 'user' in kwargs.keys():
            self.user = kwargs.pop('user')
        elif 'request' in kwargs.keys():
            self.user = kwargs['request'].user
        elif hasattr(self, 'request'):
            self.user = self.request.user
        else:
            raise NoUserGivenForUserForm("The class inheriting from UserAwareForm was not called with a user or request parameter")
        super(UserAwareForm, self).__init__(*args, **kwargs)


class UserAwareModelForm(UserAwareForm, forms.ModelForm):  # , autocomplete_light.ModelForm):
    class Meta:
        model = MDR._concept
        exclude = ['superseded_by', '_is_public', '_is_locked', 'originURI', 'submitter']

    def _media(self):
        js = ('aristotle_mdr/aristotle.wizard.js', )  # , '/static/tiny_mce/tiny_mce.js', '/static/aristotle_mdr/aristotle.tinymce.js')
        media = forms.Media(js=js)
        for field in self.fields.values():
            media = media + field.widget.media
        return media
    media = property(_media)


class WorkgroupVerificationMixin(forms.ModelForm):
    cant_move_any_permission_error = _("You do not have permission to move an item between workgroups.")
    cant_move_from_permission_error = _("You do not have permission to remove an item from this workgroup.")
    cant_move_to_permission_error = _("You do not have permission to move an item to that workgroup.")

    def clean_workgroup(self):
        # raise a permission denied before cleaning if possible.
        # This gives us a 'clearer' error
        # cleaning before checking gives a "invalid selection" even if a user isn't allowed to change workgroups.
        if self.instance.pk is not None:
            if 'workgroup' in self.data.keys() and str(self.data['workgroup']) is not None:
                old_wg_pk = None
                if self.instance.workgroup:
                    old_wg_pk = str(self.instance.workgroup.pk)
                if str(self.data['workgroup']) != str(old_wg_pk) and not (str(self.data['workgroup']) == "" and old_wg_pk is None):
                    if not user_can_move_any_workgroup(self.user):
                        raise forms.ValidationError(WorkgroupVerificationMixin.cant_move_any_permission_error)
                    if not user_can_remove_from_workgroup(self.user, self.instance.workgroup):
                        raise forms.ValidationError(WorkgroupVerificationMixin.cant_move_from_permission_error)
        new_workgroup = self.cleaned_data['workgroup']
        if self.instance.pk is not None:
            if 'workgroup' in self.cleaned_data.keys() and self.instance.workgroup != new_workgroup:
                if not user_can_move_between_workgroups(self.user, self.instance.workgroup, new_workgroup):
                    self.data = self.data.copy()  # need to make a mutable version of the POST querydict.
                    self.data['workgroup'] = self.instance.workgroup.pk
                    raise forms.ValidationError(WorkgroupVerificationMixin.cant_move_to_permission_error)
        return new_workgroup


class CheckIfModifiedMixin(forms.ModelForm):
    modified_since_form_fetched_error = _(
        "The object you are editing has been changed, review the changes before continuing then if you wish to save your changes click the Save button below."
    )
    modified_since_field_missing = _(
        "Unable to determine if this save will overwrite an existing save. Please try again. "
    )
    last_fetched = forms.CharField(
        widget=forms.widgets.HiddenInput(),
        initial=timezone.now(), required=True,
        error_messages={'required': modified_since_field_missing}
    )

    def __init__(self, *args, **kwargs):
        # Tricky... http://www.avilpage.com/2015/03/django-form-gotchas-dynamic-initial.html
        super(CheckIfModifiedMixin, self).__init__(*args, **kwargs)
        self.initial['last_fetched'] = timezone.now()
        self.fields['last_fetched'].initial = timezone.now()

    def clean_last_fetched(self):
        # We need a UTC version of the modified time
        modified_time = timezone.localtime(self.instance.modified, timezone.utc)
        # And need to parse the submitted time back which is in UTC.
        last_fetched = self.cleaned_data['last_fetched']
        last_fetched = dateparse.parse_datetime(last_fetched)
        self.cleaned_data['last_fetched'] = last_fetched
        if self.cleaned_data['last_fetched'] is None or self.cleaned_data['last_fetched'] == "":
            self.initial['last_fetched'] = timezone.now()
            raise forms.ValidationError(CheckIfModifiedMixin.modified_since_field_missing)
        if modified_time > self.cleaned_data['last_fetched']:
            self.initial['last_fetched']= timezone.now()
            raise forms.ValidationError(CheckIfModifiedMixin.modified_since_form_fetched_error)


class ConceptForm(WorkgroupVerificationMixin, UserAwareModelForm):
    """
    Add this in when we look at reintroducing the fancy templates.
    required_css_class = 'required'
    """
    def __init__(self, *args, **kwargs):
        # TODO: Have tis throw a 'no user' error
        first_load = kwargs.pop('first_load', None)
        super(ConceptForm, self).__init__(*args, **kwargs)

        for f in self.fields:
            if hasattr(self.fields[f], 'queryset'):
                if hasattr(self.fields[f].queryset, 'visible'):
                    if f in [m2m.name for m2m in self._meta.model._meta.many_to_many]:
                        field_widget = widgets.ConceptAutocompleteSelectMultiple
                    else:
                        field_widget = widgets.ConceptAutocompleteSelect
                    self.fields[f].queryset = self.fields[f].queryset.all().visible(self.user)
                    self.fields[f].widget = field_widget(model=self.fields[f].queryset.model)
                    self.fields[f].widget.choices = self.fields[f].choices
            if type(self.fields[f]) == forms.fields.DateField:
                self.fields[f].widget = BootstrapDateTimePicker(options={"format": "YYYY-MM-DD"})

        if not self.user.is_superuser:
            self.fields['workgroup'].queryset = self.user.profile.editable_workgroups
        self.fields['name'].widget = forms.widgets.TextInput()
        self.show_slots_tab = True

    def concept_fields(self):
        # version/workgroup are displayed with name/definition
        field_names = [field.name for field in MDR.baseAristotleObject._meta.fields] + ['version', 'workgroup']
        concept_field_names = [
            field.name for field in MDR.concept._meta.fields
            if field.name not in field_names
        ]
        for name in self.fields:
            if name in concept_field_names and name != 'make_new_item':
                yield self[name]

    def object_specific_fields(self):
        # returns every field that isn't in a concept
        obj_field_names = [
            field.name for field in self._meta.model._meta.get_fields()
            if field not in MDR.concept._meta.fields
            ]
        fields = []
        for name in self.fields:
            if name in obj_field_names:
                fields.append(self[name])
        return fields


class Concept_1_Search(UserAwareForm):
    template = "aristotle_mdr/create/concept_wizard_1_search.html"
    # Object class fields
    name = forms.CharField(max_length=256)
    version = forms.CharField(max_length=256, required=False)
    definition = forms.CharField(widget=forms.Textarea, required=False)

    def save(self, *args, **kwargs):
        pass


def subclassed_modelform(set_model):
    class MyForm(ConceptForm):
        class Meta(ConceptForm.Meta):
            model = set_model
            fields = '__all__'
    return MyForm


def subclassed_edit_modelform(set_model):
    class MyForm(ConceptForm, CheckIfModifiedMixin):
        change_comments = forms.CharField(widget=forms.Textarea, required=False)

        def _media(self):
            js = ('aristotle_mdr/aristotle.moveable.js', )
            media = forms.Media(js=js)
            for field in self.fields.values():
                media = media + field.widget.media
            return media
        media = property(_media)

        class Meta(ConceptForm.Meta):
            model = set_model
            if set_model.edit_page_excludes:
                exclude = set(list(UserAwareModelForm._meta.exclude) + list(set_model.edit_page_excludes))
            else:
                fields = '__all__'
    return MyForm


def subclassed_clone_modelform(set_model):
    class MyForm(ConceptForm):
        change_comments = forms.CharField(widget=forms.Textarea, required=False)

        class Meta(ConceptForm.Meta):
            model = set_model
            if set_model.edit_page_excludes:
                exclude = set_model.edit_page_excludes
            else:
                fields = '__all__'
    return MyForm


def subclassed_wizard_2_Results(set_model):
    class MyForm(Concept_2_Results):
        class Meta(Concept_2_Results.Meta):
            model = set_model
            fields = '__all__'
    return MyForm


class Concept_2_Results(ConceptForm):
    make_new_item = forms.BooleanField(
        initial=False,
        label=_("I've reviewed these items, and none of them meet my needs. Make me a new one."),
        error_messages={'required': 'You must select this to ackowledge you have reviewed the above items.'}
    )

    def __init__(self, *args, **kwargs):
        self.check_similar = kwargs.pop('check_similar', True)
        super(Concept_2_Results, self).__init__(*args, **kwargs)
        self.fields['workgroup'].queryset = self.user.profile.editable_workgroups
        self.fields['workgroup'].initial = self.user.profile.activeWorkgroup
        self.fields['name'].widget = forms.widgets.TextInput()
        # self.fields['definition'].widget = forms.widgets.TextInput()
        if not self.check_similar:
            self.fields.pop('make_new_item')


class DEC_OCP_Search(UserAwareForm):
    template = "aristotle_mdr/create/dec_1_initial_search.html"
    # Object class fields
    oc_name = forms.CharField(max_length=256)
    oc_desc = forms.CharField(widget=forms.Textarea, required=False)
    # Property fields
    pr_name = forms.CharField(max_length=256)
    pr_desc = forms.CharField(widget=forms.Textarea, required=False)

    def save(self, *args, **kwargs):
        pass


class DEC_OCP_Results(UserAwareForm):
    def __init__(self, oc_similar=None, pr_similar=None, oc_duplicate=None, pr_duplicate=None, *args, **kwargs):
        super(DEC_OCP_Results, self).__init__(*args, **kwargs)

        if oc_similar:
            oc_options = [(oc.object.id, oc) for oc in oc_similar]
            oc_options.append(("X", "None of the above meet my needs"))
            self.fields['oc_options'] = forms.ChoiceField(
                label="Similar Object Classes",
                choices=oc_options,
                widget=forms.RadioSelect()
            )
        if pr_similar:
            pr_options = [(pr.object.id, pr) for pr in pr_similar]
            pr_options.append(("X", "None of the above meet my needs"))
            self.fields['pr_options'] = forms.ChoiceField(
                label="Similar Properties",
                choices=tuple(pr_options),
                widget=forms.RadioSelect()
            )

    def clean_oc_options(self):
        if self.cleaned_data['oc_options'] == "X":
            # The user chose to make their own item, so return No item.
            return None
        try:
            oc = MDR.ObjectClass.objects.get(pk=self.cleaned_data['oc_options'])
            return oc
        except ObjectDoesNotExist:
            return None

    def clean_pr_options(self):
        if self.cleaned_data['pr_options'] == "X":
            # The user chose to make their own item, so return No item.
            return None
        try:
            return MDR.Property.objects.get(pk=self.cleaned_data['pr_options'])
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        pass


class DEC_Find_DEC_Results(Concept_2_Results):
    class Meta(Concept_2_Results.Meta):
        model = MDR.DataElementConcept


class DEC_Complete(UserAwareForm):
    make_items = forms.BooleanField(
        initial=False,
        label=_("I've reviewed these items, and wish to create them."),
        error_messages={'required': 'You must select this to ackowledge you have reviewed the above items.'}
    )

    def save(self, *args, **kwargs):
        pass


# Data Element - Object Class / Property / Value Domain search form
class DE_OCPVD_Search(UserAwareForm):
    template = "aristotle_mdr/create/de_1_initial_search.html"
    # Object Class fields
    oc_name = forms.CharField(max_length=256)
    oc_desc = forms.CharField(widget=forms.Textarea, required=False)
    # Property fields
    pr_name = forms.CharField(max_length=256)
    pr_desc = forms.CharField(widget=forms.Textarea, required=False)
    # Value Domain fields
    vd_name = forms.CharField(max_length=256)
    vd_desc = forms.CharField(widget=forms.Textarea, required=False)

    def save(self, *args, **kwargs):
        pass


class DE_OCPVD_Results(DEC_OCP_Results):
    def __init__(self, vd_similar=None, vd_duplicate=None, *args, **kwargs):
        super(DE_OCPVD_Results, self).__init__(*args, **kwargs)

        if vd_similar:
            vd_options = [(vd.object.id, vd) for vd in vd_similar]
            vd_options.append(("X", "None of the above meet my needs"))
            self.fields['vd_options'] = forms.ChoiceField(
                label="Similar Value Domains",
                choices=tuple(vd_options),
                widget=forms.RadioSelect()
            )

    def clean_vd_options(self):
        if self.cleaned_data['vd_options'] == "X":
            # The user chose to make their own item, so return No item.
            return None
        try:
            return MDR.ValueDomain.objects.get(pk=self.cleaned_data['vd_options'])
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        pass


class DE_Find_DEC_Results(UserAwareForm):
    def __init__(self, *args, **kwargs):
        dec_similar = kwargs.pop('dec_similar')
        super(DE_Find_DEC_Results, self).__init__(*args, **kwargs)
        if dec_similar:
            dec_options = [(dec.id, dec) for dec in dec_similar]
            dec_options.append(("X", "None of the above meet my needs"))
            self.fields['dec_options'] = forms.ChoiceField(
                label="Similar Data Element Concepts",
                choices=tuple(dec_options),
                widget=forms.RadioSelect()
            )

    def clean_dec_options(self):
        if self.cleaned_data['dec_options'] == "X":
            # The user chose to make their own item, so return No item.
            return None
        try:
            dec = MDR.DataElementConcept.objects.get(pk=self.cleaned_data['dec_options'])
            return dec
        except ObjectDoesNotExist:
            return None

    def save(self, *args, **kwargs):
        pass


class DE_Find_DE_Results_from_components(UserAwareForm):
    make_new_item = forms.BooleanField(
        initial=False,
        label=_("I've reviewed these items, and none of them meet my needs. Make me a new one."),
        error_messages={'required': 'You must select this to ackowledge you have reviewed the above items.'}
    )

    def save(self, *args, **kwargs):
        pass


class DE_Find_DE_Results(Concept_2_Results):
    class Meta(Concept_2_Results.Meta):
        model = MDR.DataElement


class DE_Complete(UserAwareForm):
    make_items = forms.BooleanField(
        initial=False,
        label=_("I've reviewed these items, and wish to create them."),
        error_messages={'required': 'You must select this to ackowledge you have reviewed the above items.'}
    )

    def save(self, *args, **kwargs):
        pass
