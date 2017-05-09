from aristotle_mdr.utils import get_download_template_path_for_item
import cgi

try:  # Python 2
    from cStringIO import StringIO as BytesIO
except:  # Python 3
    from io import BytesIO


from django.http import HttpResponse, Http404
# from django.shortcuts import render
from django.template.loader import select_template
from django.template import Context
from django.utils.safestring import mark_safe

import xhtml2pdf.pisa as pisa
import csv
from aristotle_mdr.contrib.help.models import ConceptHelp


item_register = {
    'csv': {'aristotle_mdr': ['valuedomain']},
    'pdf': '__template__'
}


def render_to_pdf(template_src, context_dict, debug_as_html=False):
    # If the request template doesnt exist, we will give a default one.
    template = select_template([
        template_src,
        'aristotle_mdr/downloads/pdf/managedContent.html'
    ])
    context = Context(context_dict)
    html = template.render(context)

    if debug_as_html:
        return HttpResponse(html)
    result = BytesIO()
    pdf = pisa.pisaDocument(
        BytesIO(html.encode("UTF-8")),
        result,
        encoding='UTF-8'
    )
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    return HttpResponse('We had some errors<pre>%s</pre>' % cgi.escape(html))


def download(request, download_type, item):
    """Built in download method"""
    template = get_download_template_path_for_item(item, download_type)
    from django.conf import settings
    page_size = getattr(settings, 'PDF_PAGE_SIZE', "A4")
    if download_type == "pdf":
        subItems = item.get_download_items()
        return render_to_pdf(
            template,
            {
                'item': item,
                'subitems': subItems,
                'tableOfContents': len(subItems) > 0,
                'view': request.GET.get('view', '').lower(),
                'pagesize': request.GET.get('pagesize', page_size),
                'request': request,
            }
        )

    elif download_type == "csv-vd":
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s.csv"' % (
            item.name
        )

        writer = csv.writer(response)
        writer.writerow(['value', 'meaning', 'start date', 'end date', 'role'])
        for v in item.permissibleValues.all():
            writer.writerow(
                [v.value, v.meaning, v.start_date, v.end_date, "permissible"]
            )
        for v in item.supplementaryValues.all():
            writer.writerow(
                [v.value, v.meaning, v.start_date, v.end_date, "supplementary"]
            )

        return response


def items_for_bulk_download(items, request):
    iids = {}
    item_querysets = {}  # {PythonClass:{help:ConceptHelp,qs:Queryset}}
    for item in items:
        if item and item.can_view(request.user):
            if item.__class__ not in iids.keys():
                iids[item.__class__] = []
            iids[item.__class__].append(item.pk)

            for metadata_type, qs in item.get_download_items():
                if metadata_type not in item_querysets.keys():
                    item_querysets[metadata_type] = {'help': None, 'qs': qs}
                else:
                    item_querysets[metadata_type]['qs'] |= qs

    for metadata_type, ids_set in iids.items():
        query = metadata_type.objects.filter(pk__in=ids_set)
        if metadata_type not in item_querysets.keys():
            item_querysets[metadata_type] = {'help': None, 'qs': query}
        else:
            item_querysets[metadata_type]['qs'] |= query

    for metadata_type in item_querysets.keys():
        item_querysets[metadata_type]['qs'] = item_querysets[metadata_type]['qs'].distinct().visible(request.user)
        item_querysets[metadata_type]['help'] = ConceptHelp.objects.filter(
            app_label=metadata_type._meta.app_label,
            concept_type=metadata_type._meta.model_name
        ).first()

    return item_querysets


def bulk_download(request, download_type, items, title=None, subtitle=None):
    """Built in download method"""
    template = 'aristotle_mdr/downloads/pdf/bulk_download.html'  # %(download_type)
    from django.conf import settings
    page_size = getattr(settings, 'PDF_PAGE_SIZE', "A4")

    item_querysets = items_for_bulk_download(items, request)

    if title is None:
        if request.GET.get('title', None):
            title = request.GET.get('title')
        else:
            title = "Auto-generated document"

    if subtitle is None:
        if request.GET.get('subtitle', None):
            subtitle = request.GET.get('subtitle')
        else:
            _list = "<li>" + "</li><li>".join([item.name for item in items if item]) + "</li>"
            subtitle = mark_safe("Generated from the following metadata items:<ul>%s<ul>" % _list)

    if download_type == "pdf":
        subItems = []

        debug_as_html = bool(request.GET.get('html', ''))

        return render_to_pdf(
            template,
            {
                'title': title,
                'subtitle': subtitle,
                'items': items,
                'included_items': sorted(
                    [(k, v) for k, v in item_querysets.items()],
                    key=lambda k_v: k_v[0]._meta.model_name
                ),
                'pagesize': request.GET.get('pagesize', page_size),
            },
            debug_as_html=debug_as_html
        )
