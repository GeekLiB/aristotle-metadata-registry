from django import template
from django.core.urlresolvers import reverse, resolve
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _

from aristotle_mdr.models import _concept
from aristotle_mdr.contrib.slots.models import Slot, concepts_with_similar_slots


register = template.Library()


@register.simple_tag
def count_similar(user, slot):
    return concepts_with_similar_slots(user, slot=slot).count()


@register.filter
def slots_by_type(concept, name):
    return concept.slots.filter(name=name)
