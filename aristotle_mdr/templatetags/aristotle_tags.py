# -*- coding: utf-8 -*-
"""
Tags and filters available in aristotle templates
=================================================

A number of convenience tags are available for performing common actions in custom
templates.

Include the aristotle template tags in every template that uses them, like so::

    {% load aristotle_tags %}

Available tags and filters
--------------------------
"""
from django import template
from django.conf import settings
from django.core.urlresolvers import reverse, resolve
from django.template.defaultfilters import slugify
from django.utils.translation import ugettext_lazy as _
from django.utils.html import mark_safe

from aristotle_mdr import perms
import aristotle_mdr.models as MDR

register = template.Library()


@register.filter
def can_alter_comment(user, comment):
    try:
        return perms.user_can_alter_comment(user, comment)
    except:
        return False


@register.filter
def can_alter_post(user, post):
    try:
        return perms.user_can_alter_post(user, post)
    except:
        return False


@register.filter
def is_in(item, iterable):
    return item in iterable


@register.filter
def is_installed_app(app_name):
    return app_name in settings.INSTALLED_APPS


@register.filter
def in_workgroup(user, workgroup):
    """
    A filter that acts as a wrapper around ``aristotle_mdr.perms.user_in_workgroup``.
    Returns true if the user has permission to administer the workgroup, otherwise it returns False.
    If calling ``user_in_workgroup`` throws an exception it safely returns False.

    For example::

      {% if request.user|in_workgroup:workgroup %}
        {{ something }}
      {% endif %}
    """
    try:
        return perms.user_in_workgroup(user, workgroup)
    except:
        return False


@register.filter
def can_edit(item, user):
    """
    A filter that acts as a wrapper around ``aristotle_mdr.perms.user_can_edit``.
    Returns true if the user has permission to edit the item, otherwise it returns False.
    If calling ``user_can_edit`` throws an exception it safely returns False.

    For example::

      {% if myItem|can_edit:request.user %}
        {{ item }}
      {% endif %}
    """
    # return perms.user_can_edit(user, item)
    try:
        return perms.user_can_edit(user, item)
    except:  # pragma: no cover -- passing a bad item or user is the template authors fault
        return None


@register.filter
def can_view(item, user):
    """
    A filter that acts as a wrapper around ``aristotle_mdr.perms.user_can_view``.
    Returns true if the user has permission to view the item, otherwise it returns False.
    If calling ``user_can_view`` throws an exception it safely returns False.

    For example::

      {% if myItem|can_view:request.user %}
        {{ item }}
      {% endif %}
    """
    return perms.user_can_view(user, item)


@register.filter
def can_view_iter(qs, user):
    """
    A filter that is a simple wrapper that applies the ``aristotle_mdr.models.ConceptManager.visible(user)``
    for use in templates. Filtering on a Django ``Queryset`` and passing in the current
    user as the argument returns a list (not a ``Queryset`` at this stage) of only
    the items from the ``Queryset`` the user can view.

    If calling ``can_view_iter`` throws an exception it safely returns an empty list.

    For example::

        {% for item in myItems|can_view_iter:request.user %}
          {{ item }}
        {% endfor %}
    """
    try:
        return qs.visible(user)
    except:  # pragma: no cover -- passing a bad queryset is the template authors fault
        return []


@register.filter
def public_standards(regAuth, itemType="aristotle_mdr._concept"):
    """
    This is a filter that accepts a registration Authority and an item type and returns
    a list of tuples that contain all *public* items with a status of "Standard" or
    "Preferred Standard" *in that Registration Authority only*, as well as a the
    status object for that Authority.

    The item type should consist of the name of the app the item is from and the
    name of the item itself separated by a period (``.``).

    This requires the django ``django.contrib.contenttypes`` app is installed.

    If calling ``public_standards`` throws an exception or the item type requested
    is not found it safely returns an empty list.

    For example::

        {% for item, status in registrationAuthority|public_standards:'aristotle_mdr.DataElement' %}
          {{ item }} - made standard on {{ status.registrationDate }}.
        {% endfor %}
    """
    try:
        from django.contrib.contenttypes.models import ContentType
        app_label, model_name=itemType.lower().split('.', 1)[0:2]
        standard_states = [MDR.STATES.standard, MDR.STATES.preferred]
        return [
            (i, i.statuses.filter(registrationAuthority=regAuth, state__in=standard_states).first())
            for i in ContentType.objects.get(app_label=app_label, model=model_name).model_class().objects.filter(statuses__registrationAuthority=regAuth, statuses__state__in=standard_states).public()
        ]
    except:
        return []


@register.simple_tag
def paginator_get(request, pageNumber, pop=''):
    # http://stackoverflow.com/questions/2047622/how-to-paginate-django-with-other-get-variables
    dict_ = request.GET.copy()
    for p in pop.split(','):
        dict_.pop(p, None)
    dict_['page'] = pageNumber
    return dict_.urlencode()


@register.simple_tag
def ifeq(a, b, val):
    return val if a == b else ""


@register.simple_tag
def ternary(condition, a, b):
    """
    A simple ternary tag - it beats verbose if/else tags in templates for simple strings
    If the ``condition`` is 'truthy' return ``a`` otherwise return ``b``. For example::

        <a class="{% ternary item.is_public 'public' 'private' %}">{{item.name}}</a>
    """
    if condition:
        return a
    else:
        return b


@register.filter
def paginator_range(page, mode):
    page_range = list(page.paginator.page_range)
    if mode=="start":
        if page.number <= 5:
            # show 4,5,6 if page is 4, 5,6,7 if page is 5...
            return page_range[:max(5, page.number + 2)]
        else:
            return page_range[:3]
    if mode=="middle":
        if page.number > 5 and page.number < page.paginator.num_pages - 5:
            return page_range[page.number - 3:page.number + 2]
    if mode=="end":
        if page.number > page.paginator.num_pages - 5:
            return page_range[-5:]
        else:
            return page_range[-1:]


@register.filter
def stateToText(state):
    # @register.simple_tag
    """
    This tag takes the integer value of a state for a registration status and
    converts it to its text equivilent.
    """
    return MDR.STATES[int(state)]


@register.filter
def unique_recent(recent):
    seen = []
    out = []
    for item in recent:
        if item._model and item.object and item.object.id not in seen:
            seen.append(item.object.id)
            out.append(item)
    return out


@register.simple_tag
def zws(string):
    # Adds a zerowidth space before an em-dash
    """
    ``zws`` or "zero width space" is used to insert a soft break near em-dashed.
    Since em-dashs are commonly used in Data Element Concept names, this helps them wrap
    in the right places.

    For example::

        <h1>{% zws item.name %}</h1>

    """
    import sys  # Python 2
    if sys.version_info[0] == 2:
        string = string.encode('utf-8', 'xmlcharrefreplace')
    return string.replace("—", "&shy;—")


@register.simple_tag
def adminEdit(item):
    """
    A tag for easily generating the link to an admin page for editing an item. For example::

        <a href="{% adminEdit item %}">Advanced editor for {{item.name}}</a>
    """
    app_name = item._meta.app_label
    return reverse("admin:%s_%s_change" % (app_name, item._meta.model_name), args=[item.id])


@register.simple_tag
def clone(item):
    """
    A tag for easily generating the link to an admin page for "cloning" an item. For example::

        <a href="{% clone item %}">Clone {{item.name}}</a>
    """
    app_name = item._meta.app_label
    return reverse("admin:%s_%s_add" % (app_name, item._meta.model_name)) + "?clone=%s" % item.id


@register.simple_tag
def historyLink(item):
    """
    A tag for easily generating the link to an admin page for "cloning" an item. For example::

        <a href="{% clone item %}">Clone {{item.name}}</a>
    """
    app_name = item._meta.app_label
    return reverse("admin:%s_%s_history" % (app_name, item._meta.model_name), args=[item.id])


@register.simple_tag
def downloadMenu(item):
    """
    Returns the complete download menu for a partcular item. It accepts the id of
    the item to make a download menu for, and the id must be of an item that can be downloaded,
    otherwise the links will show, but not work.

    For example::

        {% downloadMenu item %}
    """
    from django.template.loader import get_template
    from django.template import Context
    downloadOpts = getattr(settings, 'ARISTOTLE_DOWNLOADS', "")
    from aristotle_mdr.utils import get_download_template_path_for_item
    from aristotle_mdr.utils.downloads import get_download_module

    downloadsForItem = []
    app_label = item._meta.app_label
    model_name = item._meta.model_name
    for d in downloadOpts:
        download_type = d[0]
        module_name = d[3]
        downloader = get_download_module(module_name)
        item_register = getattr(downloader, 'item_register', {})

        dl = item_register.get(download_type, {})
        if type(dl) is not str:
            if dl.get(app_label, []) == '__all__':
                downloadsForItem.append(d)
            elif model_name in dl.get(app_label, []):
                downloadsForItem.append(d)
        else:
            if dl == '__all__':
                downloadsForItem.append(d)
            elif dl == '__template__':
                try:
                    get_template(get_download_template_path_for_item(item, download_type))
                    downloadsForItem.append(d)
                except template.TemplateDoesNotExist:
                    pass  # This is ok.
                except:
                    pass  # Something very bad has happened in the template.
    return get_template("aristotle_mdr/helpers/downloadMenu.html").render(
        Context({'item': item, 'download_options': downloadsForItem, })
        )


@register.simple_tag
def extra_content(extension, item, user):
    try:
        from django.template.loader import get_template
        from django.template import Context
        s = item._meta.object_name
        s = s[0].lower() + s[1:]

        return get_template(extension + "/extra_content/" + s + ".html").render(
            Context({'item': item, 'user': user})
        )
    except template.TemplateDoesNotExist:
        # there is no extra content for this item, and thats ok.
        return ""


@register.simple_tag
def bootstrap_modal(_id, size=None):
    size_class = ""
    if size == 'lg':
        size_class = "modal-lg"
    elif size == 'sm':
        size_class = "modal-sm"

    modal = '<div id="%s" class="modal fade"><div class="modal-dialog %s"><div class="modal-content"></div></div></div>'
    return mark_safe(modal % (_id, size_class))


@register.simple_tag
def doc(item, field=None):
    """Gets the appropriate help text or docstring for a model or field.
    Accepts 1 or 2 string arguments:
    If 1, returns the docstring for the given model in the specified app.
    If 2, returns the help_text for the field on the given model in the specified app.
    """

    from django.contrib.contenttypes.models import ContentType
    from aristotle_mdr.utils.doc_parse import parse_rst, parse_docstring

    ct = item
    if field is None:
        model_name = ct._meta.model_name
        title, body, metadata = parse_docstring(ct.__doc__)
        if title:
            title = parse_rst(title, 'model', _('model:') + model_name)
        if body:
            body = parse_rst(body, 'model', _('model:') + model_name)
        return title
    else:
        if ct._meta.get_field(field).help_text:
            return _(ct._meta.get_field(field).help_text)
        else:
            # return _("No help text for the field '%(field)s' found on the model '%(model)s' in the app '%(app)s'") % {'app':app_label,'model':model_name,'field':field}
            return _("No help text for the field '%(field)s' found for the model '%(model)s'") % {'model': item.get_verbose_name(), 'field': field}


@register.filter
def can_use_action(user, bulk_action, *args):
    from aristotle_mdr.views.bulk_actions import get_bulk_actions
    bulk_action = get_bulk_actions().get(bulk_action)
    return bulk_action['can_use'](user)


@register.filter
def template_path(item, _type):
    from aristotle_mdr.utils import get_download_template_path_for_item
    _type, subpath=_type.split(',')
    return get_download_template_path_for_item(item, _type, subpath)


@register.filter
def visibility_text(item):
    visibility = _("hidden")
    if item._is_locked:
        visibility = _("locked")
    if item._is_public:
        visibility = _("public")
    return visibility
