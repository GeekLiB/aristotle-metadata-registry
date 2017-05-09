from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import render, redirect, get_object_or_404
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

import reversion

from aristotle_mdr.utils import cache_per_item_user, concept_to_dict, construct_change_message, url_slugify_concept
from aristotle_mdr import forms as MDRForms
from aristotle_mdr import models as MDR
from aristotle_mdr import perms


def compare_concepts(request, obj_type=None):
    comparison = {}
    item_a = request.GET.get('item_a', None)
    item_b = request.GET.get('item_b', None)

    context = {"item_a": item_a, "item_b": item_b}

    item_a = MDR._concept.objects.visible(request.user).filter(pk=item_a).first()  # .item
    item_b = MDR._concept.objects.visible(request.user).filter(pk=item_b).first()  # .item
    context = {"item_a": item_a, "item_b": item_b}

    request.GET = request.GET.copy()

    if item_a:
        item_a = item_a.item
    else:
        request.GET['item_a']="0"
    if item_b:
        item_b = item_b.item
    else:
        request.GET['item_b']="0"

    qs = MDR._concept.objects.visible(request.user)
    form = MDRForms.CompareConceptsForm(request.GET, user=request.user, qs=qs)  # A form bound to the POST data
    if form.is_valid():
        from django.contrib.contenttypes.models import ContentType

        revs=[]
        for item in [item_a, item_b]:
            from reversion.models import Version
            versions = Version.objects.get_for_object(item)
            ct = ContentType.objects.get_for_model(item)
            version = reversion.models.Version.objects.filter(content_type=ct, object_id=item.pk).order_by('-revision__date_created').first()
            revs.append(version)
        if revs[0] is None:
            form.add_error('item_a', _('This item has no revisions. A comparison cannot be made'))
        if revs[1] is None:
            form.add_error('item_b', _('This item has no revisions. A comparison cannot be made'))
        if revs[0] is not None and revs[1] is not None:
            comparator_a_to_b = item_a.comparator()
            comparator_b_to_a = item_b.comparator()
            version1 = revs[0]
            version2 = revs[1]

            compare_data_a, has_unfollowed_fields_a = comparator_a_to_b.compare(item_a, version2, version1)
            compare_data_b, has_unfollowed_fields_b = comparator_b_to_a.compare(item_a, version1, version2)

            has_unfollowed = has_unfollowed_fields_a or has_unfollowed_fields_b

            context.update({'debug': {'cmp_a': compare_data_a}})
            comparison = {}
            for field_diff_a in compare_data_a:
                name = field_diff_a['field'].name
                x = comparison.get(name, {})
                x['field'] = field_diff_a['field']
                x['a'] = field_diff_a['diff']
                comparison[name] = x
            for field_diff_b in compare_data_b:
                name = field_diff_b['field'].name
                comparison.get(name, {})['b'] = field_diff_b['diff']

            same = {}
            for f in item_a._meta.fields:
                if f.name not in comparison.keys():
                    same[f.name] = {'field': f, 'value': getattr(item_a, f.name)}
                if f.name.startswith('_'):
                    # hidden field
                    comparison.pop(f.name, None)
                    same.pop(f.name, None)

            hidden_fields = ['workgroup', 'created', 'modified', 'id', 'submitter', 'statuses']
            for h in hidden_fields:
                comparison.pop(h, None)
                same.pop(h, None)

            only_a = {}
            for f in item_a._meta.fields:
                if (f not in item_b._meta.fields and f not in comparison.keys() and f not in same.keys() and f.name not in hidden_fields):
                    only_a[f.name] = {'field': f, 'value': getattr(item_a, f.name)}

            only_b = {}
            for f in item_b._meta.fields:
                if (f not in item_a._meta.fields and f not in comparison.keys() and f not in same.keys() and f.name not in hidden_fields):
                    only_b[f.name] = {'field': f, 'value': getattr(item_b, f.name)}

            comparison = sorted(comparison.items())
            context.update({
                "comparison": comparison,
                "same": same,
                "only_a": only_a,
                "only_b": only_b,
            })
    context.update({"form": form})
    # comparison = {'a': compare_data_a, 'b': compare_data_b}
    return render(request, "aristotle_mdr/actions/compare/compare_items.html", context)
