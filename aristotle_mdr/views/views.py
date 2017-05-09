from django import VERSION as django_version
from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import RequestContext
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.utils.module_loading import import_string

import reversion
from reversion_compare.views import HistoryCompareDetailView

from aristotle_mdr.perms import (
    user_can_view, user_can_edit,
    user_can_change_status
)
from aristotle_mdr import perms
from aristotle_mdr.utils import cache_per_item_user, url_slugify_concept
from aristotle_mdr import forms as MDRForms
from aristotle_mdr import models as MDR
from aristotle_mdr.utils import get_concepts_for_apps, fetch_aristotle_settings
from aristotle_mdr.views.utils import generate_visibility_matrix

from haystack.views import FacetedSearchView

import logging

logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)

PAGES_PER_RELATED_ITEM = 15


class DynamicTemplateView(TemplateView):
    def get_template_names(self):
        return ['aristotle_mdr/static/%s.html' % self.kwargs['template']]


class ConceptHistoryCompareView(HistoryCompareDetailView):
    model = MDR._concept
    pk_url_kwarg = 'iid'
    template_name = "aristotle_mdr/actions/concept_history_compare.html"

    def get_object(self, queryset=None):
        item = super(ConceptHistoryCompareView, self).get_object(queryset)
        if not user_can_view(self.request.user, item):
            raise PermissionDenied
        self.model = item.item.__class__  # Get the subclassed object
        return item

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ConceptHistoryCompareView, self).dispatch(*args, **kwargs)


def get_if_user_can_view(objtype, user, iid):
    item = get_object_or_404(objtype, pk=iid)
    if user_can_view(user, item):
        return item
    else:
        return False


def render_if_user_can_view(item_type, request, *args, **kwargs):
    # request = kwargs.pop('request')
    return render_if_condition_met(
        request, user_can_view, item_type, *args, **kwargs
    )


@login_required
def render_if_user_can_edit(item_type, request, *args, **kwargs):
    request = kwargs.pop('request')
    return render_if_condition_met(
        request, user_can_edit, item_type, *args, **kwargs
    )


def concept(*args, **kwargs):
    return render_if_user_can_view(MDR._concept, *args, **kwargs)


def measure(request, iid, model_slug, name_slug):
    item = get_object_or_404(MDR.Measure, pk=iid).item
    return render(
        request, [item.template],
        {
            'item': item,
            # 'view': request.GET.get('view', '').lower(),
            # 'last_edit': last_edit
        }
    )

    # return render_if_user_can_view(MDR.Measure, *args, **kwargs)


@cache_per_item_user(ttl=300, cache_post=False)
def render_if_condition_met(request, condition, objtype, iid, model_slug=None, name_slug=None, subpage=None):
    item = get_object_or_404(objtype, pk=iid).item
    if item._meta.model_name != model_slug or not slugify(item.name).startswith(str(name_slug)):
        return redirect(url_slugify_concept(item))
    if not condition(request.user, item):
        if request.user.is_anonymous():
            return redirect(
                reverse('friendly_login') + '?next=%s' % request.path
            )
        else:
            raise PermissionDenied

    # We add a user_can_edit flag in addition
    # to others as we have odd rules around who can edit objects.
    isFavourite = request.user.is_authenticated() and request.user.profile.is_favourite(item)
    from reversion.models import Version
    last_edit = Version.objects.get_for_object(item).first()

    default_template = "%s/concepts/%s.html" % (item.__class__._meta.app_label, item.__class__._meta.model_name)
    return render(
        request, [default_template, item.template],
        {
            'item': item,
            # 'view': request.GET.get('view', '').lower(),
            'isFavourite': isFavourite,
            'last_edit': last_edit
        }
    )


def registrationHistory(request, iid):
    item = get_if_user_can_view(MDR._concept, request.user, iid)
    if not item:
        if request.user.is_anonymous():
            return redirect(reverse('friendly_login') + '?next=%s' % request.path)
        else:
            raise PermissionDenied

    history = item.statuses.order_by("registrationAuthority", "-registrationDate")
    out = {}
    for status in history:
        if status.registrationAuthority in out.keys():
            out[status.registrationAuthority].append(status)
        else:
            out[status.registrationAuthority] = [status]

    return render(request, "aristotle_mdr/registrationHistory.html", {'item': item, 'history': out})


def unauthorised(request, path=''):
    if request.user.is_anonymous():
        return render(request, "401.html", {"path": path, "anon": True, }, status=401)
    else:
        return render(request, "403.html", {"path": path, "anon": True, }, status=403)


def create_list(request):
    if request.user.is_anonymous():
        return redirect(reverse('friendly_login') + '?next=%s' % request.path)
    if not perms.user_is_editor(request.user):
        raise PermissionDenied

    aristotle_apps = fetch_aristotle_settings().get('CONTENT_EXTENSIONS', [])
    aristotle_apps += ["aristotle_mdr"]
    out = {}

    wizards = []
    for wiz in getattr(settings, 'ARISTOTLE_SETTINGS', {}).get('METADATA_CREATION_WIZARDS', []):
        w = wiz.copy()
        _w = {
            'model': apps.get_app_config(wiz['app_label']).get_model(wiz['model']),
            'class': import_string(wiz['class']),
        }
        w.update(_w)
        wizards.append(w)

    for m in get_concepts_for_apps(aristotle_apps):
        # Only output subclasses of 11179 concept
        app_models = out.get(m.app_label, {'app': None, 'models': []})
        if app_models['app'] is None:
            try:
                app_models['app'] = getattr(apps.get_app_config(m.app_label), 'verbose_name')
            except:
                app_models['app'] = "No name"  # Where no name is configured in the app_config, set a dummy so we don't keep trying
        app_models['models'].append((m, m.model_class()))
        out[m.app_label] = app_models

    return render(
        request, "aristotle_mdr/create/create_list.html",
        {
            'models': out,
            'wizards': wizards
        }
    )


@login_required
def toggleFavourite(request, iid):
    item = get_object_or_404(MDR._concept, pk=iid).item
    if not user_can_view(request.user, item):
        if request.user.is_anonymous():
            return redirect(reverse('friendly_login') + '?next=%s' % request.path)
        else:
            raise PermissionDenied
    request.user.profile.toggleFavourite(item)
    if request.GET.get('next', None):
        return redirect(request.GET.get('next'))
    if item.concept in request.user.profile.favourites.all():
        message = _("%s added to favourites.") % (item.name)
    else:
        message = _("%s removed from favourites.") % (item.name)
    message = _(message + " Review your favourites from the user menu.")
    messages.add_message(request, messages.SUCCESS, message)
    return redirect(url_slugify_concept(item))


def registrationauthority(request, iid, *args, **kwargs):
    if iid is None:
        return redirect(reverse("aristotle_mdr:all_registration_authorities"))
    item = get_object_or_404(MDR.RegistrationAuthority, pk=iid).item

    return render(request, item.template, {'item': item.item})


def organization(request, iid, *args, **kwargs):
    if iid is None:
        return redirect(reverse("aristotle_mdr:all_organizations"))
    item = get_object_or_404(MDR.Organization, pk=iid).item

    return render(request, item.template, {'item': item.item})


def all_registration_authorities(request):
    ras = MDR.RegistrationAuthority.objects.order_by('name')
    return render(request, "aristotle_mdr/organization/all_registration_authorities.html", {'registrationAuthorities': ras})


def all_organizations(request):
    orgs = MDR.Organization.objects.order_by('name')
    return render(request, "aristotle_mdr/organization/all_organizations.html", {'organization': orgs})


# Actions


def changeStatus(request, iid):
    item = get_object_or_404(MDR._concept, pk=iid).item
    if not (item and user_can_change_status(request.user, item)):
        if request.user.is_anonymous():
            return redirect(reverse('friendly_login') + '?next=%s' % request.path)
        else:
            raise PermissionDenied
    # There would be an else here, but both branches above return,
    # so we've chopped it out to prevent an arrow anti-pattern.
    if request.method == 'POST':  # If the form has been submitted...
        form = MDRForms.ChangeStatusForm(request.POST, user=request.user)  # A form bound to the POST data
        if form.is_valid():
            # process the data in form.cleaned_data as required
            ras = form.cleaned_data['registrationAuthorities']
            state = form.cleaned_data['state']
            regDate = form.cleaned_data['registrationDate']
            cascade = form.cleaned_data['cascadeRegistration']
            changeDetails = form.cleaned_data['changeDetails']
            with transaction.atomic(), reversion.revisions.create_revision():
                reversion.revisions.set_user(request.user)
                for ra in ras:
                    if cascade:
                        register_method = ra.cascaded_register
                    else:
                        register_method = ra.register

                    register_method(
                        item,
                        state,
                        request.user,
                        changeDetails=changeDetails,
                        registrationDate=regDate,
                    )
                    # TODO: notification and message on success/failure
            return HttpResponseRedirect(url_slugify_concept(item))
    else:
        form = MDRForms.ChangeStatusForm(user=request.user)
    import json

    return render(
        request,
        "aristotle_mdr/actions/changeStatus.html",
        {
            "item": item,
            "form": form,
            "status_matrix": json.dumps(generate_visibility_matrix(request.user)),
        }
    )


def supersede(request, iid):
    item = get_object_or_404(MDR._concept, pk=iid).item
    if not (item and user_can_edit(request.user, item)):
        if request.user.is_anonymous():
            return redirect(reverse('friendly_login') + '?next=%s' % request.path)
        else:
            raise PermissionDenied
    qs=item.__class__.objects.all()
    if request.method == 'POST':  # If the form has been submitted...
        form = MDRForms.SupersedeForm(request.POST, user=request.user, item=item, qs=qs)  # A form bound to the POST data
        if form.is_valid():
            with transaction.atomic(), reversion.revisions.create_revision():
                reversion.revisions.set_user(request.user)
                item.superseded_by = form.cleaned_data['newerItem']
                item.save()
            return HttpResponseRedirect(url_slugify_concept(item))
    else:
        form = MDRForms.SupersedeForm(item=item, user=request.user, qs=qs)
    return render(request, "aristotle_mdr/actions/supersedeItem.html", {"item": item, "form": form})


def deprecate(request, iid):
    item = get_object_or_404(MDR._concept, pk=iid).item
    if not (item and user_can_edit(request.user, item)):
        if request.user.is_anonymous():
            return redirect(reverse('friendly_login') + '?next=%s' % request.path)
        else:
            raise PermissionDenied
    qs=item.__class__.objects.filter().editable(request.user)
    if request.method == 'POST':  # If the form has been submitted...
        form = MDRForms.DeprecateForm(request.POST, user=request.user, item=item, qs=qs)  # A form bound to the POST data
        if form.is_valid():
            # Check use the itemset as there are permissions issues and we want to remove some:
            #  Everything that was superseded, but isn't in the returned set
            #  Everything that was in the returned set, but isn't already superseded
            #  Everything left over can stay the same, as its already superseded
            #    or wasn't superseded and is staying that way.
            with transaction.atomic(), reversion.revisions.create_revision():
                reversion.revisions.set_user(request.user)
                for i in item.supersedes.all():
                    if i not in form.cleaned_data['olderItems'] and user_can_edit(request.user, i):
                        item.supersedes.remove(i)
                for i in form.cleaned_data['olderItems']:
                    if user_can_edit(request.user, i):  # Would check item.supersedes but its a set
                        kwargs = {}
                        if django_version > (1, 9):
                            kwargs = {'bulk': False}
                        item.supersedes.add(i, **kwargs)
            return HttpResponseRedirect(url_slugify_concept(item))
    else:
        form = MDRForms.DeprecateForm(user=request.user, item=item, qs=qs)
    return render(request, "aristotle_mdr/actions/deprecateItems.html", {"item": item, "form": form})


def extensions(request):
    content=[]
    aristotle_apps = fetch_aristotle_settings().get('CONTENT_EXTENSIONS', [])

    if aristotle_apps:
        for app_label in aristotle_apps:
            app=apps.get_app_config(app_label)
            try:
                app.about_url = reverse('%s:about' % app_label)
            except:
                pass  # if there is no about URL, thats ok.
            content.append(app)

    content = list(set(content))
    aristotle_downloads = getattr(settings, 'ARISTOTLE_DOWNLOADS', [])
    downloads=dict()
    if aristotle_downloads:
        for download in aristotle_downloads:
            app_label = download[3]
            app_details = downloads.get(
                app_label,
                {'app': apps.get_app_config(app_label), 'downloads': []}
            )
            try:
                app_details['about_url'] = reverse('%s:about' % app_label)
            except:
                pass  # if there is no about URL, thats ok.
            app_details['downloads'].append(download)
            downloads[app_label]=app_details

    return render(
        request,
        "aristotle_mdr/static/extensions.html",
        {'content_extensions': content, 'download_extensions': downloads, }
    )


# Search views

class PermissionSearchView(FacetedSearchView):
    def build_form(self):
        form = super(self.__class__, self).build_form()
        form.request = self.request
        form.request.GET = self.clean_facets(self.request)
        return form

    def clean_facets(self, request):
        get = request.GET.copy()
        for k, val in get.items():
            if k.startswith('f__'):
                get.pop(k)
                k = k[4:]
                get.update({'f': '%s::%s' % (k, val)})
        return get
