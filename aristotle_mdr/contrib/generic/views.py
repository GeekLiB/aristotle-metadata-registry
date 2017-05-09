from django import forms
from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.forms.models import modelformset_factory
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, ListView, TemplateView

from aristotle_mdr.contrib.autocomplete import widgets
from aristotle_mdr.utils import get_concepts_for_apps
from aristotle_mdr.models import _concept
from aristotle_mdr.perms import user_can_edit, user_can_view
from aristotle_mdr.utils import construct_change_message

import reversion


def generic_foreign_key_factory_view(request, **kwargs):
    item = get_object_or_404(_concept, pk=kwargs['iid']).item
    field = None

    for f in item._meta.fields:
        if f.name.lower() == kwargs['fk_field'].lower():
            field = f.name

    if not field:
        raise Http404

    return GenericAlterForeignKey.as_view(
        model_base=item.__class__,
        model_base_field=field,
        form_title=_('Add Object Class')
    )(request, **kwargs)


class GenericWithItemURLFormView(FormView):
    user_checks = []
    permission_checks = [user_can_view]
    model_base = _concept

    def dispatch(self, request, *args, **kwargs):
        self.item = get_object_or_404(self.model_base, pk=self.kwargs['iid'])

        if not (
            self.item and
            all([perm(request.user, self.item) for perm in self.permission_checks]) and
            all([perm(request.user) for perm in self.user_checks])
        ):
            if request.user.is_anonymous():
                return redirect(reverse('friendly_login') + '?next=%s' % request.path)
            else:
                raise PermissionDenied
        return super(GenericWithItemURLFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(GenericWithItemURLFormView, self).get_context_data(*args, **kwargs)
        context['item'] = self.item
        context['submit_url'] = self.request.get_full_path()
        return context

    def get_success_url(self):
        return self.item.get_absolute_url()


class GenericAlterManyToSomethingFormView(GenericWithItemURLFormView):
    permission_checks = [user_can_edit]
    model_base = None
    model_to_add = None
    model_base_field = None
    form_title = None
    form_submit_text = _('Save')

    def get_context_data(self, *args, **kwargs):
        context = super(GenericAlterManyToSomethingFormView, self).get_context_data(*args, **kwargs)
        context['model_to_add'] = self.model_to_add
        context['model_base'] = self.model_base
        context['item'] = self.item
        context['form_title'] = self.form_title or _('Add child item')
        context['form_submit_text'] = self.form_submit_text
        return context


class GenericAlterForeignKey(GenericAlterManyToSomethingFormView):
    """
    A view that provides a framework for altering ManyToOne relationships
    (Include through models from ManyToMany relationships)
    from one 'base' object to many others.

    The URL pattern must pass a kwarg with the name `iid` that is the object from the
    `model_base` to use as the main link for the many to many relation.

    * `model_base` - mandatory - The model with the instance to be altered
    * `model_to_add` - mandatory - The model that has instances we will link to the base.
    * `template_name`
        - optional - The template used to display the form.
        - default - "aristotle_mdr/generic/actions/alter_foreign_key.html"
    * `model_base_field` - mandatory - the name of the field that goes from the `model_base` to the `model_to_add`.
    * `model_to_add_field` - mandatory - the name of the field on the `model_to_add` model that links to the `model_base` model.
    * `form_title` - Title for the form

    For example: If we have a many to many relationship from `DataElement`s to
    `Dataset`s, to alter the `DataElement`s attached to a `Dataset`, `Dataset` is the
    `base_model` and `model_to_add` is `DataElement`.
    """

    template_name = "aristotle_mdr/generic/actions/alter_foreign_key.html"
    model_to_add_field = None
    form = None

    def get_context_data(self, *args, **kwargs):
        context = super(GenericAlterForeignKey, self).get_context_data(*args, **kwargs)
        context['form_add_another_text'] = self.form_submit_text or _('Add another')
        form = self.form or self.get_form()(instance=self.item)
        context['form'] = form
        return context

    def get_form(self, form_class=None):
        foreign_model = self.model_base._meta.get_field(self.model_base_field).related_model
        qs = foreign_model.objects.visible(self.request.user)
        model_base_field = self.model_base_field

        class FKOnlyForm(forms.ModelForm):
            class Meta():
                model = self.model_base
                fields = (self.model_base_field,)
                widgets = {
                    self.model_base_field: widgets.ConceptAutocompleteSelect(
                        model=foreign_model
                    )
                }

            def __init__(self, *args, **kwargs):
                super(FKOnlyForm, self).__init__(*args, **kwargs)
                self.fields[model_base_field].queryset = qs

        return FKOnlyForm

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = self.get_form()
        self.form = form(self.request.POST, self.request.FILES, instance=self.item)
        if self.form.is_valid():
            with transaction.atomic(), reversion.revisions.create_revision():
                self.form.save()  # do this to ensure we are saving reversion records for the value domain, not just the values
                reversion.revisions.set_user(request.user)
                reversion.revisions.set_comment(
                    _("Altered relationship of '%s' on %s") % (self.model_base_field, self.item)
                )

            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)


class GenericAlterManyToManyView(GenericAlterManyToSomethingFormView):
    """
    A view that provides a framework for altering ManyToMany relationships from
    one 'base' object to many others.

    The URL pattern must pass a kwarg with the name `iid` that is the object from the
    `model_base` to use as the main link for the many to many relation.

    * `model_base` - mandatory - The model with the instance to be altered
    * `model_to_add` - mandatory - The model that has instances we will link to the base.
    * `template_name`
        - optional - The template used to display the form.
        - default - "aristotle_mdr/generic/actions/alter_many_to_many.html"
    * `model_base_field` - mandatory - the field name that goes from the `model_base` to the `model_to_add`.
    * `form_title` - Title for the form

    For example: If we have a many to many relationship from `DataElement`s to
    `Dataset`s, to alter the `DataElement`s attached to a `Dataset`, `Dataset` is the
    `base_model` and `model_to_add` is `DataElement`.
    """

    template_name = "aristotle_mdr/generic/actions/alter_many_to_many.html"

    def get_context_data(self, *args, **kwargs):
        context = super(GenericAlterManyToManyView, self).get_context_data(*args, **kwargs)
        return context

    def get_form_class(self):
        class M2MForm(forms.Form):
            items_to_add = forms.ModelMultipleChoiceField(
                queryset=self.model_to_add.objects.visible(self.request.user),
                label="Attach",
                required=False,
                widget=widgets.ConceptAutocompleteSelectMultiple(
                    model=self.model_to_add
                )
            )
        return M2MForm

    def get_initial(self):
        return {
            'items_to_add': getattr(self.item, self.model_base_field).all()
        }

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = self.get_form()
        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def form_valid(self, form):
        self.item.__setattr__(self.model_base_field, form.cleaned_data['items_to_add'])
        self.item.save()
        return HttpResponseRedirect(self.get_success_url())


class GenericAlterOneToManyView(GenericAlterManyToSomethingFormView):
    """
    A view that provides a framework for altering ManyToOne relationships
    (Include through models from ManyToMany relationships)
    from one 'base' object to many others.

    The URL pattern must pass a kwarg with the name `iid` that is the object from the
    `model_base` to use as the main link for the many to many relation.

    * `model_base` - mandatory - The model with the instance to be altered
    * `model_to_add` - mandatory - The model that has instances we will link to the base.
    * `template_name`
        - optional - The template used to display the form.
        - default - "aristotle_mdr/generic/actions/alter_many_to_many.html"
    * `model_base_field` - mandatory - the name of the field that goes from the `model_base` to the `model_to_add`.
    * `model_to_add_field` - mandatory - the name of the field on the `model_to_add` model that links to the `model_base` model.
    * `ordering_field` - optional - name of the ordering field, if entered this field is hidden and updated using a drag-and-drop library
    * `form_add_another_text` - optional - string used for the button to add a new row to the form - defaults to "Add another"
    * `form_title` - Title for the form

    For example: If we have a many to many relationship from `DataElement`s to
    `Dataset`s, to alter the `DataElement`s attached to a `Dataset`, `Dataset` is the
    `base_model` and `model_to_add` is `DataElement`.
    """

    template_name = "aristotle_mdr/generic/actions/alter_one_to_many.html"
    model_to_add_field = None
    ordering_field = None
    form_add_another_text = None

    formset = None

    def get_context_data(self, *args, **kwargs):
        context = super(GenericAlterOneToManyView, self).get_context_data(*args, **kwargs)
        context['form_add_another_text'] = self.form_add_another_text or _('Add another')
        num_items = getattr(self.item, self.model_base_field).count()
        context['formset'] = self.formset or self.get_formset()(
            queryset=getattr(self.item, self.model_base_field).all(),
            initial=[{'ORDER': num_items + 1}]
            )
        return context

    def get_form(self, form_class=None):
        return None

    def get_formset(self):
        _widgets = {}

        for f in self.model_to_add._meta.fields:
            foreign_model = self.model_to_add._meta.get_field(f.name).related_model
            if foreign_model and issubclass(foreign_model, _concept):
                _widgets.update({
                    f.name: widgets.ConceptAutocompleteSelect(
                        model=foreign_model
                    )
                })

        from aristotle_mdr.contrib.generic.forms import HiddenOrderModelFormSet
        return modelformset_factory(
            self.model_to_add,
            formset=HiddenOrderModelFormSet,
            can_order=True,  # we assign this back to the ordering field
            can_delete=True,
            exclude=[self.model_to_add_field, self.ordering_field],
            # fields='__all__',
            extra=1,
            widgets=_widgets
            )

    def post(self, request, *args, **kwargs):
        """
        Handles POST requests, instantiating a form instance with the passed
        POST variables and then checked for validity.
        """
        form = self.get_form()
        GenericFormSet = self.get_formset()
        self.formset = GenericFormSet(self.request.POST, self.request.FILES)
        formset = self.formset
        if formset.is_valid():
            with transaction.atomic(), reversion.revisions.create_revision():
                self.item.save()  # do this to ensure we are saving reversion records for the value domain, not just the values
                formset.save(commit=False)
                for form in formset.forms:
                    all_blank = not any(form[f].value() for f in form.fields if f is not self.ordering_field)
                    if all_blank:
                        continue
                    if form['id'].value() not in [deleted_record['id'].value() for deleted_record in formset.deleted_forms]:
                        # Don't immediately save, we need to attach the parent object
                        value = form.save(commit=False)
                        setattr(value, self.model_to_add_field, self.item)
                        if self.ordering_field:
                            setattr(value, self.ordering_field, form.cleaned_data['ORDER'])
                        value.save()
                for obj in formset.deleted_objects:
                    obj.delete()
                # formset.save(commit=True)
                reversion.revisions.set_user(request.user)
                reversion.revisions.set_comment(construct_change_message(request, None, [formset]))

            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.form_invalid(form)
