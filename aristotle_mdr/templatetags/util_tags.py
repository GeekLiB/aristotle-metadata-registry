from django import template
from django.conf import settings
from django.core.urlresolvers import reverse, resolve


register = template.Library()


@register.filter
def order_by(qs, order):
    return qs.order_by(*(order.split(",")))


@register.filter
def startswith(string, substr):
    return string.startswith(substr)


@register.filter
def visible_count(model, user):
    return model.objects.all().visible(user).count()


@register.filter
def izip(a, b):
    return zip(a, b)
