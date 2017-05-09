# -*- coding: utf-8 -*-
"""
Search filters and tags available in aristotle templates
--------------------------------------------------------

A number of convenience tags are available for performing actions only used by
search engine pages.

Include the aristotle search template tags in every template that uses them, like so::

    {% load aristotle_search_tags %}

"""
from django import template
from django.core.urlresolvers import reverse, resolve
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from aristotle_mdr import perms
import aristotle_mdr.models as MDR
import logging


register = template.Library()


logger = logging.getLogger(__name__)
logger.debug("Logging started for " + __name__)


@register.simple_tag
def search_describe_filters(search_form):
    """
    Takes a search form and returns a user friendly
    textual description of the filters.
    """

    out = ""
    if search_form.applied_filters:
        filter_texts = []
        for f in search_form.applied_filters:
            val = search_form.cleaned_data.get(f)
            field = search_form.fields.get(f)

            if field.label is None:
                continue
            if hasattr(field, 'choices'):
                preamble = _('%s is') % field.label
                try:
                    choices = dict(field.choices)
                    opts = [choices[x] for x in val]
                except KeyError:
                    choices = dict([(str(k), v) for k, v in field.choices])
                    opts = [choices[x] for x in val]

                if len(opts) > 1:
                    verbed = ", ".join([str(o) for o in opts][:-1])
                    verbed += _(' or %s') % str(opts[-1])
                else:
                    verbed = str(opts[0])
                filter_texts.append('%s %s' % (preamble, verbed))
            else:
                preamble = _('%s is') % field.label
                verbed = str(val)
                filter_texts.append('%s %s' % (preamble, verbed))
        if len(filter_texts) > 1:
            out = "; ".join([str(o) for o in filter_texts][:-1])
            out += _(' and %s') % str(filter_texts[-1])
        elif len(filter_texts) == 1:
            out = str(filter_texts[0])

    return out


@register.filter
def get_item_from_facet(_type, _id):
    from django.contrib.contenttypes.models import ContentType

    model_type = {
        'ra': MDR.RegistrationAuthority,
        'wg': MDR.Workgroup,
        'ct': ContentType,
    }.get(_type, None)

    item = None

    if model_type and _id:
        # Related to https://github.com/aristotle-mdr/aristotle-metadata-registry/pull/343
        # This fails sometimes on Postgres in *tests only*... so far.
        item = model_type.objects.filter(pk=int(_id)).first()
        if item is None:
            logger.warning(
                "Warning: Failed to find item type [%s] with id [%s]" % (model_type, _id)
            )
            item = {
                'name': 'None',
                'id': _id
            }
    return item


@register.filter
def search_state_to_text(state):
    try:
        return MDR.STATES[int(state)]
    except:
        # KeyError, TypeError:
        return _('Not registered')


@register.filter
def restriction_to_text(state):
    from aristotle_mdr.search_indexes import RESTRICTION
    return RESTRICTION[state]


@register.filter
def first_letters(string):
    return ''.join(s[0].upper() for s in string.split(" "))


@register.simple_tag
def facet_display(details, val):
    if details.get('display', None):
        return details['display'](val)
    else:
        return val


@register.simple_tag
def unfacet(request, field, value):
    # http://stackoverflow.com/questions/2047622/how-to-paginate-django-with-other-get-variables
    dict_ = request.GET.copy()
    if 'f' in dict_.keys():
        f = dict_.getlist('f')
        facet = '%s::%s' % (field, value)
        if facet in f:
            f.remove(facet)
            dict_.setlist('f', f)

    return dict_.urlencode()
