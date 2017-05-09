from django.apps import apps
from django.http import Http404
from django.shortcuts import redirect

from aristotle_mdr.models import _concept
from aristotle_mdr.utils import url_slugify_concept


def scoped_identifier_redirect(request, ns_prefix, iid):
    objs = _concept.objects.filter(
        identifiers__namespace__shorthand_prefix=ns_prefix,
        identifiers__identifier=iid,
    )
    if request.GET.get('v', None):
        v = request.GET.get('v')
        objs = objs.filter(
            identifiers__version=v
        )

    if objs.count() == 0:
        raise Http404
    elif objs.count() == 1:
        return redirect(url_slugify_concept(objs.first().item))
    else:
        item = objs.order_by('version').last()  # lets hope there is an order to the versions.
        return redirect(url_slugify_concept(item.item))
