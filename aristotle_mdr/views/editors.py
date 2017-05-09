from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.db import transaction
from django.forms import ValidationError, ModelForm
from django.forms.models import modelformset_factory, inlineformset_factory
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView
from django.utils import timezone
from django.utils.decorators import method_decorator

import reversion

from aristotle_mdr.perms import user_can_view, user_can_edit, user_can_change_status
from aristotle_mdr.utils import cache_per_item_user, concept_to_clone_dict, concept_to_dict, construct_change_message, url_slugify_concept
from aristotle_mdr import forms as MDRForms
from aristotle_mdr import models as MDR

import logging

logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)


class PermissionFormView(FormView):
    item = None

    def dispatch(self, request, *args, **kwargs):
        if not self.item:
            self.item = get_object_or_404(
                MDR._concept, pk=self.kwargs['iid']
            ).item
        self.model = self.item.__class__
        if not user_can_edit(self.request.user, self.item):
            if request.user.is_anonymous():
                return redirect(reverse('friendly_login') + '?next=%s' % request.path)
            else:
                raise PermissionDenied
        return super(PermissionFormView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(PermissionFormView, self).get_form_kwargs()
        kwargs.update({
            'user': self.request.user,
        })
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super(PermissionFormView, self).get_context_data(*args, **kwargs)
        context.update({'model': self.model._meta.model_name,
                        'app_label': self.model._meta.app_label,
                        'item': self.item})
        return context


class EditItemView(PermissionFormView):
    template_name = "aristotle_mdr/actions/advanced_editor.html"

    def __init__(self, *args, **kwargs):
        super(EditItemView, self).__init__(*args, **kwargs)
        self.slots_active = 'aristotle_mdr.contrib.slots' in settings.INSTALLED_APPS
        self.identifiers_active = 'aristotle_mdr.contrib.identifiers' in settings.INSTALLED_APPS

    def get_form_class(self):
        return MDRForms.wizards.subclassed_edit_modelform(self.model)

    def get_form_kwargs(self):
        kwargs = super(EditItemView, self).get_form_kwargs()
        kwargs.update({
            'instance': self.item,
        })
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        slot_formset = None

        if form.is_valid():
            with transaction.atomic(), reversion.revisions.create_revision():
                item = form.save(commit=False)

                has_change_comments = form.data.get('change_comments', False)
                change_comments = form.data.get('change_comments', "")
                if self.slots_active:
                    slot_formset = self.get_slots_formset()(request.POST, request.FILES, item.concept)
                    if slot_formset.is_valid():

                        # Save the slots
                        slot_formset.save()

                        # Save the change comments
                        if not has_change_comments:
                            change_comments += construct_change_message(request, form, [slot_formset])
                    else:
                        return self.form_invalid(form, slots_FormSet=slot_formset)

                if self.identifiers_active:
                    id_formset = self.get_identifier_formset()(request.POST, request.FILES, item.concept)
                    if id_formset.is_valid():

                        # Save the slots
                        id_formset.save()

                        if not has_change_comments:
                            change_comments += construct_change_message(request, form, [id_formset])
                    else:
                        return self.form_invalid(form, identifier_FormSet=id_formset)

                reversion.revisions.set_user(request.user)
                reversion.revisions.set_comment(change_comments)
                form.save_m2m()
                item.save()
                return HttpResponseRedirect(url_slugify_concept(self.item))

        return self.form_invalid(form)

    def get_slots_formset(self):
        from aristotle_mdr.contrib.slots.forms import slot_inlineformset_factory
        return slot_inlineformset_factory(model=self.model)

    def get_identifier_formset(self):
        from aristotle_mdr.contrib.identifiers.models import ScopedIdentifier
        from django.forms.models import inlineformset_factory
        return inlineformset_factory(
            MDR._concept, ScopedIdentifier,
            can_delete=True,
            fields=('concept', 'namespace', 'identifier', 'version'),
            extra=1,
            )

    def form_invalid(self, form, slots_FormSet=None, identifier_FormSet=None):
        """
        If the form is invalid, re-render the context data with the
        data-filled form and errors.
        """
        return self.render_to_response(self.get_context_data(form=form, slots_FormSet=slots_FormSet))

    def get_context_data(self, *args, **kwargs):
        from aristotle_mdr.contrib.slots.models import Slot
        context = super(EditItemView, self).get_context_data(*args, **kwargs)
        if self.slots_active and kwargs.get('slots_FormSet', None):
            context['slots_FormSet'] = kwargs['slots_FormSet']
        else:
            context['slots_FormSet'] = self.get_slots_formset()(
                queryset=Slot.objects.filter(concept=self.item.id),
                instance=self.item.concept
                )
        from aristotle_mdr.contrib.identifiers.models import ScopedIdentifier
        if self.identifiers_active and kwargs.get('identifier_FormSet', None):
            context['identifier_FormSet'] = kwargs['identifier_FormSet']
        else:
            context['identifier_FormSet'] = self.get_identifier_formset()(
                queryset=ScopedIdentifier.objects.filter(concept=self.item.id),
                instance=self.item.concept
                )

        context['show_slots_tab'] = self.slots_active
        context['show_id_tab'] = self.identifiers_active
        return context


class CloneItemView(PermissionFormView):
    template_name = "aristotle_mdr/create/clone_item.html"

    def dispatch(self, request, *args, **kwargs):
        self.item_to_clone = get_object_or_404(
            MDR._concept, pk=self.kwargs['iid']
        ).item
        self.item = self.item_to_clone
        return super(CloneItemView, self).dispatch(request, *args, **kwargs)

    def get_form_class(self):
        return MDRForms.wizards.subclassed_clone_modelform(self.model)

    def get_form_kwargs(self):
        kwargs = super(CloneItemView, self).get_form_kwargs()
        kwargs.update({
            'initial': concept_to_clone_dict(self.item_to_clone)
        })
        return kwargs

    def post(self, request, *args, **kwargs):
        form = self.get_form()

        if form.is_valid():
            with transaction.atomic(), reversion.revisions.create_revision():
                new_clone = form.save()
                reversion.revisions.set_user(self.request.user)
                reversion.revisions.set_comment("Cloned from %s (id: %s)" % (self.item_to_clone.name, str(self.item_to_clone.pk)))
                return HttpResponseRedirect(url_slugify_concept(new_clone))
        else:
            return self.form_invalid(form)
