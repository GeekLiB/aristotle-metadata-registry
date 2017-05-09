from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.defaultfilters import slugify
from django.template.loader import select_template
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView
from django.utils.decorators import method_decorator
import datetime

from aristotle_mdr.perms import user_can_view, user_can_edit, user_can_change_status
from aristotle_mdr.utils import cache_per_item_user, concept_to_dict, construct_change_message, url_slugify_concept
from aristotle_mdr import forms as MDRForms
from aristotle_mdr import exceptions as registry_exceptions
from aristotle_mdr import models as MDR
from aristotle_mdr.utils import fetch_aristotle_settings


class BulkAction(FormView):

    def dispatch(self, *args, **kwargs):
        action = self.get_action()
        if not action:
            return HttpResponseRedirect(self.request.GET.get("next", "/"))
        if not action['can_use'](self.request.user):
            if self.request.user.is_anonymous():
                return redirect(
                    reverse('friendly_login') + '?next=%s' % self.request.path
                )
            else:
                raise PermissionDenied
        return super(BulkAction, self).dispatch(*args, **kwargs)

    def get_action(self):
        actions = get_bulk_actions()
        action = self.request.POST.get("bulkaction", None)
        return actions.get(action, None)

    def post(self, request, *args, **kwargs):
        url = request.GET.get("next", "/")
        message = ""
        action = self.get_action()

        if action is None:
            # no action, messed up, redirect
            return HttpResponseRedirect(url)
        action_form = action['form']
        if action_form.confirm_page is None:
            # if there is no confirm page or extra details required, do the action and redirect
            form = action_form(request.POST, user=request.user, request=request)  # A form bound to the POST data

            if form.is_valid():
                to_change = form.items_to_change
                confirmed = request.POST.get("confirmed", None)
                if to_change.count() > 10 and not confirmed:
                    new_form = request.POST.copy()
                    new_form.setlist('items', form.items_to_change.values_list('id', flat=True))
                    form = action_form(new_form, user=request.user, request=request, items=[])
                    return render(
                        request,
                        "aristotle_mdr/actions/bulk_actions/lots_of_things.html",
                        {
                            "items": to_change,
                            "form": form,
                            "next": url,
                            "action": action,
                        }
                    )
                message = form.make_changes()
                messages.add_message(request, messages.INFO, message)
            else:
                messages.add_message(request, messages.ERROR, form.errors)
            return HttpResponseRedirect(url)
        else:
            form = action_form(request.POST, user=request.user, request=request)
            items = []
            if form.is_valid():
                items = form.cleaned_data['items']

            confirmed = request.POST.get("confirmed", None)
            if form.items_to_change:
                new_form = request.POST.copy()
                new_form.setlist('items', form.items_to_change.values_list('id', flat=True))
                request.POST = new_form

            if confirmed:
                # We've passed the confirmation page, try and save.
                form = action_form(request.POST, user=request.user, request=request, items=items)  # A form bound to the POST data
                # there was an error with the form redisplay
                if form.is_valid():
                    message = form.make_changes()

                    messages.add_message(request, messages.INFO, message)
                    return HttpResponseRedirect(url)
            else:
                # we need a confirmation, render the next form
                form = action_form(request.POST, user=request.user, request=request, items=items)
            return render(
                request,
                action_form.confirm_page,
                {
                    "items": items,
                    "form": form,
                    "next": url,
                    "action": action,
                }
            )
        return HttpResponseRedirect(url)


def get_bulk_actions():
    import re
    config = fetch_aristotle_settings()
    if not hasattr(get_bulk_actions, 'actions') or not get_bulk_actions.actions:
        actions = {}
        for action_name, form in config.get('BULK_ACTIONS', {}).items():
            if not re.search('^[a-zA-Z0-9\_\.]+$', form):  # pragma: no cover
                # Invalid download_type
                raise registry_exceptions.BadBulkActionModuleName("Bulk action isn't a valid Python module name.")

            from django.utils.module_loading import import_string
            # module, form = form.rsplit('.', 1)
            # f = exec('from %s import %s as f' % (module, form))
            f = import_string(form)
            # We need to make this a dictionary, not a class as otherwise
            # the template engine tries to instantiate it.
            frm = {'form': f}
            for prop in ['classes', 'can_use', 'text']:
                frm[prop] = getattr(f, prop, None)
            actions[action_name] = frm
        # Save to method to prevent having to reimport everytime
        get_bulk_actions.actions = actions
    return get_bulk_actions.actions
