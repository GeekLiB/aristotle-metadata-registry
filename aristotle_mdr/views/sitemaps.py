from __future__ import division
from django.shortcuts import render
from aristotle_mdr import models as MDR


def main(request):
    count = MDR._concept.objects.public().count()
    list_range = range(1 + count // 1000)
    return render(request, "meta/sitemaps/main.xml", {'range_list': list_range}, content_type='text/xml')


def page_range(request, page):
    i = int(page)
    items = MDR._concept.objects.public()[i * 1000:(i + 1) * 1000]
    return render(request, "meta/sitemaps/page.xml", {'items': items}, content_type='text/xml')
